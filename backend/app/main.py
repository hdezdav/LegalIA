"""FastAPI application factory and wiring.

Kept thin: configuration lives in `app.core.config`, routes in
`app.api.routes`, and business logic in `app.services`. This module only
assembles them and installs cross-cutting middleware.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging import bind_request_id, configure_logging, get_logger
from app.db.session import check_database, check_pgvector, engine

logger = get_logger(__name__)

# Header used to propagate a request id in from Caddy or LibreChat, and back out
# on every response so a user-reported problem can be traced without content.
REQUEST_ID_HEADER = "X-Request-ID"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Verify dependencies at boot, dispose the pool at shutdown.

    Connectivity failures are logged but do not abort startup: the health
    endpoint must stay reachable to report *why* the system is unhealthy, which
    is more useful than a container that crash-loops before it can answer.
    """
    configure_logging()
    logger.info(
        "starting",
        extra={
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_dimension": settings.embedding_dimension,
            "reranker_provider": settings.RERANKER_PROVIDER,
            "llm_model": settings.ANTHROPIC_MODEL,
            "verification_mode": settings.VERIFICATION_MODE,
        },
    )

    if not check_database():
        logger.error("database unreachable at startup")
    elif not check_pgvector():
        logger.error("pgvector extension unavailable at startup")

    yield

    engine.dispose()
    logger.info("stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Legal retrieval and verification system for Colombian law. "
            "Answers are grounded in retrieved sources; when the corpus holds "
            "insufficient evidence, the system declines to answer."
        ),
        lifespan=lifespan,
        # Interactive docs are useful in development and an unnecessary surface
        # in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # CORS: allow_credentials requires explicit origins (not "*")
    # In production, CORS_ORIGINS must list only the actual frontend domain
    cors_origins = settings.cors_origin_list
    if settings.is_production and "*" in cors_origins:
        logger.warning(
            "CORS wildcard (*) with credentials is insecure in production. "
            "Set CORS_ORIGINS to explicit domains."
        )
        cors_origins = []  # Fail closed: deny all CORS in production with wildcard

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )

    _install_middleware(app)
    _install_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


def _install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Bind a request id and log one line per request.

        The log line carries method, route template, status and duration. Never
        the full path or query string: a legal question can end up in either.
        """
        request_id = bind_request_id(request.headers.get(REQUEST_ID_HEADER))
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            # exc_info without the message: the traceback is safe, an exception
            # string may quote the offending input.
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "route": _route_template(request),
                    "latency_ms": elapsed_ms,
                },
            )
            raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers[REQUEST_ID_HEADER] = request_id

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        logger.info(
            "request",
            extra={
                "method": request.method,
                "route": _route_template(request),
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )
        return response


def _route_template(request: Request) -> str:
    """The matched route pattern, e.g. `/api/v1/documents/{document_id}`.

    Preferred over `request.url.path` so path parameters (which may identify a
    private document) never reach the logs.
    """
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def _install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """422 with field locations but without echoed input.

        FastAPI's default handler includes the rejected value, which would put
        user content into an error body and, from there, into client logs.
        """
        errors = [
            {"field": ".".join(str(p) for p in err["loc"]), "error": err["msg"]}
            for err in exc.errors()
        ]
        logger.info("validation error", extra={"error_count": len(errors)})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Request validation failed", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
        """Generic 500. The class name is logged; nothing is returned to the client."""
        logger.error(
            "unhandled exception", extra={"error_type": type(exc).__name__}, exc_info=exc
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


app = create_app()

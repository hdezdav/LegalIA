"""Health endpoint.

Unauthenticated on purpose: Caddy, Docker and any external monitor need it
before a token exists. It therefore reveals configuration *shape* (which
provider is active, which model) but never credentials.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.db.session import check_database, check_pgvector, check_text_search_config
from app.schemas.health import ComponentStatus, HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health",
    responses={503: {"model": HealthResponse, "description": "A dependency is down"}},
)
def health(response: Response) -> HealthResponse:
    """Report per-dependency health.

    Returns 503 when a hard dependency (database, pgvector) is down, so probes
    can rely on the status code alone. A missing `legal_es` configuration is
    reported as degraded rather than fatal: retrieval still works, semantic-only.
    """
    database_ok = check_database()
    # Both extension checks need a working connection; skip them when the
    # database itself is unreachable rather than reporting two derived failures.
    pgvector_ok = check_pgvector() if database_ok else False
    text_search_ok = check_text_search_config() if database_ok else False

    failures: list[str] = []
    if not database_ok:
        failures.append("database")
    if not pgvector_ok:
        failures.append("pgvector")

    degraded: list[str] = []
    if database_ok and not text_search_ok:
        degraded.append("text_search")

    if failures:
        overall = ComponentStatus.ERROR
        detail = f"unavailable: {', '.join(failures)}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif degraded:
        overall = ComponentStatus.DEGRADED
        detail = (
            f"degraded: {', '.join(degraded)} "
            "(lexical retrieval unavailable, semantic search still works)"
        )
    else:
        overall = ComponentStatus.OK
        detail = None

    return HealthResponse(
        status=overall,
        database=ComponentStatus.OK if database_ok else ComponentStatus.ERROR,
        pgvector=ComponentStatus.OK if pgvector_ok else ComponentStatus.ERROR,
        text_search=(
            ComponentStatus.OK if text_search_ok else ComponentStatus.DEGRADED
        ),
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_dimension=settings.embedding_dimension,
        reranker_provider=settings.RERANKER_PROVIDER,
        llm_model=settings.ANTHROPIC_MODEL,
        detail=detail,
    )

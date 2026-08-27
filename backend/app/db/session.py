"""Engine, session factory and the FastAPI session dependency.

Sync SQLAlchemy on purpose. The pipeline's latency is dominated by three
external HTTP calls (embeddings, reranker, Anthropic), not by database
round-trips, and pgvector plus `psycopg` behave identically either way. A sync
session also keeps the ingestion CLI and the test suite free of an event loop.
Route handlers that do I/O are `async def` and hand DB work to threadpool-backed
dependencies via `Depends`.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _create_engine() -> Engine:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        # Recycle before typical idle-connection timeouts, and check liveness on
        # checkout: the API keeps connections open across long idle periods and
        # a restarted Postgres must not surface as a 500 on the next request.
        pool_recycle=1800,
        pool_pre_ping=True,
        # Server-side statement timeout: a pathological vector scan cannot hold
        # a worker forever. Generous enough for HNSW search over the MVP corpus.
        connect_args={"options": "-c statement_timeout=30000"},
    )

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection: Any, _record: Any) -> None:
        """Teach psycopg about pgvector on every new connection.

        Without this, `Vector` columns round-trip as strings and cosine distance
        comparisons silently stop working.
        """
        from pgvector.psycopg import register_vector

        register_vector(dbapi_connection)

    return engine


engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    # Attributes stay readable after commit, so a handler can serialize a model
    # it just wrote without a second SELECT.
    expire_on_commit=False,
    class_=Session,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional session.

    Commits on success, rolls back on any exception. Handlers therefore never
    call `commit()` themselves, which keeps a request's writes atomic: a failure
    during verification cannot leave a message row without its citations.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database() -> bool:
    """True when a trivial query succeeds. Used by the health endpoint."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("database check failed", extra={"error_type": type(exc).__name__})
        return False


def check_pgvector() -> bool:
    """True when the vector extension is installed and usable.

    Exercises an actual distance operation rather than only reading
    `pg_extension`: a present-but-broken extension would otherwise pass.
    """
    try:
        with engine.connect() as connection:
            installed = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            if not installed:
                return False
            connection.execute(
                text("SELECT '[1,0]'::vector <=> '[0,1]'::vector")
            )
        return True
    except Exception as exc:
        logger.warning("pgvector check failed", extra={"error_type": type(exc).__name__})
        return False


def check_text_search_config() -> bool:
    """True when the `legal_es` FTS configuration exists.

    The lexical half of hybrid retrieval depends on it; if bootstrap did not run,
    retrieval degrades to semantic-only and that must be visible.
    """
    try:
        with engine.connect() as connection:
            found = connection.execute(
                text("SELECT 1 FROM pg_ts_config WHERE cfgname = 'legal_es'")
            ).scalar()
        return bool(found)
    except Exception as exc:
        logger.warning(
            "text search config check failed", extra={"error_type": type(exc).__name__}
        )
        return False

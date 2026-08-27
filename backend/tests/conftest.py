"""Shared test fixtures.

Two rules this suite holds to, from sections 37 and 43 of the brief:

1. No external API is ever called. Provider tests run against mock providers or
   stubbed transports.
2. Tests that need a real database are skipped, not faked, when none is
   reachable. A skipped integration test is honest; an in-memory SQLite stand-in
   would silently stop exercising pgvector, generated columns and native enums,
   which is most of what the schema is for.

Set TEST_DATABASE_URL to run the database-backed tests:

    TEST_DATABASE_URL=postgresql://legalia:legalia@localhost:5432/legalia_test
"""

from __future__ import annotations

import os
from collections.abc import Generator, Iterator

import pytest

# Must be set before app.core.config is imported: Settings reads the environment
# at construction time, and the cached instance is created on first import.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("RERANKER_PROVIDER", "mock")
os.environ.setdefault("VERIFICATION_MODE", "heuristic")
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-outside-tests")
os.environ.setdefault("LOG_FORMAT", "console")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


# --- Application ------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    """Synchronous test client. Runs lifespan, so startup checks execute."""
    with TestClient(app) as test_client:
        yield test_client


# --- Database ---------------------------------------------------------------


def _normalize(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Engine against TEST_DATABASE_URL, with the schema created from metadata.

    Skips the whole test if the database is unreachable, so `pytest` passes on a
    laptop with no Postgres while still exercising the real schema in CI and in
    the container.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set; database tests skipped")

    engine = create_engine(_normalize(TEST_DATABASE_URL), poolclass=None)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"test database unreachable: {type(exc).__name__}")

    from pgvector.psycopg import register_vector
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _register(dbapi_connection, _record):  # type: ignore[no-untyped-def]
        register_vector(dbapi_connection)

    _bootstrap(engine)

    from app.db.base import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


def _bootstrap(engine: Engine) -> None:
    """Create extensions and `legal_es`, mirroring container bootstrap.

    chunks.content_tsv is a generated column referencing legal_es, so
    create_all() fails outright without this.
    """
    with engine.begin() as connection:
        for extension in ("vector", "pg_trgm", "unaccent", "pgcrypto"):
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_ts_config WHERE cfgname = 'legal_es'
                    ) THEN
                        CREATE TEXT SEARCH CONFIGURATION legal_es (COPY = spanish);
                        ALTER TEXT SEARCH CONFIGURATION legal_es
                            ALTER MAPPING FOR asciiword, asciihword,
                                              hword_asciipart, word, hword,
                                              hword_part
                            WITH unaccent, spanish_stem;
                    END IF;
                END
                $$;
                """
            )
        )


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Session wrapped in a transaction that is always rolled back.

    Each test therefore starts from the same clean schema without paying for a
    drop/create cycle per test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# --- Convenience ------------------------------------------------------------


@pytest.fixture
def test_settings():
    return settings

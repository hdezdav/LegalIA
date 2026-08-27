"""Configuration tests.

Focus on the invariants that would otherwise fail silently in production: a
retrieval weighting that no longer sums to 1, a rerank window larger than the
candidate set, or a vector dimension that stops matching the active provider.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings


def _settings(**overrides: object) -> Settings:
    """Build Settings from explicit values, ignoring any ambient .env file."""
    base: dict[str, object] = {
        "ENVIRONMENT": "test",
        "EMBEDDING_PROVIDER": "mock",
        "RERANKER_PROVIDER": "mock",
        "_env_file": None,
    }
    return Settings(**(base | overrides))  # type: ignore[arg-type]


# --- Derived values ---------------------------------------------------------


def test_database_url_is_composed_from_postgres_parts() -> None:
    settings = _settings(
        POSTGRES_USER="u",
        POSTGRES_PASSWORD="p",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5433,
        POSTGRES_DB="legalia",
    )

    assert settings.DATABASE_URL == "postgresql+psycopg://u:p@db:5433/legalia"


def test_database_url_override_gets_the_psycopg_driver_pinned() -> None:
    """`.env.example` documents the plain libpq form; SQLAlchemy needs a driver.

    Without normalization this would silently fall back to psycopg2, which is
    not installed.
    """
    settings = _settings(DATABASE_URL="postgresql://u:p@host:5432/db")

    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")


def test_database_url_override_keeps_an_explicit_driver() -> None:
    settings = _settings(DATABASE_URL="postgresql+psycopg://u:p@host:5432/db")

    assert settings.DATABASE_URL == "postgresql+psycopg://u:p@host:5432/db"


def test_password_is_not_exposed_by_repr() -> None:
    """SecretStr keeps credentials out of tracebacks and log lines."""
    settings = _settings(POSTGRES_PASSWORD="hunter2", JWT_SECRET="s3cret")

    rendered = repr(settings)

    assert "hunter2" not in rendered
    assert "s3cret" not in rendered


def test_cors_origins_are_parsed_and_trimmed() -> None:
    settings = _settings(CORS_ORIGINS="http://a.test, http://b.test ,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


# --- Embedding dimension ---------------------------------------------------


@pytest.mark.parametrize(
    ("provider", "expected"),
    [("alibaba", 1024), ("bge", 1024), ("mock", 8)],
)
def test_embedding_dimension_follows_the_active_provider(
    provider: str, expected: int
) -> None:
    """The vector width is never a constant; it tracks the selected provider."""
    settings = _settings(
        EMBEDDING_PROVIDER=provider,
        ALIBABA_EMBEDDING_DIMENSION=1024,
        BGE_EMBEDDING_DIMENSION=1024,
        MOCK_EMBEDDING_DIMENSION=8,
    )

    assert settings.embedding_dimension == expected


def test_embedding_dimension_reflects_a_provider_specific_override() -> None:
    settings = _settings(EMBEDDING_PROVIDER="bge", BGE_EMBEDDING_DIMENSION=768)

    assert settings.embedding_dimension == 768


# --- Retrieval invariants --------------------------------------------------


def test_retrieval_weights_must_sum_to_one() -> None:
    """Weights that do not sum to 1 would make hybrid scores incomparable."""
    with pytest.raises(ValidationError, match="must equal 1.0"):
        _settings(SEMANTIC_WEIGHT=0.9, LEXICAL_WEIGHT=0.3)


def test_retrieval_weights_accept_a_valid_split() -> None:
    settings = _settings(SEMANTIC_WEIGHT=0.5, LEXICAL_WEIGHT=0.5)

    assert settings.SEMANTIC_WEIGHT == 0.5


def test_rerank_window_cannot_exceed_the_candidate_set() -> None:
    """Reranking selects from what retrieval returned; it cannot invent rows."""
    with pytest.raises(ValidationError, match="cannot exceed"):
        _settings(RETRIEVAL_TOP_K=5, RERANK_TOP_K=10)


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="smaller than CHUNK_SIZE"):
        _settings(CHUNK_SIZE=500, CHUNK_OVERLAP=500)


# --- Credential enforcement ------------------------------------------------


def test_development_boots_without_any_provider_credentials() -> None:
    """A fresh clone must run on mock providers with no keys at all."""
    settings = _settings(ENVIRONMENT="development")

    assert settings.ENVIRONMENT is Environment.DEVELOPMENT


def test_production_rejects_a_default_jwt_secret() -> None:
    # Passed explicitly: conftest exports JWT_SECRET into the environment, and
    # `_env_file=None` only suppresses the .env file, not real env vars.
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(
            ENVIRONMENT="production",
            JWT_SECRET="change_me",
            ANTHROPIC_API_KEY="key",
            EMBEDDING_PROVIDER="mock",
            RERANKER_PROVIDER="mock",
        )


def test_production_requires_a_key_for_the_selected_embedding_provider() -> None:
    """Selecting a remote provider without its key must fail at boot, not at the
    first user question."""
    with pytest.raises(ValidationError, match="ALIBABA_API_KEY"):
        _settings(
            ENVIRONMENT="production",
            JWT_SECRET="a-real-secret",
            ANTHROPIC_API_KEY="key",
            EMBEDDING_PROVIDER="alibaba",
            RERANKER_PROVIDER="mock",
        )


def test_production_does_not_require_keys_for_unselected_providers() -> None:
    settings = _settings(
        ENVIRONMENT="production",
        JWT_SECRET="a-real-secret",
        ANTHROPIC_API_KEY="key",
        EMBEDDING_PROVIDER="mock",
        RERANKER_PROVIDER="mock",
    )

    assert settings.is_production

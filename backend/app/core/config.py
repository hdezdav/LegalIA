"""Application configuration.

Every runtime knob is read from the environment once, at import time, and
exposed through a single `settings` object. No other module reads os.environ
directly, so swapping a provider or a threshold is always an environment change
rather than a code change.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ------------------------------------------------------
    APP_NAME: str = "Legalia"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # --- API --------------------------------------------------------------
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated; parsed by `cors_origin_list`.
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Database ---------------------------------------------------------
    POSTGRES_DB: str = "legalia"
    POSTGRES_USER: str = "legalia"
    POSTGRES_PASSWORD: SecretStr = SecretStr("legalia")
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # Optional explicit override. When unset, the URL is composed from the
    # POSTGRES_* values above so there is a single source of truth.
    DATABASE_URL_OVERRIDE: str | None = Field(default=None, alias="DATABASE_URL")

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # --- Auth -------------------------------------------------------------
    JWT_SECRET: SecretStr = SecretStr("change_me")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Shared secret LibreChat presents to reach the chat endpoint on behalf of
    # its own users. Distinct from JWT_SECRET, which signs LegalIA user tokens.
    LEGALIA_SERVICE_TOKEN: SecretStr | None = None

    # --- LLM --------------------------------------------------------------
    LLM_PROVIDER: Literal["openai_compatible", "anthropic", "mock"] = "openai_compatible"
    LLM_BASE_URL: str = "https://access.nodule-provider.store/v1"
    LLM_API_KEY: SecretStr | None = None
    LLM_MODEL: str = "claude-sonnet-4.6"
    ANTHROPIC_API_KEY: SecretStr | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4.6"
    ANTHROPIC_MAX_TOKENS: int = 4096
    ANTHROPIC_TEMPERATURE: float = 0.0
    ANTHROPIC_TIMEOUT_SECONDS: float = 120.0
    ANTHROPIC_MAX_RETRIES: int = 2

    # Cheaper model used by the verification pass. Kept separate so grounding
    # checks never silently inherit the answer model's cost.
    VERIFIER_MODEL: str = "claude-haiku-4.5"

    # --- Web Search (Tavily AI & DDGS) ------------------------------------
    TAVILY_API_KEY: SecretStr | None = None

    # --- Embeddings -------------------------------------------------------
    # `mock` is a first-class option, not a test artifact: it lets the whole
    # pipeline run end to end with no external API key.
    # `pending` is the "en gris" state: acts like mock for development but
    # signals that real semantic embeddings are intended but not yet available.
    EMBEDDING_PROVIDER: Literal["alibaba", "bge", "mock", "pending"] = "pending"

    ALIBABA_API_KEY: SecretStr | None = None
    ALIBABA_EMBEDDING_MODEL: str = "text-embedding-v4"
    ALIBABA_EMBEDDING_DIMENSION: int = 1024
    ALIBABA_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    BGE_MODEL_PATH: str = "BAAI/bge-m3"
    BGE_EMBEDDING_DIMENSION: int = 1024
    BGE_BATCH_SIZE: int = 32

    MOCK_EMBEDDING_DIMENSION: int = 1024

    EMBEDDING_BATCH_SIZE: int = 16
    EMBEDDING_TIMEOUT_SECONDS: float = 60.0

    # --- Reranking --------------------------------------------------------
    RERANKER_PROVIDER: Literal["alibaba", "mock", "none", "pending"] = "pending"
    ALIBABA_RERANKER_API_KEY: SecretStr | None = None
    ALIBABA_RERANKER_MODEL: str = "gte-rerank-v2"
    ALIBABA_RERANKER_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/api/v1"
    RERANKER_TIMEOUT_SECONDS: float = 30.0

    # --- Retrieval --------------------------------------------------------
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    MIN_SIMILARITY_SCORE: float = 0.5
    SEMANTIC_WEIGHT: float = 0.7
    LEXICAL_WEIGHT: float = 0.3

    # Reciprocal Rank Fusion constant used when merging the semantic and
    # lexical result lists. 60 is the value from the original RRF paper.
    RRF_K: int = 60

    # NO EVIDENCE -> NO ANSWER thresholds. If the best reranked chunk scores
    # below MIN_EVIDENCE_SCORE, or fewer than MIN_EVIDENCE_CHUNKS survive, the
    # pipeline refuses to answer instead of guessing.
    MIN_EVIDENCE_SCORE: float = 0.35
    MIN_EVIDENCE_CHUNKS: int = 1

    # Hard ceiling on context handed to the LLM.
    MAX_CONTEXT_TOKENS: int = 12000

    # Conversation history limit: how many prior turns to load.
    MAX_CONVERSATION_HISTORY: int = 20

    # --- Chunking ---------------------------------------------------------
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MIN_CHUNK_SIZE: int = 100
    MAX_DOCUMENT_SIZE_MB: int = 50

    # --- Verification -----------------------------------------------------
    ENABLE_VERIFICATION: bool = True
    # `heuristic` needs no LLM call, so tests and the first MVP run never
    # depend on a second round trip. `llm` upgrades the same interface.
    VERIFICATION_MODE: Literal["heuristic", "llm", "mock"] = "heuristic"

    # --- Observability ----------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    ENABLE_USAGE_LOGGING: bool = True
    ENABLE_CITATION_TRACKING: bool = True

    # --- Rate limiting ----------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # --- LibreChat --------------------------------------------------------
    LIBRECHAT_URL: str = "http://librechat:3000"

    # --- Derived values ---------------------------------------------------

    # repr=False: the URL embeds POSTGRES_PASSWORD, and a computed field is
    # rendered by repr() by default, which would put the credential into any
    # traceback or log line that touches `settings`.
    @computed_field(repr=False)  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Sync SQLAlchemy URL (psycopg 3 driver). Used by Alembic."""
        if self.DATABASE_URL_OVERRIDE:
            return self._normalize_driver(self.DATABASE_URL_OVERRIDE)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @staticmethod
    def _normalize_driver(url: str) -> str:
        """Pin the psycopg 3 driver on a bare `postgresql://` URL.

        `.env.example` documents the plain libpq form because it is what psql
        and pg_dump accept; SQLAlchemy needs the driver spelled out.
        """
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def embedding_dimension(self) -> int:
        """Vector width for the active provider.

        Nothing hardcodes a dimension: the DB column is created from this value
        and switching providers across dimensions requires a migration plus a
        re-embed (documented in docs/DATABASE.md).
        """
        if self.EMBEDDING_PROVIDER == "alibaba":
            return self.ALIBABA_EMBEDDING_DIMENSION
        elif self.EMBEDDING_PROVIDER == "bge":
            return self.BGE_EMBEDDING_DIMENSION
        return self.MOCK_EMBEDDING_DIMENSION

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT is Environment.PRODUCTION

    # --- Validation -------------------------------------------------------

    @model_validator(mode="after")
    def _check_retrieval_weights(self) -> Settings:
        total = self.SEMANTIC_WEIGHT + self.LEXICAL_WEIGHT
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"SEMANTIC_WEIGHT + LEXICAL_WEIGHT must equal 1.0, got {total}"
            )
        if self.RERANK_TOP_K > self.RETRIEVAL_TOP_K:
            raise ValueError(
                "RERANK_TOP_K cannot exceed RETRIEVAL_TOP_K: reranking selects "
                "from the retrieved candidates"
            )
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @model_validator(mode="after")
    def _check_provider_credentials(self) -> Settings:
        """Fail fast when a selected provider has no usable credentials.

        Only enforced outside development/test, so a fresh clone can boot and
        run its tests with mock providers and no keys at all.
        """
        if self.ENVIRONMENT in (Environment.DEVELOPMENT, Environment.TEST):
            return self

        missing: list[str] = []
        if self.EMBEDDING_PROVIDER == "alibaba" and not self.ALIBABA_API_KEY:
            missing.append("ALIBABA_API_KEY (EMBEDDING_PROVIDER=alibaba)")
        if self.RERANKER_PROVIDER == "alibaba" and not self.ALIBABA_RERANKER_API_KEY:
            missing.append("ALIBABA_RERANKER_API_KEY (RERANKER_PROVIDER=alibaba)")
        if not (self.LLM_API_KEY or self.ANTHROPIC_API_KEY):
            missing.append("LLM_API_KEY or ANTHROPIC_API_KEY")
        if self.JWT_SECRET.get_secret_value() in ("change_me", ""):
            missing.append("JWT_SECRET (still at its default value)")

        if missing:
            raise ValueError(
                "Missing required configuration for ENVIRONMENT="
                f"{self.ENVIRONMENT}: {', '.join(missing)}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached accessor. Tests override via `get_settings.cache_clear()`."""
    return Settings()


settings = get_settings()

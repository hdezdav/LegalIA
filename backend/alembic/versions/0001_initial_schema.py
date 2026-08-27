"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-26

Creates the full MVP schema: users, documents, document_relations, chunks,
conversations, messages, citations, usage_logs.

Two deliberate choices in this file:

1. Enum values are written out literally rather than imported from
   `app.db.models.enums`. A migration is a frozen snapshot; if it imported live
   code, adding an enum member later would retroactively change what this
   revision does.

2. The `chunks.embedding` width IS read from configuration
   (`settings.embedding_dimension`), because the vector width is a
   deployment-time provider choice and a fresh install must match its provider.
   The consequence is explicit: switching to a provider with a different
   dimension on an EXISTING database requires a new migration plus a full
   re-embed. See docs/DATABASE.md.

Extensions and the `legal_es` text-search configuration are also ensured here.
`infrastructure/postgres/init.sql` normally creates them, but it only runs on a
fresh container volume, and `chunks.content_tsv` is a generated column that
references `legal_es` directly, so a database bootstrapped some other way (a
scratch test database, a managed instance) must still be able to migrate.
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

EMBEDDING_DIMENSION: int = settings.embedding_dimension

# --- Enum types --------------------------------------------------------------
# Values frozen at this revision. create_type=False on the column definitions
# below, because the types are created once, explicitly, in upgrade().

DOCUMENT_STATUS = (
    "VIGENTE",
    "DEROGADO",
    "MODIFICADO",
    "INEXEQUIBLE",
    "PARCIALMENTE_MODIFICADO",
    "DESCONOCIDO",
)

DOCUMENT_TYPE = (
    "CONSTITUCION",
    "ACTO_LEGISLATIVO",
    "LEY",
    "LEY_ESTATUTARIA",
    "DECRETO",
    "DECRETO_LEY",
    "RESOLUCION",
    "CIRCULAR",
    "ACUERDO",
    "ORDENANZA",
    "CODIGO",
    "SENTENCIA",
    "AUTO",
    "CONCEPTO",
    "DOCTRINA",
    "OTRO",
)

JURISDICTION = (
    "NACIONAL",
    "DEPARTAMENTAL",
    "MUNICIPAL",
    "DISTRITAL",
    "INTERNACIONAL",
    "DESCONOCIDA",
)

COURT = (
    "CORTE_CONSTITUCIONAL",
    "CORTE_SUPREMA_JUSTICIA",
    "CONSEJO_ESTADO",
    "CONSEJO_SUPERIOR_JUDICATURA",
    "JURISDICCION_ESPECIAL_PAZ",
    "TRIBUNAL_SUPERIOR",
    "TRIBUNAL_ADMINISTRATIVO",
    "OTRO",
)

LEGAL_AREA = (
    "CONSTITUCIONAL",
    "CIVIL",
    "PENAL",
    "LABORAL",
    "ADMINISTRATIVO",
    "COMERCIAL",
    "TRIBUTARIO",
    "PROCESAL",
    "FAMILIA",
    "AMBIENTAL",
    "SEGURIDAD_SOCIAL",
    "INTERNACIONAL",
    "OTRO",
)

RELATION_TYPE = (
    "DEROGA",
    "DEROGA_PARCIALMENTE",
    "MODIFICA",
    "ADICIONA",
    "REGLAMENTA",
    "DECLARA_INEXEQUIBLE",
    "DECLARA_EXEQUIBLE",
    "DECLARA_EXEQUIBLE_CONDICIONADA",
    "INTERPRETA",
    "CITA",
    "COMPILA",
    "CORRIGE",
)

MESSAGE_ROLE = ("user", "assistant", "system")

VERIFICATION_STATUS = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
    "INSUFFICIENT_EVIDENCE",
    "NOT_VERIFIED",
)

CITATION_VERIFICATION_STATUS = (
    "VERIFIED",
    "EXCERPT_MISMATCH",
    "NOT_IN_CONTEXT",
    "UNVERIFIED",
)

RETRIEVAL_SOURCE = ("SEMANTIC", "LEXICAL", "HYBRID")

_ENUM_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("document_status", DOCUMENT_STATUS),
    ("document_type", DOCUMENT_TYPE),
    ("jurisdiction", JURISDICTION),
    ("court", COURT),
    ("legal_area", LEGAL_AREA),
    ("relation_type", RELATION_TYPE),
    ("message_role", MESSAGE_ROLE),
    ("verification_status", VERIFICATION_STATUS),
    ("citation_verification_status", CITATION_VERIFICATION_STATUS),
    ("retrieval_source", RETRIEVAL_SOURCE),
)


def _enum(name: str, values: tuple[str, ...]) -> postgresql.ENUM:
    """Reference an already-created enum type from a column definition."""
    return postgresql.ENUM(*values, name=name, create_type=False)


def _ensure_prerequisites() -> None:
    """Extensions and the `legal_es` FTS configuration.

    Mirrors infrastructure/postgres/init.sql so this revision also applies to a
    database that container bootstrap never touched.
    """
    for extension in ("vector", "pg_trgm", "unaccent", "pgcrypto"):
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'legal_es') THEN
                CREATE TEXT SEARCH CONFIGURATION legal_es (COPY = spanish);
                ALTER TEXT SEARCH CONFIGURATION legal_es
                    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart,
                                      word, hword, hword_part
                    WITH unaccent, spanish_stem;
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    _ensure_prerequisites()

    for name, values in _ENUM_TYPES:
        postgresql.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)

    _create_users()
    _create_documents()
    _create_document_relations()
    _create_chunks()
    _create_conversations()
    _create_messages()
    _create_citations()
    _create_usage_logs()


def downgrade() -> None:
    # Reverse dependency order.
    for table in (
        "usage_logs",
        "citations",
        "messages",
        "conversations",
        "chunks",
        "document_relations",
        "documents",
        "users",
    ):
        op.drop_table(table)

    for name, values in reversed(_ENUM_TYPES):
        postgresql.ENUM(*values, name=name).drop(op.get_bind(), checkfirst=True)

    # Extensions and legal_es are intentionally left in place: other databases
    # or schemas may depend on them, and dropping `vector` would be destructive
    # beyond this revision's scope.


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("external_issuer", sa.String(64), nullable=True),
        sa.Column("external_subject", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint(
            "external_issuer",
            "external_subject",
            name="uq_users_external_issuer_external_subject",
        ),
    )
    op.create_index("ix_users_is_active", "users", ["is_active"])


def _create_documents() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_type", _enum("document_type", DOCUMENT_TYPE), nullable=False),
        sa.Column("issuing_entity", sa.String(255), nullable=True),
        sa.Column("court", _enum("court", COURT), nullable=True),
        sa.Column(
            "jurisdiction",
            _enum("jurisdiction", JURISDICTION),
            server_default="NACIONAL",
            nullable=False,
        ),
        sa.Column("legal_area", _enum("legal_area", LEGAL_AREA), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            _enum("document_status", DOCUMENT_STATUS),
            server_default="DESCONOCIDO",
            nullable=False,
        ),
        sa.Column("status_note", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_storage_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint(
            "source_name", "external_id", name="uq_documents_source_name_external_id"
        ),
    )
    op.create_index("ix_documents_external_id", "documents", ["external_id"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_issuing_entity", "documents", ["issuing_entity"])
    op.create_index("ix_documents_court", "documents", ["court"])
    op.create_index("ix_documents_jurisdiction", "documents", ["jurisdiction"])
    op.create_index("ix_documents_legal_area", "documents", ["legal_area"])
    op.create_index("ix_documents_publication_date", "documents", ["publication_date"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_type_status", "documents", ["document_type", "status"])
    op.create_index("ix_documents_area_status", "documents", ["legal_area", "status"])
    op.create_index(
        "ix_documents_title_trgm",
        "documents",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )


def _create_document_relations() -> None:
    op.create_table(
        "document_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", _enum("relation_type", RELATION_TYPE), nullable=False),
        sa.Column("affected_section", sa.String(255), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_document_relations"),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
            name="fk_document_relations_source_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["documents.id"],
            name="fk_document_relations_target_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "relation_type",
            "affected_section",
            name="uq_document_relations_source_target_type_section",
        ),
    )
    op.create_index(
        "ix_document_relations_source_document_id",
        "document_relations",
        ["source_document_id"],
    )
    op.create_index(
        "ix_document_relations_target_document_id",
        "document_relations",
        ["target_document_id"],
    )
    op.create_index(
        "ix_document_relations_relation_type", "document_relations", ["relation_type"]
    )
    op.create_index(
        "ix_document_relations_target_type",
        "document_relations",
        ["target_document_id", "relation_type"],
    )


def _create_chunks() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(512), nullable=True),
        sa.Column("article_number", sa.String(64), nullable=True),
        sa.Column("hierarchy_path", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        # Width comes from the active provider. See the module docstring for the
        # migration path when this changes.
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('public.legal_es', content)", persisted=True),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunks_document_id_chunk_index"
        ),
        sa.CheckConstraint("token_count > 0", name="ck_chunks_token_count_positive"),
        sa.CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start",
            name="ck_chunks_char_range_ordered",
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_section", "chunks", ["section"])
    op.create_index("ix_chunks_article_number", "chunks", ["article_number"])
    op.create_index("ix_chunks_embedding_model", "chunks", ["embedding_model"])
    op.create_index("ix_chunks_created_at", "chunks", ["created_at"])
    op.create_index("ix_chunks_document_index", "chunks", ["document_id", "chunk_index"])
    # Lexical half of hybrid retrieval.
    op.create_index(
        "ix_chunks_content_tsv", "chunks", ["content_tsv"], postgresql_using="gin"
    )
    # Semantic half. HNSW needs no training pass, so it is valid on an empty
    # table; IVFFlat would have to be built after the corpus was loaded.
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def _create_conversations() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("external_conversation_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "external_conversation_id",
            name="uq_conversations_user_id_external_conversation_id",
        ),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index(
        "ix_conversations_user_updated", "conversations", ["user_id", "updated_at"]
    )


def _create_messages() -> None:
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", _enum("message_role", MESSAGE_ROLE), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            _enum("verification_status", VERIFICATION_STATUS),
            nullable=True,
        ),
        sa.Column(
            "refused_for_lack_of_evidence",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("retrieval_candidate_count", sa.Integer(), nullable=True),
        sa.Column("context_chunk_count", sa.Integer(), nullable=True),
        sa.Column("top_evidence_score", sa.Float(), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_messages_input_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_messages_output_tokens_non_negative",
        ),
        # A user turn can never carry an answer's audit fields.
        sa.CheckConstraint(
            "role <> 'user' OR (verification_status IS NULL "
            "AND refused_for_lack_of_evidence = false)",
            name="ck_messages_user_messages_have_no_verification",
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_verification_status", "messages", ["verification_status"])
    op.create_index(
        "ix_messages_refused_for_lack_of_evidence",
        "messages",
        ["refused_for_lack_of_evidence"],
    )
    op.create_index("ix_messages_request_id", "messages", ["request_id"])
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )


def _create_citations() -> None:
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("document_title", sa.Text(), nullable=False),
        sa.Column("section", sa.String(512), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("status", _enum("document_status", DOCUMENT_STATUS), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("excerpt_char_start", sa.Integer(), nullable=True),
        sa.Column("excerpt_char_end", sa.Integer(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column(
            "retrieval_source", _enum("retrieval_source", RETRIEVAL_SOURCE), nullable=True
        ),
        sa.Column(
            "verification_status",
            _enum("citation_verification_status", CITATION_VERIFICATION_STATUS),
            server_default="UNVERIFIED",
            nullable=False,
        ),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_citations"),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_citations_message_id_messages",
            ondelete="CASCADE",
        ),
        # RESTRICT on both source references: deleting a cited document or chunk
        # would destroy the audit trail of an answer already given.
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_citations_document_id_documents",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_citations_chunk_id_chunks",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "message_id", "position", name="uq_citations_message_id_position"
        ),
        sa.CheckConstraint("position >= 1", name="ck_citations_position_positive"),
        sa.CheckConstraint("length(excerpt) > 0", name="ck_citations_excerpt_not_empty"),
        sa.CheckConstraint(
            "excerpt_char_end IS NULL OR excerpt_char_start IS NULL "
            "OR excerpt_char_end >= excerpt_char_start",
            name="ck_citations_excerpt_range_ordered",
        ),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])
    op.create_index("ix_citations_document_id", "citations", ["document_id"])
    op.create_index("ix_citations_chunk_id", "citations", ["chunk_id"])
    op.create_index(
        "ix_citations_verification_status", "citations", ["verification_status"]
    )
    op.create_index("ix_citations_created_at", "citations", ["created_at"])
    # "Which answers cited this document?" - needed when a norm is repealed and
    # prior answers must be reviewed.
    op.create_index(
        "ix_citations_document_created", "citations", ["document_id", "created_at"]
    )


def _create_usage_logs() -> None:
    op.create_table(
        "usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("verifier_model", sa.String(128), nullable=True),
        sa.Column("verifier_input_tokens", sa.Integer(), nullable=True),
        sa.Column("verifier_output_tokens", sa.Integer(), nullable=True),
        sa.Column("embedding_provider", sa.String(64), nullable=True),
        sa.Column("reranker_provider", sa.String(64), nullable=True),
        sa.Column("retrieval_count", sa.Integer(), nullable=True),
        sa.Column("context_chunk_count", sa.Integer(), nullable=True),
        sa.Column("top_evidence_score", sa.Float(), nullable=True),
        sa.Column(
            "verification_status",
            _enum("verification_status", VERIFICATION_STATUS),
            nullable=True,
        ),
        sa.Column(
            "refused_for_lack_of_evidence",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("embedding_latency_ms", sa.Integer(), nullable=True),
        sa.Column("retrieval_latency_ms", sa.Integer(), nullable=True),
        sa.Column("rerank_latency_ms", sa.Integer(), nullable=True),
        sa.Column("llm_latency_ms", sa.Integer(), nullable=True),
        sa.Column("verification_latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_usage_logs"),
        # SET NULL, not CASCADE: deleting a user must not erase the cost record.
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_usage_logs_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_usage_logs_input_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_usage_logs_output_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_usage_logs_latency_non_negative",
        ),
    )
    op.create_index("ix_usage_logs_user_id", "usage_logs", ["user_id"])
    op.create_index("ix_usage_logs_request_id", "usage_logs", ["request_id"])
    op.create_index("ix_usage_logs_endpoint", "usage_logs", ["endpoint"])
    op.create_index("ix_usage_logs_model", "usage_logs", ["model"])
    op.create_index("ix_usage_logs_embedding_provider", "usage_logs", ["embedding_provider"])
    op.create_index(
        "ix_usage_logs_verification_status", "usage_logs", ["verification_status"]
    )
    op.create_index(
        "ix_usage_logs_refused_for_lack_of_evidence",
        "usage_logs",
        ["refused_for_lack_of_evidence"],
    )
    op.create_index("ix_usage_logs_status_code", "usage_logs", ["status_code"])
    op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])
    op.create_index("ix_usage_logs_user_created", "usage_logs", ["user_id", "created_at"])
    # Refusal rate over time: the headline metric for NO EVIDENCE -> NO ANSWER.
    op.create_index(
        "ix_usage_logs_created_refused",
        "usage_logs",
        ["created_at", "refused_for_lack_of_evidence"],
    )

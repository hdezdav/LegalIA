"""Retrievable fragments of a document, with their embeddings.

This is the unit retrieval returns and the unit citations point at, so every
field needed to quote a passage and locate it inside the original document lives
here.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.citation import Citation
    from app.db.models.document import Document

class Chunk(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """One retrievable fragment of a document.

    Append-only in practice: re-ingesting a document replaces its chunks rather
    than mutating them, so a citation stored earlier can never silently start
    pointing at different text.
    """

    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position within the document. Restores reading order and lets a citation
    # be rendered with its neighbours for context.
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Human-readable location, produced by LegalTextSplitter:
    # "Artículo 90", "Capítulo II > Artículo 15 > Parágrafo 1".
    # This is what makes a citation precise rather than "somewhere in the PDF".
    section: Mapped[str | None] = mapped_column(String(512), index=True)

    # Structural fields kept separate from `section` so they can be filtered on.
    article_number: Mapped[str | None] = mapped_column(String(64), index=True)
    hierarchy_path: Mapped[str | None] = mapped_column(Text)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Character offsets into the cleaned document text. Lets the exact passage
    # be highlighted in the source without re-running the splitter.
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)

    # --- Vector -----------------------------------------------------------
    # Width comes from the active provider's configured dimension; nothing
    # hardcodes a number. Changing providers across dimensions requires a
    # migration plus a re-embed (see docs/DATABASE.md).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimension)
    )
    # Which model produced this vector. A row whose model differs from the
    # active provider is stale and must not be trusted for search.
    embedding_model: Mapped[str | None] = mapped_column(String(128), index=True)

    # --- Lexical search ---------------------------------------------------
    # Generated column, so the tsvector cannot drift from `content`: PostgreSQL
    # recomputes it on write. Uses the accent-insensitive Spanish configuration
    # created in infrastructure/postgres/init.sql.
    content_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('public.legal_es', content)", persisted=True),
    )

    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
    citations: Mapped[list[Citation]] = relationship(
        back_populates="chunk", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunks_document_id_chunk_index"
        ),
        CheckConstraint("token_count > 0", name="token_count_positive"),
        CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start",
            name="char_range_ordered",
        ),
        # Reading order and neighbour lookup.
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
        # Lexical half of hybrid retrieval.
        Index("ix_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
        # Semantic half. HNSW over cosine distance: better recall/latency than
        # IVFFlat on a CPU-only box, and it needs no training pass, so it works
        # on an empty table at migration time.
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Chunk {self.id} doc={self.document_id} idx={self.chunk_index} "
            f"section={self.section!r}>"
        )

"""Citations: the link between a sentence in an answer and the text that backs it.

This table is the product's core claim. A citation is a *row*, not a string
inside the answer, so it can be resolved, re-rendered, and independently
verified. `excerpt` is stored verbatim from the chunk so the quote shown to the
user can be checked character by character against its source.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    CitationVerificationStatus,
    DocumentStatus,
    RetrievalSource,
)

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.document import Document
    from app.db.models.message import Message


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
        create_constraint=False,
    )


class Citation(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """One source backing one part of one answer."""

    __tablename__ = "citations"
    __table_args__ = (
        # Most common query: get all citations for a message, ordered by position
        Index("ix_citations_message_id_position", "message_id", "position"),
        # Query by document for citation analysis
        Index("ix_citations_document_id", "document_id"),
        # Query by verification status for background verification jobs
        Index("ix_citations_verification_status", "verification_status"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- What is being cited ----------------------------------------------
    # RESTRICT, not CASCADE: deleting a document that has been cited would
    # destroy the audit trail of answers already given. Re-ingestion replaces
    # chunks, so this also forces that path to deal with existing citations
    # explicitly instead of silently dropping them.
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Order in which citations are presented, matching the answer's [1], [2].
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Denormalized display fields --------------------------------------
    # Copied at answer time on purpose. A citation must render exactly as it did
    # when shown, even after the document's title is corrected or its vigencia
    # changes. The live values remain reachable through the relationships.
    document_title: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(String(512))
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)

    # Vigencia as it stood when the answer was produced. Compared against the
    # document's current status to detect that an old answer has gone stale.
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False
    )

    # The quoted passage, verbatim from the chunk. Verification checks that this
    # text really occurs in chunk.content.
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    # Offsets of the excerpt within the chunk, so it can be highlighted.
    excerpt_char_start: Mapped[int | None] = mapped_column(Integer)
    excerpt_char_end: Mapped[int | None] = mapped_column(Integer)

    # --- Retrieval provenance ---------------------------------------------
    relevance_score: Mapped[float | None] = mapped_column(Float)
    # Rank after reranking. Kept for evaluation: it shows whether cited sources
    # were the ones the reranker put first.
    rank: Mapped[int | None] = mapped_column(Integer)
    retrieval_source: Mapped[RetrievalSource | None] = mapped_column(
        _pg_enum(RetrievalSource, "retrieval_source")
    )

    # --- Verification ------------------------------------------------------
    verification_status: Mapped[CitationVerificationStatus] = mapped_column(
        _pg_enum(CitationVerificationStatus, "citation_verification_status"),
        nullable=False,
        default=CitationVerificationStatus.UNVERIFIED,
        server_default=CitationVerificationStatus.UNVERIFIED.value,
        index=True,
    )
    verification_note: Mapped[str | None] = mapped_column(Text)

    citation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    message: Mapped[Message] = relationship(back_populates="citations")
    document: Mapped[Document] = relationship(back_populates="citations")
    chunk: Mapped[Chunk] = relationship(back_populates="citations")

    __table_args__ = (
        UniqueConstraint(
            "message_id", "position", name="uq_citations_message_id_position"
        ),
        CheckConstraint("position >= 1", name="position_positive"),
        CheckConstraint("length(excerpt) > 0", name="excerpt_not_empty"),
        CheckConstraint(
            "excerpt_char_end IS NULL OR excerpt_char_start IS NULL "
            "OR excerpt_char_end >= excerpt_char_start",
            name="excerpt_range_ordered",
        ),
        # "Which answers cited this document?" - needed when a norm is repealed
        # and prior answers must be reviewed.
        Index("ix_citations_document_created", "document_id", "created_at"),
    )

    @property
    def is_stale(self) -> bool:
        """True when the cited document's vigencia changed since this answer.

        Requires the `document` relationship to be loaded.
        """
        return self.status is not self.document.status

    def __repr__(self) -> str:
        return (
            f"<Citation {self.id} pos={self.position} doc={self.document_id} "
            f"verification={self.verification_status}>"
        )

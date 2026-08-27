"""Legal source documents and the relations between them."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    Court,
    DocumentStatus,
    DocumentType,
    Jurisdiction,
    LegalArea,
    RelationType,
)

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.citation import Citation


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    """Native PostgreSQL enum that stores the member *value*.

    Without `values_callable`, SQLAlchemy persists the member *name*. For
    StrEnum both coincide today, but pinning the value makes the column contents
    independent of any later rename of a Python member.
    """
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
        create_constraint=False,
    )


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One legal source: a statute, a decree, a judgment, a concept.

    Citations resolve through here, so every field a user needs in order to
    independently verify a claim lives on this row: title, issuing body, date,
    vigencia, and a URL back to the official source.
    """

    __tablename__ = "documents"

    # Stable identifier from the source system ("LEY_1437_2011", "C-355-06").
    # Unique so re-ingesting the same document updates instead of duplicating.
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)

    document_type: Mapped[DocumentType] = mapped_column(
        _pg_enum(DocumentType, "document_type"),
        nullable=False,
        index=True,
    )

    # Body that issued the document (Congreso de la República, DIAN, ...).
    issuing_entity: Mapped[str | None] = mapped_column(String(255), index=True)

    # Set only for jurisprudence; NULL for statutes.
    court: Mapped[Court | None] = mapped_column(
        _pg_enum(Court, "court"), index=True
    )

    jurisdiction: Mapped[Jurisdiction] = mapped_column(
        _pg_enum(Jurisdiction, "jurisdiction"),
        nullable=False,
        default=Jurisdiction.NACIONAL,
        server_default=Jurisdiction.NACIONAL.value,
        index=True,
    )

    legal_area: Mapped[LegalArea | None] = mapped_column(
        _pg_enum(LegalArea, "legal_area"), index=True
    )

    publication_date: Mapped[date | None] = mapped_column(Date, index=True)
    # When the norm took effect, which is often not its publication date.
    effective_date: Mapped[date | None] = mapped_column(Date)

    # Defaults to DESCONOCIDO: ingestion must not imply a document is in force
    # merely because nothing said otherwise.
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"),
        nullable=False,
        default=DocumentStatus.DESCONOCIDO,
        server_default=DocumentStatus.DESCONOCIDO.value,
        index=True,
    )
    # Free text explaining a non-VIGENTE status, shown next to the caveat.
    status_note: Mapped[str | None] = mapped_column(Text)

    # --- Provenance -------------------------------------------------------
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_storage_path: Mapped[str | None] = mapped_column(Text)
    # Hash of the raw bytes: detects that a source changed under a stable id.
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    # Which embedding model produced this document's vectors. Required to know
    # what must be re-embedded after a provider change.
    embedding_model: Mapped[str | None] = mapped_column(String(128))

    # Anything source-specific that does not deserve a column (expediente
    # number, magistrado ponente, gaceta reference).
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    # --- Relationships ----------------------------------------------------
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    citations: Mapped[list[Citation]] = relationship(
        back_populates="document", passive_deletes=True
    )

    # Relations where this document is the actor ("this repeals that").
    outgoing_relations: Mapped[list[DocumentRelation]] = relationship(
        foreign_keys="DocumentRelation.source_document_id",
        back_populates="source_document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    # Relations where this document is acted upon ("that repeals this").
    incoming_relations: Mapped[list[DocumentRelation]] = relationship(
        foreign_keys="DocumentRelation.target_document_id",
        back_populates="target_document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Same logical document from the same source must not be ingested twice.
        UniqueConstraint(
            "source_name", "external_id", name="uq_documents_source_name_external_id"
        ),
        # Metadata filters in retrieval almost always combine type + status.
        Index("ix_documents_type_status", "document_type", "status"),
        Index("ix_documents_area_status", "legal_area", "status"),
        # Trigram index for fuzzy title lookup ("Codigo Sustantivo del Trabajo").
        Index(
            "ix_documents_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Document {self.document_type}:{self.external_id or self.id} "
            f"status={self.status}>"
        )


class DocumentRelation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A directed relation: source_document acts upon target_document.

    Read as a sentence: `source` DEROGA `target`. Vigencia is derived from these
    rows rather than trusted from a single document's own text.
    """

    __tablename__ = "document_relations"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relation_type: Mapped[RelationType] = mapped_column(
        _pg_enum(RelationType, "relation_type"), nullable=False, index=True
    )

    # Narrows the relation to part of the target ("artículo 5", "inciso 2").
    # NULL means it applies to the whole document.
    affected_section: Mapped[str | None] = mapped_column(String(255))

    effective_date: Mapped[date | None] = mapped_column(Date)

    # Where this relation was asserted, so a derived status stays auditable.
    source_note: Mapped[str | None] = mapped_column(Text)

    source_document: Mapped[Document] = relationship(
        foreign_keys=[source_document_id], back_populates="outgoing_relations"
    )
    target_document: Mapped[Document] = relationship(
        foreign_keys=[target_document_id], back_populates="incoming_relations"
    )

    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "relation_type",
            "affected_section",
            name="uq_document_relations_source_target_type_section",
        ),
        # Answers "what affects this document?", the lookup vigencia needs.
        Index(
            "ix_document_relations_target_type",
            "target_document_id",
            "relation_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentRelation {self.source_document_id} "
            f"{self.relation_type} {self.target_document_id}>"
        )

"""Persistence for the ingestion pipeline.

Owns the database side and nothing else: loaders extract, processors clean and
split, `embeddings/generator.py` vectorizes, and this module writes rows. Keeping
the split means a re-embed pass or a different provider never touches storage
logic.

Three decisions that matter more than they look:

**Change detection is by content hash.** Re-ingesting a byte-identical file that
was already embedded with the active model is a no-op. Without this, a nightly
corpus refresh would re-embed everything and pay for it every night.

**Chunks are replaced, never mutated.** A chunk's text is quoted back to users as
a citation excerpt, so editing one in place would silently change what an
already-delivered answer claimed its source said.

**A cited chunk cannot be deleted.** `citations.chunk_id` is `ON DELETE RESTRICT`
by design, so re-ingesting a document whose passages have been cited is refused
rather than allowed to destroy the audit trail of answers already given. The
operator is told exactly why and what the options are.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.chunk import Chunk
from app.db.models.citation import Citation
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from ingestion.processors.legal_splitter import LegalChunk
from ingestion.processors.metadata import DocumentMetadata

logger = get_logger(__name__)


class IngestionError(Exception):
    """Raised when a document cannot be stored."""


class CitedDocumentError(IngestionError):
    """Re-ingestion would destroy chunks that existing answers cite."""


@dataclass(slots=True)
class IndexOutcome:
    """What the indexer did, for the CLI to report."""

    document_id: str
    title: str
    chunk_count: int
    #: True when nothing changed and the write was skipped.
    skipped: bool = False
    #: True when an existing document was replaced rather than created.
    replaced: bool = False
    reason: str = ""


class DocumentIndexer:
    """Writes documents and their chunks."""

    def __init__(self, embedding_model: str) -> None:
        #: Recorded on every chunk. Retrieval filters on it, so a chunk embedded by
        #: another model is invisible to search rather than silently mixed in.
        self.embedding_model = embedding_model

    def find_existing(
        self, session: Session, source_name: str, external_id: str | None
    ) -> Document | None:
        """Locate a previously ingested version of this document.

        Matched on `(source_name, external_id)`, which carries a UNIQUE constraint.
        A document with no external id cannot be matched this way and is treated as
        new — deliberately: guessing identity from a title would risk overwriting a
        different norm.
        """
        if external_id is None:
            return None

        return session.scalar(
            select(Document).where(
                Document.source_name == source_name,
                Document.external_id == external_id,
            )
        )

    def is_unchanged(self, existing: Document, content_hash: str) -> bool:
        """True when the source bytes and the embedding model both still match.

        The model check is as important as the hash: an unchanged file whose
        embeddings came from a superseded model still needs re-embedding, or it
        stays invisible to retrieval.
        """
        return (
            existing.content_hash == content_hash
            and existing.embedding_model == self.embedding_model
        )

    def store(
        self,
        session: Session,
        *,
        metadata: DocumentMetadata,
        chunks: list[LegalChunk],
        vectors: list[list[float]],
        content_hash: str,
        source_name: str,
        source_path: Path | None = None,
        source_url: str | None = None,
        status: DocumentStatus = DocumentStatus.DESCONOCIDO,
        status_note: str | None = None,
        force: bool = False,
    ) -> IndexOutcome:
        """Create or replace a document and its chunks.

        Args:
            status: vigencia. Defaults to `DESCONOCIDO` and is never inferred from
                the document's text — a norm almost never states that it was
                repealed, so assuming VIGENTE from silence is exactly the error the
                unknown state exists to prevent.
            force: proceed even when the stored version looks unchanged. Does NOT
                override the cited-chunk guard.

        Raises:
            IngestionError: chunk and vector counts disagree.
            CitedDocumentError: existing chunks are cited by stored answers.
        """
        if len(chunks) != len(vectors):
            raise IngestionError(
                f"{len(chunks)} chunks but {len(vectors)} vectors; refusing to "
                "store a misaligned document"
            )
        if not chunks:
            raise IngestionError("Document produced no chunks")

        existing = self.find_existing(session, source_name, metadata.external_id)

        if existing is not None:
            if not force and self.is_unchanged(existing, content_hash):
                logger.info(
                    "document unchanged, skipping",
                    extra={
                        "document_id": str(existing.id),
                        "external_id": metadata.external_id,
                    },
                )
                return IndexOutcome(
                    document_id=str(existing.id),
                    title=existing.title,
                    chunk_count=self._count_chunks(session, existing),
                    skipped=True,
                    reason="unchanged content and embedding model",
                )

            self._guard_cited_chunks(session, existing)
            document = self._update_document(
                existing,
                metadata=metadata,
                content_hash=content_hash,
                source_url=source_url,
                source_path=source_path,
                status=status,
                status_note=status_note,
            )
            self._delete_chunks(session, existing)
            replaced = True
        else:
            document = self._create_document(
                metadata=metadata,
                content_hash=content_hash,
                source_name=source_name,
                source_url=source_url,
                source_path=source_path,
                status=status,
                status_note=status_note,
            )
            session.add(document)
            session.flush()
            replaced = False

        self._insert_chunks(session, document, chunks, vectors)
        session.flush()

        logger.info(
            "document indexed",
            extra={
                "document_id": str(document.id),
                "external_id": document.external_id,
                "document_type": document.document_type.value,
                "status": document.status.value,
                "chunk_count": len(chunks),
                "embedding_model": self.embedding_model,
                "replaced": replaced,
            },
        )

        return IndexOutcome(
            document_id=str(document.id),
            title=document.title,
            chunk_count=len(chunks),
            replaced=replaced,
        )

    # --- Guards -----------------------------------------------------------

    @staticmethod
    def _guard_cited_chunks(session: Session, document: Document) -> None:
        """Refuse to replace chunks that stored answers cite.

        `citations.chunk_id` is ON DELETE RESTRICT, so the database would reject
        this anyway; catching it here turns an opaque IntegrityError into an
        explanation with a way forward.
        """
        cited = session.scalar(
            select(func.count())
            .select_from(Citation)
            .where(Citation.document_id == document.id)
        )
        if not cited:
            return

        raise CitedDocumentError(
            f"{cited} stored citation(s) reference this document, so replacing its "
            "chunks would break the audit trail of answers already given.\n"
            "Options:\n"
            "  - ingest the new version under a different external_id, and mark "
            "this one MODIFICADO or DEROGADO;\n"
            "  - or delete the affected conversations first, if this corpus is "
            "still disposable test data."
        )

    # --- Writes -----------------------------------------------------------

    def _create_document(
        self,
        *,
        metadata: DocumentMetadata,
        content_hash: str,
        source_name: str,
        source_url: str | None,
        source_path: Path | None,
        status: DocumentStatus,
        status_note: str | None,
    ) -> Document:
        return Document(
            external_id=metadata.external_id,
            title=metadata.title,
            document_type=metadata.document_type,
            issuing_entity=metadata.issuing_entity,
            court=metadata.court,
            jurisdiction=metadata.jurisdiction,
            legal_area=metadata.legal_area,
            publication_date=metadata.publication_date,
            status=status,
            status_note=status_note,
            source_name=source_name,
            source_url=source_url,
            raw_storage_path=str(source_path) if source_path else None,
            content_hash=content_hash,
            embedding_model=self.embedding_model,
            doc_metadata=dict(metadata.extra),
        )

    def _update_document(
        self,
        document: Document,
        *,
        metadata: DocumentMetadata,
        content_hash: str,
        source_url: str | None,
        source_path: Path | None,
        status: DocumentStatus,
        status_note: str | None,
    ) -> Document:
        """Refresh a stored document from a newly extracted version.

        `status` is only overwritten when the caller passed something other than
        the default. Vigencia is usually curated by an operator or derived from
        `document_relations`, and a routine re-ingest must not reset a
        hand-corrected DEROGADO back to DESCONOCIDO.
        """
        document.title = metadata.title
        document.document_type = metadata.document_type
        document.issuing_entity = metadata.issuing_entity
        document.court = metadata.court
        document.jurisdiction = metadata.jurisdiction
        document.legal_area = metadata.legal_area
        document.publication_date = metadata.publication_date
        document.content_hash = content_hash
        document.embedding_model = self.embedding_model

        if source_url:
            document.source_url = source_url
        if source_path:
            document.raw_storage_path = str(source_path)

        if status is not DocumentStatus.DESCONOCIDO:
            document.status = status
            document.status_note = status_note

        document.doc_metadata = dict(metadata.extra)
        return document

    @staticmethod
    def _delete_chunks(session: Session, document: Document) -> None:
        session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        session.flush()

    def _insert_chunks(
        self,
        session: Session,
        document: Document,
        chunks: list[LegalChunk],
        vectors: list[list[float]],
    ) -> None:
        """Insert chunk rows.

        `content_tsv` is a generated column, so PostgreSQL computes the lexical
        index itself on write and it can never drift from `content`.
        """
        session.add_all(
            Chunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                section=chunk.section,
                article_number=chunk.article_number,
                hierarchy_path=chunk.hierarchy_path,
                content=chunk.content,
                token_count=chunk.token_count,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                embedding=vector,
                embedding_model=self.embedding_model,
                chunk_metadata=_chunk_metadata(chunk),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        )

    @staticmethod
    def _count_chunks(session: Session, document: Document) -> int:
        return (
            session.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_id == document.id)
            )
            or 0
        )


def _chunk_metadata(chunk: LegalChunk) -> dict[str, object]:
    """Per-chunk extras worth keeping.

    Partial chunks are flagged so a citation can say "part 2 of 4 of Artículo 15"
    rather than implying the excerpt is the whole article.
    """
    data: dict[str, object] = {}
    if chunk.is_partial:
        data["is_partial"] = True
        data["part_index"] = chunk.part_index
        data["part_total"] = chunk.part_total
    if chunk.metadata:
        data.update(chunk.metadata)
    return data

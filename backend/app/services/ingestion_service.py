"""Document ingestion service with automatic chunking and embedding.

Handles the complete ingestion pipeline:
1. Parse document (PDF/DOCX/TXT) → markdown
2. Chunk with LegalTextSplitter
3. Generate embeddings
4. Persist Document + Chunks to database
5. Detect duplicates by content hash
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, DocumentType, Jurisdiction
from app.providers.embeddings import EmbeddingProvider
from app.services.document_parser import parse_document_to_markdown
from app.services.legal_text_splitter import LegalTextSplitter

logger = get_logger(__name__)


class IngestionService:
    """Handles document ingestion with automatic chunking and embedding."""

    def __init__(
        self,
        session: Session,
        embedding_provider: EmbeddingProvider,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.session = session
        self.embedding_provider = embedding_provider
        self.splitter = LegalTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def compute_content_hash(self, file_bytes: bytes) -> str:
        """Compute SHA-256 hash of file content for duplicate detection."""
        return hashlib.sha256(file_bytes).hexdigest()

    def check_duplicate(
        self,
        source_name: str,
        external_id: str | None = None,
        content_hash: str | None = None,
    ) -> Document | None:
        """Check if document already exists by external_id or content_hash.

        Returns existing document if found, None otherwise.
        """
        if external_id:
            stmt = select(Document).where(
                Document.source_name == source_name,
                Document.external_id == external_id,
            )
            existing = self.session.execute(stmt).scalar_one_or_none()
            if existing:
                logger.info(
                    "Duplicate detected by external_id",
                    extra={"external_id": external_id, "document_id": str(existing.id)},
                )
                return existing

        if content_hash:
            stmt = select(Document).where(Document.content_hash == content_hash)
            existing = self.session.execute(stmt).scalar_one_or_none()
            if existing:
                logger.info(
                    "Duplicate detected by content_hash",
                    extra={"content_hash": content_hash, "document_id": str(existing.id)},
                )
                return existing

        return None

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        # Document metadata
        title: str | None = None,
        external_id: str | None = None,
        document_type: DocumentType = DocumentType.LEY,
        issuing_entity: str | None = None,
        jurisdiction: Jurisdiction = Jurisdiction.NACIONAL,
        publication_date: date | None = None,
        effective_date: date | None = None,
        status: DocumentStatus = DocumentStatus.DESCONOCIDO,
        status_note: str | None = None,
        source_name: str = "Upload manual",
        source_url: str | None = None,
        doc_metadata: dict[str, Any] | None = None,
        # Ingestion options
        skip_if_duplicate: bool = True,
        force_reembed: bool = False,
    ) -> tuple[Document, int]:
        """Ingest a legal document with automatic chunking and embedding.

        Returns:
            (document, chunk_count)
        """
        # 1. Compute content hash
        content_hash = self.compute_content_hash(file_bytes)

        # 2. Check for duplicates
        if skip_if_duplicate:
            existing = self.check_duplicate(source_name, external_id, content_hash)
            if existing:
                chunk_count = self.session.query(Chunk).filter(
                    Chunk.document_id == existing.id
                ).count()
                logger.info(
                    "Skipping duplicate document",
                    extra={"document_id": str(existing.id), "title": existing.title},
                )
                return existing, chunk_count

        # 3. Parse to markdown
        logger.info("Parsing document to markdown", extra={"filename": filename})
        parse_result = parse_document_to_markdown(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        # 4. Chunk the markdown
        logger.info(
            "Chunking document",
            extra={
                "filename": filename,
                "markdown_tokens": parse_result.markdown_tokens_est,
            },
        )
        chunks_data = self.splitter.split_text(parse_result.markdown)
        logger.info(
            "Document chunked",
            extra={"filename": filename, "chunk_count": len(chunks_data)},
        )

        if not chunks_data:
            raise ValueError(f"Document {filename} produced zero chunks after splitting")

        # 5. Generate embeddings for all chunks
        logger.info(
            "Generating embeddings",
            extra={"filename": filename, "chunk_count": len(chunks_data)},
        )
        chunk_texts = [c["content"] for c in chunks_data]
        embeddings = await self.embedding_provider.embed_batch(chunk_texts)

        # 6. Create Document row
        document = Document(
            title=title or filename,
            external_id=external_id,
            document_type=document_type,
            issuing_entity=issuing_entity,
            jurisdiction=jurisdiction,
            publication_date=publication_date,
            effective_date=effective_date,
            status=status,
            status_note=status_note,
            source_name=source_name,
            source_url=source_url,
            content_hash=content_hash,
            embedding_model=self.embedding_provider.model_name,
            doc_metadata=doc_metadata or {},
        )
        self.session.add(document)
        self.session.flush()  # Get document.id before creating chunks

        # 7. Create Chunk rows with embeddings
        chunks: list[Chunk] = []
        for idx, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunk = Chunk(
                document_id=document.id,
                chunk_index=idx,
                section=chunk_data.get("section"),
                article_number=chunk_data.get("article_number"),
                hierarchy_path=chunk_data.get("hierarchy_path"),
                content=chunk_data["content"],
                token_count=chunk_data.get("token_count", len(chunk_data["content"]) // 4),
                char_start=chunk_data.get("char_start"),
                char_end=chunk_data.get("char_end"),
                embedding=embedding,
                embedding_model=self.embedding_provider.model_name,
                chunk_metadata=chunk_data.get("metadata", {}),
            )
            chunks.append(chunk)

        self.session.bulk_save_objects(chunks, return_defaults=False)
        self.session.commit()

        logger.info(
            "Document ingested successfully",
            extra={
                "document_id": str(document.id),
                "title": document.title,
                "chunk_count": len(chunks),
                "embedding_model": self.embedding_provider.model_name,
            },
        )

        return document, len(chunks)

    async def reingest_document(
        self,
        document_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[Document, int]:
        """Re-ingest an existing document (replaces all chunks).

        Use this to fix corrupted documents or update content.
        """
        # 1. Get existing document
        document = self.session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(
            "Re-ingesting document",
            extra={"document_id": document_id, "title": document.title},
        )

        # 2. Delete old chunks
        self.session.query(Chunk).filter(Chunk.document_id == document.id).delete()

        # 3. Parse to markdown
        parse_result = parse_document_to_markdown(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        # 4. Chunk the markdown
        chunks_data = self.splitter.split_text(parse_result.markdown)
        if not chunks_data:
            raise ValueError(f"Document {filename} produced zero chunks after splitting")

        # 5. Generate embeddings
        chunk_texts = [c["content"] for c in chunks_data]
        embeddings = await self.embedding_provider.embed_batch(chunk_texts)

        # 6. Update document metadata
        document.content_hash = self.compute_content_hash(file_bytes)
        document.embedding_model = self.embedding_provider.model_name

        # 7. Create new chunks
        chunks: list[Chunk] = []
        for idx, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunk = Chunk(
                document_id=document.id,
                chunk_index=idx,
                section=chunk_data.get("section"),
                article_number=chunk_data.get("article_number"),
                hierarchy_path=chunk_data.get("hierarchy_path"),
                content=chunk_data["content"],
                token_count=chunk_data.get("token_count", len(chunk_data["content"]) // 4),
                char_start=chunk_data.get("char_start"),
                char_end=chunk_data.get("char_end"),
                embedding=embedding,
                embedding_model=self.embedding_provider.model_name,
                chunk_metadata=chunk_data.get("metadata", {}),
            )
            chunks.append(chunk)

        self.session.bulk_save_objects(chunks, return_defaults=False)
        self.session.commit()

        logger.info(
            "Document re-ingested successfully",
            extra={
                "document_id": str(document.id),
                "title": document.title,
                "chunk_count": len(chunks),
            },
        )

        return document, len(chunks)

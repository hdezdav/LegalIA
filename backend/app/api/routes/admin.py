"""Admin-only endpoints for document ingestion and management."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentSuperuser, DbSession
from app.core.logging import get_logger
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, DocumentType, Jurisdiction
from app.db.models.user import User
from app.providers.embeddings import get_embedding_provider
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Max upload limit: 50 MB for admin uploads
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class IngestionResponse(BaseModel):
    document_id: str
    title: str
    chunk_count: int
    embedding_model: str
    was_duplicate: bool
    message: str


class DocumentListItem(BaseModel):
    id: str
    title: str
    document_type: str
    status: str
    chunk_count: int
    publication_date: date | None
    created_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class CorpusIngestRequest(BaseModel):
    url: str
    source_name: str = "Web scraper"
    document_type: DocumentType = DocumentType.LEY
    jurisdiction: Jurisdiction = Jurisdiction.NACIONAL


class CorpusIngestResponse(BaseModel):
    success: bool
    message: str
    documents_ingested: int


@router.post(
    "/documents",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new legal document",
)
async def ingest_document(
    db: DbSession,
    current_user: CurrentSuperuser,
    file: UploadFile = File(..., description="PDF, DOCX, or TXT legal document"),
    title: str = Form(..., description="Document title"),
    external_id: str | None = Form(None, description="External identifier (e.g. LEY_1437_2011)"),
    document_type: DocumentType = Form(DocumentType.LEY, description="Document type"),
    issuing_entity: str | None = Form(None, description="Issuing entity (e.g. Congreso de la República)"),
    jurisdiction: Jurisdiction = Form(Jurisdiction.NACIONAL, description="Jurisdiction"),
    publication_date: date | None = Form(None, description="Publication date (YYYY-MM-DD)"),
    effective_date: date | None = Form(None, description="Effective date (YYYY-MM-DD)"),
    status: DocumentStatus = Form(DocumentStatus.DESCONOCIDO, description="Document status"),
    status_note: str | None = Form(None, description="Status note"),
    source_name: str = Form("Upload admin", description="Source name"),
    source_url: str | None = Form(None, description="Official source URL"),
    skip_if_duplicate: bool = Form(True, description="Skip if duplicate detected"),
) -> IngestionResponse:
    """Ingest a legal document with automatic chunking and embedding.

    **Admin only.** Automatically:
    - Parses PDF/DOCX/TXT to markdown
    - Chunks with LegalTextSplitter
    - Generates embeddings
    - Detects duplicates by content hash or external_id
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    content_type = file.content_type or "application/octet-stream"

    # Get embedding provider
    embedding_provider = get_embedding_provider()

    # Create ingestion service
    ingestion_service = IngestionService(
        session=db,
        embedding_provider=embedding_provider,
    )

    try:
        # Ingest document
        document, chunk_count = await ingestion_service.ingest_document(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=content_type,
            title=title,
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
            skip_if_duplicate=skip_if_duplicate,
        )

        was_duplicate = chunk_count > 0 and skip_if_duplicate
        message = (
            f"Document '{title}' already exists, skipped ingestion"
            if was_duplicate
            else f"Document '{title}' ingested successfully with {chunk_count} chunks"
        )

        return IngestionResponse(
            document_id=str(document.id),
            title=document.title,
            chunk_count=chunk_count,
            embedding_model=document.embedding_model or "unknown",
            was_duplicate=was_duplicate,
            message=message,
        )

    except ValueError as exc:
        logger.error("Ingestion validation error", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Ingestion failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document",
        ) from exc


@router.post(
    "/documents/{document_id}/reingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-ingest an existing document",
    
)
async def reingest_document(
    document_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
    file: UploadFile = File(..., description="PDF, DOCX, or TXT legal document"),
) -> IngestionResponse:
    """Re-ingest an existing document (replaces all chunks).

    **Admin only.** Use this to:
    - Fix corrupted documents
    - Update document content
    - Re-process with new chunking strategy
    - Re-generate embeddings with new provider
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Get embedding provider
    embedding_provider = get_embedding_provider()

    # Create ingestion service
    ingestion_service = IngestionService(
        session=db,
        embedding_provider=embedding_provider,
    )

    try:
        document, chunk_count = await ingestion_service.reingest_document(
            document_id=document_id,
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=content_type,
        )

        return IngestionResponse(
            document_id=str(document.id),
            title=document.title,
            chunk_count=chunk_count,
            embedding_model=document.embedding_model or "unknown",
            was_duplicate=False,
            message=f"Document '{document.title}' re-ingested successfully with {chunk_count} chunks",
        )

    except ValueError as exc:
        logger.error("Re-ingestion validation error", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Re-ingestion failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-ingest document",
        ) from exc


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all documents",
    
)
async def list_documents(
    db: DbSession,
    current_user: CurrentSuperuser,
) -> DocumentListResponse:
    """List all documents in the corpus with chunk counts.

    **Admin only.**
    """
    from sqlalchemy import func

    stmt = (
        db.query(
            Document.id,
            Document.title,
            Document.document_type,
            Document.status,
            Document.publication_date,
            Document.created_at,
            func.count(Chunk.id).label("chunk_count"),
        )
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )

    results = stmt.all()

    documents = [
        DocumentListItem(
            id=str(row.id),
            title=row.title,
            document_type=row.document_type.value,
            status=row.status.value,
            chunk_count=row.chunk_count,
            publication_date=row.publication_date,
            created_at=row.created_at.isoformat(),
        )
        for row in results
    ]

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
    )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
):
    """Delete a document and all its chunks.

    **Admin only.** This is irreversible.
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    logger.warning(
        "Deleting document",
        extra={
            "document_id": document_id,
            "title": document.title,
            "admin_user_id": str(current_user.id),
        },
    )

    db.delete(document)
    db.commit()


@router.post("/corpus/ingest")
async def ingest_corpus(
    request: CorpusIngestRequest,
    db: DbSession,
    current_superuser: CurrentSuperuser,
) -> CorpusIngestResponse:
    """Ingest legal corpus from a URL (web scraping).

    **Admin only.** Scrapes the URL and ingests all found documents.
    """
    from app.services.corpus_scraper import CorpusScraper

    scraper = CorpusScraper(db=db)

    try:
        count = await scraper.scrape_and_ingest(
            url=request.url,
            source_name=request.source_name,
            document_type=request.document_type,
            jurisdiction=request.jurisdiction,
        )

        return CorpusIngestResponse(
            success=True,
            message=f"Successfully ingested {count} documents from {request.url}",
            documents_ingested=count,
        )
    except Exception as exc:
        logger.error("Corpus ingestion failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest corpus: {str(exc)}",
        ) from exc


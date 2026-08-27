"""File upload, MarkItDown conversion, and legal document analysis router."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.document_parser import parse_document_to_markdown

logger = get_logger(__name__)

router = APIRouter(tags=["Files & MarkItDown"])

# Max upload limit: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


class FileStatsResponse(BaseModel):
    raw_bytes: int
    raw_tokens_est: int
    markdown_tokens_est: int
    token_reduction_pct: float
    word_count: int
    char_count: int


class FileAnalysisResponse(BaseModel):
    doc_type: str
    jurisdiction: str
    radicado: str | None = None
    parties: dict[str, str | None]
    key_clauses: list[dict[str, str]]
    filename: str


class FileParseResponse(BaseModel):
    filename: str
    content_type: str
    markdown: str
    stats: FileStatsResponse
    analysis: FileAnalysisResponse


@router.post(
    "/parse",
    response_model=FileParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert legal document to token-optimized Markdown via MarkItDown",
)
async def parse_file(
    file: UploadFile = File(..., description="PDF, DOCX, TXT, or scanned legal document"),
) -> FileParseResponse:
    """Accepts a legal file, converts it into structured Markdown via MarkItDown,

    estimates token savings, and extracts key Colombian procedural entities.
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

    try:
        result = parse_document_to_markdown(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=content_type,
        )
    except Exception as exc:
        logger.error("file parse failure", extra={"filename": file.filename}, exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse and convert document to Markdown",
        ) from exc

    return FileParseResponse(
        filename=result.filename,
        content_type=result.content_type,
        markdown=result.markdown,
        stats=FileStatsResponse(
            raw_bytes=result.raw_bytes,
            raw_tokens_est=result.raw_tokens_est,
            markdown_tokens_est=result.markdown_tokens_est,
            token_reduction_pct=result.token_reduction_pct,
            word_count=result.word_count,
            char_count=result.char_count,
        ),
        analysis=FileAnalysisResponse(
            doc_type=result.analysis.get("doc_type", "Documento Jurídico"),
            jurisdiction=result.analysis.get("jurisdiction", "Jurisdicción Ordinaria"),
            radicado=result.analysis.get("radicado"),
            parties=result.analysis.get("parties", {}),
            key_clauses=result.analysis.get("key_clauses", []),
            filename=result.filename,
        ),
    )

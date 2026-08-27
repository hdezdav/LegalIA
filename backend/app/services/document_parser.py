"""Legal Document Parser & Markdown Conversion Service.

Leverages Microsoft's `markitdown` engine combined with resilient legal text
normalizers (removing page headers/footers, formatting noise, and layout bloat)
to minimize LLM token consumption while preserving critical legal semantics.
"""

from __future__ import annotations

import io
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Fallback / primary MarkItDown instance
_markitdown_instance: Any = None


def get_markitdown() -> Any:
    global _markitdown_instance
    if _markitdown_instance is None:
        try:
            from markitdown import MarkItDown
            _markitdown_instance = MarkItDown()
        except Exception as exc:
            logger.warning("markitdown library could not be initialized, using fallback", exc_info=exc)
            _markitdown_instance = False
    return _markitdown_instance


@dataclass(frozen=True)
class DocumentParseResult:
    filename: str
    content_type: str
    markdown: str
    raw_bytes: int
    raw_tokens_est: int
    markdown_tokens_est: int
    token_reduction_pct: float
    word_count: int
    char_count: int
    analysis: dict[str, Any]


def estimate_tokens(text: str) -> int:
    """Fast, reliable token estimation for Spanish legal text (approx 3.8 chars/token)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


def clean_legal_markdown(md_text: str) -> str:
    """Cleans repetitive artifacts, excess newlines, and page numbering from legal documents."""
    if not md_text:
        return ""

    # Normalize carriage returns
    text = md_text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive repeated blank lines (3+ -> 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove common repetitive footer/header lines in Colombian legal docs (e.g. "Página X de Y", "Calle 12 No...")
    text = re.sub(r"(?im)^\s*p[aá]gina\s+\d+\s+(?:de\s+\d+)?\s*$", "", text)
    text = re.sub(r"(?im)^\s*folio\s+\d+\s*$", "", text)

    # Trim leading/trailing whitespace
    return text.strip()


def analyze_colombian_legal_doc(text: str, filename: str) -> dict[str, Any]:
    """Extracts key structural legal metadata from Colombian legal documents."""
    text_lower = text.lower()

    # 1. Document Type Detection
    doc_type = "Documento Jurídico General"
    if any(k in text_lower for k in ["accion de tutela", "acción de tutela", "juez de tutela"]):
        doc_type = "Acción de Tutela"
    elif any(k in text_lower for k in ["demanda ordinaria", "proceso ordinario laboral", "cptss"]):
        doc_type = "Demanda Ordinaria Laboral"
    elif any(k in text_lower for k in ["demanda declarativa", "proceso verbal", "cgp", "ley 1564"]):
        doc_type = "Demanda Civil / CGP"
    elif any(k in text_lower for k in ["contrato de arrendamiento", "contrato de prestacion", "contrato de trabajo", "contrato"]):
        doc_type = "Contrato / Minuta"
    elif any(k in text_lower for k in ["derecho de peticion", "derecho de petición", "articulo 23 cp"]):
        doc_type = "Derecho de Petición"
    elif any(k in text_lower for k in ["sentencia", "corte constitucional", "corte suprema", "consejo de estado"]):
        doc_type = "Providencia / Sentencia Judicial"
    elif any(k in text_lower for k in ["recurso de apelacion", "recurso de reposicion", "recurso de queja"]):
        doc_type = "Recurso Procesal"

    # 2. Jurisdiction Detection
    jurisdiction = "Jurisdicción Ordinaria (Colombia)"
    if "constitucional" in text_lower or "tutela" in text_lower:
        jurisdiction = "Jurisdicción Constitucional"
    elif "laboral" in text_lower or "cst" in text_lower:
        jurisdiction = "Jurisdicción Laboral y Seguridad Social"
    elif "civil" in text_lower or "cgp" in text_lower or "comercial" in text_lower:
        jurisdiction = "Jurisdicción Civil y Comercial"
    elif "administrativ" in text_lower or "cpaca" in text_lower or "consejo de estado" in text_lower:
        jurisdiction = "Jurisdicción de lo Contencioso Administrativo"
    elif "penal" in text_lower or "fiscal" in text_lower or "ley 906" in text_lower:
        jurisdiction = "Jurisdicción Penal"

    # 3. Radicado / Case Number Detection
    radicado_match = re.search(r"(?:radicaci[oó]n|radicado|expediente|n[uú]mero)\s*(?:no\.?|n°|:)?\s*([0-9\-]{8,25})", text, re.IGNORECASE)
    radicado = radicado_match.group(1).strip() if radicado_match else None

    # 4. Extract Detected Parties if present
    demandante = None
    demandado = None

    pte_match = re.search(r"(?:demandante|accionante|solicitante|convocante)\s*(?:es|:|\-)?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.]{3,50})", text, re.IGNORECASE)
    if pte_match:
        demandante = pte_match.group(1).strip()

    pda_match = re.search(r"(?:demandad[oa]|accionad[oa]|solicitad[oa]|convocad[oa])\s*(?:es|:|\-)?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s\.]{3,50})", text, re.IGNORECASE)
    if pda_match:
        demandado = pda_match.group(1).strip()

    # 5. Extract Sample Clauses or Key Sections
    key_clauses: list[dict[str, str]] = []
    clause_matches = re.findall(r"(?im)^\s*(?:cl[aá]usula|art[ií]culo|hecho|pretensi[oó]n)\s+([^\n\:\.]{1,40})[:\.\-]\s*([^\n]+)", text)
    for title, snippet in clause_matches[:5]:
        if len(snippet.strip()) > 10:
            key_clauses.append({
                "title": title.strip().title(),
                "summary": snippet.strip()[:140] + ("..." if len(snippet) > 140 else "")
            })

    return {
        "doc_type": doc_type,
        "jurisdiction": jurisdiction,
        "radicado": radicado,
        "parties": {
            "demandante": demandante,
            "demandado": demandado,
        },
        "key_clauses": key_clauses,
        "filename": filename,
    }


def parse_document_to_markdown(
    file_bytes: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
) -> DocumentParseResult:
    """Converts uploaded file into token-optimized Markdown with legal metadata."""
    raw_size = len(file_bytes)
    markdown_output = ""
    suffix = Path(filename).suffix.lower()

    # Strategy A: Use Microsoft's MarkItDown
    md_engine = get_markitdown()
    if md_engine:
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                res = md_engine.convert(tmp_path)
                markdown_output = res.text_content or ""
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("markitdown conversion error, falling back to dedicated parsers", exc_info=exc)
            markdown_output = ""

    # Strategy B: Fallback dedicated parsers if MarkItDown produced empty or failed
    if not markdown_output.strip():
        if suffix in [".pdf"] or "pdf" in content_type:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                pages = []
                for i, page in enumerate(reader.pages):
                    ptxt = page.extract_text() or ""
                    if ptxt.strip():
                        pages.append(f"### Página {i+1}\n\n{ptxt.strip()}")
                markdown_output = "\n\n---\n\n".join(pages)
            except Exception as exc:
                logger.error("pypdf fallback failed", exc_info=exc)

        elif suffix in [".docx"] or "wordprocessingml" in content_type:
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                markdown_output = "\n\n".join(paras)
            except Exception as exc:
                logger.error("python-docx fallback failed", exc_info=exc)

        elif suffix in [".txt", ".md", ".json", ".csv"] or "text" in content_type:
            try:
                markdown_output = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                markdown_output = str(file_bytes, errors="replace")

    # Clean & normalize markdown
    cleaned_markdown = clean_legal_markdown(markdown_output)
    if not cleaned_markdown:
        cleaned_markdown = f"# {filename}\n\n*(Documento vacío o sin texto extraíble)*"

    # Token calculations
    # Raw token estimate assumes unoptimized binary / raw text representation
    raw_tokens_est = estimate_tokens(cleaned_markdown) + max(50, int(raw_size / 20))
    markdown_tokens_est = estimate_tokens(cleaned_markdown)
    reduction = 0.0
    if raw_tokens_est > markdown_tokens_est:
        reduction = round(((raw_tokens_est - markdown_tokens_est) / raw_tokens_est) * 100, 1)

    words = len(cleaned_markdown.split())
    chars = len(cleaned_markdown)

    # Colombian Legal Analysis
    analysis = analyze_colombian_legal_doc(cleaned_markdown, filename)

    return DocumentParseResult(
        filename=filename,
        content_type=content_type,
        markdown=cleaned_markdown,
        raw_bytes=raw_size,
        raw_tokens_est=raw_tokens_est,
        markdown_tokens_est=markdown_tokens_est,
        token_reduction_pct=reduction,
        word_count=words,
        char_count=chars,
        analysis=analysis,
    )

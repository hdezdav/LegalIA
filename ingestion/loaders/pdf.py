"""PDF loader.

Text-layer extraction only. Scanned PDFs are detected and rejected rather than
ingested as a handful of stray characters: a document that silently yields almost
no text would produce embeddings for noise, and noise in the corpus is worse than
a missing document, because retrieval can return it and a citation can point at it.

OCR is deliberately out of scope for the MVP (section 40: no GPU, no heavy local
models). The rejection message names OCR as the remedy so the operator knows what
the file needs.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ingestion.loaders.base import DocumentLoader, LoadedDocument, LoaderError

# Below this many extracted characters per page, the file is treated as scanned.
# Even a sparse legal cover page carries more than this; a scanned page typically
# yields 0.
_MIN_CHARS_PER_PAGE = 50


class PDFLoader(DocumentLoader):
    suffixes = (".pdf",)

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes

    def load(self, path: Path) -> LoadedDocument:
        # Size-checked before opening, so an oversized file is refused without
        # being parsed.
        self.read_bytes(path, self.max_bytes)

        try:
            reader = PdfReader(str(path))
        except (PdfReadError, OSError, ValueError) as exc:
            raise LoaderError(f"Could not read PDF {path}: {type(exc).__name__}") from exc

        if reader.is_encrypted:
            # An empty-password decrypt covers the common case of a PDF that is
            # merely permission-protected rather than genuinely secret.
            try:
                if reader.decrypt("") == 0:
                    raise LoaderError(f"PDF is password protected: {path}")
            except (PdfReadError, NotImplementedError) as exc:
                raise LoaderError(
                    f"PDF is encrypted with an unsupported scheme: {path}"
                ) from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise LoaderError(f"PDF has no pages: {path}")

        pages = _extract_pages(reader, path)
        text = "\n\n".join(pages).strip()

        if not text:
            raise LoaderError(
                f"No text layer found in {path}. The file is likely a scan; it "
                "must be OCR'd before ingestion."
            )

        density = len(text) / page_count
        if density < _MIN_CHARS_PER_PAGE:
            raise LoaderError(
                f"Text layer in {path} is too sparse "
                f"({density:.0f} chars/page over {page_count} pages). The file is "
                "likely a scan; it must be OCR'd before ingestion."
            )

        return LoadedDocument(
            text=text,
            source_path=path,
            content_hash=self.hash_file(path),
            title=_pdf_title(reader),
            page_count=page_count,
            raw_metadata={
                "loader": "pdf",
                "page_count": page_count,
                "chars_per_page": round(density, 1),
            },
        )


def _extract_pages(reader: PdfReader, path: Path) -> list[str]:
    """Extract each page, tolerating individual page failures.

    One malformed page in a 300-page decree should not lose the other 299; the
    sparseness check above still catches a file where most pages failed.
    """
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - pypdf raises a wide variety here
            pages.append("")

    if not any(pages):
        raise LoaderError(f"Every page failed to extract in {path}")

    return pages


def _pdf_title(reader: PdfReader) -> str | None:
    """The embedded document title, when it is meaningful.

    PDF metadata titles are often a filename, an export artifact, or blank, so a
    short or path-like value is discarded instead of being trusted as the
    document's legal title.
    """
    try:
        raw = (reader.metadata or {}).get("/Title")
    except Exception:  # noqa: BLE001 - malformed metadata dictionaries
        return None

    if not raw:
        return None

    title = str(raw).strip()
    if len(title) < 10 or title.lower().endswith(".pdf") or "\\" in title:
        return None

    return title

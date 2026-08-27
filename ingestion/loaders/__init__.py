"""Loader registry.

`for_path` resolves a file to its loader by suffix. Selection is explicit rather
than sniffed: a mislabelled file should fail loudly at ingestion time, not be
half-extracted into the corpus.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from ingestion.loaders.base import DocumentLoader, LoadedDocument, LoaderError
from ingestion.loaders.html import HTMLLoader
from ingestion.loaders.pdf import PDFLoader
from ingestion.loaders.text import TextLoader


def _max_bytes() -> int:
    return settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024


def available_loaders() -> tuple[DocumentLoader, ...]:
    max_bytes = _max_bytes()
    return (
        PDFLoader(max_bytes),
        HTMLLoader(max_bytes),
        TextLoader(max_bytes),
    )


def supported_suffixes() -> tuple[str, ...]:
    return tuple(
        sorted({suffix for loader in available_loaders() for suffix in loader.suffixes})
    )


def for_path(path: Path) -> DocumentLoader:
    """Return the loader for `path`.

    Raises:
        LoaderError: no loader handles this suffix.
    """
    for loader in available_loaders():
        if loader.supports(path):
            return loader

    raise LoaderError(
        f"Unsupported file type {path.suffix!r} for {path}. "
        f"Supported: {', '.join(supported_suffixes())}"
    )


def load(path: Path) -> LoadedDocument:
    """Load `path` with the loader that handles its type."""
    return for_path(path).load(path)


__all__ = [
    "DocumentLoader",
    "HTMLLoader",
    "LoadedDocument",
    "LoaderError",
    "PDFLoader",
    "TextLoader",
    "available_loaders",
    "for_path",
    "load",
    "supported_suffixes",
]

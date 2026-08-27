"""Loader interface.

A loader turns a file into raw text plus whatever provenance the format itself
carries (a PDF's title, an HTML page's canonical URL). It does no cleaning and no
splitting: those are separate stages, so a bad extraction can be diagnosed
without re-running the rest of the pipeline.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class LoaderError(Exception):
    """Raised when a file cannot be read or yields no usable text."""


@dataclass(slots=True)
class LoadedDocument:
    """Raw extraction result.

    `text` is the unmodified extraction. `content_hash` is taken over the source
    bytes, not the text, so it detects a changed source even when extraction
    happens to produce the same string.
    """

    text: str
    source_path: Path
    content_hash: str
    # Format-level hints only. Never guessed: a missing title stays absent so the
    # metadata stage can decide, rather than inheriting a filename as if it were
    # authoritative.
    title: str | None = None
    page_count: int | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)


class DocumentLoader(ABC):
    """Base class for format-specific loaders."""

    #: File suffixes this loader handles, lowercase, including the dot.
    suffixes: tuple[str, ...] = ()

    @abstractmethod
    def load(self, path: Path) -> LoadedDocument:
        """Extract text from `path`.

        Raises:
            LoaderError: the file is unreadable, or contains no extractable text.
        """

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    @staticmethod
    def hash_file(path: Path) -> str:
        """SHA-256 of the file's bytes, streamed so large PDFs stay cheap."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def read_bytes(path: Path, max_bytes: int) -> bytes:
        """Read a file, refusing anything over `max_bytes`.

        Checked before reading, so an oversized file cannot exhaust memory on the
        8 GB VPS just to be rejected afterwards.
        """
        if not path.is_file():
            raise LoaderError(f"Not a file: {path}")

        size = path.stat().st_size
        if size == 0:
            raise LoaderError(f"File is empty: {path}")
        if size > max_bytes:
            raise LoaderError(
                f"File exceeds the maximum size of {max_bytes} bytes: "
                f"{path} is {size} bytes"
            )

        return path.read_bytes()

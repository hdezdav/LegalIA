"""Plain-text loader.

Also the fallback for Markdown. Encoding is detected rather than assumed:
Colombian legal text downloaded from official portals is frequently latin-1, and
decoding it as UTF-8 mangles every accented character, which then propagates into
chunks, embeddings and quoted excerpts.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.loaders.base import DocumentLoader, LoadedDocument, LoaderError

# Tried in order. utf-8-sig first so a BOM is consumed rather than becoming a
# stray character at the start of the first chunk.
_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class TextLoader(DocumentLoader):
    suffixes = (".txt", ".text", ".md", ".markdown")

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes

    def load(self, path: Path) -> LoadedDocument:
        raw = self.read_bytes(path, self.max_bytes)
        text, encoding = _decode(raw, path)

        if not text.strip():
            raise LoaderError(f"File contains no text: {path}")

        return LoadedDocument(
            text=text,
            source_path=path,
            content_hash=self.hash_file(path),
            # No title is inferred from the filename: the metadata stage decides
            # that, with the document's own text available to it.
            title=None,
            raw_metadata={"encoding": encoding, "loader": "text"},
        )


def _decode(raw: bytes, path: Path) -> tuple[str, str]:
    """Decode bytes, returning the text and the encoding that worked.

    latin-1 is last and cannot fail, so this always terminates; recording which
    encoding was used keeps a later mojibake report diagnosable.
    """
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    raise LoaderError(f"Could not decode {path} with any known encoding")

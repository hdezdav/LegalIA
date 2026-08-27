"""Text normalization, applied between extraction and splitting.

The rule that governs every decision here: **cleaning may delete or normalize
noise, never rewrite legal wording**. A chunk's text is what gets quoted back to
the user as a verbatim excerpt and what verification compares against, so any
transformation that altered the substance of a norm would make citations lie.

Concretely, this stage is allowed to fix whitespace, join words the PDF extractor
broke across lines, drop page furniture, and normalize Unicode confusables. It is
not allowed to expand abbreviations, correct spelling, reorder text, or strip
accents.

The confusable map and `normalize_query` live in `app.core.text`, shared with
retrieval: a query must be normalized by the same rules that normalized the
indexed chunks, or lexical search quietly stops matching text it should find.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text import MULTIPLE_SPACES, fold_confusables, normalize_query

__all__ = ["CleaningReport", "clean_text", "normalize_query"]


@dataclass(slots=True)
class CleaningReport:
    """What cleaning changed. Recorded so a bad extraction stays diagnosable."""

    original_length: int
    cleaned_length: int
    dropped_lines: int
    rejoined_hyphenations: int

    @property
    def removed_ratio(self) -> float:
        if self.original_length == 0:
            return 0.0
        return 1.0 - (self.cleaned_length / self.original_length)


# --- Page furniture ---------------------------------------------------------
# Matched against a whole stripped line, so these never touch text inside a
# sentence. Anchored and case-insensitive.

_FURNITURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Página 3", "Pág. 3 de 47", "- 3 -", a bare page number.
    re.compile(r"^p[áa]g(?:ina|\.)?\s*\d+(?:\s*(?:de|/)\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^-+\s*\d+\s*-+$"),
    re.compile(r"^\d{1,4}$"),
    # Official gazette headers repeated on every page.
    re.compile(r"^diario\s+oficial(?:\s+n[oº°.]?\s*[\d.]+)?.*$", re.IGNORECASE),
    re.compile(r"^gaceta\s+(?:oficial|del\s+congreso).*$", re.IGNORECASE),
    # Portal furniture that survives HTML extraction.
    re.compile(r"^(?:imprimir|compartir|descargar|volver|inicio)$", re.IGNORECASE),
    # Horizontal rules made of punctuation.
    re.compile(r"^[\W_]{3,}$"),
)

_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")

# A word broken across lines by PDF layout: "responsabili-\ndad".
# Requires lowercase either side so it cannot join "ARTÍCULO 5.-\nEl" or a
# hyphenated case number like "C-355/\n06".
_HYPHEN_BREAK = re.compile(r"([a-záéíóúñü])-\n([a-záéíóúñü])")

# A sentence continued on the next line without punctuation. Joined with a space
# so paragraph reflowing does not glue words together.
_SOFT_WRAP = re.compile(r"([a-záéíóúñü,;])\n([a-záéíóúñü])")


def clean_text(text: str) -> tuple[str, CleaningReport]:
    """Normalize extracted text for splitting.

    Returns the cleaned text and a report of what changed.
    """
    original_length = len(text)

    # NFC composition plus confusable folding. Never NFKD, which would decompose
    # accents and change the bytes a citation excerpt must match.
    text = fold_confusables(text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text, rejoined = _rejoin_hyphenations(text)
    text, dropped = _drop_furniture(text)

    text = MULTIPLE_SPACES.sub(" ", text)
    # Collapse runs of blank lines to exactly one, preserving paragraph breaks as
    # a signal for the splitter.
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    text = text.strip()

    return text, CleaningReport(
        original_length=original_length,
        cleaned_length=len(text),
        dropped_lines=dropped,
        rejoined_hyphenations=rejoined,
    )


def _rejoin_hyphenations(text: str) -> tuple[str, int]:
    """Repair words split across lines, then reflow soft-wrapped sentences.

    Applied repeatedly because one substitution can expose another on the same
    line.
    """
    rejoined = 0
    while True:
        text, count = _HYPHEN_BREAK.subn(r"\1\2", text)
        rejoined += count
        if count == 0:
            break

    while True:
        text, count = _SOFT_WRAP.subn(r"\1 \2", text)
        if count == 0:
            break

    return text, rejoined


def _drop_furniture(text: str) -> tuple[str, int]:
    """Remove lines that are page furniture rather than legal text."""
    kept: list[str] = []
    dropped = 0

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(p.match(stripped) for p in _FURNITURE_PATTERNS):
            dropped += 1
            continue
        kept.append(stripped)

    return "\n".join(kept), dropped

"""Text normalization primitives shared by ingestion and retrieval.

These live in `app.core` rather than in `ingestion` because both sides need them
and the dependency may only run one way: `ingestion` imports from `app`, never the
reverse. Retrieval normalizing a query with the same rules that normalized the
indexed chunks is what keeps a query and its target comparable; if the two drifted
apart, lexical search would quietly stop matching text it should find.

The governing rule, inherited by every caller: normalization may fix
representation, never wording. Nothing here expands abbreviations, corrects
spelling, or strips accents — a chunk's text is quoted back to the user verbatim
as a citation excerpt, so altering substance would make citations lie.
"""

from __future__ import annotations

import re
import unicodedata

#: Unicode confusables. Legal text pasted out of Word is full of these, and they
#: break lexical search and exact-excerpt verification alike.
CHARACTER_MAP: dict[str, str] = {
    " ": " ",  # non-breaking space
    " ": " ",  # thin space
    " ": " ",  # narrow no-break space
    "​": "",  # zero-width space
    "‌": "",  # zero-width non-joiner
    "‍": "",  # zero-width joiner
    "﻿": "",  # BOM
    "‘": "'",
    "’": "'",
    "‚": "'",
    "“": '"',
    "”": '"',
    "–": "-",  # en dash
    "—": "-",  # em dash
    "―": "-",  # horizontal bar
    "…": "...",
    "­": "",  # soft hyphen
    "\t": " ",
}

MULTIPLE_SPACES = re.compile(r"[ ]{2,}")

#: Characters per token for Spanish legal prose. A ratio rather than a tokenizer
#: call: this runs per candidate split during recursion, where `tiktoken` is both
#: the wrong vocabulary for Claude and far too slow. Measured against Colombian
#: legal text, which is denser than English. Exact counts always come from the
#: provider's own usage reporting.
CHARS_PER_TOKEN = 3.6


def fold_confusables(text: str) -> str:
    """Apply NFC composition and replace confusable characters.

    NFC, never NFKD: NFKD would decompose accents into separate code points,
    changing the bytes a citation excerpt has to match.
    """
    text = unicodedata.normalize("NFC", text)
    for source, replacement in CHARACTER_MAP.items():
        text = text.replace(source, replacement)
    return text


def normalize_query(query: str) -> str:
    """Normalize a user question before embedding and lexical search.

    Lighter than ingestion's `clean_text`: only the transformations that must
    match how chunk text was normalized, so a query and its target agree.

    Accents are deliberately kept. The `legal_es` FTS configuration strips them at
    the database level, which handles accent-insensitivity for lexical search
    without changing what gets embedded.
    """
    return MULTIPLE_SPACES.sub(" ", fold_confusables(query).replace("\n", " ")).strip()


def estimate_tokens(text: str) -> int:
    """Approximate token count for Spanish legal prose."""
    return max(1, round(len(text) / CHARS_PER_TOKEN))


def estimate_tokens_for_length(length: int) -> int:
    """Token estimate for a span length, without materializing the substring."""
    return max(1, round(length / CHARS_PER_TOKEN))

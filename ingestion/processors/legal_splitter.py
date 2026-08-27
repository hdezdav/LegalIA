"""Structure-aware splitting for Colombian legal text.

Splitting on character count alone is what makes RAG citations vague: a chunk that
starts mid-article can only ever be cited as "somewhere in this document". This
splitter instead finds the document's own structural boundaries — artículo,
parágrafo, numeral, inciso, capítulo, considerando, resolutivo — and cuts there,
so every chunk knows its own address.

Three properties the rest of the system depends on:

* **Every chunk carries a `section` label** ("Artículo 90", "Artículo 15 >
  Parágrafo 1"), which is what a citation shows the user.
* **`char_start`/`char_end` are exact offsets into the cleaned text**, so a quoted
  excerpt can be located in the source and verified character by character.
* **Content is never rewritten.** Chunks are substrings of the input. An
  oversized article is split at sentence boundaries, and the ancestor path is
  recorded in `hierarchy_path` rather than injected into the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from app.core.text import estimate_tokens, estimate_tokens_for_length


class SectionKind(StrEnum):
    """Structural units, ordered from outermost to innermost by `depth`."""

    LIBRO = "LIBRO"
    PARTE = "PARTE"
    TITULO = "TITULO"
    CAPITULO = "CAPITULO"
    SECCION = "SECCION"
    SUBSECCION = "SUBSECCION"
    ARTICULO = "ARTICULO"
    PARAGRAFO = "PARAGRAFO"
    NUMERAL = "NUMERAL"
    LITERAL = "LITERAL"
    INCISO = "INCISO"
    # Judgment and resolution parts.
    CONSIDERANDO = "CONSIDERANDO"
    RESUELVE = "RESUELVE"
    PREAMBULO = "PREAMBULO"
    # Text before any recognized heading.
    CUERPO = "CUERPO"


#: Nesting depth per kind. Used to decide whether a new heading closes the
#: previous one or nests inside it.
_DEPTH: dict[SectionKind, int] = {
    SectionKind.PREAMBULO: 0,
    SectionKind.LIBRO: 1,
    SectionKind.PARTE: 1,
    SectionKind.TITULO: 2,
    SectionKind.CAPITULO: 3,
    SectionKind.SECCION: 4,
    SectionKind.SUBSECCION: 5,
    SectionKind.CONSIDERANDO: 6,
    SectionKind.RESUELVE: 6,
    SectionKind.ARTICULO: 6,
    SectionKind.PARAGRAFO: 7,
    SectionKind.NUMERAL: 8,
    SectionKind.LITERAL: 9,
    SectionKind.INCISO: 9,
    SectionKind.CUERPO: 10,
}


@dataclass(slots=True)
class Section:
    """A structural heading found in the text."""

    kind: SectionKind
    #: Identifier as written: "90", "15A", "1", "a", "PRIMERO", "II".
    number: str | None
    #: The heading line itself, verbatim.
    heading: str
    #: Offset of the heading's first character in the cleaned text.
    start: int

    @property
    def depth(self) -> int:
        return _DEPTH[self.kind]

    @property
    def label(self) -> str:
        """Human-readable label, e.g. "Artículo 90", "Parágrafo 1"."""
        name = self.kind.value.capitalize()
        if self.kind is SectionKind.ARTICULO:
            name = "Artículo"
        elif self.kind is SectionKind.PARAGRAFO:
            name = "Parágrafo"
        elif self.kind is SectionKind.CAPITULO:
            name = "Capítulo"
        elif self.kind is SectionKind.TITULO:
            name = "Título"
        elif self.kind is SectionKind.SECCION:
            name = "Sección"
        elif self.kind is SectionKind.SUBSECCION:
            name = "Subsección"

        return f"{name} {self.number}" if self.number else name


@dataclass(slots=True)
class LegalChunk:
    """One chunk, with everything a citation needs to locate it."""

    content: str
    chunk_index: int
    #: Innermost section label, or the ancestor path when nested.
    section: str | None
    #: Article number alone, for metadata filtering.
    article_number: str | None
    #: Full ancestor path: "Título II > Capítulo I > Artículo 15".
    hierarchy_path: str | None
    char_start: int
    char_end: int
    token_count: int
    #: True when an oversized section had to be divided, so the chunk is a part
    #: of a section rather than a whole one.
    is_partial: bool = False
    part_index: int | None = None
    part_total: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


# --- Heading patterns -------------------------------------------------------
# Matched at the start of a line (MULTILINE). Ordered: the first match wins, so
# more specific patterns come first.
#
# Written against how these headings actually appear in Colombian sources:
# "ARTÍCULO 90.", "Artículo 90º.-", "ART. 90.", "PARÁGRAFO 1o.", "PARÁGRAFO
# TRANSITORIO." Accents and the ordinal markers º/o/°/ª are optional throughout,
# because they vary between transcriptions of the same norm.

_ORDINAL = r"(?:[oº°ª]\.?)?"
_SEP = r"\s*(?:[.\-–:)]|\s)"

_PATTERNS: tuple[tuple[SectionKind, re.Pattern[str]], ...] = (
    (
        SectionKind.ARTICULO,
        re.compile(
            rf"^\s*(?:ART[IÍ]CULOS?|ARTS?\.?)\s+"
            rf"(\d+[A-Za-z]?|[IVXLCDM]+|[ÚU]NICO|TRANSITORIO)"
            rf"{_ORDINAL}{_SEP}",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.PARAGRAFO,
        re.compile(
            rf"^\s*(?:PAR[AÁ]GRAFOS?|PAR[AÁ]GS?\.?|PAR\.)\s*"
            rf"(\d+|[IVXLCDM]+|[ÚU]NICO|TRANSITORIO)?"
            rf"{_ORDINAL}{_SEP}",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.LIBRO,
        re.compile(
            rf"^\s*LIBRO\s+([IVXLCDM]+|\d+|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)"
            rf"{_ORDINAL}\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.PARTE,
        re.compile(
            r"^\s*PARTE\s+([IVXLCDM]+|\d+|PRIMERA|SEGUNDA|TERCERA|CUARTA)\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.TITULO,
        re.compile(
            rf"^\s*T[IÍ]TULO\s+([IVXLCDM]+|\d+|PRELIMINAR|[ÚU]NICO){_ORDINAL}\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.CAPITULO,
        re.compile(
            rf"^\s*CAP[IÍ]TULO\s+([IVXLCDM]+|\d+|[ÚU]NICO){_ORDINAL}\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.SUBSECCION,
        re.compile(
            rf"^\s*SUBSECCI[OÓ]N\s+([IVXLCDM]+|\d+|[ÚU]NICA){_ORDINAL}\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.SECCION,
        re.compile(
            rf"^\s*SECCI[OÓ]N\s+([IVXLCDM]+|\d+|[ÚU]NICA){_ORDINAL}\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.CONSIDERANDO,
        re.compile(
            r"^\s*(CONSIDERANDO|CONSIDERACIONES(?:\s+DE\s+LA\s+CORTE)?)\s*:?\s*$",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionKind.RESUELVE,
        re.compile(
            r"^\s*(RESUELVE|DECIDE|RESUELVE\s*:|DECRETA|ORDENA|FALLA)\s*:?\s*$",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    # Ordinal resolutives: "PRIMERO.- Declarar...". Only these fixed words, so a
    # sentence beginning with an ordinal is not mistaken for a heading.
    (
        SectionKind.NUMERAL,
        re.compile(
            r"^\s*(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[EÉ]PTIMO|"
            r"OCTAVO|NOVENO|D[EÉ]CIMO)\s*[.\-–:]",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    # Numbered items: "1.", "2)", "3.1.". Requires the number to be followed by
    # punctuation and then text, so a year or a monetary amount cannot match.
    (
        SectionKind.NUMERAL,
        re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[.)]\s+(?=[A-ZÁÉÍÓÚÑa-záéíóúñ])", re.MULTILINE),
    ),
    # Lettered items: "a)", "b.", "LITERAL c)".
    (
        SectionKind.LITERAL,
        re.compile(
            r"^\s*(?:LITERAL\s+)?([a-z])\s*[.)]\s+(?=[A-ZÁÉÍÓÚÑa-záéíóúñ])",
            re.MULTILINE,
        ),
    ),
)

# Sentence boundary, used only when an oversized section must be divided.
# Requires whitespace and an uppercase or digit start, so "art. 5" and "Nº 3."
# do not end a sentence.
_SENTENCE_END = re.compile(r"(?<=[.;:])\s+(?=[A-ZÁÉÍÓÚÑ0-9¿«\"])")

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


# Token estimation is shared with retrieval and context construction via
# app.core.text, so a chunk sized at ingestion time and a context budget checked
# at query time agree on what a token is.


class LegalTextSplitter:
    """Splits legal text at its structural boundaries.

    Args:
        chunk_size: target chunk size in tokens.
        chunk_overlap: token overlap applied only when dividing an oversized
            section. Structural chunks never overlap: an article is a complete
            unit, and duplicating its neighbours' text would make retrieval
            return the same passage twice under different ids.
        min_chunk_size: sections shorter than this are merged forward, so a
            one-line heading does not become its own chunk.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if min_chunk_size >= chunk_size:
            raise ValueError("min_chunk_size must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    # --- Public API --------------------------------------------------------

    def split(self, text: str) -> list[LegalChunk]:
        """Split `text` into chunks.

        Offsets in the result index into `text` exactly as given, so callers must
        pass the same cleaned string they store as the document's text.
        """
        if not text.strip():
            return []

        sections = self.find_sections(text)

        if not sections:
            # No recognizable structure: fall back to sentence-aware splitting,
            # still never cutting mid-word.
            return self._split_unstructured(text)

        spans = self._to_spans(text, sections)
        spans = self._merge_short_spans(spans)

        chunks: list[LegalChunk] = []
        for span_sections, start, end in spans:
            chunks.extend(self._emit(text, span_sections, start, end, len(chunks)))

        return chunks

    def find_sections(self, text: str) -> list[Section]:
        """Locate every structural heading, in document order.

        Overlapping matches are resolved by preferring the earliest start and,
        at equal starts, the outermost kind.
        """
        found: list[Section] = []

        for kind, pattern in _PATTERNS:
            for match in pattern.finditer(text):
                number = None
                if match.lastindex:
                    raw = match.group(1)
                    number = raw.strip() if raw else None
                    # A heading word captured as its own number ("CONSIDERANDO")
                    # carries no identifier.
                    if number and number.upper() == kind.value:
                        number = None

                found.append(
                    Section(
                        kind=kind,
                        number=number,
                        heading=match.group(0).strip(),
                        start=match.start(),
                    )
                )

        found.sort(key=lambda s: (s.start, s.depth))

        # Drop duplicates at the same offset, keeping the outermost kind.
        deduped: list[Section] = []
        for section in found:
            if deduped and deduped[-1].start == section.start:
                continue
            deduped.append(section)

        return deduped

    # --- Internals ---------------------------------------------------------

    def _to_spans(
        self, text: str, sections: list[Section]
    ) -> list[tuple[list[Section], int, int]]:
        """Convert headings into (ancestor_stack, start, end) spans.

        Each span runs from its heading to the next heading at the same or a
        shallower depth. The ancestor stack is what produces `hierarchy_path`.
        """
        spans: list[tuple[list[Section], int, int]] = []
        stack: list[Section] = []

        # Text before the first heading is its own span when substantial.
        if sections[0].start > 0:
            preamble = text[: sections[0].start]
            if estimate_tokens(preamble) >= self.min_chunk_size:
                spans.append(([], 0, sections[0].start))

        for index, section in enumerate(sections):
            while stack and stack[-1].depth >= section.depth:
                stack.pop()
            stack.append(section)

            end = sections[index + 1].start if index + 1 < len(sections) else len(text)
            spans.append((list(stack), section.start, end))

        return spans

    def _merge_short_spans(
        self, spans: list[tuple[list[Section], int, int]]
    ) -> list[tuple[list[Section], int, int]]:
        """Merge a span that is too short into the following one.

        Structural containers behave this way naturally: "CAPÍTULO II" on its own
        line is a heading for the articles beneath it, not a chunk. Merging keeps
        the heading attached to the text it introduces.
        """
        merged: list[tuple[list[Section], int, int]] = []

        for stack, start, end in spans:
            if not merged:
                merged.append((stack, start, end))
                continue

            previous_stack, previous_start, previous_end = merged[-1]
            previous_tokens = estimate_tokens_for_length(previous_end - previous_start)

            if previous_tokens < self.min_chunk_size:
                combined = estimate_tokens_for_length(end - previous_start)
                if combined <= self.chunk_size:
                    # Keep the shallower stack: the merged chunk is introduced by
                    # the container heading.
                    keep = (
                        previous_stack
                        if len(previous_stack) <= len(stack)
                        else stack
                    )
                    merged[-1] = (keep, previous_start, end)
                    continue

            merged.append((stack, start, end))

        return merged

    def _emit(
        self,
        text: str,
        stack: list[Section],
        start: int,
        end: int,
        next_index: int,
    ) -> list[LegalChunk]:
        """Produce chunks for one span, dividing it if it exceeds chunk_size."""
        body = text[start:end].strip()
        if not body:
            return []

        # Offsets must point at the stripped content, not the raw span.
        offset = start + (len(text[start:end]) - len(text[start:end].lstrip()))
        section_label, article_number, hierarchy = _describe(stack)

        if estimate_tokens(body) <= self.chunk_size:
            return [
                LegalChunk(
                    content=body,
                    chunk_index=next_index,
                    section=section_label,
                    article_number=article_number,
                    hierarchy_path=hierarchy,
                    char_start=offset,
                    char_end=offset + len(body),
                    token_count=estimate_tokens(body),
                )
            ]

        parts = self._divide(body)
        total = len(parts)

        return [
            LegalChunk(
                content=part,
                chunk_index=next_index + position,
                section=section_label,
                article_number=article_number,
                hierarchy_path=hierarchy,
                char_start=offset + part_offset,
                char_end=offset + part_offset + len(part),
                token_count=estimate_tokens(part),
                is_partial=True,
                part_index=position + 1,
                part_total=total,
            )
            for position, (part, part_offset) in enumerate(parts)
        ]

    def _divide(self, body: str) -> list[tuple[str, int]]:
        """Divide an oversized section, returning (text, offset_within_body).

        Splits at paragraph breaks first, then sentence boundaries, then — only if
        a single sentence still exceeds the budget — at whitespace. Never
        mid-word: a truncated word would corrupt both the embedding and any
        excerpt quoted from it.
        """
        units = _split_units(body)

        parts: list[tuple[str, int]] = []
        current: list[tuple[str, int]] = []
        current_tokens = 0

        for unit, unit_offset in units:
            unit_tokens = estimate_tokens(unit)

            if current and current_tokens + unit_tokens > self.chunk_size:
                parts.append(_join(current, body))
                current = _carry_over(current, self.chunk_overlap)
                current_tokens = sum(estimate_tokens(u) for u, _ in current)

            current.append((unit, unit_offset))
            current_tokens += unit_tokens

        if current:
            parts.append(_join(current, body))

        return parts

    def _split_unstructured(self, text: str) -> list[LegalChunk]:
        """Fallback for text with no recognizable legal structure."""
        body = text.strip()
        offset = len(text) - len(text.lstrip())

        if estimate_tokens(body) <= self.chunk_size:
            return [
                LegalChunk(
                    content=body,
                    chunk_index=0,
                    section=None,
                    article_number=None,
                    hierarchy_path=None,
                    char_start=offset,
                    char_end=offset + len(body),
                    token_count=estimate_tokens(body),
                )
            ]

        parts = self._divide(body)
        total = len(parts)

        return [
            LegalChunk(
                content=part,
                chunk_index=position,
                section=None,
                article_number=None,
                hierarchy_path=None,
                char_start=offset + part_offset,
                char_end=offset + part_offset + len(part),
                token_count=estimate_tokens(part),
                is_partial=True,
                part_index=position + 1,
                part_total=total,
            )
            for position, (part, part_offset) in enumerate(parts)
        ]


# --- Helpers ----------------------------------------------------------------


def _describe(stack: list[Section]) -> tuple[str | None, str | None, str | None]:
    """Derive (section label, article number, hierarchy path) from an ancestor stack."""
    if not stack:
        return None, None, None

    hierarchy = " > ".join(section.label for section in stack)

    article_number = next(
        (s.number for s in reversed(stack) if s.kind is SectionKind.ARTICULO), None
    )

    # The label shown in a citation: the innermost unit, prefixed with its
    # article when nested inside one, so "Parágrafo 1" is never ambiguous.
    innermost = stack[-1]
    if innermost.kind is SectionKind.ARTICULO or article_number is None:
        section_label = innermost.label
    else:
        section_label = f"Artículo {article_number} > {innermost.label}"

    return section_label[:512], article_number, hierarchy[:2000]


def _split_units(body: str) -> list[tuple[str, int]]:
    """Break text into the smallest units a chunk boundary may fall between."""
    units: list[tuple[str, int]] = []

    for paragraph, paragraph_offset in _spans(body, _PARAGRAPH_BREAK):
        if not paragraph.strip():
            continue
        sentences = list(_spans(paragraph, _SENTENCE_END))
        for sentence, sentence_offset in sentences:
            if sentence.strip():
                units.append((sentence, paragraph_offset + sentence_offset))

    return units or [(body, 0)]


def _spans(text: str, pattern: re.Pattern[str]) -> list[tuple[str, int]]:
    """Split on `pattern`, keeping each piece's offset within `text`."""
    pieces: list[tuple[str, int]] = []
    position = 0

    for match in pattern.finditer(text):
        pieces.append((text[position : match.start()], position))
        position = match.end()

    pieces.append((text[position:], position))
    return pieces


def _join(units: list[tuple[str, int]], body: str) -> tuple[str, int]:
    """Join consecutive units back into a verbatim substring of `body`.

    Sliced from the original rather than concatenated, so the result is exactly
    the source text and its offsets stay valid.
    """
    start = units[0][1]
    end = units[-1][1] + len(units[-1][0])
    raw = body[start:end]
    stripped = raw.strip()
    return stripped, start + (len(raw) - len(raw.lstrip()))


def _carry_over(
    units: list[tuple[str, int]], overlap_tokens: int
) -> list[tuple[str, int]]:
    """Trailing units to repeat at the start of the next part.

    Overlap exists so a sentence split across two parts of one long article is
    still retrievable from either. It applies only within a divided section.
    """
    if overlap_tokens <= 0:
        return []

    carried: list[tuple[str, int]] = []
    total = 0

    for unit, offset in reversed(units):
        carried.insert(0, (unit, offset))
        total += estimate_tokens(unit)
        if total >= overlap_tokens:
            break

    # Never carry the whole part forward: that would not make progress.
    return carried if len(carried) < len(units) else carried[1:]

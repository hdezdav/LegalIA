"""Metadata extraction from Colombian legal documents.

Reads a document's own text to recover what it *is*: a law, a decree, a judgment;
its number and year; who issued it; when it was published. That metadata is what
retrieval filters on and what a citation shows the user, so getting it wrong is
not cosmetic.

One rule governs every function here: **absence is reported, never guessed.** A
document whose type cannot be determined gets `OTRO`, not a plausible-looking
label; one with no detectable date gets `None`. And `status` is never inferred
from text at all — vigencia is derived from `document_relations` or set by an
operator, because a norm's own text almost never says it was repealed. Defaulting
a document to VIGENTE because nothing contradicted it is exactly the failure the
`DESCONOCIDO` state exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.db.models.enums import Court, DocumentType, Jurisdiction, LegalArea

# --- Document identity ------------------------------------------------------
# Anchored near the start of a line and case-insensitive, matching how these
# appear in official transcriptions: "LEY 1437 DE 2011", "Decreto 1082 de 2015",
# "SENTENCIA C-355/06", "Sentencia T-760 de 2008".

_LAW_LIKE = re.compile(
    r"\b(?P<kind>LEY\s+ESTATUTARIA|LEY|DECRETO\s+LEY|DECRETO|"
    r"ACTO\s+LEGISLATIVO|RESOLUCI[OÓ]N|CIRCULAR|ACUERDO|ORDENANZA)\s+"
    r"(?:N[oº°.]?\s*)?(?P<number>\d{1,5})\s+(?:DE|DEL)\s+(?P<year>\d{4})",
    re.IGNORECASE,
)

# Constitutional-court style docket: C-355 de 2006, T-760/08, SU-047 de 1999.
_JUDGMENT = re.compile(
    r"\b(?P<series>SU|C|T|A)\s*-\s*(?P<number>\d{1,4})\s*"
    r"(?:/\s*(?P<short_year>\d{2})|\s+(?:DE|DEL)\s+(?P<year>\d{4}))",
    re.IGNORECASE,
)

_CODE = re.compile(
    r"\bC[OÓ]DIGO\s+(?P<name>[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ\s]{3,60}?)"
    r"(?=[.,\n]|\s+ART)",
    re.IGNORECASE,
)

_CONSTITUTION = re.compile(
    r"\bCONSTITUCI[OÓ]N\s+POL[IÍ]TICA(?:\s+DE\s+COLOMBIA)?", re.IGNORECASE
)

# --- Dates ------------------------------------------------------------------

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_SPELLED_DATE = re.compile(
    r"\b(?P<day>\d{1,2})\s+de\s+(?P<month>"
    + "|".join(_MONTHS)
    + r")\s+de\s+(?P<year>\d{4})",
    re.IGNORECASE,
)

_NUMERIC_DATE = re.compile(r"\b(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})\b")

# --- Issuing bodies ---------------------------------------------------------
# Ordered: the first match wins, so more specific patterns come first.

_ISSUERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"CONGRESO\s+DE\s+COLOMBIA", re.IGNORECASE), "Congreso de Colombia"),
    (
        re.compile(r"CONGRESO\s+DE\s+LA\s+REP[UÚ]BLICA", re.IGNORECASE),
        "Congreso de la República",
    ),
    (
        re.compile(r"PRESIDENTE\s+DE\s+LA\s+REP[UÚ]BLICA", re.IGNORECASE),
        "Presidencia de la República",
    ),
    (
        re.compile(r"ASAMBLEA\s+NACIONAL\s+CONSTITUYENTE", re.IGNORECASE),
        "Asamblea Nacional Constituyente",
    ),
    (re.compile(r"\bDIAN\b|DIRECCI[OÓ]N\s+DE\s+IMPUESTOS", re.IGNORECASE), "DIAN"),
    (
        re.compile(r"MINISTERIO\s+DE\s+(?:[A-ZÁÉÍÓÚÑ]+\s*){1,4}", re.IGNORECASE),
        "",  # captured verbatim below
    ),
)

_COURTS: tuple[tuple[re.Pattern[str], Court], ...] = (
    (
        re.compile(r"CORTE\s+CONSTITUCIONAL", re.IGNORECASE),
        Court.CORTE_CONSTITUCIONAL,
    ),
    (
        re.compile(r"CORTE\s+SUPREMA\s+DE\s+JUSTICIA", re.IGNORECASE),
        Court.CORTE_SUPREMA_JUSTICIA,
    ),
    (re.compile(r"CONSEJO\s+DE\s+ESTADO", re.IGNORECASE), Court.CONSEJO_ESTADO),
    (
        re.compile(r"CONSEJO\s+SUPERIOR\s+DE\s+LA\s+JUDICATURA", re.IGNORECASE),
        Court.CONSEJO_SUPERIOR_JUDICATURA,
    ),
    (
        re.compile(r"JURISDICCI[OÓ]N\s+ESPECIAL\s+PARA\s+LA\s+PAZ|\bJEP\b", re.IGNORECASE),
        Court.JURISDICCION_ESPECIAL_PAZ,
    ),
    (
        re.compile(r"TRIBUNAL\s+ADMINISTRATIVO", re.IGNORECASE),
        Court.TRIBUNAL_ADMINISTRATIVO,
    ),
    (re.compile(r"TRIBUNAL\s+SUPERIOR", re.IGNORECASE), Court.TRIBUNAL_SUPERIOR),
)

# --- Legal area -------------------------------------------------------------
# Keyword scoring, not classification. A weak signal is reported as no signal:
# a wrong `legal_area` silently removes documents from filtered searches, which
# is worse than leaving it unset.

_AREA_TERMS: dict[LegalArea, tuple[str, ...]] = {
    LegalArea.CONSTITUCIONAL: (
        "constitución política", "derecho fundamental", "acción de tutela",
        "bloque de constitucionalidad", "exequible", "inexequible", "habeas corpus",
    ),
    LegalArea.PENAL: (
        "código penal", "delito", "punible", "pena privativa", "imputado",
        "fiscalía", "antijurídic", "dolo", "culpabilidad",
    ),
    LegalArea.LABORAL: (
        "contrato de trabajo", "trabajador", "empleador", "salario", "prestaciones sociales",
        "jornada laboral", "cesantías", "vacaciones remuneradas", "despido",
    ),
    LegalArea.TRIBUTARIO: (
        "estatuto tributario", "impuesto", "renta", "iva", "contribuyente",
        "declaración tributaria", "retención en la fuente", "dian",
    ),
    LegalArea.ADMINISTRATIVO: (
        "función pública", "acto administrativo", "contratación estatal",
        "entidad estatal", "servidor público", "cpaca", "secop",
    ),
    LegalArea.COMERCIAL: (
        "código de comercio", "sociedad comercial", "comerciante", "título valor",
        "establecimiento de comercio", "insolvencia",
    ),
    LegalArea.CIVIL: (
        "código civil", "obligación", "contrato civil", "bienes inmuebles",
        "prescripción adquisitiva", "responsabilidad contractual",
    ),
    LegalArea.PROCESAL: (
        "código general del proceso", "demanda", "recurso de apelación", "notificación",
        "término judicial", "caducidad", "competencia territorial",
    ),
    LegalArea.FAMILIA: (
        "código de infancia", "alimentos", "custodia", "patria potestad", "unión marital",
        "divorcio",
    ),
    LegalArea.SEGURIDAD_SOCIAL: (
        "sistema de seguridad social", "pensión", "eps", "afiliado", "riesgos laborales",
        "invalidez",
    ),
    LegalArea.AMBIENTAL: (
        "licencia ambiental", "recursos naturales", "impacto ambiental", "anla",
    ),
}

#: Below this many keyword hits, no area is claimed.
_MIN_AREA_HITS = 2


@dataclass(slots=True)
class DocumentMetadata:
    """What could be determined about a document. Unset fields are genuinely unknown."""

    title: str
    document_type: DocumentType
    external_id: str | None = None
    issuing_entity: str | None = None
    court: Court | None = None
    jurisdiction: Jurisdiction = Jurisdiction.NACIONAL
    legal_area: LegalArea | None = None
    publication_date: date | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def extract_metadata(
    text: str,
    *,
    fallback_title: str,
    loader_title: str | None = None,
) -> DocumentMetadata:
    """Derive metadata from a document's text.

    Args:
        text: cleaned document text.
        fallback_title: used only when neither the text nor the loader yielded a
            usable title. Typically the filename — a last resort, not a default.
        loader_title: title the file format carried, when it looked meaningful.

    Only the opening of the document is scanned for identity and dates: the header
    is where a norm names itself, while a later mention of "Ley 100 de 1993" is a
    cross-reference to a different document, not this one's identity.
    """
    head = text[:4000]

    document_type, external_id, derived_title = _identify(head)

    return DocumentMetadata(
        title=(derived_title or loader_title or fallback_title).strip()[:1000],
        document_type=document_type,
        external_id=external_id,
        issuing_entity=_issuer(head),
        court=_court(head),
        legal_area=_legal_area(text),
        publication_date=_publication_date(head),
        extra={"detected_from": "text" if derived_title else "fallback"},
    )


def _identify(head: str) -> tuple[DocumentType, str | None, str | None]:
    """Return (type, external_id, title) from the document header.

    Finds all candidate identities and prefers the earliest match in the header,
    so the document's primary title at the top is selected rather than a later
    cross-reference.
    """
    candidates: list[tuple[int, tuple[DocumentType, str | None, str | None]]] = []

    if match := _CONSTITUTION.search(head):
        candidates.append((
            match.start(),
            (
                DocumentType.CONSTITUCION,
                "CONSTITUCION_POLITICA_1991",
                "Constitución Política de Colombia",
            ),
        ))

    if match := _LAW_LIKE.search(head):
        raw_kind = re.sub(r"\s+", " ", match.group("kind")).upper()
        number = match.group("number")
        year = match.group("year")
        kind = _LAW_KINDS.get(raw_kind, DocumentType.OTRO)
        pretty = raw_kind.title()
        candidates.append((
            match.start(),
            (
                kind,
                f"{kind.value}_{number}_{year}",
                f"{pretty} {number} de {year}",
            ),
        ))

    if match := _JUDGMENT.search(head):
        series = match.group("series").upper()
        number = match.group("number")
        year = _full_year(match.group("year"), match.group("short_year"))
        docket = f"{series}-{number}"
        external_id = f"{docket}-{year}" if year else docket
        kind = DocumentType.AUTO if series == "A" else DocumentType.SENTENCIA
        label = "Auto" if series == "A" else "Sentencia"
        title = f"{label} {docket} de {year}" if year else f"{label} {docket}"
        candidates.append((match.start(), (kind, external_id, title)))

    if match := _CODE.search(head):
        name = re.sub(r"\s+", " ", match.group("name")).strip().title()
        candidates.append((match.start(), (DocumentType.CODIGO, None, f"Código {name}")))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    # Nothing recognizable. OTRO is honest; a guess would put the document into
    # the wrong filter bucket permanently.
    return DocumentType.OTRO, None, None



_LAW_KINDS: dict[str, DocumentType] = {
    "LEY": DocumentType.LEY,
    "LEY ESTATUTARIA": DocumentType.LEY_ESTATUTARIA,
    "DECRETO": DocumentType.DECRETO,
    "DECRETO LEY": DocumentType.DECRETO_LEY,
    "ACTO LEGISLATIVO": DocumentType.ACTO_LEGISLATIVO,
    "RESOLUCION": DocumentType.RESOLUCION,
    "RESOLUCIÓN": DocumentType.RESOLUCION,
    "CIRCULAR": DocumentType.CIRCULAR,
    "ACUERDO": DocumentType.ACUERDO,
    "ORDENANZA": DocumentType.ORDENANZA,
}


def _full_year(year: str | None, short_year: str | None) -> str | None:
    """Expand a two-digit docket year.

    Colombian court dockets run from 1992, so a two-digit year of 92-99 is 1900s
    and 00-91 is 2000s. Pivoting at the wrong place would misdate decisions.
    """
    if year:
        return year
    if not short_year:
        return None
    value = int(short_year)
    return str(1900 + value) if value >= 92 else str(2000 + value)


def _publication_date(head: str) -> date | None:
    """First plausible date in the header, or None."""
    if match := _SPELLED_DATE.search(head):
        return _safe_date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )

    if match := _NUMERIC_DATE.search(head):
        return _safe_date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    """Build a date, rejecting impossible values rather than raising.

    OCR and transcription noise produce "31 de febrero"; that is a failed
    extraction, not a reason to abort ingesting the document.
    """
    if not 1800 <= year <= 2100:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _issuer(head: str) -> str | None:
    for pattern, name in _ISSUERS:
        if match := pattern.search(head):
            return (name or re.sub(r"\s+", " ", match.group(0)).strip().title())[:255]
    return None


def _court(head: str) -> Court | None:
    for pattern, court in _COURTS:
        if pattern.search(head):
            return court
    return None


def _legal_area(text: str) -> LegalArea | None:
    """Score keyword hits and return the leading area, if it leads clearly.

    Returns None on a weak or tied signal: an unset area keeps a document visible
    to every search, while a wrong one hides it from the right one.
    """
    haystack = text[:20000].lower()

    scores = {
        area: sum(1 for term in terms if term in haystack)
        for area, terms in _AREA_TERMS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: -item[1])

    best_area, best_score = ranked[0]
    if best_score < _MIN_AREA_HITS:
        return None

    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    if best_score == runner_up:
        return None

    return best_area

"""Domain vocabulary shared by models, schemas and services.

These are stored as native PostgreSQL enums. Adding a value is a migration, and
that is intentional: `status` in particular drives whether a source may be
presented as current law, so it must not accept arbitrary strings from an
ingestion script.
"""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Vigencia of a legal source.

    The distinction the whole product rests on: a derogated norm may be
    retrieved and cited, but must never be presented as current law.
    """

    VIGENTE = "VIGENTE"
    DEROGADO = "DEROGADO"
    MODIFICADO = "MODIFICADO"
    INEXEQUIBLE = "INEXEQUIBLE"
    PARCIALMENTE_MODIFICADO = "PARCIALMENTE_MODIFICADO"
    # Default for freshly ingested material. Never silently treated as VIGENTE:
    # unknown vigencia is surfaced to the user as unknown.
    DESCONOCIDO = "DESCONOCIDO"

    @property
    def is_current_law(self) -> bool:
        """True only when the source can be cited as law in force.

        MODIFICADO and PARCIALMENTE_MODIFICADO are in force but altered, so they
        are current with a caveat rather than plainly current.
        """
        return self in (DocumentStatus.VIGENTE,)

    @property
    def is_repealed(self) -> bool:
        return self in (DocumentStatus.DEROGADO, DocumentStatus.INEXEQUIBLE)

    @property
    def requires_caveat(self) -> bool:
        """Answer must warn the reader before relying on this source."""
        return self is not DocumentStatus.VIGENTE


class DocumentType(StrEnum):
    """Kind of legal instrument."""

    CONSTITUCION = "CONSTITUCION"
    ACTO_LEGISLATIVO = "ACTO_LEGISLATIVO"
    LEY = "LEY"
    LEY_ESTATUTARIA = "LEY_ESTATUTARIA"
    DECRETO = "DECRETO"
    DECRETO_LEY = "DECRETO_LEY"
    RESOLUCION = "RESOLUCION"
    CIRCULAR = "CIRCULAR"
    ACUERDO = "ACUERDO"
    ORDENANZA = "ORDENANZA"
    CODIGO = "CODIGO"
    SENTENCIA = "SENTENCIA"
    AUTO = "AUTO"
    CONCEPTO = "CONCEPTO"
    DOCTRINA = "DOCTRINA"
    OTRO = "OTRO"

    @property
    def is_jurisprudence(self) -> bool:
        return self in (DocumentType.SENTENCIA, DocumentType.AUTO)


class Jurisdiction(StrEnum):
    NACIONAL = "NACIONAL"
    DEPARTAMENTAL = "DEPARTAMENTAL"
    MUNICIPAL = "MUNICIPAL"
    DISTRITAL = "DISTRITAL"
    INTERNACIONAL = "INTERNACIONAL"
    DESCONOCIDA = "DESCONOCIDA"


class Court(StrEnum):
    """High courts and bodies that produce citable decisions."""

    CORTE_CONSTITUCIONAL = "CORTE_CONSTITUCIONAL"
    CORTE_SUPREMA_JUSTICIA = "CORTE_SUPREMA_JUSTICIA"
    CONSEJO_ESTADO = "CONSEJO_ESTADO"
    CONSEJO_SUPERIOR_JUDICATURA = "CONSEJO_SUPERIOR_JUDICATURA"
    JURISDICCION_ESPECIAL_PAZ = "JURISDICCION_ESPECIAL_PAZ"
    TRIBUNAL_SUPERIOR = "TRIBUNAL_SUPERIOR"
    TRIBUNAL_ADMINISTRATIVO = "TRIBUNAL_ADMINISTRATIVO"
    OTRO = "OTRO"


class LegalArea(StrEnum):
    """Areas used both as a retrieval filter and as benchmark categories."""

    CONSTITUCIONAL = "CONSTITUCIONAL"
    CIVIL = "CIVIL"
    PENAL = "PENAL"
    LABORAL = "LABORAL"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    COMERCIAL = "COMERCIAL"
    TRIBUTARIO = "TRIBUTARIO"
    PROCESAL = "PROCESAL"
    FAMILIA = "FAMILIA"
    AMBIENTAL = "AMBIENTAL"
    SEGURIDAD_SOCIAL = "SEGURIDAD_SOCIAL"
    INTERNACIONAL = "INTERNACIONAL"
    OTRO = "OTRO"


class RelationType(StrEnum):
    """How one document acts upon another.

    This is what lets vigencia be derived rather than trusted: if B DEROGA A,
    A's status can be corrected even when A's own source says nothing.
    """

    DEROGA = "DEROGA"
    DEROGA_PARCIALMENTE = "DEROGA_PARCIALMENTE"
    MODIFICA = "MODIFICA"
    ADICIONA = "ADICIONA"
    REGLAMENTA = "REGLAMENTA"
    DECLARA_INEXEQUIBLE = "DECLARA_INEXEQUIBLE"
    DECLARA_EXEQUIBLE = "DECLARA_EXEQUIBLE"
    DECLARA_EXEQUIBLE_CONDICIONADA = "DECLARA_EXEQUIBLE_CONDICIONADA"
    INTERPRETA = "INTERPRETA"
    CITA = "CITA"
    COMPILA = "COMPILA"
    CORRIGE = "CORRIGE"

    @property
    def repeals_target(self) -> bool:
        return self in (
            RelationType.DEROGA,
            RelationType.DECLARA_INEXEQUIBLE,
        )


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class VerificationStatus(StrEnum):
    """Outcome of checking an answer against its retrieved sources."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    # Retrieval found too little to answer from: the NO EVIDENCE -> NO ANSWER
    # path. Distinct from UNSUPPORTED, where evidence existed but the answer
    # went beyond it.
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    # Verification was disabled or errored. Never rendered as a pass.
    NOT_VERIFIED = "NOT_VERIFIED"

    @property
    def is_trustworthy(self) -> bool:
        return self is VerificationStatus.SUPPORTED


class CitationVerificationStatus(StrEnum):
    """Whether a single citation's excerpt really occurs in its chunk."""

    VERIFIED = "VERIFIED"
    # Cited chunk exists and was in context, but the quoted excerpt does not
    # match its text.
    EXCERPT_MISMATCH = "EXCERPT_MISMATCH"
    # The model referenced a chunk that was never in the context window.
    NOT_IN_CONTEXT = "NOT_IN_CONTEXT"
    UNVERIFIED = "UNVERIFIED"


class RetrievalSource(StrEnum):
    """Which retrieval arm produced a candidate. Kept for evaluation."""

    SEMANTIC = "SEMANTIC"
    LEXICAL = "LEXICAL"
    HYBRID = "HYBRID"

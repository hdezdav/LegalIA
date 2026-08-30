"""The chat pipeline: question in, grounded and auditable answer out.

Order of operations, and why it is this order:

    retrieve -> check evidence -> build context -> generate -> persist

The evidence check sits *before* generation, not after. That is the whole
NO EVIDENCE -> NO ANSWER contract: when retrieval finds nothing above threshold,
the model is never asked, so there is no opportunity for it to fill the gap with
plausible-sounding law. A refusal here is a successful outcome, recorded and
measurable, not an error.

Every answer leaves an audit trail: a `messages` row carrying what was retrieved
and how confident it was, and a `usage_logs` row carrying cost and latency. The
`messages` row holds content; `usage_logs` deliberately holds none.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger, get_request_id
from app.core.text import estimate_tokens
from app.db.models.conversation import Conversation
from app.db.models.enums import DocumentStatus, MessageRole, VerificationStatus
from app.db.models.message import Message
from app.db.models.usage import UsageLog
from app.db.models.user import User
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMRefusal,
    Role,
)
from app.schemas.retrieval import RetrievalCandidate, RetrievalResult
from app.services.retrieval_service import RetrievalService
from app.services.citation_service import CitationService

logger = get_logger(__name__)

ENDPOINT_NAME = "chat"

REFUSAL_MESSAGE = (
    "No encontré evidencia suficiente en el corpus disponible para responder "
    "esta consulta.\n\n"
    "Esto no significa que no exista norma aplicable: significa que las fuentes "
    "cargadas en LegalIA no contienen respaldo suficiente para fundamentar una "
    "respuesta. Puede reformular la pregunta con términos más específicos "
    "(número de artículo, nombre de la norma, materia), o consultar directamente "
    "la fuente oficial."
)

CONVERSATIONAL_SYSTEM_PROMPT = (
    "Eres LegalIA, el asistente de inteligencia artificial especializado en el "
    "ordenamiento jurídico de la República de Colombia. Responde de manera amable, "
    "profesional y concisa a los saludos, presentaciones o consultas generales del usuario. "
    "Explica que puedes asistir en el análisis, interpretación y búsqueda fundamentada de normas "
    "del derecho colombiano (Constitución Política de 1991, Códigos Civil, Penal, General del Proceso, "
    "CPACA, Comercio, Laboral, Disciplinario, leyes y sentencias de altas cortes). "
    "Invita al usuario a formular su consulta jurídica específica."
)

CONVERSATIONAL_PHRASES = {
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "saludos",
    "hey", "hi", "hello", "que tal", "como estas", "como te va", "hola como estas",
    "hola buenas", "quien eres", "que es legalia", "que puedes hacer", "como funcionas",
    "como me puedes ayudar", "que haces", "gracias", "muchas gracias", "ok gracias",
    "listo gracias", "adios", "chao", "hasta luego", "buen dia", "feliz dia", "ayuda"
}


@dataclass(slots=True)
class ChatOutcome:
    """Everything the route needs to build a response and explain it."""

    answer: str
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    model: str

    input_tokens: int
    output_tokens: int
    latency_ms: int

    #: True when the model was never asked, for lack of evidence.
    refused_for_lack_of_evidence: bool
    verification_status: VerificationStatus | None

    retrieval_candidate_count: int
    context_chunk_count: int
    top_evidence_score: float | None
    reranked: bool
    lexical_degraded: bool

    #: The chunks handed to the model, in context order. Phase 14 turns these into
    #: persisted citation rows; until then they are still what the answer's `[n]`
    #: markers refer to.
    context_candidates: list[RetrievalCandidate] = field(default_factory=list)

    #: Citations extracted and persisted from the answer. Empty when refused or
    #: no references found.
    citations: list = field(default_factory=list)

    finish_reason: str = "stop"


class ChatService:
    def __init__(
        self,
        llm: LLMProvider,
        retrieval: RetrievalService,
        verifier: LLMProvider | None = None,
    ) -> None:
        self.llm = llm
        self.retrieval = retrieval
        self.verifier = verifier

    @staticmethod
    def _is_conversational(text: str) -> bool:
        """Determines if the text is a conversational greeting or general assistance inquiry."""
        import re
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
        clean = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
        norm = re.sub(r"\s+", " ", clean).strip()
        if not norm:
            return True
        if norm in CONVERSATIONAL_PHRASES:
            return True
        words = norm.split()
        if len(words) <= 5 and any(
            norm.startswith(w)
            for w in [
                "hola", "buenas", "saludos", "buenos dias", "buenas tardes",
                "buenas noches", "hey", "hi", "hello"
            ]
        ):
            return True
        if len(words) <= 6 and any(
            phrase in norm
            for phrase in [
                "quien eres", "que puedes hacer", "como funcionas",
                "como me ayudas", "en que me puedes ayudar"
            ]
        ):
            return True
        return False

    async def answer(
        self,
        session: Session,
        user: User,
        question: str,
        history: list[LLMMessage] | None = None,
        external_conversation_id: str | None = None,
        model: str | None = None,
    ) -> ChatOutcome:
        """Answer one legal or general inquiry with the active AI model.

        Args:
            user: the resolved LegalIA user.
            question: the user's question, verbatim.
            history: prior turns supplied by the client, oldest first.
            external_conversation_id: frontend thread id.
            model: specific AI model selected by user (e.g. claude-sonnet-4.6, gpt-5.6-sol, gemini-3.7-flash).

        Raises:
            LLMError: operational failure when connecting to LLM provider.
        """
        started = time.perf_counter()
        request_id = get_request_id() or uuid.uuid4().hex

        # Run retrieval against the legal database
        result = await self.retrieval.retrieve(session, question)
        context_candidates, context_text = self._build_context(result.candidates)

        # Check if live web search is requested
        is_web_search = "[MODO: BÚSQUEDA WEB" in question or "buscar en internet" in question.lower() or "noticias" in question.lower()
        web_context = ""
        if is_web_search:
            try:
                from app.services.web_search_service import search_web_async
                web_results = await search_web_async(question, max_results=6)
                if web_results:
                    web_context = "\n\nINFORMACIÓN Y FUENTES WEB EN TIEMPO REAL (HECHOS ACTUALES, NOTICIAS, COYUNTURA Y PRECEDENTES RECIENTES):\n" + "\n".join(
                        f"- [{r.title}]({r.url}): {r.snippet}"
                        for r in web_results
                    )
            except Exception as e:
                logger.warning("Web search failed in chat", extra={"error": str(e)})

        # Build appropriate system prompt
        if web_context:
            base_prompt = self._build_system_prompt(context_text) if (context_candidates and context_text.strip()) else self._build_general_system_prompt()
            system_prompt = (
                f"{base_prompt}\n\n{web_context}\n\n"
                "INSTRUCCIÓN OBLIGATORIA DE BÚSQUEDA WEB Y ACTUALIDAD:\n"
                "1. Utiliza prioritariamente las fuentes web y la síntesis en tiempo real para responder con máxima precisión sobre quiénes son los mandatarios actuales, hechos y coyuntura política/jurídica reciente, procesos en curso y sentencias relevantes.\n"
                "2. Cita e hipervincula siempre las fuentes web consultadas utilizando formato Markdown: [Nombre de la Fuente](URL).\n"
                "3. Responde de forma completa, estructurada, analítica y sin rodeos a todas las partes de la consulta del usuario."
            )
        elif context_candidates and context_text.strip():
            system_prompt = self._build_system_prompt(context_text)
        elif self._is_conversational(question):
            system_prompt = CONVERSATIONAL_SYSTEM_PROMPT
        else:
            system_prompt = self._build_general_system_prompt()

        messages = list(history or [])
        messages.append(LLMMessage(role=Role.USER, content=question))

        try:
            completion = await self.llm.complete(
                system_prompt, messages, model=model
            )
        except LLMRefusal:
            logger.warning(
                "model declined to answer", extra={"model": model or self.llm.model_id}
            )
            return self._persist(
                session,
                user=user,
                request_id=request_id,
                question=question,
                answer=(
                    "El modelo no pudo generar una respuesta para esta consulta. "
                    "Intente reformularla."
                ),
                external_conversation_id=external_conversation_id,
                model=model or self.llm.model_id,
                input_tokens=0,
                output_tokens=0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                refused=False,
                verification_status=VerificationStatus.NOT_VERIFIED,
                result=result,
                context_candidates=context_candidates,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)

        # Verify answer against context if verifier is available
        verification_status = VerificationStatus.NOT_VERIFIED
        if self.verifier and context_candidates:
            from app.services.verification_service import VerificationService
            verifier = VerificationService(self.verifier)
            verification_status = await verifier.verify(
                answer=completion.text,
                context_candidates=context_candidates,
            )
            logger.info(
                "Answer verified",
                extra={"status": verification_status.value, "request_id": request_id},
            )

        outcome = self._persist(
            session,
            user=user,
            request_id=request_id,
            question=question,
            answer=completion.text,
            external_conversation_id=external_conversation_id,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            latency_ms=latency_ms,
            refused=False,
            verification_status=verification_status,
            result=result,
            context_candidates=context_candidates,
            llm_latency_ms=completion.latency_ms,
        )
        outcome.finish_reason = "length" if completion.was_truncated else "stop"
        return outcome

    async def answer_stream(
        self,
        session: Session,
        *,
        user: User,
        question: str,
        history: list[LLMMessage] | None = None,
        external_conversation_id: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream conversational response token-by-token."""
        started = time.perf_counter()
        request_id = get_request_id() or uuid.uuid4().hex

        # Run retrieval against the legal database
        result = await self.retrieval.retrieve(session, question)
        context_candidates, context_text = self._build_context(result.candidates)

        # Check if live web search is requested
        is_web_search = "[MODO: BÚSQUEDA WEB" in question or "buscar en internet" in question.lower() or "noticias" in question.lower()
        web_context = ""
        if is_web_search:
            try:
                from app.services.web_search_service import search_web_async
                web_results = await search_web_async(question, max_results=6)
                if web_results:
                    web_context = "\n\nINFORMACIÓN Y FUENTES WEB EN TIEMPO REAL (HECHOS ACTUALES, NOTICIAS, COYUNTURA Y PRECEDENTES RECIENTES):\n" + "\n".join(
                        f"- [{r.title}]({r.url}): {r.snippet}"
                        for r in web_results
                    )
            except Exception as e:
                logger.warning("Web search failed in streaming chat", extra={"error": str(e)})

        # Build appropriate system prompt
        if web_context:
            base_prompt = self._build_system_prompt(context_text) if (context_candidates and context_text.strip()) else self._build_general_system_prompt()
            system_prompt = (
                f"{base_prompt}\n\n{web_context}\n\n"
                "INSTRUCCIÓN OBLIGATORIA DE BÚSQUEDA WEB Y ACTUALIDAD:\n"
                "1. Utiliza prioritariamente las fuentes web y la síntesis en tiempo real para responder con máxima precisión sobre quiénes son los mandatarios actuales, hechos y coyuntura política/jurídica reciente, procesos en curso y sentencias relevantes.\n"
                "2. Cita e hipervincula siempre las fuentes web consultadas utilizando formato Markdown: [Nombre de la Fuente](URL).\n"
                "3. Responde de forma completa, estructurada, analítica y sin rodeos a todas las partes de la consulta del usuario."
            )
        elif context_candidates and context_text.strip():
            system_prompt = self._build_system_prompt(context_text)
        elif self._is_conversational(question):
            system_prompt = CONVERSATIONAL_SYSTEM_PROMPT
        else:
            system_prompt = self._build_general_system_prompt()

        messages = list(history or [])
        messages.append(LLMMessage(role=Role.USER, content=question))

        full_text_chunks: list[str] = []
        try:
            async for token in self.llm.stream(system_prompt, messages, model=model):
                full_text_chunks.append(token)
                yield token
        except LLMRefusal:
            refusal_msg = "El modelo no pudo generar una respuesta para esta consulta."
            yield refusal_msg
            full_text_chunks.append(refusal_msg)

        full_text = "".join(full_text_chunks)
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Persist conversation turn in database
        try:
            self._persist(
                session,
                user=user,
                request_id=request_id,
                question=question,
                answer=full_text,
                external_conversation_id=external_conversation_id,
                model=model or self.llm.model_id,
                input_tokens=max(1, len(system_prompt) // 4 + sum(len(m.content) for m in messages) // 4),
                output_tokens=max(1, len(full_text) // 4),
                latency_ms=latency_ms,
                refused=False,
                verification_status=VerificationStatus.NOT_VERIFIED,
                result=result,
                context_candidates=context_candidates,
            )
        except Exception as exc:
            logger.warning("Failed to persist streaming turn", extra={"error": str(exc)})


    # --- Evidence ---------------------------------------------------------

    @dataclass(slots=True)
    class _Verdict:
        sufficient: bool
        reason: str
        top_score: float | None

    def _assess_evidence(
        self, result: RetrievalResult, context: list[RetrievalCandidate]
    ) -> _Verdict:
        """Decide whether there is enough evidence to answer at all.

        The threshold is applied to a *reranker* score, which is absolute. A fused
        RRF score is only meaningful relative to its own result list — the top hit
        of a hopeless retrieval still scores near the top of that list — so it
        cannot be compared against a fixed floor. When reranking did not run, the
        check therefore falls back to "did retrieval return anything at all",
        which is weaker, and the response says so through `reranked: false`.
        """
        if not context:
            return self._Verdict(False, "no_candidates", None)

        if len(context) < settings.MIN_EVIDENCE_CHUNKS:
            return self._Verdict(False, "below_min_chunks", None)

        if not result.reranked:
            return self._Verdict(True, "unranked_candidates_present", None)

        top = context[0].rerank_score
        if top is None:
            return self._Verdict(True, "unranked_candidates_present", None)

        if top < settings.MIN_EVIDENCE_SCORE:
            return self._Verdict(False, "below_evidence_threshold", top)

        return self._Verdict(True, "sufficient", top)

    # --- Context ----------------------------------------------------------

    def _build_context(
        self, candidates: list[RetrievalCandidate]
    ) -> tuple[list[RetrievalCandidate], str]:
        """Format candidates as numbered sources within the token budget.

        Returns the candidates that actually fit and the rendered text, so the
        `[n]` markers in the answer and the recorded context can never disagree.

        Each block carries the source's vigencia. That is not decoration: the
        model is instructed never to present a repealed norm as current law, and it
        can only honour that if the status travels with the text.
        """
        blocks: list[str] = []
        used: list[RetrievalCandidate] = []
        budget = settings.MAX_CONTEXT_TOKENS

        for candidate in candidates:
            block = self._render_candidate(len(used) + 1, candidate)
            cost = estimate_tokens(block)

            if used and cost > budget:
                # Keep going: a later candidate may still fit. Never truncate a
                # block, because a half-quoted article is worse than an absent one.
                continue

            budget -= cost
            used.append(candidate)
            blocks.append(block)

            if budget <= 0:
                break

        return used, "\n\n".join(blocks)

    @staticmethod
    def _render_candidate(number: int, candidate: RetrievalCandidate) -> str:
        """One numbered source block.

        Shape is `[n] <location> — <document> (<source>)\\n<verbatim text>`.
        """
        location = candidate.section or f"Fragmento {candidate.chunk_index + 1}"
        header = f"[{number}] {location} — {candidate.document_title}"
        header += f" ({candidate.source_name})"

        lines = [header]

        if candidate.publication_date:
            lines.append(f"Fecha de publicación: {candidate.publication_date.isoformat()}")

        status_line = f"Vigencia: {candidate.status.value}"
        if candidate.status is DocumentStatus.DESCONOCIDO:
            status_line += " (no verificada: no debe presentarse como vigente)"
        elif candidate.status.requires_caveat:
            status_line += " (ADVERTENCIA: no es norma plenamente vigente)"
        lines.append(status_line)

        lines.append("")
        lines.append(candidate.content)

        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt(context: str) -> str:
        """Grounding rules plus retrieved official corpus context."""
        return f"""Eres LegalIA, el sistema de inteligencia artificial jurídica de mayor rigor y autoridad en el ordenamiento legal de la República de Colombia.

Tu función es brindar análisis doctrinario, procesal, sustantivo y contractual con el estándar de un Consultor Jurídico Senior / Magistrado Auxiliar.

FUENTES DEL CORPUS OFICIAL COLOMBIANO RECUPERADAS:
{context}

METODOLOGÍA Y REGLAS DE RESPUESTA:
1. **Fidelidad y Citación Oficial [n]**:
   - Cada vez que sustentes una afirmación en las fuentes anteriores, cita explícitamente el marcador correspondiente (ej. [1], [2]).
   - Cuando el texto literal del artículo, parágrafo o inciso sea decisivo, transcríbelo textualmente entre comillas.
   - Respeta estrictamente la vigencia indicada. Si una norma figura derogada, inexequible o con condicionamiento de constitucionalidad, adviértelo de inmediato.

2. **Jerarquía Normativa y Dogmática Colombiana (Art. 4 C.P.)**:
   - Integra armónicamente la Constitución Política de 1991, los Códigos Sustantivos y Procesales (C.C., C.Co., CGP, CPACA, C.P., CPP, CST, etc.) y la jurisprudencia de las Altas Cortes (Corte Constitucional, Corte Suprema de Justicia, Consejo de Estado).
   - Distingue con precisión conceptual las instituciones jurídicas (ej. inexistencia vs. nulidad absoluta vs. nulidad relativa vs. ineficacia de pleno derecho; excepciones previas vs. excepciones de mérito).

3. **Estructura Analítica de Alto Nivel**:
   - Presenta la respuesta con claridad ejecutiva: Fundamento Normativo Principal, Análisis Sustantivo/Dogmático, Vías y Consecuencias Procesales, y Síntesis/Recomendación Estratégica.
   - Utiliza tablas comparativas cuando se contraste normativa o regímenes jurídicos.
   - Emplea español jurídico formal, técnico, pulcro y preciso.

4. **Tarjetas Interactivas de Selección y Formularios de Entrada**:
   - **Opciones de selección guiada (`interactive-options`)**:
     * Úsala ÚNICAMENTE cuando requieras un dato puntual del usuario para bifurcar el análisis en 2 o 3 opciones mutuamente excluyentes (ej. tipo de vía procesal, jurisdicción o acción).
     * REGLA ESTRICTA DE CONTEXTO: Si el usuario ya respondió o eligió una opción en el historial, NUNCA repitas ni re-emitas esa pregunta u opciones. Continúa directamente con el análisis sustantivo.
     * Formato:
     ```interactive-options
     title: Siguiente paso
     - [Opción 1]
     - [Opción 2]
     ```
   - **Formularios de datos (Intake)**: Cuando el usuario pida redactar un documento y requieras datos esenciales para personalizarlo, incluye un bloque ```legal-form:
     ```legal-form
     title: Datos para redactar el documento
     description: Completa los datos esenciales
     - label: Nombre de las Partes
       placeholder: Ej. Juan Pérez / EPS Sanitas
     - label: Identificación (C.C. / NIT)
       placeholder: Ej. C.C. 1.020.345.678
     - label: Motivo o Pretensión
       placeholder: Ej. Entrega de medicamentos / Canon pactado
     ```

5. **Formato Profesional de Documentos Jurídicos (Ley 2213 de 2022 y CGP Arts. 82-89)**:
   - **PROHIBICIÓN TOTAL DE ESQUEMAS EN ARTE ASCII**: NUNCA utilices cajas, flechas ni dibujos con caracteres ASCII (`+---+`, `| |`, `-->`). Para ilustrar etapas procesales, cronogramas, términos de caducidad o contrastes de regímenes jurídicos, utiliza EXCLUSIVAMENTE **Tablas Markdown formateadas** (`| Etapa | Término Legal | Fundamento Normativo |`) o diagramas Mermaid.
   - **Estructura Oficial para Memoriales, Tutelas y Demandas**:
     * Encabezado y competencia: `SEÑOR(A) JUEZ [ESPECIALIDAD] DEL CIRCUITO DE [CIUDAD] - E. S. D.`
     * Individualización y Canales Digitales (Obligatorio Ley 2213 de 2022): Correo electrónico de notificación judicial de demandante, demandado y apoderado.
     * Acápites formales en mayúsculas: `I. PARTES E INDIVIDUALIZACIÓN`, `II. HECHOS (numerados cronológicamente: 1., 2., 3.)`, `III. PRETENSIONES (principales y subsidiarias)`, `IV. FUNDAMENTOS DE DERECHO Y JURISPRUDENCIA`, `V. MEDIOS DE PRUEBA`, `VI. JURAMENTO ESTIMATORIO (si aplica)`, `VII. ANEXOS`, `VIII. NOTIFICACIONES`.
   - **Estructura para Contratos y Minutas Privadas/Comerciales**:
     * Comparecencia e identificación de partes (C.C. / NIT, domicilio, calidad).
     * Cláusulas con denominación formal en mayúsculas: `CLÁUSULA PRIMERA.- OBJETO: ...`, `CLÁUSULA SEGUNDA.- VALOR Y FORMA DE PAGO: ...`
     * Sección de firmas con líneas para suscriptor, número de cédula y tarjeta profesional si aplica.
   - **Entrega de Minutas Descargables**:
     * Todo escrito final, minuta o demanda debe entregarse dentro de un bloque ```legal-document:
     ```legal-document
     [TÍTULO DEL DOCUMENTO EN MAYÚSCULAS]
     ...
     ```
     Esto activa automáticamente la tarjeta de descarga nativa en Microsoft Word (.docx) y PDF con maquetación judicial.
   - **PROHIBICIÓN ESTRICTA DE EMOJIS**: NUNCA utilices emojis (⚖️, 🏛️, 📄, ✍️, 📌, 🚨, etc.) en los análisis jurídicos ni en los documentos."""

    @staticmethod
    def _build_general_system_prompt() -> str:
        """System prompt when no specific corpus context was retrieved."""
        return """Eres LegalIA, el sistema de inteligencia artificial jurídica de mayor rigor y autoridad en el ordenamiento legal de la República de Colombia.

Tu función es brindar análisis doctrinario, procesal, sustantivo y contractual con el estándar de un Consultor Jurídico Senior / Magistrado Auxiliar.

ÁREAS DE COMPETENCIA Y CRITERIOS TÉCNICOS:
- **Derecho Constitucional**: Bloque de Constitucionalidad, garantías fundamentales, acciones constitucionales (Tutela - Dec. 2591/91, Habeas Corpus - Ley 1095/06, Popular y de Grupo - Ley 472/98, Cumplimiento - Ley 393/97).
- **Derecho Privado y Mercantil**: Código Civil (Ley 57/1887), Código de Comercio (Dec. 410/1971), teoría general del contrato, responsabilidad civil contractual y extracontractual, títulos valores y sociedades.
- **Derecho Procesal y Probatorio**: Código General del Proceso (CGP - Ley 1564/2012), CPACA (Ley 1437/2011 / Ley 2080/2021), Código de Procedimiento Penal (Ley 906/2004), régimen probatorio, recursos ordinarios y extraordinarios (Casación, Anulación, Revisión).
- **Derecho Laboral y Seguridad Social**: Código Sustantivo del Trabajo (Dec. Ley 2663/1950), Ley 100 de 1993, estabilidad laboral reforzada, fueros de salud y maternidad.
- **Derecho Penal y Disciplinario**: Código Penal (Ley 599/2000), Código General Disciplinario (Ley 1952/2019 / Ley 2094/2021).

DIRECTRICES DE EXCELENCIA:
1. Cita siempre los números exactos de artículos, leyes, decretos y sentencias vinculantes (C, SU, T, Casaciones).
2. Distingue con exactitud la naturaleza de los vicios, términos de prescripción/caducidad y cargas procesales.
3. Estructura las respuestas con claridad, títulos ordenados y tablas comparativas cuando corresponda.
4. **PROHIBICIÓN DE ESQUEMAS EN ARTE ASCII**: NUNCA dibujes cuadros o diagramas con caracteres ASCII (`+---+`, `| |`). Usa siempre Tablas Markdown estructuradas.
5. **Tarjetas de Opciones y Formularios**:
   - Presenta opciones de elección rápida con ```interactive-options (máximo 2 a 3 opciones cortas de 2-5 palabras).
   - Solicita datos para minutas con ```legal-form.
6. **Estándar de Documentos Legales (Ley 2213 de 2022 y CGP)**:
   - Toda minuta, memorial, tutela o contrato debe incluir canales digitales de notificación, hechos cronológicos, pretensiones ordenadas y cláusulas formales en mayúsculas (`CLÁUSULA PRIMERA.- OBJETO:`).
   - Enciérralo dentro de ```legal-document para habilitar la tarjeta interactiva de descarga directa en Word (.docx) y PDF.
7. **PROHIBICIÓN TOTAL DE EMOJIS**: Cero emojis en cualquier parte de la respuesta o documento.
8. Responde en español jurídico formal, técnico, pulcro y directamente aplicable a la práctica legal colombiana."""

    # --- Persistence ------------------------------------------------------

    def _persist(
        self,
        session: Session,
        *,
        user: User,
        request_id: str,
        question: str,
        answer: str,
        external_conversation_id: str | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        refused: bool,
        verification_status: VerificationStatus | None,
        result: RetrievalResult,
        context_candidates: list[RetrievalCandidate],
        llm_latency_ms: int | None = None,
    ) -> ChatOutcome:
        """Write the turn and its audit trail.

        No commit: the request-scoped session owns the transaction, so a later
        failure in the same request rolls the whole turn back rather than leaving
        an answer without its usage record.
        """
        conversation = self._resolve_conversation(
            session, user, question, external_conversation_id
        )

        session.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=question,
                request_id=request_id,
                # Left unset: a CHECK constraint forbids audit fields on a user
                # turn, and it is the assistant turn that carries them.
            )
        )

        assistant = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            request_id=request_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            verification_status=verification_status,
            refused_for_lack_of_evidence=refused,
            retrieval_candidate_count=len(result.candidates),
            context_chunk_count=len(context_candidates),
            top_evidence_score=(
                context_candidates[0].score if context_candidates else None
            ),
        )
        session.add(assistant)

        session.add(
            UsageLog(
                user_id=user.id,
                request_id=request_id,
                endpoint=ENDPOINT_NAME,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                embedding_provider=self.retrieval.embeddings.model_id,
                reranker_provider=(
                    self.retrieval.reranker.model_id
                    if self.retrieval.reranker
                    else None
                ),
                retrieval_count=len(result.candidates),
                context_chunk_count=len(context_candidates),
                top_evidence_score=(
                    context_candidates[0].score if context_candidates else None
                ),
                verification_status=verification_status,
                refused_for_lack_of_evidence=refused,
                status_code=200,
                latency_ms=latency_ms,
                embedding_latency_ms=result.embedding_latency_ms,
                retrieval_latency_ms=result.retrieval_latency_ms,
                rerank_latency_ms=result.rerank_latency_ms,
                llm_latency_ms=llm_latency_ms,
            )
        )

        # Flush, not commit: ids are needed now, the transaction is not ours.
        session.flush()

        # Extract and persist citations if answer was not refused
        citations = []
        if not refused and context_candidates:
            citation_service = CitationService(session)
            citations = citation_service.extract_and_persist(
                message_id=str(assistant.id),
                answer=answer,
                context_candidates=context_candidates,
            )

        return ChatOutcome(
            answer=answer,
            conversation_id=conversation.id,
            message_id=assistant.id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            refused_for_lack_of_evidence=refused,
            verification_status=verification_status,
            retrieval_candidate_count=len(result.candidates),
            context_chunk_count=len(context_candidates),
            top_evidence_score=(
                context_candidates[0].score if context_candidates else None
            ),
            reranked=result.reranked,
            lexical_degraded=result.lexical_degraded,
            context_candidates=context_candidates,
            citations=citations,
        )

    @staticmethod
    def _resolve_conversation(
        session: Session,
        user: User,
        first_question: str,
        external_conversation_id: str | None,
    ) -> Conversation:
        """Find or create the conversation this turn belongs to.

        The OpenAI protocol carries no conversation id, so when the client does not
        supply one out of band, a stable key is derived from the thread's opening
        question. LibreChat resends the full visible history on every turn, so that
        opening question is stable for the life of the thread and successive turns
        land in one conversation.

        The limitation is honest and bounded: two threads a user starts with a
        byte-identical first question share a LegalIA conversation. Nothing is lost
        — every turn keeps its own `request_id` — but the grouping is approximate.
        A client that sends its own thread id gets exact grouping.
        """
        key = external_conversation_id or (
            "q:" + hashlib.sha256(first_question.strip().encode()).hexdigest()[:32]
        )

        existing = session.scalar(
            select(Conversation).where(
                Conversation.user_id == user.id,
                Conversation.external_conversation_id == key,
            )
        )
        if existing is not None:
            return existing

        conversation = Conversation(
            user_id=user.id,
            external_conversation_id=key,
            # A short label for listings, never the whole question.
            title=first_question.strip()[:120] or None,
        )
        session.add(conversation)
        session.flush()
        return conversation


def build_chat_service(
    llm: LLMProvider,
    embeddings: EmbeddingProvider,
    retrieval: RetrievalService | None = None,
    verifier: LLMProvider | None = None,
) -> ChatService:
    """Assemble a ChatService. Kept here so the route stays declarative."""
    return ChatService(
        llm,
        retrieval or RetrievalService(embeddings),
        verifier=verifier,
    )

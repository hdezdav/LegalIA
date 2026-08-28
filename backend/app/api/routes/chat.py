"""Chat endpoints, OpenAI-compatible.

    POST /api/v1/chat/completions
    GET  /api/v1/models

LibreChat's custom endpoints speak the OpenAI Chat Completions protocol, so that
is what LegalIA exposes. Only the wire format is borrowed: retrieval, grounding,
vigencia handling and the refusal contract all stay on this side, which is what
keeps the frontend replaceable (section 5 of the brief).

The route stays declarative — resolve the caller, hand the question to
`ChatService`, translate the outcome. Every legal decision lives in the service.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import ChatPrincipal, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.providers.embeddings import get_embedding_provider
from app.providers.llm import LLMError, get_llm_provider, get_verifier_provider
from app.providers.llm.base import LLMMessage, Role
from app.providers.reranking import get_reranker_provider
from app.schemas.chat import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    CitationSchema,
    LegalIAMetadata,
    ModelCard,
    ModelList,
)
from app.services.chat_service import ChatService
from app.services.nodule_service import get_nodule_quota
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)


@router.get(
    "/usage/quota",
    summary="Get live Nodule AI token quota and balance",
)
async def get_token_quota(session: DbSession):
    return await get_nodule_quota(session=session)


#: The model name clients select. Deliberately opaque: which Claude model, which
#: embedding provider and which reranker are LegalIA's decisions, not the
#: client's, and they change without the client needing to know.
MODEL_NAME = "legalia"


def _build_service() -> ChatService:
    """Assemble the pipeline from the process-wide providers.

    Providers are cached singletons, so this is cheap per request and there is one
    place where a swap takes effect.
    """
    # Get the verifier LLM (Haiku 4.5) for verification
    verifier = None
    try:
        verifier = get_verifier_provider()
    except Exception as e:
        logger.warning(
            "Could not initialize verifier LLM, verification will be skipped",
            extra={"error": str(e)},
        )

    return ChatService(
        llm=get_llm_provider(),
        retrieval=RetrievalService(
            embedding_provider=get_embedding_provider(),
            reranker_provider=get_reranker_provider(),
        ),
        verifier=verifier,
    )


def _enrich_model_card(model_id: str, owned_by: str = "nodule", created: int = 0) -> ModelCard:
    """Enriches a raw model ID from Nodule with official display name, provider and total context limit."""
    mid = model_id.lower()
    owned = owned_by.lower()

    if mid == "legalia":
        return ModelCard(
            id="legalia",
            owned_by="legalia",
            name="Legalia Auto",
            provider="Legalia",
            context_limit=200000,
            context_limit_label="200k tokens",
            description="Enrutador jurídico automático con verificación RAG y citas normativas oficiales",
            badge="RAG Oficial",
            created=created,
        )

    # Google Gemini Models (1,000,000 tokens)
    if "gemini" in mid or "google" in owned or "antigravity" in owned:
        name = mid.replace("gemini-", "Gemini ").replace("-preview", " Preview").replace("-", ".")
        if mid == "gemini-3.7-flash":
            name = "Gemini 3.7 Flash"
        elif mid == "gemini-3.6-flash":
            name = "Gemini 3.6 Flash"
        elif mid == "gemini-3.5-flash":
            name = "Gemini 3.5 Flash"
        elif mid == "gemini-3.1-pro":
            name = "Gemini 3.1 Pro"
        elif mid == "gemini-3-flash-preview":
            name = "Gemini 3 Flash Preview"
        return ModelCard(
            id=model_id,
            owned_by=owned_by,
            name=name,
            provider="Google",
            context_limit=1000000,
            context_limit_label="1M tokens",
            description="Motor multimodal de Google con ventana masiva de 1 millón de tokens para expedientes completos",
            badge="1M Tokens" if "flash" in mid else "Preview" if "preview" in mid else None,
            created=created,
        )

    # Anthropic Claude Models (200,000 tokens)
    if "claude" in mid or "anthropic" in owned or "kiro" in owned:
        name = model_id
        if mid == "claude-sonnet-4.6":
            name = "Claude Sonnet 4.6"
        elif mid == "claude-sonnet-5":
            name = "Claude Sonnet 5"
        elif mid == "claude-opus-5":
            name = "Claude Opus 5"
        elif mid == "claude-opus-4.8":
            name = "Claude Opus 4.8"
        elif mid == "claude-opus-4.6":
            name = "Claude Opus 4.6"
        elif mid == "claude-haiku-4.5":
            name = "Claude Haiku 4.5"
        return ModelCard(
            id=model_id,
            owned_by=owned_by,
            name=name,
            provider="Anthropic",
            context_limit=200000,
            context_limit_label="200k tokens",
            description="Alta precisión en razonamiento procesal, hermenéutica y jurisprudencia colombiana",
            badge="Recomendado" if mid == "claude-sonnet-4.6" else "Rápido" if "haiku" in mid else None,
            created=created,
        )

    # OpenAI GPT Models (128,000 tokens)
    if "gpt" in mid or "openai" in owned:
        name = mid.upper().replace("-", " ")
        if mid == "gpt-5.6-sol":
            name = "GPT-5.6 Sol"
        elif mid == "gpt-5.6-terra":
            name = "GPT-5.6 Terra"
        elif mid == "gpt-5.6-luna":
            name = "GPT-5.6 Luna"
        elif mid == "gpt-5.5":
            name = "GPT-5.5"
        elif mid == "gpt-5.4":
            name = "GPT-5.4"
        elif mid == "gpt-5.4-mini":
            name = "GPT-5.4 Mini"
        return ModelCard(
            id=model_id,
            owned_by=owned_by,
            name=name,
            provider="OpenAI",
            context_limit=128000,
            context_limit_label="128k tokens",
            description="Generación y estructuración de minutas contractuales, alegatos y análisis documental",
            badge="Económico" if "mini" in mid else None,
            created=created,
        )

    # xAI Grok Models (128,000 tokens)
    if "grok" in mid or "xai" in owned:
        name = mid.replace("grok-", "Grok ")
        return ModelCard(
            id=model_id,
            owned_by=owned_by,
            name=name,
            provider="xAI",
            context_limit=128000,
            context_limit_label="128k tokens",
            description="Motor de razonamiento analítico xAI",
            created=created,
        )

    return ModelCard(
        id=model_id,
        owned_by=owned_by,
        name=model_id,
        provider="Legalia",
        context_limit=128000,
        context_limit_label="128k tokens",
        description=f"Modelo Nodule ({model_id})",
        created=created,
    )


@router.get(
    "/models",
    response_model=ModelList,
    summary="List available models (OpenAI-compatible, scraped live from provider)",
)
async def list_models() -> ModelList:
    """Dynamically scrape and return available models from Nodule / LLM provider."""
    import httpx
    models: list[ModelCard] = []

    if settings.LLM_PROVIDER == "openai_compatible" and settings.LLM_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {settings.LLM_API_KEY.get_secret_value()}"},
                )
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    for item in data:
                        model_id = item.get("id")
                        if (
                            model_id
                            and "image" not in model_id.lower()
                            and "dall" not in model_id.lower()
                            and "embed" not in model_id.lower()
                        ):
                            models.append(_enrich_model_card(
                                model_id=model_id,
                                owned_by=item.get("owned_by", "nodule"),
                                created=item.get("created", 0),
                            ))
        except Exception as exc:
            logger.warning("failed to dynamically fetch models from remote endpoint", exc_info=exc)

    if not models:
        default_ids = [
            ("claude-sonnet-4.6", "anthropic-kiro"),
            ("claude-sonnet-5", "anthropic-kiro"),
            ("claude-opus-5", "anthropic-kiro"),
            ("claude-haiku-4.5", "anthropic-kiro"),
            ("gemini-3.7-flash", "gemini-antigravity"),
            ("gpt-5.6-sol", "nodule-gpt"),
        ]
        models = [_enrich_model_card(mid, owned) for mid, owned in default_ids]

    # Prepend legalia default
    if not any(m.id == "legalia" for m in models):
        models.insert(0, _enrich_model_card("legalia", "legalia"))

    return ModelList(data=models)


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Answer a legal question (OpenAI-compatible)",
    responses={
        400: {"description": "The request contains no user message"},
        503: {"description": "Answer generation is unavailable"},
    },
)
async def chat_completions(
    payload: ChatCompletionRequest,
    principal: ChatPrincipal,
    session: DbSession,
) -> ChatCompletionResponse:
    """Answer the final user message, grounded in retrieved sources."""
    try:
        question = payload.last_user_message()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must contain at least one user message",
        ) from exc

    history = [
        LLMMessage(role=Role(message.role), content=message.content)
        for message in payload.history()
        if message.role in ("user", "assistant")
    ]

    user = principal.resolve_subject(payload.user)
    service = _build_service()

    if payload.stream:
        selected_model = payload.model if payload.model and payload.model != "legalia" else settings.LLM_MODEL

        async def sse_generator():
            import json
            import time
            import uuid

            req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            created_ts = int(time.time())

            try:
                async for token in service.answer_stream(
                    session,
                    user=user,
                    question=question,
                    history=history,
                    model=payload.model if payload.model and payload.model != "legalia" else None,
                ):
                    chunk = {
                        "id": req_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": selected_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                final_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": selected_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error("SSE stream error", extra={"error": str(e)})
                err_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": selected_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "\n\n[Error al generar la respuesta en streaming]"},
                            "finish_reason": "error",
                        }
                    ],
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        outcome = await service.answer(
            session,
            user=user,
            question=question,
            history=history,
            model=payload.model if payload.model and payload.model != "legalia" else None,
        )
    except LLMError as exc:
        # Retrieval worked and generation did not: an operational failure, and it
        # must not be dressed up as "no evidence". 503, because it is expected to
        # be transient.
        logger.error(
            "generation unavailable",
            extra={"error_type": type(exc).__name__, "model": settings.ANTHROPIC_MODEL},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "La generación de respuestas no está disponible en este momento. "
                "Intente nuevamente."
            ),
        ) from exc

    return ChatCompletionResponse(
        model=outcome.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionMessage(
                    role="assistant", content=outcome.answer
                ),
                finish_reason=outcome.finish_reason,
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=outcome.input_tokens,
            completion_tokens=outcome.output_tokens,
            total_tokens=outcome.input_tokens + outcome.output_tokens,
        ),
        legalia=LegalIAMetadata(
            conversation_id=str(outcome.conversation_id),
            message_id=str(outcome.message_id),
            refused_for_lack_of_evidence=outcome.refused_for_lack_of_evidence,
            verification_status=outcome.verification_status,
            retrieval_candidate_count=outcome.retrieval_candidate_count,
            context_chunk_count=outcome.context_chunk_count,
            top_evidence_score=outcome.top_evidence_score,
            reranked=outcome.reranked,
            lexical_degraded=outcome.lexical_degraded,
            embedding_provider=settings.EMBEDDING_PROVIDER,
            reranker_provider=settings.RERANKER_PROVIDER,
            latency_ms=outcome.latency_ms,
            citations=[
                CitationSchema(
                    id=str(citation.id),
                    position=citation.position,
                    document_id=str(citation.document_id),
                    chunk_id=str(citation.chunk_id),
                    document_title=citation.document_title,
                    section=citation.section,
                    source_name=citation.source_name,
                    source_url=citation.source_url,
                    publication_date=citation.publication_date.isoformat() if citation.publication_date else None,
                    status=citation.status,
                    excerpt=citation.excerpt,
                    excerpt_char_start=citation.excerpt_char_start,
                    excerpt_char_end=citation.excerpt_char_end,
                    relevance_score=citation.relevance_score,
                    rank=citation.rank,
                    verification_status=citation.verification_status,
                )
                for citation in outcome.citations
            ],
        ),
    )

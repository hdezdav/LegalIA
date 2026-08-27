"""Chat completions endpoint tests (OpenAI-compatible wire protocol for LibreChat).

Tests the HTTP surface, authentication contracts (service token vs user JWT),
user mapping, request validation, and error translation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models.user import User
from app.providers.llm.base import LLMError
from app.schemas.chat import ChatCompletionResponse, ModelList

MODELS_URL = f"{settings.API_V1_PREFIX}/models"
CHAT_URL = f"{settings.API_V1_PREFIX}/chat/completions"


# --- Models Endpoint ---------------------------------------------------------


def test_list_models_returns_legalia_card(client: TestClient) -> None:
    """LibreChat queries GET /models on startup when model fetching is enabled."""
    response = client.get(MODELS_URL)

    assert response.status_code == 200
    data = response.json()
    model_list = ModelList.model_validate(data)
    assert len(model_list.data) >= 1
    model_ids = [m.id for m in model_list.data]
    assert "legalia" in model_ids


# --- Authentication & Authorization -----------------------------------------


def test_chat_completions_requires_authentication(client: TestClient) -> None:
    """Unauthenticated calls must be rejected with 401."""
    response = client.post(
        CHAT_URL,
        json={
            "model": "legalia",
            "messages": [{"role": "user", "content": "¿Qué es el derecho de petición?"}],
        },
    )

    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_chat_completions_rejects_invalid_token(client: TestClient) -> None:
    """Corrupted bearer tokens must receive 401."""
    response = client.post(
        CHAT_URL,
        headers={"Authorization": "Bearer not-a-valid-token"},
        json={
            "model": "legalia",
            "messages": [{"role": "user", "content": "¿Qué es el derecho de petición?"}],
        },
    )

    assert response.status_code == 401


def test_chat_completions_service_token_without_user_identity_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Service token caller must supply user identity via header or body `user`."""
    service_token = "valid-test-service-token"
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", service_token)

    response = client.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {service_token}"},
        json={
            "model": "legalia",
            "messages": [{"role": "user", "content": "¿Qué es el derecho de petición?"}],
        },
    )

    assert response.status_code == 400
    assert "must identify the end user" in response.json()["detail"]


# --- Request Validation -----------------------------------------------------


def test_chat_completions_rejects_empty_messages(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty message array fails schema validation (422)."""
    service_token = "valid-test-service-token"
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", service_token)

    response = client.post(
        CHAT_URL,
        headers={
            "Authorization": f"Bearer {service_token}",
            "X-LegalIA-User": "test-user-1",
        },
        json={"model": "legalia", "messages": []},
    )

    assert response.status_code == 422


def test_chat_completions_rejects_no_user_turn(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A conversation without any user turn fails with 400."""
    service_token = "valid-test-service-token"
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", service_token)

    response = client.post(
        CHAT_URL,
        headers={
            "Authorization": f"Bearer {service_token}",
            "X-LegalIA-User": "test-user-1",
        },
        json={
            "model": "legalia",
            "messages": [{"role": "assistant", "content": "Hola, ¿en qué puedo ayudarte?"}],
        },
    )

    assert response.status_code == 400
    assert "at least one user message" in response.json()["detail"]


# --- Error Handling ----------------------------------------------------------


def test_chat_completions_handles_llm_failure_as_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the LLM provider fails, return 503 rather than disguising it as lack of evidence."""
    service_token = "valid-test-service-token"
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", service_token)

    # Mock user resolution to avoid needing a live DB for this unit test
    mock_user = User(
        email="test@librechat.internal",
        external_issuer="librechat",
        external_subject="test-user-1",
        is_active=True,
    )
    monkeypatch.setattr("app.api.dependencies._resolve_external_user", lambda session, subject: mock_user)

    async def _failing_answer(*args, **kwargs):
        raise LLMError("Provider timeout or upstream crash")

    monkeypatch.setattr("app.services.chat_service.ChatService.answer", _failing_answer)

    response = client.post(
        CHAT_URL,
        headers={
            "Authorization": f"Bearer {service_token}",
            "X-LegalIA-User": "test-user-1",
        },
        json={
            "model": "legalia",
            "messages": [{"role": "user", "content": "¿Qué es la tutela?"}],
        },
    )

    assert response.status_code == 503
    assert "no está disponible" in response.json()["detail"]


# --- Successful Completions & Metadata ---------------------------------------


def test_chat_completions_returns_openai_shape_with_legalia_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate OpenAI-compatible payload shape with LegalIA audit metadata."""
    import uuid

    from app.db.models.enums import VerificationStatus
    from app.services.chat_service import ChatOutcome

    service_token = "valid-test-service-token"
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", service_token)

    mock_user = User(
        email="test@librechat.internal",
        external_issuer="librechat",
        external_subject="test-user-1",
        is_active=True,
    )
    monkeypatch.setattr("app.api.dependencies._resolve_external_user", lambda session, subject: mock_user)

    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    async def _mock_answer(*args, **kwargs):
        return ChatOutcome(
            answer="Según el artículo 13 de la Constitución Política [1], todas las personas nacen libres e iguales ante la ley.",
            conversation_id=conv_id,
            message_id=msg_id,
            model="claude-sonnet-4-5",
            input_tokens=120,
            output_tokens=45,
            latency_ms=450,
            refused_for_lack_of_evidence=False,
            verification_status=VerificationStatus.NOT_VERIFIED,
            retrieval_candidate_count=5,
            context_chunk_count=2,
            top_evidence_score=0.92,
            reranked=True,
            lexical_degraded=False,
        )

    monkeypatch.setattr("app.services.chat_service.ChatService.answer", _mock_answer)

    response = client.post(
        CHAT_URL,
        headers={
            "Authorization": f"Bearer {service_token}",
            "X-LegalIA-User": "test-user-1",
        },
        json={
            "model": "legalia",
            "messages": [{"role": "user", "content": "¿Qué dice el artículo 13 de la Constitución?"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    resp_obj = ChatCompletionResponse.model_validate(data)

    assert resp_obj.object == "chat.completion"
    assert len(resp_obj.choices) == 1
    assert resp_obj.choices[0].message.role == "assistant"
    assert "artículo 13" in resp_obj.choices[0].message.content
    assert resp_obj.usage.prompt_tokens == 120
    assert resp_obj.usage.completion_tokens == 45
    assert resp_obj.legalia.refused_for_lack_of_evidence is False
    assert resp_obj.legalia.conversation_id == str(conv_id)
    assert resp_obj.legalia.message_id == str(msg_id)
    assert resp_obj.legalia.context_chunk_count == 2

"""Unit tests for the conversations API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.enums import MessageRole
from app.db.models.user import User
from app.db.session import get_session
from app.services import auth_service


@pytest.fixture
def api(app, db_session: Session) -> TestClient:
    """Client whose requests run inside the test's transaction."""
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user(db_session: Session) -> User:
    return auth_service.register_user(
        db_session, email="convo_test@legalia.co", password="Password123!", full_name="Test Lawyer"
    )


def test_conversations_crud(api: TestClient, db_session: Session, user: User):
    """Test full CRUD operations on /api/v1/conversations."""
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initially empty or lists existing
    res = api.get("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    initial_count = len(res.json())

    # 2. Create / sync a conversation
    convo_id = "test-convo-123"
    create_payload = {
        "id": convo_id,
        "title": "Análisis Constitucional Tutela",
        "specialization": "constitutional",
    }
    res = api.post("/api/v1/conversations", json=create_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == convo_id
    assert data["title"] == "Análisis Constitucional Tutela"
    assert data["specialization"] == "constitutional"

    # 3. Add a message directly in DB for testing retrieval
    convo_db = db_session.query(Conversation).filter(Conversation.external_conversation_id == convo_id).first()
    assert convo_db is not None
    user_msg = Message(
        conversation_id=convo_db.id,
        role=MessageRole.USER,
        content="¿Cómo procede la acción de tutela contra providencias judiciales?",
    )
    asst_msg = Message(
        conversation_id=convo_db.id,
        role=MessageRole.ASSISTANT,
        content="La acción de tutela contra providencias judiciales procede de manera excepcional...",
    )
    db_session.add_all([user_msg, asst_msg])
    db_session.commit()

    # 4. Get conversation details
    res = api.get(f"/api/v1/conversations/{convo_id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == convo_id
    assert detail["title"] == "Análisis Constitucional Tutela"
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"

    # 5. List conversations includes the new one
    res = api.get("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == initial_count + 1
    assert any(c["id"] == convo_id for c in items)

    # 6. Delete conversation
    res = api.delete(f"/api/v1/conversations/{convo_id}", headers=headers)
    assert res.status_code == 204

    # 7. Verify deletion
    res = api.get(f"/api/v1/conversations/{convo_id}", headers=headers)
    assert res.status_code == 404

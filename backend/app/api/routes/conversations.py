"""Conversation management endpoints.

Allows the frontend to list, retrieve, and delete conversations and their
audited messages persisted in PostgreSQL.
"""

from __future__ import annotations

import time
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import joinedload

from app.api.dependencies import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.services.generation_manager import generation_manager

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = get_logger(__name__)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    timestamp: int
    verification_status: str | None = None
    refused_for_lack_of_evidence: bool = False
    latency_ms: int | None = None


class ConversationListItem(BaseModel):
    id: str
    title: str
    specialization: str = "general"
    created_at: int
    updated_at: int
    message_count: int = 0
    is_generating: bool = False


class ConversationDetail(BaseModel):
    id: str
    title: str
    specialization: str = "general"
    created_at: int
    updated_at: int
    is_generating: bool = False
    generating_text: str | None = None
    messages: list[MessageOut]


class CreateConversationRequest(BaseModel):
    id: str | None = None
    title: str = "Nueva conversación"
    specialization: str = "general"


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    current_user: CurrentUser,
    session: DbSession,
) -> list[ConversationListItem]:
    """List all conversations belonging to the authenticated user."""
    convos = (
        session.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    items: list[ConversationListItem] = []
    for c in convos:
        convo_id_str = c.external_conversation_id or str(c.id)
        active_job = generation_manager.get_active_job_for_conversation(convo_id_str)
        is_generating = active_job is not None

        meta = c.conversation_metadata or {}
        spec = meta.get("specialization", "general")

        created_ms = int(c.created_at.timestamp() * 1000) if c.created_at else int(time.time() * 1000)
        updated_ms = int(c.updated_at.timestamp() * 1000) if c.updated_at else created_ms

        items.append(
            ConversationListItem(
                id=convo_id_str,
                title=c.title or "Conversación",
                specialization=spec,
                created_at=created_ms,
                updated_at=updated_ms,
                message_count=len(c.messages),
                is_generating=is_generating,
            )
        )
    return items


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: DbSession,
) -> ConversationDetail:
    """Retrieve full conversation details and its audited messages."""
    # Lookup by external_conversation_id first, then by internal UUID
    convo = (
        session.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.external_conversation_id == conversation_id,
        )
        .first()
    )

    if not convo:
        try:
            parsed_uuid = uuid.UUID(conversation_id)
            convo = (
                session.query(Conversation)
                .options(joinedload(Conversation.messages))
                .filter(
                    Conversation.user_id == current_user.id,
                    Conversation.id == parsed_uuid,
                )
                .first()
            )
        except ValueError:
            pass

    if not convo:
        # If active job exists in background, return virtual in-progress conversation
        active_job = generation_manager.get_active_job_for_conversation(conversation_id)
        if active_job:
            now_ms = int(time.time() * 1000)
            return ConversationDetail(
                id=conversation_id,
                title=active_job.question[:40] or "Conversación en curso",
                specialization="general",
                created_at=int(active_job.created_at * 1000),
                updated_at=now_ms,
                is_generating=True,
                generating_text=active_job.accumulated_text,
                messages=[
                    MessageOut(
                        id=f"msg-{uuid.uuid4().hex[:8]}",
                        role="user",
                        content=active_job.question,
                        timestamp=int(active_job.created_at * 1000),
                    ),
                    MessageOut(
                        id=f"msg-{uuid.uuid4().hex[:8]}",
                        role="assistant",
                        content=active_job.accumulated_text,
                        timestamp=now_ms,
                    ),
                ],
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )

    convo_id_str = convo.external_conversation_id or str(convo.id)
    active_job = generation_manager.get_active_job_for_conversation(convo_id_str)
    is_generating = active_job is not None
    generating_text = active_job.accumulated_text if active_job else None

    meta = convo.conversation_metadata or {}
    spec = meta.get("specialization", "general")

    created_ms = int(convo.created_at.timestamp() * 1000) if convo.created_at else int(time.time() * 1000)
    updated_ms = int(convo.updated_at.timestamp() * 1000) if convo.updated_at else created_ms

    messages_out: list[MessageOut] = []
    for m in convo.messages:
        m_created_ms = int(m.created_at.timestamp() * 1000) if m.created_at else created_ms
        messages_out.append(
            MessageOut(
                id=str(m.id),
                role=m.role.value if hasattr(m.role, "value") else str(m.role),
                content=m.content,
                timestamp=m_created_ms,
                verification_status=m.verification_status.value if m.verification_status else None,
                refused_for_lack_of_evidence=m.refused_for_lack_of_evidence or False,
                latency_ms=m.latency_ms,
            )
        )

    # If generating, ensure user sees partial text
    if is_generating and generating_text and (not messages_out or messages_out[-1].role != "assistant"):
        messages_out.append(
            MessageOut(
                id=f"msg-gen-{uuid.uuid4().hex[:8]}",
                role="assistant",
                content=generating_text,
                timestamp=int(time.time() * 1000),
            )
        )

    return ConversationDetail(
        id=convo_id_str,
        title=convo.title or "Conversación",
        specialization=spec,
        created_at=created_ms,
        updated_at=updated_ms,
        is_generating=is_generating,
        generating_text=generating_text,
        messages=messages_out,
    )


@router.post("", response_model=ConversationListItem)
def create_or_sync_conversation(
    payload: CreateConversationRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> ConversationListItem:
    """Create or update a conversation metadata in PostgreSQL."""
    convo = None
    if payload.id:
        convo = (
            session.query(Conversation)
            .filter(
                Conversation.user_id == current_user.id,
                Conversation.external_conversation_id == payload.id,
            )
            .first()
        )

    if not convo:
        convo = Conversation(
            user_id=current_user.id,
            title=payload.title,
            external_conversation_id=payload.id,
            conversation_metadata={"specialization": payload.specialization},
        )
        session.add(convo)
    else:
        convo.title = payload.title
        meta = dict(convo.conversation_metadata or {})
        meta["specialization"] = payload.specialization
        convo.conversation_metadata = meta

    session.commit()
    session.refresh(convo)

    convo_id_str = convo.external_conversation_id or str(convo.id)
    created_ms = int(convo.created_at.timestamp() * 1000) if convo.created_at else int(time.time() * 1000)
    updated_ms = int(convo.updated_at.timestamp() * 1000) if convo.updated_at else created_ms

    return ConversationListItem(
        id=convo_id_str,
        title=convo.title or "Conversación",
        specialization=payload.specialization,
        created_at=created_ms,
        updated_at=updated_ms,
        message_count=len(convo.messages),
        is_generating=False,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: DbSession,
):
    """Delete a conversation and all its messages."""
    convo = (
        session.query(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.external_conversation_id == conversation_id,
        )
        .first()
    )

    if not convo:
        try:
            parsed_uuid = uuid.UUID(conversation_id)
            convo = (
                session.query(Conversation)
                .filter(
                    Conversation.user_id == current_user.id,
                    Conversation.id == parsed_uuid,
                )
                .first()
            )
        except ValueError:
            pass

    if convo:
        session.delete(convo)
        session.commit()

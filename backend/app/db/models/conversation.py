"""Conversations owned by LegalIA.

LibreChat keeps its own conversation history in MongoDB for display purposes.
LegalIA keeps these rows because a legal answer must stay auditable on its own
terms: which sources were retrieved, what verification concluded, what the user
was actually told. That record cannot live in a frontend that is meant to be
replaceable.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.user import User


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Short label for listings. Derived from the first question by the chat
    # service; never the full question text.
    title: Mapped[str | None] = mapped_column(String(255))

    # LibreChat's conversation id, when the turn arrived through it. Lets a
    # LegalIA record be lined up with what the user sees in the frontend.
    external_conversation_id: Mapped[str | None] = mapped_column(String(255))

    conversation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )

    __table_args__ = (
        # A LibreChat conversation maps to at most one LegalIA conversation.
        UniqueConstraint(
            "user_id",
            "external_conversation_id",
            name="uq_conversations_user_id_external_conversation_id",
        ),
        # Conversation list for a user, most recent first.
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} user={self.user_id}>"

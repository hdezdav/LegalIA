"""Individual turns within a conversation.

An assistant message carries the audit trail of how it was produced: what
retrieval returned, what verification concluded, and whether the pipeline
refused to answer for lack of evidence. Citations hang off this row.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import MessageRole, VerificationStatus

if TYPE_CHECKING:
    from app.db.models.citation import Citation
    from app.db.models.conversation import Conversation


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
        create_constraint=False,
    )


class Message(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """One turn. Append-only: a message is never edited after it is stored."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        _pg_enum(MessageRole, "message_role"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Audit trail (assistant messages only) ----------------------------
    # NULL on user messages. Populated by the chat pipeline so an answer can be
    # explained after the fact without replaying it.

    verification_status: Mapped[VerificationStatus | None] = mapped_column(
        _pg_enum(VerificationStatus, "verification_status"), index=True
    )

    # True when the NO EVIDENCE -> NO ANSWER path fired: the model was never
    # asked to answer because retrieval did not clear the evidence threshold.
    refused_for_lack_of_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    # How many candidates retrieval returned, and how many survived reranking
    # into the context window. Counts only, never the passages themselves.
    retrieval_candidate_count: Mapped[int | None] = mapped_column(Integer)
    context_chunk_count: Mapped[int | None] = mapped_column(Integer)

    # Best reranked score, compared against MIN_EVIDENCE_SCORE. Kept so a
    # refusal can be justified with the number that caused it.
    top_evidence_score: Mapped[float | None] = mapped_column(Float)

    # Model that produced this message, recorded per turn: the configured model
    # can change between turns of the same conversation.
    model: Mapped[str | None] = mapped_column(String(128))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    # Ties this turn to its usage_logs row and to the request_id in the logs.
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)

    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list[Citation]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Citation.position",
    )

    __table_args__ = (
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0", name="input_tokens_non_negative"
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="output_tokens_non_negative",
        ),
        # A user message can never carry an answer's audit fields.
        CheckConstraint(
            "role <> 'user' OR (verification_status IS NULL "
            "AND refused_for_lack_of_evidence = false)",
            name="user_messages_have_no_verification",
        ),
        # Turn order within a conversation.
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        # Content is the user's legal question or the answer; never in repr.
        return (
            f"<Message {self.id} role={self.role} "
            f"verification={self.verification_status}>"
        )

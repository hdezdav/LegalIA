"""Usage accounting: one row per pipeline request.

Deliberately content-free. Section 28 of the brief forbids storing prompts,
answers or private documents here, so this table holds identifiers, counts,
scores and durations only. That is enough to answer "what did this cost, how long
did it take, and did it produce grounded output?" without retaining the question.

Kept separate from `messages` because a request can fail before any message
exists, and those failures are exactly what capacity planning needs to see.
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
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import VerificationStatus

if TYPE_CHECKING:
    from app.db.models.user import User


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
        create_constraint=False,
    )


class UsageLog(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "usage_logs"

    # SET NULL rather than CASCADE: deleting a user must not erase the cost
    # record, which is aggregate operational data once de-identified.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Correlates this row with the structured logs and with messages.request_id.
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Which surface was exercised ("chat", "search"). Chat and bare retrieval
    # have very different cost profiles.
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # --- LLM cost ---------------------------------------------------------
    model: Mapped[str | None] = mapped_column(String(128), index=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)

    # Verification runs on a cheaper model; counted separately so grounding cost
    # is never hidden inside the answer cost.
    verifier_model: Mapped[str | None] = mapped_column(String(128))
    verifier_input_tokens: Mapped[int | None] = mapped_column(Integer)
    verifier_output_tokens: Mapped[int | None] = mapped_column(Integer)

    # --- Retrieval shape --------------------------------------------------
    embedding_provider: Mapped[str | None] = mapped_column(String(64), index=True)
    reranker_provider: Mapped[str | None] = mapped_column(String(64))
    retrieval_count: Mapped[int | None] = mapped_column(Integer)
    context_chunk_count: Mapped[int | None] = mapped_column(Integer)
    top_evidence_score: Mapped[float | None] = mapped_column(Float)

    # --- Outcome ----------------------------------------------------------
    verification_status: Mapped[VerificationStatus | None] = mapped_column(
        _pg_enum(VerificationStatus, "verification_status"), index=True
    )
    refused_for_lack_of_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    # HTTP status and an error *class* name. Never a message: exception strings
    # can quote the input that caused them.
    status_code: Mapped[int | None] = mapped_column(Integer, index=True)
    error_type: Mapped[str | None] = mapped_column(String(128))

    # --- Latency breakdown ------------------------------------------------
    # Total plus per-stage, so a slow turn can be attributed to the right stage
    # without tracing.
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    embedding_latency_ms: Mapped[int | None] = mapped_column(Integer)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer)
    rerank_latency_ms: Mapped[int | None] = mapped_column(Integer)
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer)
    verification_latency_ms: Mapped[int | None] = mapped_column(Integer)

    usage_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    user: Mapped[User | None] = relationship(back_populates="usage_logs")

    __table_args__ = (
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="input_tokens_non_negative",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="output_tokens_non_negative",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0", name="latency_non_negative"
        ),
        # Per-user cost over a window, the common billing/quota query.
        Index("ix_usage_logs_user_created", "user_id", "created_at"),
        # Refusal rate over time: the headline quality metric for
        # NO EVIDENCE -> NO ANSWER.
        Index(
            "ix_usage_logs_created_refused", "created_at", "refused_for_lack_of_evidence"
        ),
    )

    @property
    def total_tokens(self) -> int:
        return sum(
            t or 0
            for t in (
                self.input_tokens,
                self.output_tokens,
                self.verifier_input_tokens,
                self.verifier_output_tokens,
            )
        )

    def __repr__(self) -> str:
        return (
            f"<UsageLog {self.request_id} endpoint={self.endpoint} "
            f"status={self.status_code}>"
        )

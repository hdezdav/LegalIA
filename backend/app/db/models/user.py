"""LegalIA users.

Separate from LibreChat's own user store (MongoDB). `external_subject` is the
seam that lets a LibreChat identity be mapped onto a LegalIA user later without
a schema change.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.usage import UsageLog


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Stored lowercased by the auth service so lookups are case-insensitive
    # without needing citext.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)

    # NULL for users that only ever arrive through an external identity, so
    # such a row can never be logged into with a password.
    password_hash: Mapped[str | None] = mapped_column(String(128))

    full_name: Mapped[str | None] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # --- External identity mapping ----------------------------------------
    # Set when this user was created on behalf of a LibreChat account.
    # `external_issuer` names the system ("librechat"), `external_subject` its
    # user id there.
    external_issuer: Mapped[str | None] = mapped_column(String(64))
    external_subject: Mapped[str | None] = mapped_column(String(255))

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    usage_logs: Mapped[list[UsageLog]] = relationship(
        back_populates="user", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint(
            "external_issuer",
            "external_subject",
            name="uq_users_external_issuer_external_subject",
        ),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        # Email is PII; keep it out of repr so it cannot leak through a log line.
        return f"<User {self.id} active={self.is_active}>"

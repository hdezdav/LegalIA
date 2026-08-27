"""Authentication payloads.

Password rules live here rather than in the route so they are enforced
identically wherever a password is accepted, and so the error a client gets is a
422 with a field location instead of a 500 from deeper down.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES, MIN_PASSWORD_LENGTH


class _PasswordField(BaseModel):
    """Shared password validation."""

    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def _fits_bcrypt(cls, value: str) -> str:
        """Reject passwords bcrypt would silently truncate.

        bcrypt ignores everything past 72 bytes, which would make every longer
        suffix equivalent. Rejecting is honest; truncating is a security bug.
        """
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(
                f"Password must not exceed {MAX_PASSWORD_BYTES} bytes when "
                "UTF-8 encoded"
            )
        return value


class RegisterRequest(_PasswordField):
    email: EmailStr = Field(max_length=320)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(_PasswordField):
    email: EmailStr = Field(max_length=320)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Seconds until the access token expires, so a client need not decode the JWT.
    expires_in: int


class UserResponse(BaseModel):
    """Public view of a user. Never carries `password_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

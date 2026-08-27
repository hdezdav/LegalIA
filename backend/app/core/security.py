"""Password hashing and JWT issuance/verification.

Deliberately thin: no user lookup, no database access, no FastAPI types. The
routes and dependencies layer composes these primitives, which keeps them
directly unit-testable without a database.
"""

from __future__ import annotations

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

import bcrypt
import jwt

from app.core.config import settings

# bcrypt silently truncates at 72 bytes, so a longer password would make every
# suffix equivalent. Rejected explicitly instead.
MAX_PASSWORD_BYTES: Final = 72
MIN_PASSWORD_LENGTH: Final = 8


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised when a token is malformed, expired, or of the wrong type."""


# --- Passwords -------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Raises:
        ValueError: password is too short, or exceeds bcrypt's 72-byte limit.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )

    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} bytes when UTF-8 "
            "encoded (bcrypt truncates beyond that)"
        )

    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time password check. Never raises on malformed input."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Corrupt or non-bcrypt hash in the row: treat as a failed login rather
        # than a 500, but the caller still learns nothing about which it was.
        return False


# --- Tokens ----------------------------------------------------------------


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        # jti lets a specific token be revoked later without a schema change.
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        # Reserved claims are set above and must not be overridable.
        reserved = {"sub", "type", "iat", "exp", "jti"}
        payload.update(
            {k: v for k, v in extra_claims.items() if k not in reserved}
        )

    return jwt.encode(
        payload,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    subject: str, extra_claims: dict[str, Any] | None = None
) -> str:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(
    token: str, expected_type: TokenType | None = None
) -> dict[str, Any]:
    """Decode and validate a token.

    Args:
        token: the encoded JWT.
        expected_type: when given, reject a token of any other type. This is
            what stops a refresh token from being replayed as an access token.

    Raises:
        TokenError: signature, expiry, or type validation failed.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid") from exc

    if expected_type is not None and payload.get("type") != expected_type.value:
        raise TokenError(
            f"Expected a {expected_type.value} token, got "
            f"{payload.get('type')!r}"
        )

    return payload


# --- Service authentication ------------------------------------------------


def verify_service_token(presented: str) -> bool:
    """Compare a bearer token against LEGALIA_SERVICE_TOKEN.

    LibreChat authenticates as a service, not as an end user. Compared with
    hmac.compare_digest so a wrong token leaks no timing information.
    """
    configured = settings.LEGALIA_SERVICE_TOKEN
    if configured is None:
        return False
    expected = (
        configured.get_secret_value()
        if hasattr(configured, "get_secret_value")
        else str(configured)
    )
    if not expected:
        return False
    return hmac.compare_digest(presented, expected)

"""Password hashing and JWT primitives.

No database and no HTTP: these are the security decisions the rest of the auth
layer is built on, so they are tested in isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    MAX_PASSWORD_BYTES,
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_service_token,
)

# --- Passwords --------------------------------------------------------------


def test_hash_password_verifies_against_the_original() -> None:
    hashed = hash_password("correct horse battery")

    assert verify_password("correct horse battery", hashed)


def test_hash_password_rejects_a_wrong_password() -> None:
    hashed = hash_password("correct horse battery")

    assert not verify_password("Correct horse battery", hashed)


def test_hash_is_salted_so_equal_passwords_differ() -> None:
    """Two users with the same password must not share a hash."""
    first = hash_password("same password")
    second = hash_password("same password")

    assert first != second
    assert verify_password("same password", first)
    assert verify_password("same password", second)


def test_hash_password_rejects_a_short_password() -> None:
    with pytest.raises(ValueError, match="at least"):
        hash_password("short")


def test_hash_password_rejects_a_password_bcrypt_would_truncate() -> None:
    """bcrypt ignores bytes past 72, which would make longer suffixes equivalent.

    Rejecting is the honest behaviour; truncating silently is a security bug.
    """
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_password_length_limit_counts_bytes_not_characters() -> None:
    """Multi-byte characters consume bcrypt's budget faster than characters do."""
    # 'ñ' is two bytes in UTF-8, so 40 of them exceed 72 bytes at 40 characters.
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("ñ" * 40)


def test_accented_password_round_trips() -> None:
    hashed = hash_password("contraseña segura")

    assert verify_password("contraseña segura", hashed)


def test_verify_password_returns_false_for_a_corrupt_hash() -> None:
    """A malformed stored hash must fail the login, not raise a 500."""
    assert not verify_password("whatever", "not-a-bcrypt-hash")


def test_verify_password_returns_false_for_an_empty_hash() -> None:
    assert not verify_password("whatever", "")


# --- Tokens -----------------------------------------------------------------


def test_access_token_round_trips_its_subject() -> None:
    token = create_access_token("user-123")

    payload = decode_token(token, expected_type=TokenType.ACCESS)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_tokens_carry_a_unique_jti() -> None:
    """A per-token id is what makes selective revocation possible later."""
    first = decode_token(create_access_token("u"))
    second = decode_token(create_access_token("u"))

    assert first["jti"] != second["jti"]


def test_extra_claims_are_included() -> None:
    token = create_access_token("u", extra_claims={"email": "a@b.test"})

    assert decode_token(token)["email"] == "a@b.test"


def test_extra_claims_cannot_override_reserved_claims() -> None:
    """Otherwise a caller could mint a token for a different subject, or one that
    never expires."""
    token = create_access_token(
        "real-subject",
        extra_claims={"sub": "attacker", "type": "refresh", "exp": 0},
    )

    payload = decode_token(token, expected_type=TokenType.ACCESS)

    assert payload["sub"] == "real-subject"
    assert payload["type"] == "access"


def test_refresh_token_is_rejected_where_an_access_token_is_required() -> None:
    """The type check is what stops a long-lived refresh token being replayed as
    an access token."""
    refresh = create_refresh_token("user-123")

    with pytest.raises(TokenError, match="Expected a access token"):
        decode_token(refresh, expected_type=TokenType.ACCESS)


def test_access_token_is_rejected_where_a_refresh_token_is_required() -> None:
    access = create_access_token("user-123")

    with pytest.raises(TokenError, match="Expected a refresh token"):
        decode_token(access, expected_type=TokenType.REFRESH)


def test_expired_token_is_rejected() -> None:
    expired = jwt.encode(
        {
            "sub": "u",
            "type": "access",
            "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(TokenError, match="expired"):
        decode_token(expired)


def test_token_signed_with_another_secret_is_rejected() -> None:
    forged = jwt.encode(
        {
            "sub": "u",
            "type": "access",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        "a-different-secret",
        algorithm="HS256",
    )

    with pytest.raises(TokenError, match="invalid"):
        decode_token(forged)


def test_unsigned_token_is_rejected() -> None:
    """`alg: none` must never be accepted: it would make signatures optional."""
    unsigned = jwt.encode(
        {
            "sub": "u",
            "type": "access",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        key="",
        algorithm="none",
    )

    with pytest.raises(TokenError):
        decode_token(unsigned)


def test_token_without_required_claims_is_rejected() -> None:
    incomplete = jwt.encode(
        {"exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())},
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(TokenError):
        decode_token(incomplete)


def test_garbage_is_rejected() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.token")


# --- Service token ----------------------------------------------------------


def test_service_token_matches_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setattr(
        settings, "LEGALIA_SERVICE_TOKEN", SecretStr("shared-secret")
    )

    assert verify_service_token("shared-secret")
    assert not verify_service_token("shared-secre")


def test_service_token_is_rejected_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset service token must not authenticate anything, least of all an
    empty string."""
    monkeypatch.setattr(settings, "LEGALIA_SERVICE_TOKEN", None)

    assert not verify_service_token("")
    assert not verify_service_token("anything")

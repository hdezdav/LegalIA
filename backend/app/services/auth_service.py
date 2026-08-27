"""User registration, login and token refresh.

Holds the database work and the security decisions; the route layer only
translates results into HTTP. Keeping them apart is what lets these rules be
tested without a client, and reused by a future LibreChat identity bridge.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User

logger = get_logger(__name__)


class AuthError(Exception):
    """Base class for authentication failures."""


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    """Wrong email, wrong password, or a deactivated account.

    Deliberately one exception for all three: distinguishing them would let an
    attacker enumerate registered accounts.
    """


class InactiveUser(AuthError):
    """Raised only for an already-authenticated user whose account was disabled."""


def normalize_email(email: str) -> str:
    """Lowercase and trim.

    Applied on every write and every lookup so `users.email` stays effectively
    case-insensitive without a citext column.
    """
    return email.strip().lower()


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == normalize_email(email)))


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def register_user(
    session: Session,
    email: str,
    password: str,
    full_name: str | None = None,
) -> User:
    """Create a user.

    Raises:
        EmailAlreadyRegistered: the email is taken.
        ValueError: the password does not meet policy.
    """
    normalized = normalize_email(email)

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    session.add(user)

    try:
        # Flush rather than commit: the request-scoped session owns the
        # transaction, so a later failure in the same request still rolls this
        # back. The unique constraint is what actually decides the race.
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise EmailAlreadyRegistered(
            "An account with this email already exists"
        ) from exc

    logger.info("user registered", extra={"user_id": str(user.id)})
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    """Verify credentials and stamp `last_login_at`.

    Raises:
        InvalidCredentials: unknown email, wrong password, or inactive account.
    """
    user = get_user_by_email(session, email)

    if user is None:
        # Hash anyway so a missing account and a wrong password take
        # indistinguishable time. Without this, response latency alone reveals
        # which emails are registered.
        _burn_password_cycle(password)
        raise InvalidCredentials("Incorrect email or password")

    if user.password_hash is None:
        # External-identity user: no password was ever set, so password login
        # must not be possible for this row.
        _burn_password_cycle(password)
        raise InvalidCredentials("Incorrect email or password")

    if not verify_password(password, user.password_hash):
        logger.info("failed login", extra={"user_id": str(user.id)})
        raise InvalidCredentials("Incorrect email or password")

    if not user.is_active:
        logger.info("login by inactive user", extra={"user_id": str(user.id)})
        raise InvalidCredentials("Incorrect email or password")

    user.last_login_at = datetime.now(UTC)
    session.add(user)
    session.flush()

    logger.info("user logged in", extra={"user_id": str(user.id)})
    return user


def _burn_password_cycle(password: str) -> None:
    """Spend one bcrypt verification against a throwaway hash.

    Equalizes timing between "no such user" and "wrong password".
    """
    verify_password(
        password,
        "$2b$12$" + "0" * 22 + "0" * 31,  # structurally valid, matches nothing
    )


def get_or_create_external_user(
    session: Session, issuer: str, subject: str
) -> User:
    """Find or create the LegalIA user behind an external identity.

    Called on the service-token path, where a trusted frontend asserts which of
    its own users a request belongs to. The created row has no password hash, so
    it can never be used for password login.

    The synthetic email keeps `users.email` NOT NULL without inventing a real
    address: nothing is ever sent to it, and it is namespaced by issuer so it
    cannot collide with a self-registered account.
    """
    existing = session.scalar(
        select(User).where(
            User.external_issuer == issuer, User.external_subject == subject
        )
    )
    if existing is not None:
        return existing

    user = User(
        email=f"{subject}@{issuer}.external.legalia.invalid".lower(),
        password_hash=None,
        external_issuer=issuer,
        external_subject=subject,
        is_active=True,
    )
    session.add(user)

    try:
        session.flush()
    except IntegrityError:
        # Concurrent first request for the same identity: the unique constraint
        # decided, so adopt the row that won instead of failing the request.
        session.rollback()
        winner = session.scalar(
            select(User).where(
                User.external_issuer == issuer, User.external_subject == subject
            )
        )
        if winner is None:
            raise
        return winner

    logger.info(
        "external user provisioned",
        extra={"user_id": str(user.id), "external_issuer": issuer},
    )
    return user


def issue_tokens(user: User) -> tuple[str, str, int]:
    """Return (access_token, refresh_token, expires_in_seconds)."""
    access = create_access_token(str(user.id), extra_claims={"email": user.email})
    refresh = create_refresh_token(str(user.id))
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return access, refresh, expires_in


def refresh_access_token(session: Session, refresh_token: str) -> tuple[str, str, int]:
    """Exchange a refresh token for a fresh token pair.

    The token type is checked, so an access token cannot be replayed here to
    mint a longer-lived credential. The user is re-read from the database, so an
    account deactivated after the refresh token was issued stops working
    immediately.

    Raises:
        InvalidCredentials: the token is invalid, expired, of the wrong type, or
            its user no longer exists or is inactive.
    """
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError as exc:
        raise InvalidCredentials(str(exc)) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidCredentials("Token subject is not a valid user id") from exc

    user = get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise InvalidCredentials("User is no longer active")

    return issue_tokens(user)


def count_users(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User)) or 0

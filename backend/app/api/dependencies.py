"""Shared FastAPI dependencies.

Two kinds of caller reach this API:

* an **end user**, holding a LegalIA access token;
* the **frontend as a service**, holding LEGALIA_SERVICE_TOKEN, acting on behalf
  of one of its own users.

Both resolve to a `User` row, so everything downstream — conversations,
citations, usage accounting — is attributed the same way and never has to care
which door the request came through.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    TokenError,
    TokenType,
    decode_token,
    verify_service_token,
)
from app.db.models.user import User
from app.db.session import get_session
from app.services import auth_service

logger = get_logger(__name__)

# Alias for backwards compatibility / explicitness
get_db_session = get_session

# auto_error=False so a missing header produces our own 401 with a
# WWW-Authenticate challenge, rather than FastAPI's bare 403.
_bearer = HTTPBearer(auto_error=False, description="LegalIA access token")

DbSession = Annotated[Session, Depends(get_session)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(_bearer)
]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    session: DbSession, credentials: BearerCredentials
) -> User:
    """Resolve the caller from a LegalIA access token.

    Raises 401 for a missing, malformed, expired or wrong-type token, and for a
    token whose user has since been deleted or deactivated.
    """
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Token subject is not a valid user id") from exc

    user = auth_service.get_user_by_id(session, user_id)
    if user is None:
        # Valid signature, but the row is gone. Treated as unauthenticated
        # rather than 404: the caller learns nothing about which it was.
        raise _unauthorized("User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_superuser(user: CurrentUser) -> User:
    """Restrict an endpoint to administrators.

    Guards corpus mutation: ingesting or deleting a document changes what every
    future answer is grounded in.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires elevated privileges",
        )
    return user


CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]


@dataclass(slots=True)
class ChatCaller:
    """Who is asking, on the chat surface.

    Two shapes, because two kinds of caller reach it:

    * `user` set — an end user presented their own LegalIA access token, and the
      row is already resolved.
    * `user` None and `service_authenticated` True — a trusted frontend presented
      the service token. The end-user identity has not been established yet: it
      arrives in the request body (OpenAI's `user` field) or in the
      `X-LegalIA-User` header, and the route resolves it with `resolve_subject`.

    Split this way because the identity can live in the body, and a FastAPI
    dependency cannot see the body of an arbitrary request without coupling itself
    to that schema.
    """

    session: Session
    user: User | None = None
    service_authenticated: bool = False
    header_subject: str | None = None

    def resolve_subject(self, body_subject: str | None) -> User:
        """Return the acting user, mapping an external identity if needed.

        Args:
            body_subject: the identity from the request body, used when the header
                did not carry one. The header wins: it is set by the deployment,
                while the body is client-supplied.

        Raises:
            HTTPException: the service token was presented with no identity at all.
        """
        if self.user is not None:
            return self.user

        subject = (self.header_subject or body_subject or "").strip()
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A service token must identify the end user, either in the "
                    "X-LegalIA-User header or in the request's `user` field."
                ),
            )

        return _resolve_external_user(self.session, subject)


def resolve_chat_principal(
    session: DbSession,
    credentials: BearerCredentials,
    x_legalia_user: Annotated[
        str | None,
        Header(
            alias="X-LegalIA-User",
            description=(
                "End-user identity, sent by a trusted frontend together with the "
                "service token. Takes precedence over the body's `user` field."
            ),
        ),
    ] = None,
) -> ChatCaller:
    """Authenticate the chat caller, accepting either credential.

    A user access token resolves to its `User` immediately. A service token is
    accepted here and its end-user identity is resolved later by the route, since
    LibreChat carries that identity in the OpenAI `user` field rather than a header.

    Mapping an external identity onto a LegalIA user is the point: LibreChat owns
    its own user store, but a legal answer must be attributable to a stable LegalIA
    user or usage accounting and citation history have nothing to hang on.
    """
    if credentials is None:
        raise _unauthorized("Not authenticated")

    token = credentials.credentials

    # Service path first: a service token is not a JWT and would fail to decode.
    if settings.LEGALIA_SERVICE_TOKEN and verify_service_token(token):
        return ChatCaller(
            session=session,
            service_authenticated=True,
            header_subject=x_legalia_user,
        )

    return ChatCaller(session=session, user=get_current_user(session, credentials))


ChatPrincipal = Annotated[ChatCaller, Depends(resolve_chat_principal)]


def _resolve_external_user(session: Session, subject: str) -> User:
    """Find or create the LegalIA user behind an external identity.

    The row carries no password hash, so it can never be used for password
    login. `external_issuer` is fixed to "librechat": the service token already
    established which system is asserting the identity, so the caller does not
    get to choose the namespace it writes into.
    """
    subject = subject.strip()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-LegalIA-User must not be empty",
        )
    if len(subject) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-LegalIA-User exceeds the maximum length of 255",
        )

    user = auth_service.get_or_create_external_user(
        session, issuer="librechat", subject=subject
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
        )

    return user

"""Authentication endpoints.

Thin by design: every decision lives in `app.services.auth_service`, and this
module only maps its exceptions onto status codes. Note that login and refresh
failures collapse onto a single 401 with one message, so responses cannot be used
to tell a wrong password from an unregistered email.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service
from app.services.auth_service import EmailAlreadyRegistered, InvalidCredentials

router = APIRouter(tags=["auth"])

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={409: {"description": "Email already registered"}},
)
def register(payload: RegisterRequest, session: DbSession) -> UserResponse:
    try:
        user = auth_service.register_user(
            session,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        # Password policy rejected by the security layer. Schema validation
        # catches this first for normal clients; this covers the rest.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for a token pair",
    responses={401: {"description": "Incorrect email or password"}},
)
def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    try:
        user = auth_service.authenticate_user(
            session, email=payload.email, password=payload.password
        )
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    access, refresh, expires_in = auth_service.issue_tokens(user)
    return TokenResponse(
        access_token=access, refresh_token=refresh, expires_in=expires_in
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
    responses={401: {"description": "Invalid or expired refresh token"}},
)
def refresh(payload: RefreshRequest, session: DbSession) -> TokenResponse:
    try:
        access, refresh_token, expires_in = auth_service.refresh_access_token(
            session, payload.refresh_token
        )
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    return TokenResponse(
        access_token=access, refresh_token=refresh_token, expires_in=expires_in
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current authenticated user",
)
def me(user: CurrentUser) -> UserResponse:
    """Lets a client confirm a token is still valid without a side effect."""
    return UserResponse.model_validate(user)

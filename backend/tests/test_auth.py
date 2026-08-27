"""Authentication service and endpoint tests.

These exercise the real schema (unique constraints, nullable password_hash,
external identity mapping), so they need a live PostgreSQL and skip without
TEST_DATABASE_URL. The security primitives they build on are covered
database-free in test_security.py.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenType, create_access_token, decode_token
from app.db.models.user import User
from app.db.session import get_session
from app.services import auth_service
from app.services.auth_service import EmailAlreadyRegistered, InvalidCredentials

AUTH = f"{settings.API_V1_PREFIX}/auth"

PASSWORD = "a-valid-password"


@pytest.fixture
def api(app, db_session: Session) -> TestClient:
    """Client whose requests run inside the test's rolled-back transaction."""
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user(db_session: Session) -> User:
    return auth_service.register_user(
        db_session, email="Abogado@Example.CO", password=PASSWORD, full_name="Ada"
    )


# --- Service: registration --------------------------------------------------


def test_register_stores_the_email_lowercased(db_session: Session, user: User) -> None:
    """Emails are normalized on write so lookups are case-insensitive without
    a citext column."""
    assert user.email == "abogado@example.co"


def test_register_does_not_store_the_plaintext_password(user: User) -> None:
    assert user.password_hash is not None
    assert PASSWORD not in user.password_hash


def test_register_rejects_a_duplicate_email(db_session: Session, user: User) -> None:
    with pytest.raises(EmailAlreadyRegistered):
        auth_service.register_user(
            db_session, email="abogado@example.co", password=PASSWORD
        )


def test_register_treats_differently_cased_emails_as_the_same_account(
    db_session: Session, user: User
) -> None:
    with pytest.raises(EmailAlreadyRegistered):
        auth_service.register_user(
            db_session, email="ABOGADO@EXAMPLE.CO", password=PASSWORD
        )


# --- Service: login ---------------------------------------------------------


def test_authenticate_accepts_correct_credentials(
    db_session: Session, user: User
) -> None:
    authenticated = auth_service.authenticate_user(
        db_session, email="abogado@example.co", password=PASSWORD
    )

    assert authenticated.id == user.id


def test_authenticate_stamps_last_login(db_session: Session, user: User) -> None:
    assert user.last_login_at is None

    authenticated = auth_service.authenticate_user(
        db_session, email=user.email, password=PASSWORD
    )

    assert authenticated.last_login_at is not None


def test_authenticate_rejects_a_wrong_password(db_session: Session, user: User) -> None:
    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user(
            db_session, email=user.email, password="wrong-password"
        )


def test_authenticate_rejects_an_unknown_email(db_session: Session) -> None:
    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user(
            db_session, email="nobody@example.co", password=PASSWORD
        )


def test_authenticate_rejects_an_inactive_user(
    db_session: Session, user: User
) -> None:
    """A deactivated account must stop working immediately, and must not be
    distinguishable from a wrong password."""
    user.is_active = False
    db_session.flush()

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user(
            db_session, email=user.email, password=PASSWORD
        )


def test_password_login_is_impossible_for_an_external_identity_user(
    db_session: Session,
) -> None:
    """External users have no password hash, so no password may ever match."""
    external = auth_service.get_or_create_external_user(
        db_session, issuer="librechat", subject="lc-user-1"
    )
    assert external.password_hash is None

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user(
            db_session, email=external.email, password=PASSWORD
        )


# --- Service: external identity mapping ------------------------------------


def test_external_user_is_created_once_and_then_reused(db_session: Session) -> None:
    """The mapping must be stable: usage accounting and citation history hang off
    a single LegalIA user id per external identity."""
    first = auth_service.get_or_create_external_user(
        db_session, issuer="librechat", subject="lc-42"
    )
    second = auth_service.get_or_create_external_user(
        db_session, issuer="librechat", subject="lc-42"
    )

    assert first.id == second.id


def test_external_users_from_different_subjects_are_distinct(
    db_session: Session,
) -> None:
    first = auth_service.get_or_create_external_user(
        db_session, issuer="librechat", subject="lc-1"
    )
    second = auth_service.get_or_create_external_user(
        db_session, issuer="librechat", subject="lc-2"
    )

    assert first.id != second.id


# --- Service: refresh -------------------------------------------------------


def test_refresh_issues_a_new_token_pair(db_session: Session, user: User) -> None:
    _, refresh, _ = auth_service.issue_tokens(user)

    access, new_refresh, expires_in = auth_service.refresh_access_token(
        db_session, refresh
    )

    assert decode_token(access, expected_type=TokenType.ACCESS)["sub"] == str(user.id)
    assert decode_token(new_refresh, expected_type=TokenType.REFRESH)
    assert expires_in == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_refresh_rejects_an_access_token(db_session: Session, user: User) -> None:
    """Otherwise a leaked access token could be traded up for a long-lived one."""
    access, _, _ = auth_service.issue_tokens(user)

    with pytest.raises(InvalidCredentials):
        auth_service.refresh_access_token(db_session, access)


def test_refresh_stops_working_once_the_user_is_deactivated(
    db_session: Session, user: User
) -> None:
    """The user is re-read on refresh, so revocation does not wait for expiry."""
    _, refresh, _ = auth_service.issue_tokens(user)
    user.is_active = False
    db_session.flush()

    with pytest.raises(InvalidCredentials):
        auth_service.refresh_access_token(db_session, refresh)


def test_refresh_rejects_a_token_for_a_deleted_user(db_session: Session) -> None:
    orphan = create_access_token(str(uuid.uuid4()))

    with pytest.raises(InvalidCredentials):
        auth_service.refresh_access_token(db_session, orphan)


# --- Endpoints --------------------------------------------------------------


def test_register_endpoint_returns_the_user_without_its_hash(api: TestClient) -> None:
    response = api.post(
        f"{AUTH}/register",
        json={"email": "new@example.co", "password": PASSWORD, "full_name": "Ada"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.co"
    assert "password_hash" not in body
    assert "password" not in body


def test_register_endpoint_rejects_a_duplicate_with_409(
    api: TestClient, user: User
) -> None:
    response = api.post(
        f"{AUTH}/register", json={"email": user.email, "password": PASSWORD}
    )

    assert response.status_code == 409


def test_register_endpoint_rejects_a_short_password_with_422(api: TestClient) -> None:
    response = api.post(
        f"{AUTH}/register", json={"email": "short@example.co", "password": "abc"}
    )

    assert response.status_code == 422


def test_register_endpoint_rejects_a_malformed_email(api: TestClient) -> None:
    response = api.post(
        f"{AUTH}/register", json={"email": "not-an-email", "password": PASSWORD}
    )

    assert response.status_code == 422


def test_validation_error_does_not_echo_the_submitted_password(
    api: TestClient,
) -> None:
    """FastAPI's default 422 body includes the rejected input; ours must not,
    or a password would land in client logs."""
    response = api.post(
        f"{AUTH}/register", json={"email": "x@example.co", "password": "sh0rt"}
    )

    assert response.status_code == 422
    assert "sh0rt" not in response.text


def test_login_endpoint_returns_a_token_pair(api: TestClient, user: User) -> None:
    response = api.post(
        f"{AUTH}/login", json={"email": user.email, "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_token(body["access_token"], expected_type=TokenType.ACCESS)
    assert decode_token(body["refresh_token"], expected_type=TokenType.REFRESH)


def test_login_endpoint_gives_the_same_401_for_wrong_password_and_unknown_email(
    api: TestClient, user: User
) -> None:
    """Distinguishable responses would let an attacker enumerate accounts."""
    wrong_password = api.post(
        f"{AUTH}/login", json={"email": user.email, "password": "not-the-password"}
    )
    unknown_email = api.post(
        f"{AUTH}/login", json={"email": "nobody@example.co", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_endpoint_returns_a_new_pair(api: TestClient, user: User) -> None:
    _, refresh, _ = auth_service.issue_tokens(user)

    response = api.post(f"{AUTH}/refresh", json={"refresh_token": refresh})

    assert response.status_code == 200
    assert decode_token(response.json()["access_token"], expected_type=TokenType.ACCESS)


def test_refresh_endpoint_rejects_garbage_with_401(api: TestClient) -> None:
    response = api.post(f"{AUTH}/refresh", json={"refresh_token": "nonsense"})

    assert response.status_code == 401


def test_me_requires_authentication(api: TestClient) -> None:
    response = api.get(f"{AUTH}/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_returns_the_authenticated_user(api: TestClient, user: User) -> None:
    access, _, _ = auth_service.issue_tokens(user)

    response = api.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_me_rejects_a_refresh_token(api: TestClient, user: User) -> None:
    _, refresh, _ = auth_service.issue_tokens(user)

    response = api.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {refresh}"})

    assert response.status_code == 401


def test_me_returns_403_for_a_deactivated_user(
    api: TestClient, db_session: Session, user: User
) -> None:
    """403, not 401: the credential is valid, the account is not usable."""
    access, _, _ = auth_service.issue_tokens(user)
    user.is_active = False
    db_session.flush()

    response = api.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code == 403

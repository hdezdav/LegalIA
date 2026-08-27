"""Health endpoint tests.

Exercised without a database: `check_database` and friends are patched, because
what matters here is the endpoint's contract (status code, per-component
reporting) rather than live connectivity.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

HEALTH_URL = f"{settings.API_V1_PREFIX}/health"


@pytest.fixture
def all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("check_database", "check_pgvector", "check_text_search_config"):
        monkeypatch.setattr(f"app.api.routes.health.{name}", lambda: True)


def test_health_reports_ok_when_all_dependencies_up(
    client: TestClient, all_ok: None
) -> None:
    response = client.get(HEALTH_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["pgvector"] == "ok"
    assert body["text_search"] == "ok"
    assert body["detail"] is None


def test_health_exposes_active_provider_configuration(
    client: TestClient, all_ok: None
) -> None:
    """The endpoint must make it obvious which providers an instance is running.

    Without this, a deployment accidentally left on mock providers looks healthy
    and indistinguishable from a real one.
    """
    body = client.get(HEALTH_URL).json()

    assert body["embedding_provider"] == settings.EMBEDDING_PROVIDER
    assert body["embedding_dimension"] == settings.embedding_dimension
    assert body["reranker_provider"] == settings.RERANKER_PROVIDER
    assert body["llm_model"] == settings.ANTHROPIC_MODEL
    assert body["environment"] == "test"


def test_health_never_leaks_credentials(client: TestClient, all_ok: None) -> None:
    """No secret may appear in an unauthenticated response body."""
    raw = client.get(HEALTH_URL).text.lower()

    for forbidden in ("api_key", "secret", "password", "token"):
        assert forbidden not in raw


def test_health_returns_503_when_database_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.routes.health.check_database", lambda: False)

    response = client.get(HEALTH_URL)

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "error"
    assert "database" in body["detail"]


def test_health_does_not_report_derived_failures_when_database_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pgvector cannot be checked without a connection.

    It is reported as failing, but the detail names `database` as the cause so an
    operator is not sent chasing the extension.
    """
    monkeypatch.setattr("app.api.routes.health.check_database", lambda: False)

    def _must_not_run() -> bool:
        raise AssertionError("extension checks must be skipped when the DB is down")

    monkeypatch.setattr("app.api.routes.health.check_pgvector", _must_not_run)
    monkeypatch.setattr("app.api.routes.health.check_text_search_config", _must_not_run)

    body = client.get(HEALTH_URL).json()

    assert body["pgvector"] == "error"
    assert "database" in body["detail"]


def test_health_returns_503_when_pgvector_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No pgvector means no semantic retrieval: a hard failure, not a warning."""
    monkeypatch.setattr("app.api.routes.health.check_database", lambda: True)
    monkeypatch.setattr("app.api.routes.health.check_pgvector", lambda: False)
    monkeypatch.setattr("app.api.routes.health.check_text_search_config", lambda: True)

    response = client.get(HEALTH_URL)

    assert response.status_code == 503
    assert response.json()["pgvector"] == "error"


def test_health_degrades_but_stays_200_without_text_search_config(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Losing `legal_es` costs lexical retrieval, not the service.

    Semantic search still answers, so this must not take the instance out of
    rotation, but it must be visible.
    """
    monkeypatch.setattr("app.api.routes.health.check_database", lambda: True)
    monkeypatch.setattr("app.api.routes.health.check_pgvector", lambda: True)
    monkeypatch.setattr("app.api.routes.health.check_text_search_config", lambda: False)

    response = client.get(HEALTH_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["text_search"] == "degraded"
    assert "lexical" in body["detail"]


def test_health_response_carries_request_id(client: TestClient, all_ok: None) -> None:
    response = client.get(HEALTH_URL)

    assert response.headers.get("X-Request-ID")


def test_health_echoes_inbound_request_id(client: TestClient, all_ok: None) -> None:
    """An id supplied by Caddy or LibreChat must be preserved, not replaced."""
    response = client.get(HEALTH_URL, headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"

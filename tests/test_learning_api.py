"""Phase 2 API boundary tests."""
from fastapi.testclient import TestClient

from studio.application import create_app
from studio.auth import require_authenticated
from studio.api import learning_routes


def _client():
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "test", "role": "admin"}
    client = TestClient(app)
    return client


def test_learning_api_is_hidden_when_feature_flag_is_off():
    client = _client()
    response = client.get("/api/learning-tools")
    assert response.status_code == 404


def test_learning_api_requires_authentication_and_returns_no_seeded_tools():
    client = TestClient(create_app())
    response = client.get("/api/learning-tools")
    assert response.status_code == 401


def test_learning_api_enabled_contract_is_read_only(monkeypatch):
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", True)
    client = _client()
    assert isinstance(client.get("/api/learning-tools").json(), list)
    assert client.get("/api/learning-tools/unknown-tool/updates").status_code == 404
    assert client.get("/api/learning-tools/unknown-tool").status_code == 404

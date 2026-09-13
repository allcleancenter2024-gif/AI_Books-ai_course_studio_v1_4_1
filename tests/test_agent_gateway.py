import httpx

from providers.agents.hermes import HermesAdapter, HermesIntegrationError
from studio import config
from studio.db import init_db
from studio.services.agent_service import AgentService
from studio.services.source_service import _insert, delete_source


def test_agent_is_disabled_by_default_and_has_no_permissions(monkeypatch):
    monkeypatch.setattr(config, "HERMES_ENABLED", False)
    service = AgentService()
    assert service.health()["status"] == "disabled"
    assert service.capabilities() == {
        "status": "disabled", "skills": [], "tools": [], "write_allowed": False
    }


def test_hermes_failure_is_isolated(monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", unavailable)
    adapter = HermesAdapter("http://127.0.0.1:9999", "test-key", health_timeout=1)
    assert adapter.health().status == "unavailable"
    assert adapter.capabilities()["status"] == "unavailable"


def test_hermes_capabilities_are_read_only(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "platform": "hermes-agent", "model": "studio",
                "features": {"run_submission": True, "run_stop": True},
            }

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(httpx, "get", get)
    result = HermesAdapter("http://127.0.0.1:9999", "secret-test-key").capabilities()
    assert result == {
        "status": "healthy", "platform": "hermes-agent", "model": "studio",
        "features": {"run_submission": True, "run_stop": True}, "write_allowed": False,
    }
    assert calls[0][0] == "http://127.0.0.1:9999/v1/capabilities"
    assert calls[0][1]["headers"] == {"Authorization": "Bearer secret-test-key"}


def test_hermes_health_uses_public_official_endpoint_without_secret(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self): return None
        def json(self): return {"status": "ok"}

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(httpx, "get", get)
    result = HermesAdapter("http://127.0.0.1:8642", "secret-test-key").health()
    assert result.status == "healthy"
    assert calls == [("http://127.0.0.1:8642/health", {"headers": {}, "timeout": 3.0})]


def test_agent_rag_tool_returns_only_read_contract_fields():
    init_db()
    source = _insert("file", "Agent RAG", "agent.txt", text="Hermes는 Studio RAG를 Tool로 사용합니다.")
    try:
        rows = AgentService().search_course_knowledge([source["id"]], "Studio RAG", 2000)
        assert rows
        assert set(rows[0]) == {"source_id", "source_name", "text", "score", "retrieval_type"}
    finally:
        delete_source(source["id"])


def test_task_is_blocked_when_any_hermes_toolset_is_enabled(monkeypatch):
    class Response:
        def raise_for_status(self): return None
        def json(self): return [{"name": "terminal", "enabled": True}]

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response())
    adapter = HermesAdapter("http://127.0.0.1:8642", "test-key")
    try:
        adapter.run_task("Analyze this")
    except HermesIntegrationError as exc:
        assert "read-only policy" in str(exc)
    else:
        raise AssertionError("unsafe Hermes toolset was not blocked")


def test_task_submission_uses_runs_api_after_empty_toolset_check(monkeypatch):
    class GetResponse:
        def raise_for_status(self): return None
        def json(self): return []

    class PostResponse:
        def raise_for_status(self): return None
        def json(self): return {"run_id": "run_test", "status": "started"}

    calls = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: GetResponse())
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: calls.append((url, kwargs)) or PostResponse())
    result = HermesAdapter("http://127.0.0.1:8642", "test-key").run_task("Analyze this")
    assert result == {"task_id": "run_test", "status": "started"}
    assert calls[0][0] == "http://127.0.0.1:8642/v1/runs"
    assert "Read-only analysis only" in calls[0][1]["json"]["instructions"]

import httpx
import pytest

from fastapi import HTTPException

from providers.errors import (
    ProviderExecutionBlockedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from providers.engine import ProviderManager
from studio.api.provider_routes import _provider_failure


def test_provider_error_types_expose_safe_normalized_codes():
    assert ProviderTimeoutError.code == "provider_timeout"
    assert ProviderUnavailableError.code == "provider_unavailable"


def test_provider_error_is_exposed_with_a_safe_stable_http_contract():
    error = _provider_failure(ProviderTimeoutError("응답 시간이 초과되었습니다."))
    assert isinstance(error, HTTPException)
    assert error.status_code == 504
    assert error.detail == {"code": "provider_timeout", "message": "응답 시간이 초과되었습니다."}


def test_unknown_provider_error_does_not_expose_exception_detail():
    error = _provider_failure(RuntimeError("secret endpoint detail"))
    assert error.status_code == 502
    assert error.detail["code"] == "provider_request_failed"
    assert "secret endpoint detail" not in error.detail["message"]


def test_retry_network_failure_is_normalized(monkeypatch, caplog):
    manager = ProviderManager()

    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("providers.engine.httpx.Client", BrokenClient)
    monkeypatch.setattr("providers.engine.time.sleep", lambda _: None)
    with pytest.raises(ProviderUnavailableError):
        manager._post_json_with_retry("http://127.0.0.1:12345/v1/chat/completions", headers={}, body={}, timeout=httpx.Timeout(1), label="LM Studio")
    assert "connection refused" not in caplog.text


def test_live_health_probe_is_bounded_and_non_blocking(monkeypatch):
    manager = ProviderManager()
    manager.configs["lmstudio"].model = "qwen-local"

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "qwen-local"}]}

    monkeypatch.setattr("providers.engine.httpx.get", lambda *args, **kwargs: Response())
    result = manager.probe_health("lmstudio", timeout_seconds=1)
    assert result["status"] == "healthy" and result["probe"] == "ok"


def test_retry_is_bounded_to_three_attempts(monkeypatch):
    manager = ProviderManager()
    calls = {"count": 0}

    class Response:
        status_code = 503

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs):
            calls["count"] += 1
            return Response()

    monkeypatch.setattr("providers.engine.httpx.Client", Client)
    monkeypatch.setattr("providers.engine.time.sleep", lambda _: None)
    with pytest.raises(Exception):
        manager._post_json_with_retry("http://local", headers={}, body={}, timeout=httpx.Timeout(1), label="LM Studio")
    assert calls["count"] == 3


def test_audit_safe_mode_blocks_provider_execution(monkeypatch):
    manager = ProviderManager()
    monkeypatch.setattr("providers.engine.AUDIT_SAFE_MODE", True)
    with pytest.raises(ProviderExecutionBlockedError, match="Audit Safe Mode"):
        manager.get("lmstudio")

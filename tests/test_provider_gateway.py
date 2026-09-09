"""Provider gateway contract tests; no local server or network is contacted."""
from providers.engine import ProviderManager


def test_provider_health_snapshot_is_safe_and_capability_aware():
    manager = ProviderManager()
    rows = manager.list_public()
    assert {row["name"] for row in rows} == {"lmstudio", "ollama"}
    for row in rows:
        assert row["status"] in {"configured", "degraded", "disabled"}
        assert row["enabled"] is True
        assert row["capabilities"]["chat"] is True
        assert row["capabilities"]["structured_output"] is True
        assert "api_key" in row and row["api_key"] == ""


def test_disabled_provider_fails_at_gateway_boundary(monkeypatch):
    monkeypatch.setattr("providers.engine.LMSTUDIO_ENABLED", False)
    manager = ProviderManager()
    assert manager.health_snapshot("lmstudio")["status"] == "disabled"
    assert manager.list_public()[0]["enabled"] is False
    try:
        manager.get("lmstudio")
    except Exception as exc:
        assert "비활성화" in str(exc)
    else:
        raise AssertionError("disabled provider must not be returned by the gateway")

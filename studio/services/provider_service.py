"""Application-facing boundary for local AI provider operations."""
from __future__ import annotations

from typing import Any

from providers.engine import ProviderManager


class ProviderService:
    def __init__(self, manager: ProviderManager):
        self._manager = manager

    def list_public(self) -> list[dict[str, Any]]:
        return self._manager.list_public()

    def configure(self, provider: str, *, model: str | None, base_url: str | None, api_key: str | None, timeout: float | None) -> None:
        self._manager.configure(provider, model=model, base_url=base_url, api_key=api_key, timeout=timeout)

    def test(self, provider: str) -> dict[str, Any]:
        return self._manager.test(provider)

    def list_models(self, provider: str) -> list[dict[str, Any]]:
        return self._manager.list_models(provider, strict=True)

    def auto_connect(self, provider: str) -> dict[str, Any]:
        return self._manager.auto_connect(provider)

    def health_snapshot(self, provider: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        if provider:
            return self._manager.health_snapshot(provider)
        return [{"name": name, **self._manager.health_snapshot(name)} for name in ("lmstudio", "ollama")]

    def probe_health(self, provider: str) -> dict[str, Any]:
        return self._manager.probe_health(provider)

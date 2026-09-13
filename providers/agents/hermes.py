"""Minimal, read-only Hermes health and capability adapter."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import httpx

from .base import AgentHealth

logger = logging.getLogger(__name__)


class HermesIntegrationError(RuntimeError):
    """Safe boundary error that never includes response bodies or secrets."""


class HermesAdapter:
    def __init__(self, base_url: str, api_key: str = "", health_timeout: float = 3.0):
        self._base_url = base_url.rstrip("/") + "/"
        self._api_key = api_key
        self._timeout = max(1.0, min(float(health_timeout), 15.0))

    def _get(self, path: str, *, authenticated: bool = True, expected_type: type | tuple[type, ...] = dict):
        headers = {"Authorization": f"Bearer {self._api_key}"} if authenticated and self._api_key else {}
        response = httpx.get(
            urljoin(self._base_url, path.lstrip("/")),
            headers=headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, expected_type):
            raise ValueError("Hermes response has an unexpected JSON shape")
        return payload

    def _post(self, path: str, payload: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = httpx.post(
                urljoin(self._base_url, path.lstrip("/")),
                headers=headers,
                json=payload or {},
                timeout=self._timeout,
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Hermes response must be a JSON object")
            return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HermesIntegrationError("Hermes request failed") from exc

    def health(self) -> AgentHealth:
        try:
            payload = self._get("health", authenticated=False)
            return AgentHealth(
                status="healthy" if payload.get("status") == "ok" else "degraded",
                adapter="hermes",
                version=str(payload.get("version")) if payload.get("version") else None,
            )
        except (httpx.HTTPError, ValueError, TypeError):
            logger.info("Hermes health probe unavailable")
            return AgentHealth(status="unavailable", adapter="hermes")

    def capabilities(self) -> dict[str, object]:
        try:
            payload = self._get("v1/capabilities")
        except (httpx.HTTPError, ValueError, TypeError):
            return {"status": "unavailable", "features": {}, "write_allowed": False}
        features = payload.get("features", {})
        return {
            "status": "healthy",
            "platform": payload.get("platform"),
            "model": payload.get("model"),
            "features": features if isinstance(features, dict) else {},
            "write_allowed": False,
        }

    def _assert_read_only_toolsets(self) -> None:
        try:
            payload = self._get("v1/toolsets", expected_type=(dict, list))
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HermesIntegrationError("Hermes toolset verification failed") from exc
        rows = payload if isinstance(payload, list) else payload.get("toolsets", [])
        if not isinstance(rows, list):
            raise HermesIntegrationError("Hermes toolset verification failed")
        enabled = [row.get("name") for row in rows if isinstance(row, dict) and row.get("enabled")]
        if enabled:
            logger.warning("Hermes task blocked because API toolsets are enabled")
            raise HermesIntegrationError("Hermes read-only policy is not satisfied")

    def run_task(self, prompt: str) -> dict[str, object]:
        self._assert_read_only_toolsets()
        result = self._post("v1/runs", {
            "input": prompt,
            "instructions": (
                "Read-only analysis only. Do not use tools, modify files, change settings, "
                "publish content, or perform external actions. Return a draft for human review."
            ),
        })
        return {"task_id": result.get("run_id"), "status": result.get("status", "started")}

    def get_task_status(self, task_id: str) -> dict[str, object]:
        try:
            result = self._get(f"v1/runs/{task_id}")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HermesIntegrationError("Hermes status request failed") from exc
        return {
            "task_id": result.get("run_id", task_id),
            "status": result.get("status", "unknown"),
            "output": result.get("output") if result.get("status") == "completed" else None,
        }

    def cancel_task(self, task_id: str) -> dict[str, object]:
        result = self._post(f"v1/runs/{task_id}/stop")
        return {"task_id": result.get("run_id", task_id), "status": result.get("status", "stopping")}

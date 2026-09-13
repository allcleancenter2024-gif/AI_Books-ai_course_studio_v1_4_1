"""Application boundary for optional agent orchestration."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from providers.agents import DisabledAgentAdapter, HermesAdapter
from .. import config
from .book_service import get_book, list_books
from .vector_index import retrieve
from ..repositories.agent_task_repository import AgentTaskRepository


class AgentService:
    def __init__(self, tasks: AgentTaskRepository | None = None):
        self._tasks = tasks or AgentTaskRepository()

    def _adapter(self):
        if not config.HERMES_ENABLED:
            return DisabledAgentAdapter()
        return HermesAdapter(
            config.HERMES_BASE_URL,
            config.HERMES_API_KEY,
            config.HERMES_HEALTH_TIMEOUT_SECONDS,
        )

    def health(self) -> dict[str, object]:
        return self._adapter().health().public()

    def capabilities(self) -> dict[str, object]:
        return self._adapter().capabilities()

    def list_course_materials(self) -> list[dict[str, object]]:
        """Return minimal Studio-owned metadata without paths or provider secrets."""
        fields = ("id", "weeks", "audience", "created_at")
        return [{key: row.get(key) for key in fields} for row in list_books()]

    def course_outline(self, book_id: int) -> dict[str, object] | None:
        row = get_book(book_id)
        if not row:
            return None
        return {key: row.get(key) for key in ("id", "weeks", "audience", "created_at")}

    def search_course_knowledge(self, source_ids: list[int], query: str, max_total: int) -> list[dict]:
        rows = retrieve(source_ids, query, max_total=max_total, per_source=min(8_000, max_total))
        allowed = ("source_id", "source_name", "text", "score", "retrieval_type")
        return [{key: row.get(key) for key in allowed} for row in rows]

    def run_task(self, prompt: str, idempotency_key: str | None = None) -> dict[str, object]:
        key = idempotency_key or f"agent-{uuid4().hex}"
        existing = self._tasks.get_by_idempotency_key(key)
        if existing and existing.get("hermes_task_id"):
            return self._public_task(existing, duplicate=True)
        if existing:
            raise RuntimeError("An agent task with this idempotency key is still being submitted")
        correlation_id = f"corr_{uuid4().hex}"
        record = self._tasks.create_submission(
            correlation_id, key, sha256(prompt.encode("utf-8")).hexdigest(), config.HERMES_TASK_TIMEOUT_SECONDS
        )
        try:
            result = self._adapter().run_task(prompt)
            task_id = result.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise RuntimeError("Hermes did not return a task identifier")
            record = self._tasks.bind_task(correlation_id, task_id, str(result.get("status", "started")))
            return self._public_task(record)
        except Exception:
            self._tasks.mark_submission_failed(correlation_id)
            raise

    def get_task_status(self, task_id: str) -> dict[str, object]:
        audit = self._tasks.get_by_task_id(task_id)
        if audit and datetime.fromisoformat(audit["deadline_at"]) <= datetime.now(timezone.utc):
            self._adapter().cancel_task(task_id)
            self._tasks.update_status(task_id, "timed_out", error_code="deadline_exceeded")
            return {"task_id": task_id, "status": "timed_out", "output": None, "correlation_id": audit["correlation_id"]}
        last_error: Exception | None = None
        for retry_count in range(3):
            try:
                result = self._adapter().get_task_status(task_id)
                updated = self._tasks.update_status(task_id, str(result.get("status", "unknown")), retry_count=retry_count)
                if updated:
                    result["correlation_id"] = updated["correlation_id"]
                result["retry_count"] = retry_count
                return result
            except Exception as exc:
                last_error = exc
        self._tasks.update_status(task_id, "status_unavailable", retry_count=2, error_code="status_unavailable")
        raise last_error or RuntimeError("Hermes status request failed")

    def cancel_task(self, task_id: str) -> dict[str, object]:
        result = self._adapter().cancel_task(task_id)
        self._tasks.update_status(task_id, str(result.get("status", "stopping")))
        return result

    @staticmethod
    def _public_task(record: dict, duplicate: bool = False) -> dict[str, object]:
        return {
            "task_id": record.get("hermes_task_id"),
            "status": record.get("status"),
            "correlation_id": record.get("correlation_id"),
            "idempotency_key": record.get("idempotency_key"),
            "duplicate": duplicate,
            "deadline_at": record.get("deadline_at"),
        }


agent_service = AgentService()

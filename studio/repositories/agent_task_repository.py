"""Studio-owned audit store for optional Hermes task lifecycle state."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..db import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentTaskRepository:
    def get_by_idempotency_key(self, key: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_task_audit WHERE idempotency_key=?", (key,)
            ).fetchone()
        return dict(row) if row else None

    def get_by_task_id(self, task_id: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_task_audit WHERE hermes_task_id=?", (task_id,)
            ).fetchone()
        return dict(row) if row else None

    def create_submission(self, correlation_id: str, idempotency_key: str, prompt_sha256: str, timeout_seconds: int) -> dict:
        now = _now()
        deadline = (datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)).isoformat()
        with connect() as conn:
            conn.execute(
                """INSERT INTO agent_task_audit(
                    correlation_id,idempotency_key,status,prompt_sha256,deadline_at,created_at,updated_at
                ) VALUES(?,?, 'submitting', ?, ?, ?, ?)""",
                (correlation_id, idempotency_key, prompt_sha256, deadline, now, now),
            )
        return self.get_by_idempotency_key(idempotency_key) or {}

    def bind_task(self, correlation_id: str, task_id: str, status: str) -> dict:
        now = _now()
        with connect() as conn:
            conn.execute(
                """UPDATE agent_task_audit SET hermes_task_id=?,status=?,updated_at=?
                   WHERE correlation_id=?""",
                (task_id, status, now, correlation_id),
            )
        return self.get_by_task_id(task_id) or {}

    def mark_submission_failed(self, correlation_id: str) -> None:
        with connect() as conn:
            conn.execute(
                """UPDATE agent_task_audit SET status='submission_failed',error_code='submission_failed',updated_at=?
                   WHERE correlation_id=?""",
                (_now(), correlation_id),
            )

    def update_status(self, task_id: str, status: str, *, retry_count: int | None = None, error_code: str = "") -> dict | None:
        now = _now()
        with connect() as conn:
            if retry_count is None:
                conn.execute(
                    "UPDATE agent_task_audit SET status=?,error_code=?,updated_at=? WHERE hermes_task_id=?",
                    (status, error_code, now, task_id),
                )
            else:
                conn.execute(
                    """UPDATE agent_task_audit SET status=?,retry_count=?,error_code=?,updated_at=?
                       WHERE hermes_task_id=?""",
                    (status, min(max(retry_count, 0), 2), error_code, now, task_id),
                )
        return self.get_by_task_id(task_id)

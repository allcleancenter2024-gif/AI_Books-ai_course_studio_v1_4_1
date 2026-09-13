"""SQLite repository for Studio-owned agent drafts."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ..db import connect


def _row(row) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    result["review_required"] = bool(result["review_required"])
    return result


class AgentDraftRepository:
    def create_from_task(self, task_id: str, content: str, agent_version: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with connect() as conn:
            existing = conn.execute(
                "SELECT * FROM agent_drafts WHERE agent_task_id=?", (task_id,)
            ).fetchone()
            if existing:
                return _row(existing)
            draft_id = f"draft_{uuid4().hex}"
            conn.execute(
                """INSERT INTO agent_drafts(
                    id,agent_task_id,agent_source,agent_version,content,
                    review_required,quality_gate_status,human_approval_status,
                    created_at,updated_at
                ) VALUES(?,?,?,?,?,1,'not_checked','pending',?,?)""",
                (draft_id, task_id, "hermes", agent_version, content, now, now),
            )
            return _row(conn.execute("SELECT * FROM agent_drafts WHERE id=?", (draft_id,)).fetchone())

    def get(self, draft_id: str) -> dict | None:
        with connect() as conn:
            return _row(conn.execute("SELECT * FROM agent_drafts WHERE id=?", (draft_id,)).fetchone())

    def list_recent(self, limit: int = 50) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_drafts ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 50)),)
            ).fetchall()
        return [_row(row) for row in rows]

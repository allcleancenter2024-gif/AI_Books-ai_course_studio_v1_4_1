"""Read-only persistence boundary for the AI Tool Learning Center."""
from __future__ import annotations

from ..db import connect


class LearningRepository:
    """Keep Learning Center queries isolated from Course and Publisher storage."""

    def list_tools(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM learning_tools WHERE active=1 ORDER BY name_ko"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_tool(self, tool_id: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM learning_tools WHERE (id=? OR slug=?) AND active=1",
                (tool_id, tool_id),
            ).fetchone()
        return dict(row) if row else None

    def list_by_tool(self, table: str, tool_id: str, order_by: str) -> list[dict]:
        allowed = {
            "tool_versions": "released_at DESC, id",
            "tool_capabilities": "capability_key",
            "timeline_events": "event_date ASC, id",
            "prompt_examples": "level, example_no",
            "modern_prompt_examples": "effective_from DESC, modern_prompt_id",
            "source_evidence": "checked_at DESC, id",
            "update_events": "checked_at DESC, id",
        }
        if table not in allowed or order_by != allowed[table]:
            raise ValueError("Unsupported learning resource query")
        with connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE tool_id=? ORDER BY {order_by}",
                (tool_id,),
            ).fetchall()
        return [dict(row) for row in rows]

"""Write boundary for reviewed Learning Center decisions and versions."""
from __future__ import annotations

from ..db import connect


class LearningCommandRepository:
    def get_suggestion(self, suggestion_id: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM course_update_suggestions WHERE id=?", (suggestion_id,)
            ).fetchone()
        return dict(row) if row else None

    def save_decision(self, suggestion_id: str, decision: str, reviewer: str, reviewed_at: str,
                      reason: str, source_version: str, target_version: str) -> None:
        with connect() as conn:
            conn.execute(
                """INSERT INTO course_update_decisions(
                    id,suggestion_id,decision,reviewed_by,reviewed_at,reason,source_version,target_version
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (target_version or suggestion_id, suggestion_id, decision, reviewer, reviewed_at,
                 reason, source_version, target_version),
            )
            status = {
                "KEEP": "REJECTED", "REJECT": "REJECTED", "DEFER": "DEFERRED",
                "PARTIAL_APPLY": "APPROVED", "FULL_APPLY": "APPROVED",
            }[decision]
            conn.execute(
                "UPDATE course_update_suggestions SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?",
                (status, reviewed_at, reviewer, suggestion_id),
            )

    def course(self, course_id: int) -> dict | None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        return dict(row) if row else None

    def create_version(self, version: tuple) -> None:
        with connect() as conn:
            conn.execute(
                """INSERT INTO course_versions(
                    id,course_id,source_version,version_label,content_json,created_at,created_by,reason,status
                ) VALUES(?,?,?,?,?,?,?,?,?)""", version,
            )

    def mark_applied(self, suggestion_id: str) -> None:
        with connect() as conn:
            conn.execute(
                "UPDATE course_update_suggestions SET status='APPLIED' WHERE id=? AND status='APPROVED'",
                (suggestion_id,),
            )

    def list_suggestions(self, course_id: int, limit: int) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM course_update_suggestions WHERE course_id=? ORDER BY created_at DESC LIMIT ?",
                (course_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_versions(self, course_id: int, limit: int) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id,course_id,source_version,version_label,created_at,created_by,reason,status "
                "FROM course_versions WHERE course_id=? ORDER BY created_at DESC LIMIT ?",
                (course_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def audit(self, values: tuple) -> None:
        with connect() as conn:
            conn.execute(
                """INSERT INTO learning_audit_log(
                    event_id,event_type,actor,course_id,tool_id,source_version,target_version,
                    decision,timestamp,evidence_id,result
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", values,
            )

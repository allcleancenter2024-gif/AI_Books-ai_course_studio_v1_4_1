"""Repository boundary for explicit Course-to-tool references."""
from __future__ import annotations

from ..db import connect


class CourseToolReferenceRepository:
    def course(self, course_id: int) -> dict | None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        return dict(row) if row else None

    def candidate_lessons(self, course_id: int, needle: str) -> list[dict]:
        pattern = f"%{needle}%"
        with connect() as conn:
            rows = conn.execute(
                """SELECT id,week,topic FROM lessons
                   WHERE course_id=? AND (topic LIKE ? OR student_text LIKE ? OR teacher_text LIKE ?)
                   ORDER BY week""", (course_id, pattern, pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_references(self, course_id: int) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM course_tool_references WHERE course_id=? ORDER BY created_at DESC",
                (course_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def tool_exists(self, tool_id: str) -> bool:
        with connect() as conn:
            return conn.execute("SELECT 1 FROM learning_tools WHERE id=? AND active=1", (tool_id,)).fetchone() is not None

    def add_reference(self, values: tuple) -> None:
        with connect() as conn:
            conn.execute(
                """INSERT INTO course_tool_references(
                    id,course_id,week_id,lesson_id,tool_id,match_method,status,created_at
                ) VALUES(?,?,?,?,?,?,?,?)""", values,
            )

    def scan_inputs(self, course_id: int, tool_id: str | None = None) -> list[dict]:
        query = """SELECT r.*, t.name_ko, e.id AS update_event_id, e.summary AS update_summary,
                   e.status AS update_status, NULL AS source_evidence_id
                   FROM course_tool_references r
                   JOIN learning_tools t ON t.id=r.tool_id
                   JOIN update_events e ON e.tool_id=r.tool_id AND e.status='VERIFIED'
                   WHERE r.course_id=? AND r.status='APPROVED'"""
        args: list = [course_id]
        if tool_id:
            query += " AND r.tool_id=?"
            args.append(tool_id)
        with connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [dict(row) for row in rows]

    def lessons_for_scan(self, course_id: int, week_id: int | None, lesson_id: int | None) -> list[dict]:
        query = "SELECT id,week,topic,student_text,teacher_text FROM lessons WHERE course_id=?"
        args: list = [course_id]
        if lesson_id is not None:
            query += " AND id=?"
            args.append(lesson_id)
        elif week_id is not None:
            query += " AND week=?"
            args.append(week_id)
        with connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [dict(row) for row in rows]

    def record_scan(self, match: tuple, suggestion: tuple) -> None:
        with connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO course_update_matches(
                    id,course_id,tool_id,update_event_id,week_id,lesson_id,matched_text,match_context,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""", match,
            )
            conn.execute(
                """INSERT OR IGNORE INTO course_update_suggestions(
                    id,course_id,week_id,lesson_id,tool_id,match_id,matched_text,suggested_text,reason,severity,source_evidence_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", suggestion,
            )

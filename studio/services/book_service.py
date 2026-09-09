"""Book persistence and file-access boundary for API routes."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from ..config import BOOK_EXPORTS_DIR
from ..db import connect
from ..multidb import service_record, service_records


def list_books() -> list[dict]:
    rows = service_records("books")
    if rows is None:
        with connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT id,weeks,audience,provider,model,created_at,md_path FROM books ORDER BY id DESC LIMIT 50"
            )]
    fields = ("id", "weeks", "audience", "provider", "model", "created_at", "md_path")
    return [{key: row.get(key) for key in fields} for row in sorted(rows, key=lambda row: row.get("id", 0), reverse=True)[:50]]


def get_book(book_id: int) -> dict | None:
    row = service_record("books", book_id)
    if row is not None:
        return row
    with connect() as conn:
        legacy = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    return dict(legacy) if legacy else None


def book_source_path(book_id: int) -> tuple[dict, Path]:
    row = get_book(book_id)
    if not row or not row.get("md_path"):
        raise HTTPException(404, "교재를 찾을 수 없습니다.")
    path = Path(row["md_path"])
    if not path.exists():
        raise HTTPException(404, "교재 원본 파일을 찾을 수 없습니다.")
    return row, path


def export_course_markdown(course_id: int) -> Path:
    data = service_record("courses", course_id)
    if data is not None and data.get("data_json"):
        data = json.loads(data["data_json"])
    if data is None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not row:
            raise HTTPException(404, "과정을 찾을 수 없습니다.")
        data = json.loads(row["data_json"])
    if not data:
        raise HTTPException(404, "과정을 찾을 수 없습니다.")
    lines = [f"# {data['weeks']}주 AI 강의계획서", "", f"대상: {data['audience']}", "", data["ratio"], ""]
    for week in data["schedule"]:
        lines += [f"## {week['week']}주차 · {week['topic']}", f"- 대표 실습: {week['practice']}", "- 시간: 개념 18분 / 실기·실습 144분 / 정리·점검 18분", ""]
    path = BOOK_EXPORTS_DIR.parent / f"course_{course_id}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

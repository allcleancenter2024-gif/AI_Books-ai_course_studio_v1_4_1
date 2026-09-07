"""Apply verified product-change notes to a saved book and its Markdown file."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from ..db import connect
from ..multidb import service_record, upsert_service
from .generation_service import sanitize_exercises
from .course_service import course_source
from generators.course_content import book_to_markdown
from .latest_info_service import product_rows


def _book(book_id: int) -> dict:
    record = service_record("books", book_id)
    if record is not None:
        return record
    with connect() as connection:
        row = connection.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not row:
        raise HTTPException(404, "반영할 교재를 찾을 수 없습니다.")
    record = dict(row)
    try:
        return json.loads(record["data_json"])
    except (KeyError, json.JSONDecodeError):
        return record


def apply_change_to_book(book_id: int, product_name: str) -> dict:
    book = _book(book_id)
    path = Path(book.get("md_path") or "")
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "교재 Markdown 파일을 찾을 수 없습니다.")

    change = next((row for row in product_rows(changed_only=True) if row["product_name"] == product_name), None)
    if not change:
        raise HTTPException(404, "반영할 공식 변경사항을 찾을 수 없습니다.")

    applied = book.setdefault("applied_changes", [])
    if any(item.get("product_name") == product_name for item in applied):
        return {
            "ok": True, "applied": False, "message": "이 변경사항은 이미 교재에 반영되어 있습니다.",
            "view_url": f"/api/view/book/{book_id}", "download_url": f"/api/export/book/{book_id}",
        }

    changed_date = change.get("changed_date") or change.get("checked_date")
    note = [
        "", "", "---", "",
        f"## 최신 정보 변경 반영 · {change['current_name']}", "",
        f"- 기준일: {change['release_date']}",
        f"- 변경일: {changed_date}",
        f"- 변경 전: {change['baseline_info']}",
        f"- 변경 후: {change['changed_info']}",
        f"- 수업 반영 전 확인: {change['important_notes']}",
        f"- 공식 출처: {change['source_url']}",
    ]
    original = path.read_text(encoding="utf-8")
    temporary = path.with_suffix(path.suffix + ".updating")
    temporary.write_text(original + "\n".join(note) + "\n", encoding="utf-8")
    temporary.replace(path)

    applied.append({
        "product_name": product_name,
        "current_name": change["current_name"],
        "baseline_date": change["release_date"],
        "changed_date": changed_date,
        "applied_at": datetime.now().isoformat(timespec="seconds"),
    })
    upsert_service("books", book_id, book, created_at=book.get("created_at"))
    return {
        "ok": True, "applied": True, "message": f"{change['current_name']} 변경사항을 교재에 반영했습니다.",
        "view_url": f"/api/view/book/{book_id}", "download_url": f"/api/export/book/{book_id}",
    }


def repair_book_integrity(book_id: int) -> dict:
    book = _book(book_id)
    path = Path(book.get("md_path") or "")
    if not path.exists() or not path.is_file(): raise HTTPException(404, "교재 Markdown 파일을 찾을 수 없습니다.")
    changed = 0
    for lesson in book.get("content", []):
        week = int(lesson.get("week") or 0)
        try: topic, practice = course_source(int(book.get("weeks") or 12))[week - 1]
        except (IndexError, ValueError): continue
        after = sanitize_exercises(lesson.get("exercises", []), topic, practice)
        if after != lesson.get("exercises", []): lesson["exercises"] = after; changed += 1
    if changed:
        temporary = path.with_suffix(path.suffix + ".repairing")
        temporary.write_text(book_to_markdown(book), encoding="utf-8")
        temporary.replace(path)
        upsert_service("books", book_id, book, created_at=book.get("created_at"))
    return {"ok": True, "repaired_weeks": changed, "view_url": f"/api/view/book/{book_id}", "download_url": f"/api/export/book/{book_id}"}

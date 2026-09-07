from __future__ import annotations

from ..data.catalog import PRODUCT_CHANGE_DETAILS, PRODUCT_CHANGE_STATUS
from ..db import connect
from ..multidb import service_records


def product_rows(changed_only: bool = False) -> list[dict]:
    rows = service_records("ai_products")
    if rows is None:
        connection = connect()
        try: rows = [dict(row) for row in connection.execute("SELECT * FROM ai_products ORDER BY id")]
        finally: connection.close()
    rows.sort(key=lambda row: row.get("id", 0))
    result = []
    for row in rows:
        row.update(PRODUCT_CHANGE_STATUS.get(row["product_name"], {"has_changes": False, "change_note": "변경 상태 미확인"}))
        if row["has_changes"]:
            detail = PRODUCT_CHANGE_DETAILS.get(row["product_name"], {})
            row["baseline_info"] = detail.get("baseline_info", "이전 최신 정보센터 목록에 등록되지 않음")
            row["changed_info"] = detail.get("changed_info", f"{row['current_version']} · {row['features']}")
            row["important_notes"] = detail.get("important_notes", "수업에 사용하기 전 공식 웹페이지에서 이용 조건·요금·제공 기능을 다시 확인하세요.")
            row["is_major"] = bool(detail.get("is_major", False))
            row["changed_date"] = detail.get("changed_date", row["checked_date"])
        if not changed_only or row["has_changes"]:
            result.append(row)
    return result


def lesson_change_notes(context: str = "") -> list[str]:
    """Only surface changed products that are actually named in the lesson context."""
    query = context.lower()
    rows = product_rows(changed_only=True)
    if query:
        rows = [row for row in rows if row["current_name"].lower() in query or row["product_name"].lower() in query]
    return [f"[{row['current_name']} · 기준일 {row['release_date']}: {row['changed_info']}]" for row in rows]

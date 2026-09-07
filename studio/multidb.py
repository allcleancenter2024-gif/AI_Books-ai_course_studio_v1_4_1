"""Storage compatibility boundary.

SQLite is the authoritative desktop database. PostgreSQL/MongoDB are optional
export targets managed by ``scripts/sync_sqlite_to_multidb.py``; their absence
must never make the learning UI fail.
"""
from __future__ import annotations

import json
from typing import Any

from .db import connect


def _serialise(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def next_service_id(entity_type: str) -> int:
    table = {"courses": "courses", "books": "books", "ai_products": "ai_products", "source": "sources"}.get(entity_type)
    if not table:
        raise ValueError(f"지원하지 않는 저장 엔터티: {entity_type}")
    # Serialize allocation across FastAPI worker threads. Gaps are harmless;
    # duplicate IDs would overwrite a course/book, so they are not.
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT last_id FROM app_sequences WHERE entity_type=?", (entity_type,)).fetchone()
        table_next = int(conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0])
        record_id = max(table_next, int(current[0]) + 1 if current else 1)
        conn.execute("INSERT INTO app_sequences(entity_type,last_id) VALUES(?,?) ON CONFLICT(entity_type) DO UPDATE SET last_id=excluded.last_id", (entity_type, record_id))
        conn.commit()
        return record_id
    finally:
        conn.close()


def upsert_service(entity_type: str, record_id: int, payload: dict, mongo_id: str | None = None, created_at: str | None = None) -> None:
    """Persist structured records locally; retained under the old caller API."""
    if entity_type == "courses":
        with connect() as conn:
            conn.execute("INSERT OR REPLACE INTO courses(id,course_type,audience,created_date,data_json) VALUES(?,?,?,?,?)", (record_id, payload.get("weeks"), payload.get("audience"), created_at, _serialise(payload)))
    elif entity_type == "books":
        with connect() as conn:
            conn.execute("INSERT OR REPLACE INTO books(id,weeks,audience,provider,model,created_at,data_json,md_path) VALUES(?,?,?,?,?,?,?,?)", (record_id, payload.get("weeks"), payload.get("audience"), payload.get("provider"), payload.get("model"), created_at, _serialise(payload), payload.get("md_path")))


def service_record(entity_type: str, record_id: int) -> dict | None:
    table = {"courses": "courses", "books": "books", "ai_products": "ai_products"}.get(entity_type)
    if not table: return None
    with connect() as conn: row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
    if not row: return None
    data = dict(row)
    if data.get("data_json"):
        try: return json.loads(data["data_json"])
        except json.JSONDecodeError: pass
    return data


def service_records(entity_type: str) -> list[dict] | None:
    table = {"courses": "courses", "books": "books", "ai_products": "ai_products"}.get(entity_type)
    if not table: return None
    with connect() as conn: rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
    result = []
    for row in rows:
        if row.get("data_json"):
            try: row = json.loads(row["data_json"])
            except json.JSONDecodeError: pass
        result.append(row)
    return result


def create_source_record(row: dict) -> dict:
    fields = ("kind", "title", "original_name", "url", "mime_type", "local_path", "extracted_text", "summary", "status", "created_at", "metadata_json", "updated_at", "content_hash", "vector_status", "storage_mode", "summary_path")
    values = [row.get(field, "") for field in fields]
    with connect() as conn:
        cur = conn.execute(f"INSERT INTO sources({','.join(fields)}) VALUES({','.join('?' for _ in fields)})", values)
        row["id"] = cur.lastrowid
    return row


def update_source_record(source_id: int, **changes) -> dict:
    allowed = {"title", "original_name", "url", "mime_type", "local_path", "extracted_text", "summary", "status", "metadata_json", "updated_at", "content_hash", "vector_status", "storage_mode", "summary_path"}
    changes = {key: value for key, value in changes.items() if key in allowed}
    if not changes: raise KeyError(source_id)
    assignments = ", ".join(f"{key}=?" for key in changes)
    with connect() as conn:
        cur = conn.execute(f"UPDATE sources SET {assignments} WHERE id=?", (*changes.values(), source_id))
        if not cur.rowcount: raise KeyError(source_id)
    return source_record(source_id) or {}


def source_record(source_id: int) -> dict | None:
    with connect() as conn: row = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    return dict(row) if row else None


def source_records() -> list[dict] | None:
    with connect() as conn: return [dict(row) for row in conn.execute("SELECT * FROM sources ORDER BY id DESC")]


def delete_source(source_id: int) -> None:
    with connect() as conn: conn.execute("DELETE FROM sources WHERE id=?", (source_id,))


# Optional mirror hook: normal desktop execution is deliberately local-only.
def mirror_source(row: dict) -> None: return None

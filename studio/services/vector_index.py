"""Compact SQLite vector index for relevant source-context retrieval."""
from __future__ import annotations

import hashlib
import math
import re
import struct

from ..db import connect
from ..multidb import source_records, update_source_record

DIMENSIONS, CHUNK_SIZE, CHUNK_OVERLAP = 64, 1_800, 180


def _tokens(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]{2,}", text.lower())


def _vector(text: str) -> bytes:
    values = [0.0] * DIMENSIONS
    for token in _tokens(text):
        index = int.from_bytes(hashlib.blake2s(token.encode(), digest_size=4).digest(), "big") % DIMENSIONS
        values[index] += 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return struct.pack(f"<{DIMENSIONS}f", *(value / norm for value in values))


def _chunks(text: str):
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        yield start, end
        if end == len(text): return
        start = end - CHUNK_OVERLAP


def index_source(source_id: int, text: str) -> int:
    rows = [(source_id, no, start, end, _vector(text[start:end])) for no, (start, end) in enumerate(_chunks(text.strip()))]
    with connect() as conn:
        conn.execute("DELETE FROM source_vectors WHERE source_id=?", (source_id,))
        conn.executemany("INSERT INTO source_vectors(source_id,chunk_no,char_start,char_end,embedding) VALUES(?,?,?,?,?)", rows)
    update_source_record(source_id, vector_status=f"indexed:{len(rows)}")
    return len(rows)


def retrieve(ids: list[int], query: str, *, max_total: int = 24_000, per_source: int = 8_000) -> list[dict]:
    if not ids: return []
    sources = [row for row in (source_records() or []) if row["id"] in ids]
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        vectors = conn.execute(f"SELECT source_id,char_start,char_end,embedding FROM source_vectors WHERE source_id IN ({placeholders})", ids).fetchall()
    q = struct.unpack(f"<{DIMENSIONS}f", _vector(query)); ranked = {source["id"]: [] for source in sources}
    for row in vectors:
        values = struct.unpack(f"<{DIMENSIONS}f", row["embedding"])
        ranked[row["source_id"]].append((sum(a*b for a,b in zip(q, values)), row["char_start"], row["char_end"]))
    blocks, used = [], 0
    for source in sources:
        text = (source.get("extracted_text") or source.get("summary") or "").strip()
        parts = sorted(ranked[source["id"]], reverse=True)[:3]
        selected = "\n\n".join(text[start:end] for _, start, end in parts) if parts else text[:per_source]
        if not selected: continue
        block = f"[참고자료 #{source['id']}: {source['title']} · 갱신: {source.get('updated_at') or '미확인'}]\n출처: {source.get('url') or '업로드 자료'}\n{selected[:per_source]}"[:max_total-used]
        if block: blocks.append({"source_id": source["id"], "text": block}); used += len(block)
        if used >= max_total: break
    return blocks

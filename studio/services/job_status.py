from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from threading import RLock
import json

from ..db import connect


@dataclass
class Job:
    id: str
    phase: str = "waiting"
    message: str = "대기 중"
    progress: int = 0
    bytes_done: int = 0
    bytes_total: int = 0
    error: str = ""
    # Small, public completion metadata only (for example, a source-summary
    # download URL).  Never place provider credentials or raw source text here.
    result: dict | None = None
    updated_at: str = ""


class JobStore:
    def __init__(self):
        self._items: dict[str, Job] = {}
        self._lock = RLock()

    def _ensure_table(self) -> None:
        with connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS job_states(
                id TEXT PRIMARY KEY, phase TEXT NOT NULL, message TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                bytes_done INTEGER NOT NULL DEFAULT 0, bytes_total INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
                result_json TEXT, updated_at TEXT NOT NULL)""")

    def _load(self, job_id: str) -> Job | None:
        self._ensure_table()
        with connect() as conn:
            row = conn.execute("SELECT * FROM job_states WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["result"] = json.loads(data.pop("result_json")) if data.get("result_json") else None
        return Job(**data)

    def update(self, job_id: str, **values) -> dict:
        with self._lock:
            job = self._items.setdefault(job_id, Job(id=job_id))
            for key, value in values.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            job.progress = max(0, min(100, int(job.progress)))
            job.updated_at = datetime.now().isoformat(timespec="seconds")
            self._ensure_table()
            with connect() as conn:
                conn.execute("""INSERT INTO job_states
                    (id,phase,message,progress,bytes_done,bytes_total,error,result_json,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET phase=excluded.phase,message=excluded.message,
                    progress=excluded.progress,bytes_done=excluded.bytes_done,bytes_total=excluded.bytes_total,
                    error=excluded.error,result_json=excluded.result_json,updated_at=excluded.updated_at""",
                    (job.id, job.phase, job.message, job.progress, job.bytes_done, job.bytes_total,
                     job.error, json.dumps(job.result, ensure_ascii=False) if job.result is not None else None, job.updated_at))
            return asdict(job)

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._items.get(job_id)
            if job is None:
                job = self._load(job_id)
                if job is not None:
                    self._items[job_id] = job
            return asdict(job) if job else None

    def cancel(self, job_id: str) -> dict | None:
        with self._lock:
            if self.get(job_id) is None:
                return None
            return self.update(job_id, phase="cancelled", message="사용자가 작업을 취소했습니다.", progress=100, error="")

    def is_cancelled(self, job_id: str) -> bool:
        value = self.get(job_id)
        return bool(value and value.get("phase") == "cancelled")

    def prune(self):
        cutoff = datetime.now() - timedelta(hours=6)
        with self._lock:
            stale = [key for key, job in self._items.items() if job.updated_at and datetime.fromisoformat(job.updated_at) < cutoff]
            for key in stale:
                self._items.pop(key, None)
            self._ensure_table()
            with connect() as conn:
                conn.execute("DELETE FROM job_states WHERE updated_at < ?", (cutoff.isoformat(timespec="seconds"),))


jobs = JobStore()

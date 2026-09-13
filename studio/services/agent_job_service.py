"""Studio-owned bounded polling bridge from an agent task to JobStore."""
from __future__ import annotations

from threading import RLock, Thread
from time import sleep
from uuid import uuid4

from ..services.job_status import JobStore, jobs
from .agent_service import AgentService, agent_service


class AgentJobService:
    def __init__(self, tasks: AgentService = agent_service, store: JobStore = jobs):
        self._tasks, self._store = tasks, store
        self._active: set[str] = set()
        self._lock = RLock()

    def start(self, prompt: str, idempotency_key: str | None = None, job_id: str | None = None, capture_draft: bool = False) -> dict:
        job_id = job_id or f"agent-job-{uuid4().hex}"
        with self._lock:
            existing = self._store.get(job_id)
            if existing and existing.get("phase") not in {"complete", "error", "cancelled", "timed_out"}:
                return {"job_id": job_id, "accepted": True, "already_running": True}
            if self._active:
                raise RuntimeError("An Hermes agent job is already active")
            task = self._tasks.run_task(prompt, idempotency_key or f"job-{job_id}")
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise RuntimeError("Hermes task identifier is missing")
            self._store.update(job_id, phase="queued", message="Hermes 작업을 대기열에 등록했습니다.", progress=5,
                payload={"kind": "agent_task", "task_id": task_id, "correlation_id": task.get("correlation_id"), "capture_draft": capture_draft})
            self._active.add(job_id)
            Thread(target=self._poll, args=(job_id, task_id), daemon=True, name=f"agent-job-{job_id[-8:]}").start()
            return {"job_id": job_id, "task_id": task_id, "correlation_id": task.get("correlation_id"), "accepted": True}

    def _poll(self, job_id: str, task_id: str) -> None:
        try:
            while True:
                current = self._store.get(job_id) or {}
                # A caller-owned timeout is terminal too.  Do not let this
                # asynchronous poller overwrite it with Hermes' later
                # cancellation acknowledgement.
                if current.get("phase") in {"complete", "error", "cancelled", "timed_out"}:
                    if current.get("phase") == "cancelled":
                        self._tasks.cancel_task(task_id)
                    return
                status = self._tasks.get_task_status(task_id)
                current = self._store.get(job_id) or {}
                if current.get("phase") in {"complete", "error", "cancelled", "timed_out"}:
                    return
                phase = str(status.get("status", "unknown"))
                if phase == "completed":
                    current = self._store.get(job_id) or {}
                    draft_id = None
                    if (current.get("payload") or {}).get("capture_draft"):
                        try:
                            from .agent_draft_service import AgentDraftService
                            draft_id = AgentDraftService(tasks=self._tasks).capture_completed_task(task_id).get("id")
                        except Exception:
                            draft_id = None
                    self._store.update(job_id, phase="complete", message="Hermes 초안 생성 완료", progress=100,
                        result={"task_id": task_id, "correlation_id": status.get("correlation_id"), "draft_id": draft_id, "review_required": bool(draft_id)})
                    return
                if phase == "timed_out":
                    self._store.update(job_id, phase="timed_out", message="Hermes 작업 시간이 초과되었습니다.", progress=100, error="deadline_exceeded")
                    return
                if phase in {"failed", "cancelled", "canceled"}:
                    self._store.update(job_id, phase="error" if phase == "failed" else "cancelled", message="Hermes 작업이 종료되었습니다.", progress=100, error=phase)
                    return
                self._store.update(job_id, phase="generating", message="Hermes 초안을 생성하는 중", progress=50)
                sleep(1)
        except Exception:
            if not self._store.is_cancelled(job_id):
                self._store.update(job_id, phase="error", message="Hermes 작업 상태를 확인하지 못했습니다.", progress=100, error="agent_status_failed")
        finally:
            with self._lock:
                self._active.discard(job_id)

    def get(self, job_id: str) -> dict | None:
        return self._store.get(job_id)

    def cancel(self, job_id: str) -> dict | None:
        job = self._store.get(job_id)
        if not job or (job.get("payload") or {}).get("kind") != "agent_task":
            return None
        task_id = job["payload"].get("task_id")
        cancelled = self._store.cancel(job_id)
        if task_id:
            self._tasks.cancel_task(task_id)
        return cancelled


agent_jobs = AgentJobService()

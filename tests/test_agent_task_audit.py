from datetime import datetime, timedelta, timezone

from studio.services.agent_service import AgentService


class MemoryAudit:
    def __init__(self):
        self.rows = {}

    def get_by_idempotency_key(self, key):
        return self.rows.get(key)

    def get_by_task_id(self, task_id):
        return next((row for row in self.rows.values() if row.get("hermes_task_id") == task_id), None)

    def create_submission(self, correlation_id, key, prompt_sha256, timeout_seconds):
        row = {
            "correlation_id": correlation_id, "idempotency_key": key,
            "hermes_task_id": None, "status": "submitting", "prompt_sha256": prompt_sha256,
            "deadline_at": (datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)).isoformat(),
            "retry_count": 0,
        }
        self.rows[key] = row
        return row

    def bind_task(self, correlation_id, task_id, status):
        row = next(row for row in self.rows.values() if row["correlation_id"] == correlation_id)
        row.update(hermes_task_id=task_id, status=status)
        return row

    def mark_submission_failed(self, correlation_id):
        row = next(row for row in self.rows.values() if row["correlation_id"] == correlation_id)
        row.update(status="submission_failed")

    def update_status(self, task_id, status, *, retry_count=None, error_code=""):
        row = self.get_by_task_id(task_id)
        if row:
            row.update(status=status)
            if retry_count is not None:
                row["retry_count"] = retry_count
        return row


class FakeAdapter:
    def __init__(self, statuses=None):
        self.submissions = 0
        self.statuses = list(statuses or [{"task_id": "run_1", "status": "completed", "output": "ok"}])
        self.cancelled = []

    def run_task(self, prompt):
        self.submissions += 1
        return {"task_id": "run_1", "status": "started"}

    def get_task_status(self, task_id):
        value = self.statuses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def cancel_task(self, task_id):
        self.cancelled.append(task_id)
        return {"task_id": task_id, "status": "stopping"}


def _service(adapter, audit):
    service = AgentService(tasks=audit)
    service._adapter = lambda: adapter
    return service


def test_task_submission_is_idempotent_and_audited():
    adapter, audit = FakeAdapter(), MemoryAudit()
    service = _service(adapter, audit)
    first = service.run_task("safe research", "client-key-01")
    second = service.run_task("safe research", "client-key-01")
    assert first["task_id"] == "run_1"
    assert first["correlation_id"].startswith("corr_")
    assert second["duplicate"] is True
    assert adapter.submissions == 1
    assert len(audit.rows["client-key-01"]["prompt_sha256"]) == 64


def test_status_retry_is_limited_to_two_retries():
    adapter, audit = FakeAdapter([RuntimeError("offline"), RuntimeError("offline"), {"task_id": "run_1", "status": "completed", "output": "ok"}]), MemoryAudit()
    service = _service(adapter, audit)
    service.run_task("safe research", "client-key-02")
    result = service.get_task_status("run_1")
    assert result["status"] == "completed"
    assert result["retry_count"] == 2


def test_expired_task_is_cancelled_before_status_poll():
    adapter, audit = FakeAdapter(), MemoryAudit()
    service = _service(adapter, audit)
    service.run_task("safe research", "client-key-03")
    audit.rows["client-key-03"]["deadline_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    result = service.get_task_status("run_1")
    assert result["status"] == "timed_out"
    assert adapter.cancelled == ["run_1"]

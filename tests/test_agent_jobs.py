from studio.services.agent_job_service import AgentJobService


class Store:
    def __init__(self): self.rows = {}
    def get(self, key): return self.rows.get(key)
    def update(self, key, **values):
        row = self.rows.setdefault(key, {"id": key, "payload": None})
        row.update(values); return row
    def cancel(self, key): return self.update(key, phase="cancelled")
    def is_cancelled(self, key): return bool(self.rows.get(key, {}).get("phase") == "cancelled")


class Tasks:
    def __init__(self): self.cancelled = []
    def run_task(self, prompt, key): return {"task_id": "run_job", "correlation_id": "corr_job"}
    def get_task_status(self, task_id): return {"task_id": task_id, "status": "completed", "correlation_id": "corr_job"}
    def cancel_task(self, task_id): self.cancelled.append(task_id); return {"task_id": task_id, "status": "stopping"}


def test_agent_job_owns_task_correlation_and_completion():
    tasks, store = Tasks(), Store()
    service = AgentJobService(tasks, store)
    result = service.start("safe", "key-job-01", "agent-job-01")
    service._poll(result["job_id"], result["task_id"])
    assert store.get("agent-job-01")["phase"] == "complete"
    assert store.get("agent-job-01")["result"]["correlation_id"] == "corr_job"


def test_agent_job_cancel_propagates_to_hermes_owner():
    tasks, store = Tasks(), Store()
    service = AgentJobService(tasks, store)
    store.update("agent-job-02", phase="generating", payload={"kind": "agent_task", "task_id": "run_cancel"})
    assert service.cancel("agent-job-02")["phase"] == "cancelled"
    assert tasks.cancelled == ["run_cancel"]


def test_second_agent_job_is_rejected_while_one_is_active():
    tasks, store = Tasks(), Store()
    service = AgentJobService(tasks, store)
    service._active.add("agent-job-active")
    try:
        service.start("safe", "key-job-03", "agent-job-03")
    except RuntimeError as exc:
        assert "already active" in str(exc)
    else:
        raise AssertionError("a second concurrent Hermes job must be rejected")


def test_poller_does_not_overwrite_caller_owned_timeout():
    tasks, store = Tasks(), Store()
    service = AgentJobService(tasks, store)
    store.update("agent-job-timeout", phase="timed_out", payload={"kind": "agent_task", "task_id": "run_timeout"})
    service._poll("agent-job-timeout", "run_timeout")
    assert store.get("agent-job-timeout")["phase"] == "timed_out"
    assert tasks.cancelled == []

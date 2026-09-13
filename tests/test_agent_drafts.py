from fastapi import HTTPException
import pytest

from studio import config
from studio.db import connect, init_db
from studio.repositories.agent_draft_repository import AgentDraftRepository
from studio.services.agent_draft_service import AgentDraftService


class CompletedTasks:
    def get_task_status(self, task_id):
        return {"task_id": task_id, "status": "completed", "output": "검토가 필요한 초안입니다."}


def test_agent_draft_migration_is_registered_and_idempotent():
    init_db()
    init_db()
    with connect() as conn:
        assert conn.execute(
            "SELECT 1 FROM app_schema_migrations WHERE version='007_agent_drafts'"
        ).fetchone()
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='agent_drafts'"
        ).fetchone()


def test_draft_write_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(config, "HERMES_ALLOW_WRITE", False)
    with pytest.raises(HTTPException) as exc:
        AgentDraftService(tasks=CompletedTasks()).capture_completed_task("run_disabled")
    assert exc.value.status_code == 423


def test_completed_task_becomes_idempotent_review_only_draft(monkeypatch):
    monkeypatch.setattr(config, "HERMES_ALLOW_WRITE", True)
    service = AgentDraftService(AgentDraftRepository(), CompletedTasks())
    first = service.capture_completed_task("run_complete")
    second = service.capture_completed_task("run_complete")
    assert first["id"] == second["id"]
    assert first["agent_source"] == "hermes"
    assert first["review_required"] is True
    assert first["quality_gate_status"] == "not_checked"
    assert first["human_approval_status"] == "pending"

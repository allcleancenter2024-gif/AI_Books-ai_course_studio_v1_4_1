"""Capture completed Hermes output as a review-only Studio draft."""
from __future__ import annotations

from fastapi import HTTPException

from .. import config
from ..repositories.agent_draft_repository import AgentDraftRepository
from .agent_service import agent_service


class AgentDraftService:
    def __init__(self, repository: AgentDraftRepository | None = None, tasks=agent_service):
        self._repository = repository or AgentDraftRepository()
        self._tasks = tasks

    def capture_completed_task(self, task_id: str) -> dict:
        if not config.HERMES_ALLOW_WRITE:
            raise HTTPException(423, "Hermes draft writes are disabled")
        task = self._tasks.get_task_status(task_id)
        if task.get("status") != "completed":
            raise HTTPException(409, "완료된 Hermes 작업만 Draft로 저장할 수 있습니다.")
        output = task.get("output")
        if not isinstance(output, str) or not output.strip():
            raise HTTPException(422, "Hermes 작업 결과가 비어 있습니다.")
        return self._repository.create_from_task(task_id, output.strip(), config.HERMES_VERSION)

    def get(self, draft_id: str) -> dict:
        draft = self._repository.get(draft_id)
        if not draft:
            raise HTTPException(404, "Agent Draft를 찾을 수 없습니다.")
        return draft

    def list_recent(self) -> list[dict]:
        return self._repository.list_recent()


agent_draft_service = AgentDraftService()

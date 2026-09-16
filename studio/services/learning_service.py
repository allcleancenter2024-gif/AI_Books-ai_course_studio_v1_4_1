"""Application service for the read-only Learning Center API."""
from __future__ import annotations

from ..repositories.learning_repository import LearningRepository


class LearningService:
    def __init__(self, repository: LearningRepository | None = None):
        self._repository = repository or LearningRepository()

    def list_tools(self) -> list[dict]:
        return self._repository.list_tools()

    def get_tool(self, tool_id: str) -> dict | None:
        tool = self._repository.get_tool(tool_id)
        if not tool:
            return None
        return tool

    def resource(self, tool_id: str, table: str, order_by: str) -> list[dict] | None:
        if not self._repository.get_tool(tool_id):
            return None
        return self._repository.list_by_tool(table, tool_id, order_by)


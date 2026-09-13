"""Stable contract between Studio and an optional agent orchestrator."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentHealth:
    status: str
    adapter: str
    version: str | None = None
    detail: str = ""

    def public(self) -> dict[str, str | None]:
        return asdict(self)


class AgentAdapter(Protocol):
    def health(self) -> AgentHealth: ...
    def capabilities(self) -> dict[str, object]: ...
    def run_task(self, prompt: str) -> dict[str, object]: ...
    def get_task_status(self, task_id: str) -> dict[str, object]: ...
    def cancel_task(self, task_id: str) -> dict[str, object]: ...

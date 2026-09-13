"""No-op adapter used by the safe default configuration."""
from .base import AgentHealth


class DisabledAgentAdapter:
    def health(self) -> AgentHealth:
        return AgentHealth(status="disabled", adapter="disabled")

    def capabilities(self) -> dict[str, object]:
        return {"status": "disabled", "skills": [], "tools": [], "write_allowed": False}

    def run_task(self, prompt: str) -> dict[str, object]:
        raise RuntimeError("Hermes agent is disabled")

    def get_task_status(self, task_id: str) -> dict[str, object]:
        raise RuntimeError("Hermes agent is disabled")

    def cancel_task(self, task_id: str) -> dict[str, object]:
        raise RuntimeError("Hermes agent is disabled")

"""Versioned, Studio-owned read-only prompt contracts for Hermes tasks."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentSkill:
    id: str
    version: str
    purpose: str
    output: str
    allowed_tools: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    quality_requirements: tuple[str, ...]

    def public(self) -> dict[str, object]:
        value = asdict(self)
        value["allowed_tools"] = list(self.allowed_tools)
        value["forbidden_actions"] = list(self.forbidden_actions)
        value["quality_requirements"] = list(self.quality_requirements)
        value["human_review"] = True
        value["owner"] = "studio"
        return value


_NO_TOOLS: tuple[str, ...] = ()
_FORBIDDEN = (
    "file modification", "configuration change", "network action", "publication",
    "human approval", "quality-gate bypass", "external side effect",
)
_QUALITY = ("cite uncertainty", "separate facts from proposals", "return a review-only draft")

SKILLS: dict[str, AgentSkill] = {
    "research": AgentSkill("research", "1.0.0", "Create a bounded research proposal from supplied Studio context.", "research draft", _NO_TOOLS, _FORBIDDEN, _QUALITY),
    "fact_check": AgentSkill("fact_check", "1.0.0", "Identify claims that require source verification.", "fact-check draft", _NO_TOOLS, _FORBIDDEN, _QUALITY),
    "curriculum": AgentSkill("curriculum", "1.0.0", "Propose a course-outline improvement for human review.", "curriculum draft", _NO_TOOLS, _FORBIDDEN, _QUALITY),
    "visual_prompt": AgentSkill("visual_prompt", "1.0.0", "Propose an image-generation prompt; never generate an asset.", "visual-prompt draft", _NO_TOOLS, _FORBIDDEN, _QUALITY),
}


def list_skills() -> list[dict[str, object]]:
    return [skill.public() for skill in SKILLS.values()]


def build_skill_prompt(skill_id: str, request: str) -> str:
    skill = SKILLS.get(skill_id)
    if not skill:
        raise KeyError(skill_id)
    return (
        f"Studio skill: {skill.id} v{skill.version}\n"
        f"Purpose: {skill.purpose}\n"
        "This is a read-only, single-agent task. Do not use tools or perform external actions. "
        "Do not modify files, Studio data, configuration, approvals, quality gates, or publication state. "
        "Return only a draft for human review.\n"
        f"Requested work:\n{request.strip()}"
    )

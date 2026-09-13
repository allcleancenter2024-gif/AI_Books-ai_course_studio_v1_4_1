import pytest

from studio.services.agent_skills import build_skill_prompt, list_skills


def test_skill_registry_is_versioned_read_only_and_human_reviewed():
    rows = {row["id"]: row for row in list_skills()}
    assert set(rows) == {"research", "fact_check", "curriculum", "visual_prompt"}
    for row in rows.values():
        assert row["version"] == "1.0.0"
        assert row["allowed_tools"] == []
        assert row["human_review"] is True
        assert "publication" in row["forbidden_actions"]


def test_skill_prompt_is_single_agent_read_only_contract():
    prompt = build_skill_prompt("research", "Review this source summary")
    assert "single-agent" in prompt
    assert "Do not use tools" in prompt
    assert "human review" in prompt


def test_unknown_skill_is_rejected():
    with pytest.raises(KeyError):
        build_skill_prompt("unknown", "anything")

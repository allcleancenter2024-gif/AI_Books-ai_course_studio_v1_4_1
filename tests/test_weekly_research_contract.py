from studio import config
from studio.services import weekly_research


def test_weekly_prompt_uses_small_read_only_contract(monkeypatch):
    monkeypatch.setattr(config, "HERMES_WEEKLY_SOURCE_CHAR_LIMIT", 900)
    monkeypatch.setattr(config, "HERMES_WEEKLY_OUTPUT_CHAR_LIMIT", 600)
    prompt = weekly_research._summary_prompt([
        {"source": "openai", "url": "https://official.example/release", "text": "A" * 5000}
    ])

    assert "최대 600자" in prompt
    assert "A" * 900 in prompt
    assert "A" * 901 not in prompt


def test_canary_telemetry_never_fabricates_unavailable_provider_metrics(monkeypatch):
    clock = iter([10.25])
    monkeypatch.setattr(weekly_research.time, "monotonic", lambda: next(clock))

    telemetry = weekly_research._telemetry(10.0)

    assert telemetry["total_elapsed_ms"] == 250
    assert telemetry["first_token_ms"] is None
    assert telemetry["prompt_tokens"] is None
    assert telemetry["completion_tokens"] is None
    assert telemetry["timeout_stage"] is None


def test_optional_fallback_preserves_evidence_without_publisher_changes():
    timeout = weekly_research._optional_fallback("timed_out", 7, False)
    failed = weekly_research._optional_fallback("error", 8, False)
    completed = weekly_research._optional_fallback("complete", 9, True)

    assert timeout == {
        "hermes_status": "timed_out", "optional_fallback": True,
        "evidence_retained": True, "draft_created": False, "publisher_changed": False,
    }
    assert failed["hermes_status"] == "failed" and failed["optional_fallback"] is True
    assert completed["hermes_status"] == "completed" and completed["optional_fallback"] is False

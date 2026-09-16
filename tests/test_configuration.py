"""Configuration regression tests that never use the operational runtime."""
from studio.config import (
    APP_ENV,
    APP_BASE_URL,
    APP_HOST,
    APP_PORT,
    BOOK_GENERATION_MAX_CONCURRENT,
    BOOK_GENERATION_QUEUE_LIMIT,
    DATA_STORE_ROLE,
    MAX_UPLOAD_BYTES,
    LMSTUDIO_MAX_PARALLEL_CALLS,
    LMSTUDIO_TIMEOUT_SECONDS,
    HERMES_ALLOW_WRITE,
    HERMES_CRON_ENABLED,
    HERMES_ENABLED,
    HERMES_HEALTH_TIMEOUT_SECONDS,
    OLLAMA_TIMEOUT_SECONDS,
    PUBLIC_ACCESS,
    RUNTIME_DIR,
    SCHEDULER_OWNER,
    configuration_summary,
    configuration_issues,
    FEATURE_AI_TOOL_LEARNING_CENTER,
)


def test_test_runtime_is_explicitly_isolated_from_project_data():
    assert APP_ENV == "test"
    assert RUNTIME_DIR.name.startswith("ai-course-studio-tests-")
    assert RUNTIME_DIR != RUNTIME_DIR.parent.parent
    assert "data" not in RUNTIME_DIR.parts[-1:]


def test_local_safe_defaults_and_authoritative_store_are_explicit():
    summary = configuration_summary()
    assert APP_HOST == "127.0.0.1"
    assert APP_PORT == 8765
    assert APP_BASE_URL == "http://127.0.0.1:8765"
    assert PUBLIC_ACCESS is False
    assert FEATURE_AI_TOOL_LEARNING_CENTER is True
    assert DATA_STORE_ROLE == "sqlite-authoritative"
    assert MAX_UPLOAD_BYTES == 500 * 1024 * 1024
    assert LMSTUDIO_MAX_PARALLEL_CALLS == 1
    assert BOOK_GENERATION_MAX_CONCURRENT == 1
    assert BOOK_GENERATION_QUEUE_LIMIT == 2
    assert LMSTUDIO_TIMEOUT_SECONDS == 180
    assert OLLAMA_TIMEOUT_SECONDS == 900
    assert HERMES_ENABLED is False
    assert HERMES_ALLOW_WRITE is False
    assert SCHEDULER_OWNER == "STUDIO"
    assert HERMES_CRON_ENABLED is False
    assert HERMES_HEALTH_TIMEOUT_SECONDS == 3
    assert summary["data_store_role"] == "sqlite-authoritative"
    assert summary["lmstudio_max_parallel_calls"] == 1
    assert summary["book_generation_max_concurrent"] == 1
    assert summary["hermes_enabled"] is False
    assert summary["hermes_allow_write"] is False
    assert summary["scheduler_owner"] == "STUDIO"
    assert summary["hermes_cron_enabled"] is False
    assert configuration_issues() == []

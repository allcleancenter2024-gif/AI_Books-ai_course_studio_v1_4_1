"""Phase 1 additive schema contract tests."""

from studio.db import connect, init_db


EXPECTED_TABLES = {
    "learning_tools", "tool_versions", "tool_capabilities", "timeline_events",
    "prompt_frameworks", "prompt_skills", "prompt_examples", "modern_prompt_examples",
    "update_events", "source_evidence", "update_rules", "course_tool_references",
    "course_update_matches", "course_update_suggestions", "course_update_decisions",
    "course_versions",
}


def test_learning_module_migration_is_applied_without_replacing_core_tables():
    init_db()
    with connect() as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert EXPECTED_TABLES <= tables
        assert {"courses", "lessons", "books", "lesson_units"} <= tables
        assert conn.execute(
            "SELECT 1 FROM app_schema_migrations WHERE version='011_learning_tools'"
        ).fetchone()


def test_learning_module_tables_are_seed_ready():
    init_db()
    with connect() as conn:
        for table in EXPECTED_TABLES:
            assert conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0] >= 0

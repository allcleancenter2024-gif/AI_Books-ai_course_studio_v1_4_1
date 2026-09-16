from studio.data.learning_seed import TOOLS, seed_learning_center
from studio.db import connect, init_db
from scripts.validate_learning_seed import validate


def test_learning_seed_has_required_counts_and_is_idempotent():
    init_db()
    with connect() as conn:
        assert seed_learning_center(conn)["prompts"] == 81
        assert seed_learning_center(conn)["modern_prompts"] == 18
        assert validate(conn) == []
        expected = tuple(row[0] for row in TOOLS)
        placeholders = ",".join("?" for _ in expected)
        assert conn.execute(f"SELECT COUNT(*) FROM learning_tools WHERE slug IN ({placeholders})", expected).fetchone()[0] == 9
        assert conn.execute("SELECT COUNT(*) FROM prompt_examples").fetchone()[0] == 81
        assert conn.execute("SELECT COUNT(*) FROM modern_prompt_examples").fetchone()[0] == 18
        assert conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0] == 27
        assert conn.execute("SELECT COUNT(*) FROM update_events").fetchone()[0] == 9

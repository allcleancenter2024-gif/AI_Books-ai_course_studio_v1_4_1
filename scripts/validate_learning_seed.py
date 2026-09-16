"""Read-only validation of Learning Center seed counts and contracts."""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio.db import connect
from studio.data.learning_seed import TOOLS


def validate(conn) -> list[str]:
    issues = []
    expected_slugs = {row[0] for row in TOOLS}
    tools = {row[0] for row in conn.execute("SELECT slug FROM learning_tools WHERE active=1")}
    if expected_slugs != tools & expected_slugs or len(expected_slugs) != 9:
        issues.append(f"expected all 9 seed tools, found {len(tools & expected_slugs)}")
    placeholders = ",".join("?" for _ in expected_slugs)
    if conn.execute(f"SELECT COUNT(*) FROM prompt_examples WHERE tool_id IN ({placeholders})", tuple(expected_slugs)).fetchone()[0] != 81:
        issues.append("expected 81 prompt examples")
    if conn.execute(f"SELECT COUNT(*) FROM modern_prompt_examples WHERE tool_id IN ({placeholders})", tuple(expected_slugs)).fetchone()[0] != 18:
        issues.append("expected 18 modern prompt examples")
    if conn.execute(f"SELECT COUNT(*) FROM update_events WHERE tool_id IN ({placeholders})", tuple(expected_slugs)).fetchone()[0] != 9:
        issues.append("expected 9 update registry events")
    for row in conn.execute("SELECT prompt_id,tool_id,level,example_no,prompt_ko,prompt_en FROM prompt_examples"):
        if not row[0] or not row[1] or row[2] not in {"BEGINNER", "INTERMEDIATE", "ADVANCED"} or row[3] not in {1, 2, 3} or not row[4].strip() or not row[5].strip():
            issues.append(f"invalid prompt row: {row[0]}")
    duplicate = conn.execute("SELECT prompt_id,COUNT(*) FROM prompt_examples GROUP BY prompt_id HAVING COUNT(*)>1").fetchall()
    if duplicate:
        issues.append("duplicate prompt IDs")
    invalid_status = conn.execute("SELECT COUNT(*) FROM update_events WHERE status NOT IN ('DISCOVERED','EVIDENCE_COLLECTED','VERIFIED','REJECTED','SUPERSEDED')").fetchone()[0]
    if invalid_status:
        issues.append("invalid update event status")
    return issues


if __name__ == "__main__":
    try:
        problems = validate(connect())
    except sqlite3.OperationalError as error:
        problems = [f"schema or seed is unavailable: {error}"]
    print("SEED_VALID" if not problems else "SEED_INVALID")
    for problem in problems:
        print(problem)
    raise SystemExit(1 if problems else 0)

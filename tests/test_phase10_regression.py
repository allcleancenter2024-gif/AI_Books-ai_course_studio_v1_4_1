"""Phase 10: feature isolation and rollback-safety regression checks."""
import json

from fastapi.testclient import TestClient

from studio.api import learning_routes
from studio.application import create_app
from studio.auth import require_authenticated
from studio.db import connect, init_db


def test_learning_center_disabled_keeps_existing_api_surface_unavailable(monkeypatch):
    init_db()
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", False)
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "viewer", "role": "viewer"}
    response = TestClient(app).get("/api/learning-tools")
    assert response.status_code == 404


def test_created_draft_version_contains_original_snapshot_and_is_listable(monkeypatch):
    init_db()
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", True)
    course_id = 991_001
    with connect() as conn:
        conn.execute("DELETE FROM course_versions WHERE course_id=?", (course_id,))
        conn.execute(
            "INSERT OR REPLACE INTO courses(id,course_type,audience,created_date,data_json) VALUES(?,12,?,datetime('now'),?)",
            (course_id, "회귀 검증", json.dumps({"title": "원본 보존", "lessons": []}, ensure_ascii=False)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO course_versions(id,course_id,source_version,version_label,content_json,created_at,created_by,reason,status) "
            "VALUES(?,?,?,?,?,datetime('now'),?,?,?)",
            (
                "phase10-version",
                course_id,
                f"course-{course_id}-original",
                "phase10.reviewed",
                json.dumps({"title": "초안", "_learning_update": {"rollback": "original remains authoritative"}}, ensure_ascii=False),
                "test",
                "rollback drill",
                "DRAFT",
            ),
        )
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "viewer", "role": "viewer"}
    response = TestClient(app).get(f"/api/courses/{course_id}/versions")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "DRAFT"
    with connect() as conn:
        original = json.loads(conn.execute("SELECT data_json FROM courses WHERE id=?", (course_id,)).fetchone()[0])
    assert original["title"] == "원본 보존"

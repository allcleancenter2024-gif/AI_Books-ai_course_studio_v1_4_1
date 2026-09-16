"""Phase 2-B reviewed command contracts."""
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from studio.api import learning_routes
from studio.application import create_app
from studio.auth import require_admin, require_authenticated
from studio.db import connect, init_db


def _seed_suggestion():
    init_db()
    course_id = 9101 + int(uuid4().hex[:6], 16) % 800000
    suggestion_id = "suggestion-" + uuid4().hex
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO learning_tools(id,slug,name_ko,name_en,type,created_at,updated_at) "
            "VALUES('tool-test','tool-test','테스트 도구','Test Tool','SERVICE',datetime('now'),datetime('now'))"
        )
        conn.execute(
            "INSERT INTO courses(id,course_type,audience,created_date,data_json) VALUES(?,12,'테스트',datetime('now'),?)",
            (course_id, json.dumps({"title": "원본 강의", "lessons": []}, ensure_ascii=False)),
        )
        conn.execute(
            "INSERT INTO course_update_suggestions(" 
            "id,course_id,tool_id,matched_text,suggested_text,reason,severity,created_at) "
            "VALUES(?,?, 'tool-test','옛 내용','새 내용','검증','MEDIUM',datetime('now'))",
            (suggestion_id, course_id),
        )
    return course_id, suggestion_id


def _client(monkeypatch):
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", True)
    course_id, suggestion_id = _seed_suggestion()
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"username": "admin", "role": "admin"}
    return TestClient(app), course_id, suggestion_id


def test_approve_then_apply_creates_version_without_overwriting_course(monkeypatch):
    client, course_id, suggestion_id = _client(monkeypatch)
    approved = client.post(
        f"/api/update-suggestions/{suggestion_id}/approve",
        json={"decision": "PARTIAL_APPLY", "reviewer": "admin", "reason": "확인"},
    )
    assert approved.status_code == 200
    applied = client.post(
        f"/api/update-suggestions/{suggestion_id}/apply",
        json={"reviewer": "admin", "reason": "새 버전 생성"},
    )
    assert applied.status_code == 200
    assert applied.json()["original_preserved"] is True
    with connect() as conn:
        original = conn.execute("SELECT data_json FROM courses WHERE id=?", (course_id,)).fetchone()[0]
        version_count = conn.execute("SELECT COUNT(*) FROM course_versions WHERE course_id=?", (course_id,)).fetchone()[0]
        audit_count = conn.execute("SELECT COUNT(*) FROM learning_audit_log WHERE course_id=?", (course_id,)).fetchone()[0]
    assert json.loads(original)["title"] == "원본 강의"
    assert version_count == 1
    assert audit_count == 2
    repeated = client.post(
        f"/api/update-suggestions/{suggestion_id}/apply",
        json={"reviewer": "admin", "reason": "중복 적용 방지 확인"},
    )
    assert repeated.status_code == 409


def test_apply_requires_a_recorded_human_approval(monkeypatch):
    client, _, suggestion_id = _client(monkeypatch)
    response = client.post(
        f"/api/update-suggestions/{suggestion_id}/apply",
        json={"reviewer": "admin"},
    )
    assert response.status_code == 409

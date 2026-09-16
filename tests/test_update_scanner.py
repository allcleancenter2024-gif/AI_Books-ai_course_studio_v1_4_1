import json

from fastapi.testclient import TestClient

from studio.api import learning_routes
from studio.application import create_app
from studio.auth import require_admin, require_authenticated
from studio.db import connect, init_db


def test_scanner_creates_suggestion_without_modifying_course(monkeypatch):
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", True)
    init_db()
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO learning_tools(id,slug,name_ko,name_en,type,created_at,updated_at) VALUES('scan-tool','scan-tool','스캔 도구','Scan Tool','SERVICE',datetime('now'),datetime('now'))")
        conn.execute("INSERT INTO courses(id,course_type,audience,created_date,data_json) VALUES(9301,12,'테스트',datetime('now'),?)", (json.dumps({"title": "원본"}),))
        conn.execute("INSERT INTO lessons(id,course_id,week,topic,student_text,teacher_text) VALUES(9302,9301,1,'스캔 도구 소개','스캔 도구를 사용합니다.','강사용 설명')")
        conn.execute("INSERT INTO course_tool_references(id,course_id,tool_id,match_method,status,created_at) VALUES('scan-ref',9301,'scan-tool','human_approved','APPROVED',datetime('now'))")
        conn.execute("INSERT INTO update_events(id,tool_id,event_type,title,summary,checked_at,status) VALUES('scan-event','scan-tool','official','검증 이벤트','검토가 필요한 새 설명',datetime('now'),'VERIFIED')")
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"username": "admin", "role": "admin"}
    response = TestClient(app).post("/api/courses/9301/scan-updates", json={})
    assert response.status_code == 200
    assert response.json()["original_course_changed"] is False
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM course_update_suggestions WHERE course_id=9301").fetchone()[0] == 1
        assert json.loads(conn.execute("SELECT data_json FROM courses WHERE id=9301").fetchone()[0])["title"] == "원본"

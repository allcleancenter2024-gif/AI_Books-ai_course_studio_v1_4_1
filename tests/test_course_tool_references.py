import json

from fastapi.testclient import TestClient

from studio.api import learning_routes
from studio.application import create_app
from studio.auth import require_admin, require_authenticated
from studio.db import connect, init_db


def test_course_tool_reference_requires_explicit_admin_approval(monkeypatch):
    monkeypatch.setattr(learning_routes, "FEATURE_AI_TOOL_LEARNING_CENTER", True)
    init_db()
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO learning_tools(id,slug,name_ko,name_en,type,created_at,updated_at) VALUES('ref-tool','ref-tool','참조 도구','Reference Tool','SERVICE',datetime('now'),datetime('now'))")
        conn.execute("INSERT INTO courses(id,course_type,audience,created_date,data_json) VALUES(9201,12,'테스트',datetime('now'),?)", (json.dumps({"title": "연결 테스트"}),))
    app = create_app()
    app.dependency_overrides[require_authenticated] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[require_admin] = lambda: {"username": "admin", "role": "admin"}
    client = TestClient(app)
    response = client.post("/api/courses/9201/tool-references", json={"tool_id": "ref-tool"})
    assert response.status_code == 201
    assert client.get("/api/courses/9201/tool-references").json()[0]["status"] == "APPROVED"


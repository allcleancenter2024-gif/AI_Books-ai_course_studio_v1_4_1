import io
import json
import os
import sys
import uuid
import zipfile
from pathlib import Path

os.environ.setdefault("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from studio.application import create_app
from studio.config import MAX_UPLOAD_BYTES, PDF_OUTPUT_DIR, VERSION, LAST_UPDATED
from studio.services.job_status import jobs
from studio.services.parsers import parse_file
from studio.services.source_service import _public_url, _insert, summarize_source, start_source_summary, summary_file, delete_source
from studio.services.vector_index import retrieve
from studio.services import generation_service
from studio.services import manual_service
from studio.services.summarization import summarize_text
from generators.course_content import book_to_markdown
from providers.engine import ProviderManager, ProviderError


client = TestClient(create_app())

TEST_ADMIN_PASSWORD = "test-only-password-2026"
from studio.auth import bootstrap_admin
bootstrap_admin("test_admin", TEST_ADMIN_PASSWORD)

def login_client():
    response = client.post("/api/auth/login", json={"username": "test_admin", "password": TEST_ADMIN_PASSWORD, "remember": False})
    assert response.status_code == 200 and response.json()["user"]["username"] == "test_admin"

login_client()


def test_health_ui_and_existing_features():
    health = client.get("/api/health")
    assert health.status_code == 200 and health.json()["version"] == VERSION and health.json()["last_updated"] == LAST_UPDATED
    runtime = client.get("/api/system-info")
    assert runtime.status_code == 200 and runtime.json()["rdbms"] == "SQLite 3" and runtime.json()["database_file"] == "studio.db"
    page = client.get("/")
    assert page.status_code == 200 and "최대 500MB" in page.text and "progressText" in page.text
    assert "11. GitHub 백업" in page.text and "12. 변경된 내용 안내" in page.text and 'id="release-notes"' in page.text
    release_script = client.get("/static/js/release-notes.js")
    assert release_script.status_code == 200
    assert all(label in release_script.text for label in ("변경 전", "변경 후", "기준일", "변경일자", "변화없음"))
    assert "13. 설치 및 운영 설명서" in page.text and 'id="operations-manual"' in page.text
    manual_script = client.get("/static/js/operations-manual.js")
    assert manual_script.status_code == 200
    assert manual_script.text.count("category:") >= 25
    assert all(label in manual_script.text for label in ("Windows 설치", "Ubuntu Linux", "1. AI 연결", "12. 설치 및 운영 설명서", "SQLite 안전 백업", "Tailscale Host-only", "장애 대응"))
    assert all(label in page.text for label in ("내용 업데이터", "전체 PDF 다운로드", "manualUpdateMessage"))
    assert client.get("/api/topics").status_code == 200
    assert client.get("/api/providers").status_code == 200
    course = client.post("/api/course", json={"weeks": 12, "audience": "전체 초보자"})
    assert course.status_code == 200 and len(course.json()["schedule"]) == 12
    lesson = client.post("/api/lesson/student", json={"topic": "AI 개념과 첫걸음", "audience": "60대"})
    assert lesson.status_code == 200


def test_manual_update_analysis_applies_only_changed_operational_facts(monkeypatch):
    baseline = manual_service.collect_operational_facts()
    # Normalize a persisted snapshot left by an interrupted local run.
    manual_service.apply_manual_updates()
    status = client.get("/api/manual/updates")
    assert status.status_code == 200 and status.json()["has_updates"] is False
    changed = dict(baseline, max_upload_mb="750MB", providers="LM Studio, Ollama, test-runtime")
    monkeypatch.setattr(manual_service, "collect_operational_facts", lambda: changed)
    pending = client.get("/api/manual/updates").json()
    assert pending["has_updates"] is True and pending["change_count"] == 2
    assert {item["key"] for item in pending["changes"]} == {"max_upload_mb", "providers"}
    applied = client.post("/api/manual/updates/apply", json={})
    assert applied.status_code == 200 and applied.json()["affected_chapter_count"] == 3
    assert client.get("/api/manual/updates").json()["has_updates"] is False
    monkeypatch.setattr(manual_service, "collect_operational_facts", lambda: baseline)
    manual_service.apply_manual_updates()


def test_full_manual_pdf_endpoint_returns_a_valid_pdf():
    chapters = [{"index": index, "category": "검증 분야", "title": f"{index}. 검증 장", "summary": "PDF 요약", "text": "한국어 설치 및 운영 설명서 본문입니다.\n두 번째 확인 줄입니다."} for index in range(1, 26)]
    response = client.post("/api/manual/pdf", json={"title": "AI 강의 활용 Studio 설치 및 운영 설명서", "chapters": chapters})
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF" and len(response.content) > 10_000
    for path in PDF_OUTPUT_DIR.glob("AI_Course_Studio_Installation_Operations_Manual_*.pdf"):
        path.unlink(missing_ok=True)


def test_authentication_blocks_api_and_manages_session():
    anonymous = TestClient(create_app())
    assert anonymous.get("/api/topics").status_code == 401
    assert anonymous.post("/api/auth/login", json={"username": "test_admin", "password": "wrong-password"}).status_code == 401
    login = anonymous.post("/api/auth/login", json={"username": "test_admin", "password": TEST_ADMIN_PASSWORD, "remember": True})
    assert login.status_code == 200 and "httponly" in login.headers["set-cookie"].lower()
    assert anonymous.get("/api/auth/session").json()["user"]["role"] == "admin"
    assert anonymous.post("/api/auth/logout", json={}).status_code == 200
    assert anonymous.get("/api/topics").status_code == 401


def test_repeated_failed_logins_are_temporarily_limited():
    anonymous = TestClient(create_app())
    for _ in range(5):
        assert anonymous.post("/api/auth/login", json={"username": "limited_user", "password": "wrong"}).status_code == 401
    assert anonymous.post("/api/auth/login", json={"username": "limited_user", "password": "wrong"}).status_code == 429


def test_product_checked_date_is_catalog_date_not_server_start_date():
    products = client.get("/api/products").json()
    assert products
    assert all(row["checked_date"] for row in products)
    assert {"Suno AI", "Vrew AI", "CapCut AI", "Ollama", "LM Studio", "Cursor", "VS Code", "Codex", "n8n", "Notion AI", "Google Drive", "Google Sheets"} <= {row["current_name"] for row in products}
    assert {row["has_changes"] for row in products} == {True, False}
    assert all(row["change_note"] and row["source_url"] for row in products)
    changes = client.get("/api/products/changes").json()
    assert changes and all(row["baseline_info"] and row["changed_info"] and row["important_notes"] for row in changes)


def test_ssrf_url_validation_rejects_non_global_and_credentials():
    for url in ("http://127.0.0.1", "http://0.0.0.0", "http://[::1]", "http://169.254.169.254", "http://100.64.0.1", "http://user:pass@example.com"):
        response = client.post("/api/sources/web", json={"url": url})
        assert response.status_code == 400

    assert _public_url("https://8.8.8.8") == "https://8.8.8.8"


def test_text_upload_and_job_status():
    job_id = str(uuid.uuid4())
    body = ("대용량 안전 처리 확인\n" * 1000).encode("utf-8")
    response = client.post("/api/sources/upload", data={"job_id": job_id, "declared_size": len(body)}, files={"file": ("sample.txt", body, "text/plain")})
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    import time
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        status = client.get(f"/api/jobs/{job_id}").json()
        if status["phase"] in {"complete", "error", "cancelled"}:
            break
        time.sleep(.01)
    assert status["phase"] == "complete" and status["progress"] == 100
    source_id = status["result"]["source_id"]
    listed = client.get("/api/sources").json()
    row = next(row for row in listed if row["id"] == source_id)
    assert row["has_text"] and row["original_retained"] is False and row["vector_status"].startswith("indexed:")
    matches = retrieve([source_id], "대용량 안전 처리")
    assert matches and "대용량 안전 처리" in matches[0]["text"]
    assert client.delete(f"/api/sources/{source_id}").status_code == 200


def test_declared_oversize_is_rejected_without_writing():
    job_id = str(uuid.uuid4())
    response = client.post("/api/sources/upload", data={"job_id": job_id, "declared_size": MAX_UPLOAD_BYTES + 1}, files={"file": ("too-big.txt", b"small", "text/plain")})
    assert response.status_code == 413


def test_streaming_text_limit_and_pptx_slide_parser(tmp_path):
    large = tmp_path / "large.txt"
    large.write_bytes(b"x" * 2_000_000)
    text, meta = parse_file(large)
    assert len(text) == 120_000 and meta["size"] == 2_000_000

    pptx = tmp_path / "sample.pptx"
    content = b'<p:sld xmlns:p="p" xmlns:a="a"><p:cSld><a:t>slide text</a:t></p:cSld></p:sld>'
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", content)
    text, meta = parse_file(pptx)
    assert "slide text" in text and meta["slides"] == 1


def test_job_not_found_is_clear():
    response = client.get("/api/jobs/not-found")
    assert response.status_code == 404 and "작업 상태" in response.json()["detail"]


def test_local_provider_response_variants():
    extract = ProviderManager._compatible_text
    assert extract({"choices": [{"message": {"content": "normal"}}]}) == "normal"
    assert extract({"choices": [{"message": {"content": [{"type": "text", "text": "array text"}]}}]}) == "array text"
    assert extract({"choices": [{"text": "legacy"}]}) == "legacy"
    assert extract({"choices": [{"message": {"content": "", "reasoning_content": "internal reasoning"}}]}) == ""


def test_only_local_providers_are_exposed_and_cloud_config_is_rejected():
    assert {row["name"] for row in client.get("/api/providers").json()} == {"lmstudio", "ollama"}
    response = client.post("/api/providers/config", json={"provider": "openai", "model": "cloud"})
    assert response.status_code == 422


def test_local_provider_auto_connect_selects_and_keeps_a_recommended_model(monkeypatch):
    manager = ProviderManager()
    manager.configs["lmstudio"].model = ""
    monkeypatch.setattr(manager, "_lmstudio_models", lambda cfg: (_ for _ in ()).throw(RuntimeError("legacy")))
    monkeypatch.setattr(manager, "list_models", lambda provider, strict=False: ["text-embedding-model", "qwen-local", "llama-local"])
    monkeypatch.setattr(manager, "test", lambda provider: {"ok": True, "provider": provider, "model": manager.configs[provider].model, "response": "연결 성공"})
    result = manager.auto_connect("lmstudio")
    assert result["automatic"] is True and result["model"] == "qwen-local" and result["model_count"] == 3


def test_lmstudio_candidates_exclude_embeddings_and_rank_safe_gguf():
    rows = [
        {"key": "text-embedding-model", "type": "embedding", "size_bytes": 100, "format": "gguf"},
        {"key": "large:20b", "type": "llm", "size_bytes": 14 * 1024**3, "format": "gguf"},
        {"key": "small:2b", "type": "llm", "size_bytes": 2 * 1024**3, "format": "gguf"},
        {"key": "balanced:4b", "type": "llm", "size_bytes": 3 * 1024**3, "format": "gguf"},
    ]
    assert ProviderManager._recommended_lmstudio_models(rows) == ["balanced:4b", "small:2b", "large:20b"]
    assert ProviderManager._recommended_lmstudio_models(rows, "small:2b")[0] == "small:2b"


def test_lmstudio_loaded_model_does_not_issue_another_load_request(monkeypatch):
    manager = ProviderManager()
    monkeypatch.setattr(manager, "_lmstudio_models", lambda cfg: [
        {"key": "qwen:4b", "type": "llm", "loaded_instances": [{"id": "qwen:4b"}]},
    ])
    monkeypatch.setattr("providers.engine.httpx.post", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("already loaded")))
    manager.ensure_lmstudio_model_loaded("qwen:4b")


def test_lmstudio_unloaded_model_is_preloaded_with_safe_context(monkeypatch):
    manager = ProviderManager()
    captured = {}
    monkeypatch.setattr(manager, "_lmstudio_models", lambda cfg: [
        {"key": "lfm:2b", "type": "llm", "max_context_length": 4096, "loaded_instances": []},
    ])

    class Response:
        is_success = True
        status_code = 200

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr("providers.engine.httpx.post", post)
    manager.ensure_lmstudio_model_loaded("lfm:2b", context_length=8192)
    assert captured["url"].endswith("/api/v1/models/load")
    assert captured["json"] == {"model": "lfm:2b", "context_length": 4096, "echo_load_config": False}


def test_lmstudio_transport_error_automatically_switches_model(monkeypatch):
    manager = ProviderManager()
    rows = [
        {"key": "qwen:4b", "type": "llm", "size_bytes": 3 * 1024**3, "format": "gguf"},
        {"key": "lfm:2b", "type": "llm", "size_bytes": 2 * 1024**3, "format": "gguf"},
    ]
    monkeypatch.setattr(manager, "_lmstudio_models", lambda cfg: rows)

    def chat(cfg, model, *args, **kwargs):
        if model == "qwen:4b":
            raise generation_service.ProviderError("length")
        return '{"ok":true}'

    monkeypatch.setattr(manager, "_lmstudio_chat", chat)
    assert manager.generate("lmstudio", "system", "prompt", model="qwen:4b") == '{"ok":true}'
    assert manager.get("lmstudio").model == "lfm:2b"
    assert manager.consume_failovers()[0]["to"] == "lfm:2b"


def test_ollama_default_is_unpinned_and_auto_selection_avoids_oversized_and_code_models():
    manager = ProviderManager()
    assert manager.configs["ollama"].model == ""
    rows = [
        {"model": "huge-general:36b", "size": 24 * 1024**3},
        {"model": "small-opencode:2b", "size": 3 * 1024**3},
        {"model": "general:8b", "size": 6 * 1024**3},
        {"model": "general:3b", "size": 3 * 1024**3},
    ]
    assert manager._recommended_ollama_model(rows) == "general:3b"
    assert manager._recommended_ollama_model(rows, "huge-general:36b") == "huge-general:36b"


def test_ollama_native_chat_disables_thinking_and_sets_structured_output(monkeypatch):
    captured = {}

    class Response:
        is_success = True

        def json(self):
            return {"message": {"content": '{"ok":true}', "thinking": ""}, "done_reason": "stop"}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return Response()

    monkeypatch.setattr("providers.engine.httpx.Client", Client)
    manager = ProviderManager()
    text = manager.generate("ollama", "system", "prompt", model="test:2b", max_tokens=2400, json_mode=True)
    body = captured["json"]
    assert text == '{"ok":true}'
    assert captured["url"].endswith("/api/chat")
    assert body["think"] is False and body["format"] == "json"
    assert body["keep_alive"] == "5m" and body["options"]["num_predict"] == 2400


def test_lmstudio_native_chat_disables_reasoning_and_reads_visible_message(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "output": [
                    {"type": "reasoning", "content": "hidden"},
                    {"type": "message", "content": '{"ok":true}'},
                ],
                "stats": {"total_output_tokens": 12, "reasoning_output_tokens": 0},
            }

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return Response()

    monkeypatch.setattr("providers.engine.httpx.Client", Client)
    manager = ProviderManager()
    text = manager.generate("lmstudio", "system", "prompt", model="qwen-test", max_tokens=3200, json_mode=True)
    body = captured["json"]
    assert text == '{"ok":true}'
    assert captured["url"].endswith("/api/v1/chat")
    assert body["reasoning"] == "off" and body["max_output_tokens"] == 3200 and body["store"] is False


def test_lmstudio_reasoning_only_response_is_classified_for_fast_failover(monkeypatch):
    class Response:
        status_code = 200
        is_success = True
        def json(self):
            return {"output": [{"type": "reasoning", "content": "hidden"}], "stats": {"total_output_tokens": 1100, "reasoning_output_tokens": 1099}}

    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()

    monkeypatch.setattr("providers.engine.httpx.Client", Client)
    manager = ProviderManager()
    try:
        manager.generate("lmstudio", "system", "prompt", model="reasoning-only", max_tokens=1100)
    except ProviderError as exc:
        assert "reasoning_budget_exhausted" in str(exc)
    else:
        raise AssertionError("reasoning-only response must be classified")


def test_lmstudio_native_chat_falls_back_for_legacy_server(monkeypatch):
    class Response:
        status_code = 404
        is_success = False

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("providers.engine.httpx.Client", Client)
    manager = ProviderManager()
    calls = []
    monkeypatch.setattr(manager, "_openai_compatible", lambda *args, **kwargs: calls.append(kwargs) or "legacy")
    assert manager.generate("lmstudio", "system", "prompt", model="legacy-model", json_mode=True) == "legacy"
    assert calls and calls[0]["json_mode"] is True


def test_local_generation_uses_complete_json_output_budgets(monkeypatch):
    budgets = {}

    def generate(provider, system, prompt, **kwargs):
        if '"student"' in prompt:
            budgets["lesson"] = kwargs["max_tokens"]
            return '{"topic":"t","student":{},"teacher":{},"review":{}}'
        if '"prompt_examples"' in prompt:
            budgets["prompts"] = kwargs["max_tokens"]
            return '{"prompt_examples":[]}'
        budgets["exercises"] = kwargs["max_tokens"]
        return '{"exercises":[]}'

    monkeypatch.setattr(generation_service.providers, "generate", generate)
    for part in ("lesson", "prompts", "exercises"):
        generation_service.generate_part("ollama", 12, 1, "전체 초보자", part)
    assert budgets == generation_service.LOCAL_OUTPUT_TOKENS == {
        "lesson": 1000,
        "prompts": 800,
        "exercises": 1200,
    }


def test_lmstudio_generates_prompt_and_exercise_items_individually(monkeypatch):
    calls = []

    def generate(provider, system, prompt, **kwargs):
        calls.append((prompt, kwargs["max_tokens"]))
        if '"prompt_example"' in prompt:
            number = next(n for n in range(1, 4) if f'"no":{n}' in prompt)
            return json.dumps({"prompt_example": {"no": number, "title": f"p{number}", "prompt": "질문", "reason": "이유", "how_to": "방법", "expected_result": "결과", "verification": "검증"}})
        number = next(n for n in range(1, 8) if f'"no":{n}' in prompt)
        return json.dumps({"exercise": {"no": number, "title": f"e{number}", "task": "과제", "steps": ["1", "2", "3"], "reason": "이유", "expected_result": "결과", "verification": "검증"}})

    monkeypatch.setattr(generation_service.providers, "generate", generate)
    monkeypatch.setattr(generation_service.providers, "ensure_lmstudio_model_loaded", lambda *args, **kwargs: None)
    prompts = generation_service.generate_part("lmstudio", 12, 1, "전체 초보자", "prompts")
    exercises = generation_service.generate_part("lmstudio", 12, 1, "전체 초보자", "exercises")
    assert [item["no"] for item in prompts["prompt_examples"]] == [1, 2, 3]
    assert [item["no"] for item in exercises["exercises"]] == list(range(1, 8))
    assert len(calls) == 10
    assert sorted(budget for _, budget in calls) == [350] * 3 + [420] * 7


def test_lmstudio_partial_items_are_completed_without_expensive_model_failover(monkeypatch):
    monkeypatch.setattr(generation_service.providers, "model_candidates", lambda provider, current="": ["qwen:4b", "lfm:2b"])
    monkeypatch.setattr(generation_service.providers, "ensure_lmstudio_model_loaded", lambda *args, **kwargs: None)
    budgets = []

    def generate(provider, system, prompt, model="", **kwargs):
        budgets.append((model, kwargs["max_tokens"]))
        number = next(n for n in range(1, 8) if f'"no":{n}' in prompt)
        if model == "qwen:4b":
            return json.dumps({"exercise": {"no": number, "title": "필드가 부족한 결과"}})
        return json.dumps({"exercise": {
            "no": number,
            "title": f"실습 {number}",
            "task": "가상 자료로 AI 기능을 연습합니다.",
            "steps": ["예상합니다.", "실행합니다.", "검증합니다."],
            "reason": "직접 연습하기 위해서입니다.",
            "expected_result": "검증 가능한 결과를 얻습니다.",
            "verification": "공식 자료와 비교합니다.",
        }})

    monkeypatch.setattr(generation_service.providers, "generate", generate)
    result = generation_service.generate_part("lmstudio", 12, 1, "전체 초보자", "exercises")
    assert len(result["exercises"]) == 7 and "누락 필드" in result.get("_warning", "")
    assert all(item["task"] and len(item["steps"]) == 3 for item in result["exercises"])
    assert {budget for model, budget in budgets if model == "qwen:4b"} == {420}
    assert not {model for model, _ in budgets if model == "lfm:2b"}


def test_lmstudio_reasoning_only_model_is_abandoned_after_one_item(monkeypatch):
    monkeypatch.setattr(generation_service.providers, "model_candidates", lambda provider, current="": ["reasoning:2b", "usable:3b"])
    monkeypatch.setattr(generation_service.providers, "ensure_lmstudio_model_loaded", lambda *args, **kwargs: None)
    calls = []

    def generate(provider, system, prompt, model="", **kwargs):
        calls.append(model)
        if model == "reasoning:2b":
            raise generation_service.ProviderError("LM Studio reasoning_budget_exhausted: no visible answer")
        number = next(n for n in range(1, 8) if f'"no":{n}' in prompt)
        return json.dumps({"exercise": {"no": number, "title": f"e{number}", "task": "과제", "steps": ["1", "2", "3"], "reason": "이유", "expected_result": "결과", "verification": "검증"}})

    monkeypatch.setattr(generation_service.providers, "generate", generate)
    result = generation_service.generate_part("lmstudio", 12, 1, "전체 초보자", "exercises")
    assert calls.count("reasoning:2b") == 1 and calls.count("usable:3b") == 7
    assert len(result["exercises"]) == 7


def test_ollama_generation_without_ui_auto_connect_uses_same_balanced_recommendation(monkeypatch):
    manager = ProviderManager()
    rows = [
        {"model": "first-opencode:2b", "size": 2 * 1024**3},
        {"model": "general:3b", "size": 3 * 1024**3},
        {"model": "huge:36b", "size": 24 * 1024**3},
    ]
    selected = {}
    monkeypatch.setattr(manager, "_ollama_models", lambda cfg: rows)
    monkeypatch.setattr(manager, "_ollama_chat", lambda cfg, model, *args, **kwargs: selected.setdefault("model", model) or "ok")
    manager.generate("ollama", "system", "prompt")
    assert manager.get("ollama").model == "general:3b"
    assert selected["model"] == "general:3b"


def test_runtime_disconnect_short_circuits_remaining_week_calls(monkeypatch):
    calls = []

    def disconnect(*args, **kwargs):
        calls.append(1)
        raise generation_service.ProviderError("Ollama가 생성 중 연결을 강제로 종료했습니다.")

    monkeypatch.setattr(generation_service.providers, "generate", disconnect)
    lesson = generation_service.build_week("ollama", 12, 1, "전체 초보자")
    assert len(calls) == 1
    assert len(lesson["prompt_examples"]) == 3 and len(lesson["exercises"]) == 7
    assert len(lesson["_warnings"]) == 1


def test_generation_keeps_book_when_a_model_stage_times_out(monkeypatch):
    def timeout(*args, **kwargs):
        raise generation_service.ProviderError("OpenAI 연결이 반복해서 시간초과되었습니다.")

    monkeypatch.setattr(generation_service.providers, "generate", timeout)
    book = generation_service.build_book("lmstudio", 12, "전체 초보자", 1, 1)
    assert book["book_id"] > 0
    assert len(book["content"]) == 1
    assert book["download_url"].endswith(f"/book/{book['book_id']}") and book["view_url"].endswith(f"/book/{book['book_id']}")
    assert len(book["content"][0]["prompt_examples"]) == 3
    assert len(book["content"][0]["exercises"]) == 7
    assert book["quality_reports"][0]["publishable"] is True
    assert len(book["warnings"]) == 1


def test_verified_change_is_appended_to_the_selected_book_file(monkeypatch):
    def timeout(*args, **kwargs):
        raise generation_service.ProviderError("test fallback")

    from studio.db import connect
    monkeypatch.setattr(generation_service.providers, "generate", timeout)
    book = generation_service.build_book("lmstudio", 12, "전체 초보자", 1, 1)
    path = Path(book["md_path"])
    try:
        response = client.post(f"/api/books/{book['book_id']}/changes/ChatGPT")
        assert response.status_code == 200
        result = response.json()
        assert result["applied"] is True and result["view_url"].endswith(f"/book/{book['book_id']}")
        markdown = path.read_text(encoding="utf-8")
        assert "## 최신 정보 변경 반영 · ChatGPT" in markdown
        assert "- 기준일: 2026-08-06" in markdown and "- 변경일:" in markdown
        viewed = client.get(result["view_url"])
        assert viewed.status_code == 200 and 'class="book-change-highlight"' in viewed.text
        assert "파란색 밑줄 · 최신 정보 변경 반영 구간" in viewed.text
        dashboard = client.get(f"/api/view/book/{book['book_id']}/dashboard")
        dashboard_download = client.get(f"/api/export/book/{book['book_id']}/dashboard")
        assert dashboard.status_code == 200 and "교재 생성 대시보드" in dashboard.text
        assert f"http://testserver/api/view/book/{book['book_id']}" in dashboard.text
        assert dashboard_download.status_code == 200 and "attachment" in dashboard_download.headers.get("content-disposition", "")
        assert f"http://testserver/api/export/book/{book['book_id']}" in dashboard_download.text
        pptx = client.get(f"/api/export/book/{book['book_id']}/pptx")
        pdf = client.get(f"/api/export/book/{book['book_id']}/pdf")
        assert pptx.status_code == 200 and pptx.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.presentationml.presentation") and pptx.content[:2] == b"PK"
        assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf") and pdf.content[:4] == b"%PDF"
        assert client.post(f"/api/books/{book['book_id']}/changes/ChatGPT").json()["applied"] is False
    finally:
        with connect() as connection:
            connection.execute("DELETE FROM lesson_units WHERE book_id=?", (book["book_id"],))
            connection.execute("DELETE FROM books WHERE id=?", (book["book_id"],))
        path.unlink(missing_ok=True)


def test_education_quality_pipeline_stores_profile_and_approval(monkeypatch):
    def timeout(*args, **kwargs):
        raise generation_service.ProviderError("test fallback")

    monkeypatch.setattr(generation_service.providers, "generate", timeout)
    book = generation_service.build_book("lmstudio", 12, "60대", 1, 1, experience="도움 있으면 가능", device_paths=["pc_web", "android_app"])
    try:
        lesson = book["content"][0]
        assert len(lesson["learning_design"]["device_paths"]) == 2
        assert book["quality_reports"][0]["score"] >= 85
        from studio.services.education_quality import lesson_quality, set_approval
        assert lesson_quality(book["book_id"], 1)["approval_status"] == "pending"
        assert set_approval(book["book_id"], 1, True, "pytest", "검증")["approval_status"] == "approved"
    finally:
        from studio.db import connect
        path = Path(book["md_path"])
        with connect() as connection:
            connection.execute("DELETE FROM lesson_units WHERE book_id=?", (book["book_id"],))
            connection.execute("DELETE FROM books WHERE id=?", (book["book_id"],))
        path.unlink(missing_ok=True)


def test_markdown_marks_relevant_changed_information_blue():
    markdown = book_to_markdown({"weeks": 1, "audience": "전체 초보자", "provider": "test", "model": "test", "latest_changes": ["[ChatGPT · 기준일 2026-08-06: GPT-5.6 계열]"], "content": []})
    assert '<span style="color:#2563eb">[ChatGPT · 기준일 2026-08-06: GPT-5.6 계열]</span>' in markdown


def test_malformed_json_field_inside_exercise_steps_is_repaired_before_publish():
    from studio.services.generation_service import sanitize_exercises
    broken = [{"no": 1, "title": "연습", "task": "과제", "steps": ["첫 단계", "reason\":\"직접 해보기 위해서입니다.", "둘째 단계", "셋째 단계"], "reason": "", "expected_result": "결과", "verification": "검증"}]
    repaired = sanitize_exercises(broken, "AI", "연습")
    assert repaired[0]["reason"] == "직접 해보기 위해서입니다."
    assert repaired[0]["steps"] == ["첫 단계", "둘째 단계", "셋째 단계"]


def test_local_summary_never_sends_an_oversized_context():
    class SmallContextProvider:
        def __init__(self): self.prompts = []
        def generate(self, provider, system, prompt, **kwargs):
            self.prompts.append(prompt)
            assert len(prompt) < 8_000
            return "- 확인된 사실"
    fake = SmallContextProvider()
    progress = []
    result = summarize_text(fake, "lmstudio", "AI 교육 자료입니다. " * 2_000, lambda done, total, message: progress.append((done, total, message)))
    assert result and len(fake.prompts) > 2 and progress


def test_summary_is_saved_as_a_markdown_file():
    class FakeProvider:
        def generate(self, *args, **kwargs): return "## 핵심 내용 5개\n- 저장 확인"
    source = _insert("file", "요약 파일 검증", "test.txt", text="요약할 교육 자료입니다.")
    try:
        result = summarize_source(source["id"], FakeProvider(), "lmstudio", "summary-test-job")
        path = summary_file(source["id"])
        assert path.exists() and "요약 파일 검증" in path.read_text(encoding="utf-8")
        assert result["download_url"].endswith("/summary-file")
    finally:
        delete_source(source["id"])


def test_source_summary_is_queued_and_returns_its_result_without_a_long_http_request(monkeypatch):
    """Long local inference must outlive the request that starts the job."""
    import time
    from studio.services import source_service

    source = _insert("file", "비동기 요약 검증", "async.txt", text="요약할 교육 자료입니다.")
    expected = {"id": source["id"], "title": source["title"], "summary": "완료", "download_url": f"/api/sources/{source['id']}/summary-file"}
    monkeypatch.setattr(source_service, "summarize_source", lambda *args, **kwargs: expected)
    try:
        accepted = start_source_summary(source["id"], object(), "lmstudio", "queued-summary-test")
        assert accepted["accepted"] is True and accepted["job_id"] == "queued-summary-test"
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            job = jobs.get("queued-summary-test")
            if job and job["phase"] == "complete":
                break
            time.sleep(.01)
        assert job["phase"] == "complete" and job["result"] == expected
    finally:
        delete_source(source["id"])


def test_source_summary_rejects_a_saturated_queue_without_spawning_threads(monkeypatch):
    from fastapi import HTTPException
    from studio.services import source_service

    source = _insert("file", "대기열 제한 검증", "queue.txt", text="요약 자료")
    class FullQueue:
        def acquire(self, blocking=False):
            return False
    monkeypatch.setattr(source_service, "_summary_slots", FullQueue())
    try:
        try:
            start_source_summary(source["id"], object(), "lmstudio", "queue-full-test")
        except HTTPException as exc:
            assert exc.status_code == 429
        else:
            raise AssertionError("포화된 요약 대기열은 요청을 거부해야 합니다")
        assert jobs.get("queue-full-test") is None
    finally:
        delete_source(source["id"])

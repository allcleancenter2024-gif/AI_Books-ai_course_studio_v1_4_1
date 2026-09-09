"""Protected course, lesson, book generation, quality, and export endpoints."""
import json
import re
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from ..auth import require_authenticated
from ..schemas import BookAIRequest, CourseRequest, ExternalEditRequest, LessonApprovalRequest, LessonRequest, WeekAIRequest, WeekPartRequest
from ..services.course_service import create_course
from ..services.book_change_service import apply_change_to_book, repair_book_integrity
from ..services.book_export_service import create_hwpx, create_pdf, create_pptx
from ..services.education_quality import lesson_quality, load_lesson_unit, set_approval
from ..services.generation_service import build_book, generate_part, start_book_generation
from ..services.job_status import jobs
from ..services.lesson_service import student_lesson, teacher_lesson
from ..services.external_edit import edit_book
from ..services.book_service import book_source_path, export_course_markdown, get_book, list_books
from ..services.source_service import resume_source_upload

router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])

@router.post("/course")
def make_course(req: CourseRequest): return create_course(req.weeks, req.audience)

@router.post("/lesson/student")
def make_student(req: LessonRequest): return student_lesson(req.topic, req.audience)

@router.post("/lesson/teacher")
def make_teacher(req: LessonRequest): return teacher_lesson(req.topic, req.audience)

@router.post("/ai/week/part")
def ai_week_part(req: WeekPartRequest): return generate_part(req.provider, req.weeks, req.week, req.audience, req.part, req.source_ids)

@router.post("/ai/week")
def ai_week(req: WeekAIRequest):
    if req.generation_mode == "external_edit" and not req.external_ai_allowed:
        raise HTTPException(400, "외부 AI 편집은 외부 전송 동의를 명시해야 합니다.")
    book = build_book(req.provider, req.weeks, req.audience, req.week, req.week, req.source_ids, req.job_id, req.experience, req.device_paths, req.edition, req.generation_mode, req.web_scope)
    lesson = book["content"][0]
    lesson.update(book_id=book["book_id"], model=book["model"], model_failovers=book.get("model_failovers",[]), download_url=book["download_url"], view_url=book["view_url"], pptx_url=book["pptx_url"], pdf_url=book["pdf_url"], hwpx_url=book["hwpx_url"], quality_report=book["quality_reports"][0], approval_status="pending")
    return lesson

@router.post("/ai/week/start")
def start_ai_week(req: WeekAIRequest):
    if req.generation_mode == "external_edit" and not req.external_ai_allowed:
        raise HTTPException(400, "외부 AI 편집은 외부 전송 동의를 명시해야 합니다.")
    return start_book_generation(req.provider, req.weeks, req.audience, req.week, req.week, req.source_ids, req.job_id, req.experience, req.device_paths, req.edition, req.generation_mode, req.web_scope)

@router.post("/ai/book")
def ai_book(req: BookAIRequest):
    if req.generation_mode == "external_edit" and not req.external_ai_allowed:
        raise HTTPException(400, "외부 AI 편집은 외부 전송 동의를 명시해야 합니다.")
    return build_book(req.provider, req.weeks, req.audience, req.start_week, req.end_week, req.source_ids, req.job_id, req.experience, req.device_paths, req.edition, req.generation_mode, req.web_scope)

@router.post("/ai/book/start")
def start_ai_book(req: BookAIRequest):
    if req.generation_mode == "external_edit" and not req.external_ai_allowed:
        raise HTTPException(400, "외부 AI 편집은 외부 전송 동의를 명시해야 합니다.")
    return start_book_generation(req.provider, req.weeks, req.audience, req.start_week, req.end_week, req.source_ids, req.job_id, req.experience, req.device_paths, req.edition, req.generation_mode, req.web_scope)

@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str):
    state = jobs.get(job_id)
    if not state: raise HTTPException(404, "작업 상태를 찾을 수 없습니다.")
    payload = state.get("payload") or {}
    if payload.get("kind") == "source_upload":
        return resume_source_upload(job_id)
    if payload.get("kind") != "book_generation": raise HTTPException(400, "재개할 수 있는 교재 생성 작업이 아닙니다.")
    if state.get("phase") not in {"cancelled", "error", "interrupted"}: raise HTTPException(409, "현재 상태에서는 작업을 재개할 수 없습니다.")
    return start_book_generation(payload["provider"], payload["weeks"], payload["audience"], payload["start"], payload.get("end"), payload.get("source_ids", []), job_id, payload.get("experience", "처음"), payload.get("device_paths", []), payload.get("edition", "combined"), payload.get("generation_mode", "local_only"), payload.get("web_scope", "disabled"))

@router.post("/external-edit/openai")
def openai_external_edit(req: ExternalEditRequest):
    return edit_book(req.book_id, req.instruction, req.consent, req.cost_limit_usd)

@router.get("/books/{book_id}/lessons/{week}/quality")
def book_lesson_quality(book_id: int, week: int):
    record = lesson_quality(book_id, week)
    if not record: raise HTTPException(404, "차시 품질 검사 기록을 찾을 수 없습니다.")
    record["profile"] = json.loads(record.pop("profile_json"))
    record["quality"] = json.loads(record.pop("qa_json"))
    record.pop("content_json", None)
    return record

@router.get("/books/{book_id}/lessons/{week}")
def book_lesson_unit(book_id: int, week: int, edition: str = "combined"):
    """Return one independently stored lesson unit for Studio/Publisher handoff."""
    if edition not in {"student", "teacher", "combined"}:
        raise HTTPException(400, "edition은 student, teacher, combined 중 하나여야 합니다.")
    record = load_lesson_unit(book_id, week)
    if not record:
        raise HTTPException(404, "해당 주차 교재를 찾을 수 없습니다.")
    content = record["content"]
    if edition == "student":
        content = {"week": content.get("week"), "topic": content.get("topic"), "student": content.get("student", {}), "learning_design": content.get("learning_design", {})}
    elif edition == "teacher":
        content = {"week": content.get("week"), "topic": content.get("topic"), "teacher": content.get("teacher", {}), "learning_design": content.get("learning_design", {})}
    source_ids = content.get("learning_design", {}).get("source_ids", [])
    return {"book_id": book_id, "week": week, "edition": edition, "audience": record["audience"], "profile": record["profile"], "content": content, "quality": record["qa"], "approval_status": record["approval_status"], "publisher_handoff": {"source_ids": source_ids, "validation_status": record["qa"].get("validation_status", "validation_failed"), "requires_instructor_approval": record["approval_status"] != "approved"}}

@router.post("/books/{book_id}/lessons/{week}/approval")
def approve_lesson(book_id: int, week: int, req: LessonApprovalRequest): return set_approval(book_id, week, req.approved, req.reviewer, req.note)

@router.get("/books")
def books(): return list_books()

@router.post("/books/{book_id}/changes/{product_name}")
def add_change_to_book(book_id: int, product_name: str):
    return apply_change_to_book(book_id, product_name)

@router.post("/books/{book_id}/repair")
def repair_book(book_id: int): return repair_book_integrity(book_id)

def _export_path(book_id: int, suffix: str) -> tuple[dict, Path]:
    row, source = book_source_path(book_id)
    return row, source.with_suffix(suffix)

@router.get("/export/book/{book_id}/pptx")
def export_book_pptx(book_id: int):
    row, path = _export_path(book_id, ".pptx")
    create_pptx(row, path)
    return FileResponse(path, filename=path.name, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")

@router.get("/export/book/{book_id}/pdf")
def export_book_pdf(book_id: int):
    row, path = _export_path(book_id, ".pdf")
    create_pdf(row, path)
    return FileResponse(path, filename=path.name, media_type="application/pdf")

@router.get("/export/book/{book_id}/hwpx")
def export_book_hwpx(book_id: int):
    row, path = _export_path(book_id, ".hwpx")
    create_hwpx(row, path)
    return FileResponse(path, filename=path.name, media_type="application/hwp+zip")

def _book_record(book_id: int):
    return get_book(book_id)

def _book_view_html(markdown: str, title: str) -> str:
    """Keep the original Markdown visible while marking appended update blocks."""
    blocks = re.split(r"(?=^## 최신 정보 변경 반영 · )", markdown, flags=re.MULTILINE)
    body = []
    for index, block in enumerate(blocks):
        css_class = "book-change-highlight" if index else "book-source"
        body.append(f'<pre class="{css_class}">{escape(block)}</pre>')
    safe_title = escape(title)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe_title} · 교재 보기</title><style>
    :root{{color-scheme:light}}body{{max-width:980px;margin:0 auto;padding:28px 20px 56px;background:#f5f8fc;color:#16253b;font-family:Pretendard,"Noto Sans KR",system-ui,sans-serif}}header{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;padding:15px 17px;border:1px solid #d4e2f4;border-radius:14px;background:#fff}}h1{{margin:0;font-size:20px}}.legend{{margin:0;color:#2864bd;font-size:12px;font-weight:800}}pre{{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.72 ui-monospace,SFMono-Regular,Consolas,monospace}}.book-source{{padding:18px;border:1px solid #dce4ee;border-radius:14px;background:#fff}}.book-change-highlight{{margin-top:15px;padding:18px;border:1px solid #b9d5fa;border-left:5px solid #2563eb;border-radius:14px;background:#eff6ff;color:#174b95;text-decoration-line:underline;text-decoration-color:#2563eb;text-decoration-thickness:2px;text-underline-offset:4px}}@media(max-width:600px){{body{{padding:14px 10px 32px}}header{{align-items:flex-start;flex-direction:column}}pre{{font-size:12px}}}}
    </style></head><body><header><h1>{safe_title}</h1><p class="legend">파란색 밑줄 · 최신 정보 변경 반영 구간</p></header>{''.join(body)}</body></html>'''

def _book_dashboard_html(book: dict, base_url: str = "") -> str:
    base_url = base_url.rstrip("/")
    book_id = book.get("book_id", book.get("id"))
    view_url = f"{base_url}/api/view/book/{book_id}"
    download_url = f"{base_url}/api/export/book/{book_id}"
    edition = {"student":"학생용", "teacher":"강사용", "combined":"학생용 + 강사용"}.get(book.get("edition"), "학생용 + 강사용")
    cards = "".join(f'<article><b>{escape(str(item.get("week")))}주차</b><span>{escape(item.get("topic", ""))}</span><small>프롬프트 {len(item.get("prompt_examples", []))}개 · 실습 {len(item.get("exercises", []))}개</small></article>' for item in book.get("content", []))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>교재 대시보드</title><style>body{{max-width:980px;margin:0 auto;padding:28px 20px;background:#f4f7fb;color:#17253b;font-family:system-ui,sans-serif}}header,article{{background:#fff;border:1px solid #d6e2f0;border-radius:15px;padding:18px}}header{{border-top:5px solid #3156d3}}h1{{margin:0 0 8px}}.meta{{display:flex;gap:8px;flex-wrap:wrap}}.meta span{{padding:6px 9px;background:#edf4ff;border-radius:999px;color:#285794;font-size:13px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px}}article b,article span,article small{{display:block}}article span{{margin:7px 0;color:#294a75}}small{{color:#64748b}}a{{display:inline-block;margin-top:16px;margin-right:8px;padding:9px 11px;border-radius:9px;background:#3156d3;color:#fff;text-decoration:none;font-weight:800}}</style></head><body><header><h1>교재 생성 대시보드</h1><div class="meta"><span>{escape(edition)}</span><span>{escape(str(book.get("weeks")))}주 과정</span><span>{escape(str(book.get("range", [])[0]))}~{escape(str(book.get("range", [])[-1]))}주차</span><span>참고자료 {len(book.get("source_ids", []))}개</span></div><a href="{view_url}">교재 내용 보기</a><a href="{download_url}">Markdown 다운로드</a></header><main>{cards}</main></body></html>'''

@router.get("/view/book/{book_id}/dashboard")
def view_book_dashboard(book_id: int, request: Request):
    row = _book_record(book_id)
    if not row: raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return HTMLResponse(_book_dashboard_html(row, str(request.base_url)))

@router.get("/export/book/{book_id}/dashboard")
def export_book_dashboard(book_id: int, request: Request):
    row = _book_record(book_id)
    if not row: raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return HTMLResponse(_book_dashboard_html(row, str(request.base_url)), headers={"Content-Disposition": f'attachment; filename="book_{book_id}_dashboard.html"'})

@router.get("/export/book/{book_id}")
def export_book(book_id: int):
    row = _book_record(book_id)
    if not row or not row.get("md_path"): raise HTTPException(404, "파일을 찾을 수 없습니다.")
    path = Path(row["md_path"])
    if not path.exists(): raise HTTPException(404, "파일을 찾을 수 없습니다.")
    return FileResponse(path, filename=path.name, media_type="text/markdown")

@router.get("/view/book/{book_id}")
def view_book(book_id: int):
    row = _book_record(book_id)
    if not row or not row.get("md_path") or not Path(row["md_path"]).exists(): raise HTTPException(404, "파일을 찾을 수 없습니다.")
    path = Path(row["md_path"])
    return HTMLResponse(_book_view_html(path.read_text(encoding="utf-8"), path.stem))

@router.get("/export/course/{course_id}")
def export_course(course_id: int):
    path = export_course_markdown(course_id)
    return FileResponse(path, filename=path.name, media_type="text/markdown")

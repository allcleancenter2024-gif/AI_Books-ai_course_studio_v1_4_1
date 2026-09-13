"""Protected course, lesson, book generation, quality, and export endpoints."""
import json
import re
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ..auth import require_authenticated
from ..schemas import (BookAIRequest, CourseRequest, ExternalEditRequest, ImagePromptApprovalRequest,
                       ImagePromptDraftRequest, LessonApprovalRequest, LessonRequest,
                       VisualAssetMetadataRequest, WeekAIRequest, WeekPartRequest)
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
from ..services.asset_service import (add_uploaded_asset, asset_file, create_prompt_draft,
                                      list_visuals, remove_asset, set_prompt_approval)
from ..services.publication_snapshot import publication_snapshot

router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])
public_view_router = APIRouter(prefix="/api")

@public_view_router.get("/view/book/{book_id}/webpage")
def public_book_webpage(book_id: int, request: Request):
    """Public read-only web textbook; all authoring and export routes stay protected."""
    row = get_book(book_id)
    if not row: raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return HTMLResponse(_book_webpage_html(row, str(request.base_url)))

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

@router.get("/books/{book_id}/lessons/{week}/visuals")
def lesson_visuals(book_id: int, week: int):
    """Preview-only visual metadata; no provider or storage credential is exposed."""
    return list_visuals(book_id, week)

@router.get("/books/{book_id}/lessons/{week}/publication-snapshot")
def lesson_publication_snapshot(book_id: int, week: int):
    return publication_snapshot(book_id, week)

@router.post("/books/{book_id}/lessons/{week}/image-prompts/draft")
def draft_lesson_image_prompt(book_id: int, week: int, req: ImagePromptDraftRequest):
    return create_prompt_draft(book_id, week, purpose=req.purpose, style=req.style, aspect_ratio=req.aspect_ratio)

@router.post("/image-prompts/{prompt_id}/approval")
def approve_image_prompt(prompt_id: str, req: ImagePromptApprovalRequest):
    return set_prompt_approval(prompt_id, req.approved)

@router.post("/books/{book_id}/lessons/{week}/visual-assets", status_code=201)
async def upload_lesson_visual_asset(
    book_id: int, week: int, file: UploadFile = File(...), role: str = Form("hero"),
    alt_text_ko: str = Form(...), alt_text_en: str = Form(""), caption_ko: str = Form(""),
    caption_en: str = Form(""), source_type: str = Form("uploaded"), source_url: str = Form(""),
    creator: str = Form(""), license: str = Form(""), copyright_status: str = Form("review_required"),
):
    metadata = VisualAssetMetadataRequest(role=role, alt_text_ko=alt_text_ko, alt_text_en=alt_text_en,
        caption_ko=caption_ko, caption_en=caption_en, source_type=source_type, source_url=source_url,
        creator=creator, license=license, copyright_status=copyright_status)
    return await add_uploaded_asset(book_id, week, file, metadata.model_dump())

@router.get("/visual-assets/{asset_id}/file")
def visual_asset_file(asset_id: str):
    asset, path = asset_file(asset_id)
    return FileResponse(path, filename=asset["original_name"], media_type=asset["mime_type"])

@router.delete("/visual-assets/{asset_id}", status_code=204)
def delete_visual_asset(asset_id: str):
    remove_asset(asset_id)

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

def _book_webpage_html(book: dict, base_url: str = "") -> str:
    """Render the generated book as a self-contained dashboard-style webpage."""
    base_url = base_url.rstrip("/")
    book_id = book.get("book_id", book.get("id"))
    view_url = f"{base_url}/api/view/book/{book_id}"
    dashboard_url = f"{base_url}/api/view/book/{book_id}/dashboard"
    markdown = ""
    if book.get("md_path"):
        path = Path(book["md_path"])
        if path.exists():
            markdown = path.read_text(encoding="utf-8")
    def highlight(text):
        safe = escape(str(text))
        for keyword in ("AI", "GPT", "Gemini", "프롬프트", "검증", "개인정보"):
            safe = safe.replace(keyword, f'<em class="keyword">{keyword}</em>')
        return safe
    lessons = []
    for item in book.get("content", []):
        prompts = item.get("prompt_examples", [])
        exercises = item.get("exercises", [])
        prompt_html = "".join(f"<li><strong>{escape(str(p.get('title', '프롬프트')))}</strong><br>{escape(str(p.get('prompt', p.get('text', ''))))}</li>" for p in prompts)
        exercise_html = "".join(f"<li><strong>{escape(str(e.get('title', '실습')))}</strong><br>{escape(str(e.get('task', e.get('text', ''))))}</li>" for e in exercises)
        student = item.get("student", {}) or {}; teacher = item.get("teacher", {}) or {}
        student_text = student.get("easy_explanation") or student.get("story") or "학습자가 이해하기 쉬운 설명을 제공합니다."
        teacher_text = teacher.get("deep_explanation") or teacher.get("teacher_script") or "수업에서 확인할 핵심 포인트를 제공합니다."
        lessons.append(f'<article class="lesson-card"><h3>{escape(str(item.get("week")))}주차 · {escape(str(item.get("topic", "")))}</h3><div class="lesson-columns"><div class="audience-card student" style="border-top:4px solid #6aa7ef;padding:12px;border-radius:10px;background:#f8fbff"><b>학생용 설명</b><p>{highlight(student_text)}</p><b>핵심 프롬프트</b><ul>{prompt_html or "<li>등록된 프롬프트가 없습니다.</li>"}</ul></div><div class="audience-card teacher" style="border-top:4px solid #9b78dc;padding:12px;border-radius:10px;background:#fcf9ff"><b>강사용 안내</b><p>{highlight(teacher_text)}</p><b>실습 활동</b><ul>{exercise_html or "<li>등록된 실습이 없습니다.</li>"}</ul></div></div></article>')
    content = "".join(lessons) if lessons else f'<pre>{escape(markdown) if markdown else "교재 내용이 아직 생성되지 않았습니다."}</pre>'
    for item in book.get("content", []):
        content = content.replace('<article class="lesson-card">', f'<article id="week-{escape(str(item.get("week")))}" class="lesson-card">', 1)
    title = escape(str(book.get("title", "교재 웹페이지")))
    sidebar = ''.join(f'<a href="#week-{escape(str(item.get("week")))}">{escape(str(item.get("week")))}주차 <span>{escape(str(item.get("topic", "")))}</span></a>' for item in book.get("content", []))
    cards = "".join(f'<article id="week-{escape(str(item.get("week")))}"><b>{escape(str(item.get("week")))}주차</b><span>{escape(item.get("topic", ""))}</span><small>프롬프트 {len(item.get("prompt_examples", []))}개 · 실습 {len(item.get("exercises", []))}개</small></article>' for item in book.get("content", []))
    cards = f'<aside class="side-nav"><strong>주차 내비게이션</strong>{sidebar}</aside>' + cards
    week_count = len(book.get("content", [])); prompt_count = sum(len(x.get("prompt_examples", [])) for x in book.get("content", [])); exercise_count = sum(len(x.get("exercises", [])) for x in book.get("content", []))
    roadmap = "".join(f'<a href="#week-{escape(str(item.get("week")))}" style="display:block;padding:10px;border:1px solid #dce6f2;border-radius:12px;text-decoration:none;color:#16253b"><b>{escape(str(item.get("week")))}주차</b><span style="display:block;margin-top:5px;color:#315a94">{escape(str(item.get("topic", "")))}</span></a>' for item in book.get("content", []))
    def highlight(text):
        safe = escape(str(text))
        for keyword in ("AI", "GPT", "Gemini", "프롬프트", "검증", "개인정보"):
            safe = safe.replace(keyword, f'<em class="keyword">{keyword}</em>')
        return safe
    hero = f'<section class="hero"><span class="eyebrow">STUDENT + INSTRUCTOR DASHBOARD</span><h1>{title}</h1><p>주차별 핵심 개념을 이해하고 직접 실습한 뒤, 결과를 확인하는 교재 제작 흐름으로 구성했습니다.</p><div class="stats"><b>{week_count}<small>주차</small></b><b>{prompt_count}<small>핵심 프롬프트</small></b><b>{exercise_count}<small>실습 활동</small></b><b>학생·강사<small>통합 구성</small></b></div></section>'
    early_return = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 웹 교재</title><style>body{{margin:0;background:#f3f6fb;color:#16253b;font-family:system-ui,"Noto Sans KR",sans-serif}}.top{{height:58px;padding:0 4%;display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #dbe4f0;font-weight:800}}.top a{{margin:0 0 0 8px;padding:9px 12px;border:1px solid #d6e2f0;border-radius:10px;color:#294a75;text-decoration:none}}.wrap{{max-width:1100px;margin:0 auto;padding:30px 22px 70px}}.hero{{padding:34px 36px;border-radius:28px;background:linear-gradient(120deg,#2f55bf,#8297f0);color:#fff;box-shadow:0 18px 38px #2f55bf2b}}.eyebrow{{display:inline-block;padding:8px 12px;border-radius:999px;background:#ffffff30;font-size:12px;font-weight:900;letter-spacing:.04em}}h1{{margin:16px 0 10px;font-size:clamp(30px,5vw,54px);line-height:1.12}}.hero p{{max-width:760px;line-height:1.7;font-weight:600}}.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}}.stats b{{min-width:120px;padding:14px;border:1px solid #ffffff45;border-radius:14px;background:#ffffff20;font-size:24px}}.stats small{{display:block;margin-top:4px;font-size:12px;font-weight:700}}.roadmap,.lesson{{margin-top:20px;padding:22px;border:1px solid #d7e2f0;border-radius:20px;background:#fff}}.roadmap h2,.lesson>h2{{margin:0 0 14px}}.roadmap-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}.roadmap-grid div{{padding:14px;border:1px solid #dce6f2;border-radius:12px}}.roadmap-grid b,.roadmap-grid span{{display:block}}.roadmap-grid span{{margin-top:7px;color:#315a94}}.week-nav{{display:flex;gap:8px;overflow:auto;margin:22px 0;padding-bottom:4px}}.week-nav a{{flex:0 0 auto;padding:9px 13px;border-radius:999px;background:#e8efff;color:#2453b7;text-decoration:none;font-weight:800}}.lesson-card{{margin-top:14px;padding:22px;border-radius:18px;border:1px solid #d6e2f0;border-top:6px solid #4e9b93;background:#fff}}.lesson-card h3{{margin:0 0 16px;color:#1d4ed8}}.lesson-columns{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.audience-card{{padding:16px;border-radius:12px;background:#f8fbff}}.audience-card.teacher{{background:#fcf9ff}}.audience-card b{{display:block;margin-bottom:8px}}li{{margin:7px 0;line-height:1.5}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}@media(max-width:700px){{.wrap{{padding:18px 12px 50px}}.hero{{padding:25px 22px;border-radius:20px}}.lesson-columns{{grid-template-columns:1fr}}.top{{padding:0 14px}}}}</style></head><body><div class="top"><span>AI 강의 활용 Studio · {week_count}주차</span><nav><a href="{dashboard_url}">교재 생성 대시보드</a><a href="{base_url}/#publisher">웹 교재 발행으로 돌아가기</a></nav></div><div class="wrap">{hero}<section class="roadmap"><h2>교재 제작 흐름 · {week_count}주차 학습 로드맵</h2><div class="roadmap-grid">{roadmap}</div></section><nav class="week-nav" aria-label="주차 내비게이션">{sidebar}</nav><section class="lesson"><h2>교재 내용</h2>{''.join(lessons)}</section></div></body></html>'''
    early_return = early_return.replace('font-family:system-ui,"Noto Sans KR",sans-serif', 'font-family:"Nanum Gothic","나눔고딕",system-ui,sans-serif')
    early_return = early_return.replace('.roadmap-grid div{{padding:14px;border:1px solid #dce6f2;border-radius:12px}}', '.roadmap-grid div{{padding:10px;border:1px solid #dce6f2;border-radius:12px}}')
    early_return = early_return.replace('</body>', '<a href="#top" id="to-top" aria-label="위로 가기">↑</a><script>addEventListener("scroll",()=>document.getElementById("to-top").classList.toggle("show",scrollY>500));</script></body>')
    early_return = early_return.replace('</style>', '#to-top{position:fixed;right:18px;bottom:18px;width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#3156d3;color:#fff;text-decoration:none;font-weight:900;opacity:0;pointer-events:none;transition:opacity .2s}#to-top.show{opacity:1;pointer-events:auto}</style>')
    return early_return
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 웹 교재</title><style>body{{max-width:1100px;margin:0 auto;padding:24px 18px 56px;background:#f4f7fb;color:#17253b;font-family:system-ui,sans-serif}}header,.lesson,.lesson-card,pre{{background:#fff;border:1px solid #d6e2f0;border-radius:15px;padding:18px}}header{{border-top:5px solid #3156d3;background:linear-gradient(135deg,#3156d3,#7188eb);color:#fff}}h1{{margin:0 0 10px;font-size:clamp(24px,4vw,42px)}}.meta{{display:flex;gap:8px;flex-wrap:wrap}}.meta span{{padding:6px 9px;background:#ffffff33;border-radius:999px;color:#fff;font-size:13px}}main{{display:grid;grid-template-columns:180px repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:16px 0}}article b,article span,article small{{display:block}}article span{{margin:7px 0;color:#294a75}}small{{color:#64748b}}a{{display:inline-block;margin:14px 8px 0 0;padding:9px 12px;border-radius:9px;background:#3156d3;color:#fff;text-decoration:none;font-weight:800}}a.back{{background:#eef4ff;color:#3156d3;border:1px solid #b9cdec}}.lesson{{margin-top:16px}}.lesson-card{{margin-top:12px}}.side-nav{{background:#101d33;color:#fff;border-radius:15px;padding:16px;grid-row:span 2}}.side-nav strong{{display:block;margin-bottom:10px;text-transform:uppercase;font-size:12px;letter-spacing:.08em;color:#a9c7ff}}.side-nav a{{display:block;margin:0;padding:9px 0;color:#fff;border-bottom:1px solid #ffffff1f}}.side-nav a span{{display:block;color:#b9c9e7;font-size:12px;margin-top:3px}}li{{margin:5px 0;color:#294a75}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 ui-monospace,Consolas,monospace}}@media(max-width:700px){{body{{padding:14px 10px 32px}}main{{display:block}}.side-nav{{margin-bottom:12px}}}}</style></head><body><header><h1>{title}</h1><div class="meta"><span>{escape(str(book.get("weeks")))}주 과정</span><span>{escape(str(book.get("edition", "combined")))}</span><span>학생용 · 강사용 대시보드</span></div><a href="{dashboard_url}">교재 생성 대시보드</a><a class="back" href="{base_url}/#publisher">웹 교재 발행으로 돌아가기</a></header><main>{cards}</main><section class="lesson"><h2>교재 내용</h2>{content}</section></body></html>'''

def _book_dashboard_html(book: dict, base_url: str = "") -> str:
    base_url = base_url.rstrip("/")
    book_id = book.get("book_id", book.get("id"))
    view_url = f"{base_url}/api/view/book/{book_id}/webpage"
    download_url = f"{base_url}/api/export/book/{book_id}"
    studio_publisher_url = f"{base_url}/#publisher"
    edition = {"student":"학생용", "teacher":"강사용", "combined":"학생용 + 강사용"}.get(book.get("edition"), "학생용 + 강사용")
    cards = "".join(f'<article><b>{escape(str(item.get("week")))}주차</b><span>{escape(item.get("topic", ""))}</span><small>프롬프트 {len(item.get("prompt_examples", []))}개 · 실습 {len(item.get("exercises", []))}개</small></article>' for item in book.get("content", []))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>교재 대시보드</title><style>body{{max-width:980px;margin:0 auto;padding:28px 20px;background:#f4f7fb;color:#17253b;font-family:system-ui,sans-serif}}header,article{{background:#fff;border:1px solid #d6e2f0;border-radius:15px;padding:18px}}header{{border-top:5px solid #3156d3}}h1{{margin:0 0 8px}}.meta{{display:flex;gap:8px;flex-wrap:wrap}}.meta span{{padding:6px 9px;background:#edf4ff;border-radius:999px;color:#285794;font-size:13px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px}}article b,article span,article small{{display:block}}article span{{margin:7px 0;color:#294a75}}small{{color:#64748b}}a{{display:inline-block;margin-top:16px;margin-right:8px;padding:9px 11px;border-radius:9px;background:#3156d3;color:#fff;text-decoration:none;font-weight:800}}a.back{{background:#eef4ff;color:#3156d3;border:1px solid #b9cdec}}a.web{{background:#e8f7ee;color:#176b3a;border:1px solid #acd9bd}}</style></head><body><header><h1>교재 생성 대시보드</h1><div class="meta"><span>{escape(edition)}</span><span>{escape(str(book.get("weeks")))}주 과정</span><span>{escape(str(book.get("range", [])[0]))}~{escape(str(book.get("range", [])[-1]))}주차</span><span>참고자료 {len(book.get("source_ids", []))}개</span></div><a class="web" href="{view_url}" target="_blank" rel="noopener noreferrer">웹페이지 바로 보기</a><a href="{view_url}">교재 내용 보기</a><a href="{download_url}">Markdown 다운로드</a><a class="back" href="{studio_publisher_url}">웹 교재 발행으로 돌아가기</a></header><main>{cards}</main></body></html>'''

@router.get("/view/book/{book_id}/dashboard")
def view_book_dashboard(book_id: int, request: Request):
    row = _book_record(book_id)
    if not row: raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return HTMLResponse(_book_dashboard_html(row, str(request.base_url)))

@router.get("/view/book/{book_id}/webpage")
def view_book_webpage(book_id: int, request: Request):
    row = _book_record(book_id)
    if not row: raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return HTMLResponse(_book_webpage_html(row, str(request.base_url)))

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

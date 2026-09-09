"""Analyze operational facts, apply targeted manual updates, and create the full manual PDF."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import APP_BASE_URL, BASE_DIR, DB_PATH, LAST_UPDATED, MAX_UPLOAD_BYTES, PDF_OUTPUT_DIR, VERSION
from ..db import connect
from ..schemas import ManualPDFRequest


FACT_LABELS = {
    "version": "현재 버전", "last_updated": "최근 수정일", "studio_url": "Studio 주소",
    "menu_count": "메뉴 수", "providers": "로컬 AI Provider", "max_upload_mb": "파일 업로드 한도",
    "session_days": "로그인 세션", "login_failures": "로그인 실패 제한", "database": "기본 데이터베이스",
    "database_path": "DB 위치", "output_formats": "교재 출력 형식", "lesson_shape": "교재 품질 구조",
    "docker_ports": "선택형 Docker 포트", "tailscale_role": "Tailscale 역할",
}

CHAPTER_FACTS = {
    "windows-install": ["version", "last_updated", "studio_url"],
    "linux-install": ["studio_url"],
    "login-session": ["session_days", "login_failures"],
    "menu-ai": ["providers"],
    "menu-sources": ["max_upload_mb"],
    "menu-book": ["output_formats", "lesson_shape"],
    "menu-dbms": ["database", "database_path", "docker_ports"],
    "menu-updates": ["version", "last_updated"],
    "menu-manual": ["menu_count", "version", "last_updated"],
    "data-paths": ["database_path", "output_formats"],
    "docker-external": ["docker_ports"],
    "network-ports": ["studio_url", "docker_ports"],
    "tailscale-host": ["tailscale_role"],
    "startup-trouble": ["version", "studio_url"],
    "ai-trouble": ["providers", "lesson_shape"],
    "update-rollback": ["version", "last_updated"],
}


SHIPPED_BASELINE = {
    "version": "1.24.0", "last_updated": "2026-08-29", "studio_url": "http://127.0.0.1:8765",
    "menu_count": "12개", "providers": "LM Studio, Ollama", "max_upload_mb": "500MB",
    "session_days": "최대 7일", "login_failures": "5회 실패 시 5분 제한",
    "database": "SQLite 3 (WAL)", "database_path": "data/studio.db",
    "output_formats": "Markdown, PPTX, PDF, HWPX", "lesson_shape": "프롬프트 3개, 실습 7개, 품질 85점 기준",
    "docker_ports": "API 3001, PostgreSQL 5434, pgAdmin 5051, MongoDB 27018, Mongo Express 8082",
    "tailscale_role": "Host-only 선택형 사설 관리망, 애플리케이션 의존성 없음",
}


def _fingerprint(snapshot: dict[str, str]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def collect_operational_facts() -> dict[str, str]:
    """Read non-secret, user-visible facts from the current application configuration."""
    index_text = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
    menu_count = len(re.findall(r'<nav class="side"[^>]*>.*?</nav>', index_text, re.S)[0].split("<a ")) - 1
    return {
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "studio_url": APP_BASE_URL,
        "menu_count": f"{menu_count}개",
        "providers": "LM Studio, Ollama",
        "max_upload_mb": f"{MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
        "session_days": "최대 7일",
        "login_failures": "5회 실패 시 5분 제한",
        "database": "SQLite 3 (WAL)",
        "database_path": str(DB_PATH.relative_to(BASE_DIR)).replace("\\", "/") if DB_PATH.is_relative_to(BASE_DIR) else DB_PATH.name,
        "output_formats": "Markdown, PPTX, PDF, HWPX",
        "lesson_shape": "프롬프트 3개, 실습 7개, 품질 85점 기준",
        "docker_ports": "API 3001, PostgreSQL 5434, pgAdmin 5051, MongoDB 27018, Mongo Express 8082",
        "tailscale_role": "Host-only 선택형 사설 관리망, 애플리케이션 의존성 없음",
    }


def _ensure_state() -> tuple[dict[str, str], str]:
    # Ensure migrations exist for direct endpoint/test invocation as well as app lifespan.
    from studio.db import init_db
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT snapshot_json,applied_at FROM manual_update_state WHERE id=1").fetchone()
        if row:
            return json.loads(row["snapshot_json"]), row["applied_at"]
        applied_at = datetime.now().isoformat(timespec="seconds")
        snapshot = dict(SHIPPED_BASELINE)
        conn.execute("INSERT INTO manual_update_state(id,snapshot_json,fingerprint,applied_at) VALUES(1,?,?,?)",
                     (json.dumps(snapshot, ensure_ascii=False, sort_keys=True), _fingerprint(snapshot), applied_at))
        return snapshot, applied_at


def _chapter_values(snapshot: dict[str, str]) -> list[dict]:
    return [{"chapter_id": chapter_id, "facts": [{"key": key, "label": FACT_LABELS[key], "value": snapshot.get(key, "-")} for key in keys]}
            for chapter_id, keys in CHAPTER_FACTS.items()]


def manual_update_status() -> dict:
    applied, applied_at = _ensure_state()
    current = collect_operational_facts()
    changes = []
    for key, after in current.items():
        before = applied.get(key, "-")
        if before != after:
            chapters = [chapter_id for chapter_id, keys in CHAPTER_FACTS.items() if key in keys]
            changes.append({"key": key, "label": FACT_LABELS[key], "before": before, "after": after, "chapter_ids": chapters})
    affected = sorted({chapter for change in changes for chapter in change["chapter_ids"]})
    return {"has_updates": bool(changes), "change_count": len(changes), "affected_chapter_count": len(affected),
            "changes": changes, "applied_at": applied_at, "applied_chapters": _chapter_values(applied),
            "current_fingerprint": _fingerprint(current)}


def apply_manual_updates() -> dict:
    status = manual_update_status()
    current = collect_operational_facts()
    applied_at = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute("""INSERT INTO manual_update_state(id,snapshot_json,fingerprint,applied_at) VALUES(1,?,?,?)
            ON CONFLICT(id) DO UPDATE SET snapshot_json=excluded.snapshot_json,fingerprint=excluded.fingerprint,applied_at=excluded.applied_at""",
            (json.dumps(current, ensure_ascii=False, sort_keys=True), _fingerprint(current), applied_at))
    return {"ok": True, "applied_at": applied_at, "changes": status["changes"],
            "affected_chapter_count": status["affected_chapter_count"], "applied_chapters": _chapter_values(current)}


def _pdf_font() -> str:
    candidates = [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/NotoSansKR-Regular.otf"),
                  Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    for path in candidates:
        if path.exists():
            name = "ManualKorean"
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return "Helvetica"


def create_manual_pdf(request: ManualPDFRequest) -> Path:
    font = _pdf_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ManualTitle", parent=styles["Title"], fontName=font, fontSize=23, leading=30,
                                 textColor=colors.HexColor("#213A61"), alignment=TA_CENTER, spaceAfter=10)
    meta_style = ParagraphStyle("ManualMeta", parent=styles["BodyText"], fontName=font, fontSize=9.5, leading=14,
                                textColor=colors.HexColor("#7A5A22"), alignment=TA_CENTER, spaceAfter=14)
    chapter_style = ParagraphStyle("ManualChapter", parent=styles["Heading2"], fontName=font, fontSize=15, leading=21,
                                   textColor=colors.HexColor("#213A61"), spaceBefore=8, spaceAfter=6)
    summary_style = ParagraphStyle("ManualSummary", parent=styles["BodyText"], fontName=font, fontSize=10, leading=15,
                                   textColor=colors.HexColor("#8A5A0A"), backColor=colors.HexColor("#FFF6DF"),
                                   borderPadding=7, spaceAfter=7)
    body_style = ParagraphStyle("ManualBody", parent=styles["BodyText"], fontName=font, fontSize=9.5, leading=15,
                                textColor=colors.HexColor("#334155"), spaceAfter=5)
    small_style = ParagraphStyle("ManualSmall", parent=body_style, fontSize=8.5, leading=13, textColor=colors.HexColor("#64748B"))

    filename = f"AI_Course_Studio_Installation_Operations_Manual_v{VERSION.replace('.', '_')}.pdf"
    destination = PDF_OUTPUT_DIR / filename
    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def page(canvas, doc):
        canvas.saveState(); canvas.setFont(font, 8); canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(17 * mm, 10 * mm, f"AI Course Studio v{VERSION} | {LAST_UPDATED}")
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"{doc.page} page"); canvas.restoreState()

    story = [Spacer(1, 18 * mm), Paragraph(escape(request.title), title_style),
             Paragraph(escape(f"운영 기준 v{VERSION} | {LAST_UPDATED} | 전체 {len(request.chapters)}개 장"), meta_style),
             Paragraph("설치 - 운영 - 교재 생성 - 백업 - 장애 대응을 현재 프로그램 구성에 맞춰 정리한 전체 설명서입니다.", body_style), Spacer(1, 8)]
    toc = [[Paragraph("장", small_style), Paragraph("분야", small_style), Paragraph("제목", small_style)]]
    for chapter in request.chapters:
        toc.append([Paragraph(str(chapter.index), small_style), Paragraph(escape(chapter.category), small_style), Paragraph(escape(chapter.title), small_style)])
    table = Table(toc, colWidths=[12 * mm, 32 * mm, 126 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F8")),
                               ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CBD5E1")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story += [table, PageBreak()]
    for offset, chapter in enumerate(request.chapters):
        story.append(Paragraph(escape(f"{chapter.index:02d}. {chapter.title}"), chapter_style))
        story.append(Paragraph(escape(f"{chapter.category} | {chapter.summary}"), summary_style))
        for block in re.split(r"\n{2,}", chapter.text.strip()):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines: continue
            story.append(Paragraph("<br/>".join(escape(line) for line in lines), body_style))
        if offset < len(request.chapters) - 1: story.append(Spacer(1, 5))
    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
                            topMargin=17 * mm, bottomMargin=18 * mm, title=request.title, author="AI 강의 활용 Studio")
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return destination

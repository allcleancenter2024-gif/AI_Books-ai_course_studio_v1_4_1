"""Generate downloadable PPTX and PDF versions of a saved book."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def _edition_label(book: dict[str, Any]) -> str:
    return {"student": "학생용", "teacher": "강사용", "combined": "학생용 + 강사용"}.get(book.get("edition"), "학생용 + 강사용")


def _book_title(book: dict[str, Any]) -> str:
    return f"AI 강의 활용 Studio · {_edition_label(book)}"


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def create_pptx(book: dict[str, Any], destination: Path) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    def text_box(slide, text, left, top, width, height, size=20, color=(22, 37, 59), bold=False):
        shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        frame = shape.text_frame; frame.word_wrap = True
        para = frame.paragraphs[0]; para.text = _safe_text(text)
        para.font.name = "Malgun Gothic"; para.font.size = Pt(size); para.font.bold = bold
        para.font.color.rgb = __import__('pptx').dml.color.RGBColor(*color)
        return shape

    slide = prs.slides.add_slide(blank)
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb = __import__('pptx').dml.color.RGBColor(239, 246, 255)
    text_box(slide, _book_title(book), 0.8, 1.25, 11.8, 0.8, 34, (27, 63, 115), True)
    text_box(slide, f"{book.get('weeks')}주 과정 · {book.get('range', [1, 1])[0]}~{book.get('range', [1, 1])[-1]}주차", 0.85, 2.25, 8, 0.5, 22, (54, 91, 139))
    text_box(slide, f"AI Provider: {book.get('provider')} · 모델: {book.get('model')}", 0.85, 2.85, 10, 0.45, 16, (82, 104, 132))
    text_box(slide, f"참고자료 {len(book.get('source_ids', []))}개 · 품질 검사 완료", 0.85, 3.45, 10, 0.45, 16, (82, 104, 132))
    text_box(slide, "교재 생성 결과 요약", 0.85, 5.8, 6, 0.5, 18, (37, 99, 235), True)

    for lesson in book.get("content", []):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid(); slide.background.fill.fore_color.rgb = __import__('pptx').dml.color.RGBColor(255, 255, 255)
        text_box(slide, f"{lesson.get('week')}주차 · {lesson.get('topic')}", 0.65, 0.45, 12, 0.6, 28, (27, 63, 115), True)
        text_box(slide, "학생용 핵심", 0.8, 1.45, 5.7, 0.4, 18, (37, 99, 235), True)
        student = lesson.get("student", {})
        text_box(slide, student.get("easy_explanation") or student.get("story"), 0.8, 1.9, 5.7, 1.5, 16, (48, 65, 88))
        text_box(slide, "강사용 핵심", 6.9, 1.45, 5.7, 0.4, 18, (22, 121, 78), True)
        teacher = lesson.get("teacher", {})
        text_box(slide, teacher.get("deep_explanation") or teacher.get("teacher_script"), 6.9, 1.9, 5.7, 1.5, 16, (48, 65, 88))
        text_box(slide, f"프롬프트 {len(lesson.get('prompt_examples', []))}개 · 실습 {len(lesson.get('exercises', []))}개", 0.8, 4.35, 6, 0.4, 18, (54, 91, 139), True)
        goals = student.get("goals", [])
        text_box(slide, "학습 목표\n" + "\n".join(f"• {x}" for x in goals[:3]), 0.8, 4.9, 5.8, 1.4, 15, (82, 104, 132))
        text_box(slide, "수업 확인\n" + "\n".join(f"• {x}" for x in teacher.get("verification_points", [])[:3]), 6.9, 4.9, 5.8, 1.4, 15, (82, 104, 132))

    destination.parent.mkdir(parents=True, exist_ok=True)
    prs.save(destination)
    return destination


def _register_pdf_font() -> str:
    candidates = [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/NotoSansKR-Regular.otf")]
    for path in candidates:
        if path.exists():
            name = "StudioKorean"
            if name not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return "Helvetica"


def create_pdf(book: dict[str, Any], destination: Path) -> Path:
    font = _register_pdf_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("StudioTitle", parent=styles["Title"], fontName=font, fontSize=22, leading=28, textColor=colors.HexColor("#1b3f73"), alignment=TA_CENTER, spaceAfter=14)
    h2 = ParagraphStyle("StudioH2", parent=styles["Heading2"], fontName=font, fontSize=16, leading=21, textColor=colors.HexColor("#1b3f73"), spaceBefore=8, spaceAfter=7)
    body = ParagraphStyle("StudioBody", parent=styles["BodyText"], fontName=font, fontSize=10.5, leading=16, textColor=colors.HexColor("#30435d"), spaceAfter=6)
    small = ParagraphStyle("StudioSmall", parent=body, fontSize=9, leading=13, textColor=colors.HexColor("#5b6f89"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=_book_title(book), author="AI 강의 활용 Studio")
    story = [Paragraph(escape(_book_title(book)), title), Paragraph(escape(f"{book.get('weeks')}주 과정 · {book.get('range', [1, 1])[0]}~{book.get('range', [1, 1])[-1]}주차"), h2), Paragraph(escape(f"Provider: {book.get('provider')} · 모델: {book.get('model')} · 참고자료 {len(book.get('source_ids', []))}개"), body), Spacer(1, 8)]
    for lesson in book.get("content", []):
        story.append(Paragraph(escape(f"{lesson.get('week')}주차 · {lesson.get('topic')}"), h2))
        student = lesson.get("student", {}); teacher = lesson.get("teacher", {})
        data = [[Paragraph("학생용", body), Paragraph("강사용", body)], [Paragraph(escape(student.get("easy_explanation") or student.get("story")), body), Paragraph(escape(teacher.get("deep_explanation") or teacher.get("teacher_script")), body)]]
        table = Table(data, colWidths=[82 * mm, 82 * mm]); table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#edf4ff")), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#eaf8f0")), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#c9d8ec")), ("INNERGRID", (0, 0), (-1, -1), .35, colors.HexColor("#dbe5f1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 8)])); story.append(table)
        goals = " · ".join(_safe_text(x) for x in student.get("goals", [])[:3]) or "-"
        checks = " · ".join(_safe_text(x) for x in teacher.get("verification_points", [])[:3]) or "-"
        story += [Spacer(1, 7), Paragraph(escape(f"학습 목표: {goals}"), small), Paragraph(escape(f"수업 확인: {checks}"), small), Paragraph(escape(f"프롬프트 {len(lesson.get('prompt_examples', []))}개 · 실습 {len(lesson.get('exercises', []))}개"), small), PageBreak()]
    if story and isinstance(story[-1], PageBreak): story.pop()
    doc.build(story)
    return destination


def create_hwpx(book: dict[str, Any], destination: Path) -> Path:
    """Create a standards-based HWPX package using the bundled HWPML builder."""
    skill_root = Path("C:/Users/Home_care/.codex/skills/hwpxskill")
    builder = skill_root / "scripts" / "build_hwpx.py"
    template = skill_root / "templates" / "base" / "Contents" / "section0.xml"
    if not builder.exists() or not template.exists():
        raise RuntimeError("HWPX 템플릿 또는 빌드 도구를 찾을 수 없습니다.")
    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    hs = "http://www.hancom.co.kr/hwpml/2011/section"
    ET.register_namespace("hp", hp); ET.register_namespace("hs", hs)
    root = ET.parse(template).getroot()
    for child in list(root):
        if child.tag == f"{{{hp}}}p": root.remove(child)
    lines = [_book_title(book), f"{book.get('weeks')}주 과정 · {book.get('range', [1, 1])[0]}~{book.get('range', [1, 1])[-1]}주차"]
    for lesson in book.get("content", []):
        lines.extend([f"{lesson.get('week')}주차 · {lesson.get('topic')}", "학생용", lesson.get("student", {}).get("easy_explanation") or lesson.get("student", {}).get("story"), "강사용", lesson.get("teacher", {}).get("deep_explanation") or lesson.get("teacher", {}).get("teacher_script")])
    for text in lines:
        p = ET.Element(f"{{{hp}}}p", {"id": str(abs(hash(text))), "paraPrIDRef": "0", "styleIDRef": "0", "pageBreak": "0", "columnBreak": "0", "merged": "0"})
        run = ET.SubElement(p, f"{{{hp}}}run", {"charPrIDRef": "0"})
        ET.SubElement(run, f"{{{hp}}}t").text = _safe_text(text)
        root.append(p)
    with tempfile.TemporaryDirectory(prefix="studio_hwpx_") as tmp:
        section = Path(tmp) / "section0.xml"; section.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([sys.executable, str(builder), "--section", str(section), "--title", _book_title(book), "--creator", "AI 강의 활용 Studio", "--output", str(destination)], capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not destination.exists():
            raise RuntimeError((result.stderr or result.stdout or "HWPX 생성 실패").strip())
    return destination

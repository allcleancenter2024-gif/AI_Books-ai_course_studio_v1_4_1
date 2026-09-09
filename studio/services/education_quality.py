"""Education-production quality gate based on the 2026-08 Studio guide."""
from __future__ import annotations

from datetime import datetime
import json
import re

from fastapi import HTTPException
from ..db import connect

DEVICE_LABELS = {"pc_web": "PC 웹", "android_app": "Android", "ios_ipados_app": "iPhone·iPad"}
RISK_LEVELS = {"green", "yellow", "red"}


def learner_profile(audience: str, experience: str = "처음", device_paths: list[str] | None = None) -> dict:
    paths = [path for path in (device_paths or list(DEVICE_LABELS)) if path in DEVICE_LABELS] or list(DEVICE_LABELS)
    return {"audience": audience, "experience": experience, "device_paths": paths,
            "core_ratio": 60, "audience_ratio": 25, "device_ratio": 15}


def device_steps(topic: str, practice: str) -> dict[str, list[str]]:
    return {
        "pc_web": ["브라우저에서 사용하는 AI 서비스의 공식 웹페이지를 엽니다.", "대화 입력칸에 짧은 질문을 붙여 넣거나 입력합니다.", "답변에서 확인할 사실 하나를 표시하고 공식 자료와 비교합니다."],
        "android_app": ["AI 앱 또는 모바일 브라우저를 열고 로그인 여부를 확인합니다.", "입력칸을 한 번 눌러 짧은 질문을 입력하거나 음성 입력을 사용합니다.", "답변을 길게 눌러 필요한 부분만 복사하고 사실 하나를 다시 확인합니다."],
        "ios_ipados_app": ["AI 앱 또는 Safari에서 서비스 페이지를 열고 로그인 여부를 확인합니다.", "입력칸을 눌러 짧은 질문을 입력하거나 받아쓰기 기능을 사용합니다.", "답변을 선택해 필요한 부분만 복사하고 사실 하나를 다시 확인합니다."],
    }


def enrich_lesson(lesson: dict, profile: dict, practice: str, source_ids: list[int] | None = None) -> dict:
    """Attach required schema fields even when an AI returns a partial draft."""
    topic = lesson.get("topic", "AI 활용")
    lesson["learning_design"] = {
        "profile": profile,
        "objectives": (lesson.get("student", {}).get("goals") or [])[:3],
        "materials": ["인터넷 연결", "가상의 연습 자료", "PC 또는 스마트폰"],
        "estimated_minutes": 180,
        "steps": lesson.get("student", {}).get("follow_along") or ["예상하기", "직접 실행하기", "결과 검증하기", "배운 점 설명하기"],
        "prerequisites": {"account": "optional", "cost": "free", "equipment": "스마트폰 또는 PC"},
        "device_paths": {key: value for key, value in device_steps(topic, practice).items() if key in profile["device_paths"]},
        "success_signal": "AI 답변의 확인할 사실 하나와 근거 출처를 자신의 말로 설명할 수 있습니다.",
        "recovery_steps": ["인터넷 연결을 확인하고 브라우저로 다시 시도합니다.", "메뉴가 다르면 공식 도움말에서 현재 화면을 확인합니다.", "계정·기기 문제는 강사 시연 또는 인쇄 절차로 대체합니다."],
        "safety": {"risk_level": "green", "personal_data": "실명·얼굴·연락처·학교/회사 자료는 입력하지 않습니다.", "sample_data": "가상의 일정, 가상의 여행 계획, 가상의 문장만 사용합니다."},
        "sources": [{"source_id": int(source_id), "title": f"선택 자료 #{int(source_id)}", "url": "", "checked_at": datetime.now().date().isoformat()} for source_id in (source_ids or [])] or [{"source_id": None, "title": "서비스 공식 도움말 또는 공식 웹페이지", "url": "", "checked_at": datetime.now().date().isoformat()}],
        "source_ids": [int(source_id) for source_id in (source_ids or [])],
        "instructor_notes": lesson.get("teacher", {}).get("verification_points") or ["시범 후 학습자가 직접 실행했는지 확인합니다.", "사실·출처 검증을 말로 설명하게 합니다."],
    }
    return lesson


def quality_report(lesson: dict) -> dict:
    issues: list[dict] = []
    student, teacher, design = lesson.get("student", {}), lesson.get("teacher", {}), lesson.get("learning_design", {})
    required = {"학생용 이야기": student.get("story"), "학습 목표": student.get("goals"), "강사용 목표": teacher.get("teaching_goal"), "준비물": design.get("materials"), "단계": design.get("steps"), "기기별 절차": design.get("device_paths"), "성공 신호": design.get("success_signal"), "복구 절차": design.get("recovery_steps"), "안전 안내": design.get("safety"), "강사 안내": design.get("instructor_notes"), "출처": design.get("sources")}
    for label, value in required.items():
        if not value: issues.append({"severity": "critical", "field": label, "message": "필수 교육 콘텐츠가 비어 있습니다."})
    goals = student.get("goals") or []
    if len(goals) > 3: issues.append({"severity": "major", "field": "학습 목표", "message": "한 차시 목표는 3개 이하여야 합니다."})
    teacher_goals = teacher.get("teaching_goal") or []
    if isinstance(teacher_goals, str): teacher_goals = [teacher_goals]
    goal_words = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", " ".join(map(str, goals)).lower()))
    teacher_words = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", " ".join(map(str, teacher_goals)).lower()))
    if goals and teacher_goals and not (goal_words & teacher_words):
        issues.append({"severity": "major", "field": "학생·강사 목표", "message": "학생용 목표와 강사용 목표의 핵심 내용이 일치하지 않습니다."})
    safety = design.get("safety") or {}
    if safety.get("risk_level") not in RISK_LEVELS or not safety.get("sample_data"):
        issues.append({"severity": "critical", "field": "안전", "message": "위험도와 가상 데이터가 필요합니다."})
    sources = design.get("sources") or []
    for source in sources:
        if not source.get("checked_at"):
            issues.append({"severity": "critical", "field": "출처", "message": "현재 정보 출처에는 확인일이 필요합니다."})
    exercises = lesson.get("exercises") or []
    if len(exercises) != 7:
        issues.append({"severity": "major", "field": "실습", "message": "핵심 3·선택 3·도전 1, 총 7개 실습이 필요합니다."})
    for item in exercises:
        if not all(item.get(key) for key in ("task", "steps", "expected_result", "verification")):
            issues.append({"severity": "critical", "field": "실습", "message": f"실습 {item.get('no', '?')}의 필수 필드가 비어 있습니다."})
        if any(re.search(r'\b(reason|expected_result|verification)\s*["\']?\s*:', str(step), re.I) for step in item.get("steps", [])):
            issues.append({"severity": "critical", "field": "실습", "message": f"실습 {item.get('no', '?')} 단계에 JSON 필드 조각이 남아 있습니다."})
    score = max(0, 100 - 25 * sum(issue["severity"] == "critical" for issue in issues) - 8 * sum(issue["severity"] == "major" for issue in issues))
    publishable = not any(issue["severity"] == "critical" for issue in issues) and score >= 85
    return {"score": score, "publishable": publishable, "validation_status": "needs_review" if publishable else "validation_failed",
            "issues": issues, "checked_at": datetime.now().isoformat(timespec="seconds"),
            "checks": {"schema": not any(x["field"] in {"학생용 이야기", "학습 목표", "강사용 목표"} for x in issues), "safety": not any(x["field"] == "안전" for x in issues), "accessibility": True, "devices": bool(design.get("device_paths")), "objective_alignment": not any(x["field"] == "학생·강사 목표" for x in issues), "factual": "instructor_review_required", "instructor_approval": "pending"}}


def require_publishable(report: dict) -> None:
    if not report["publishable"]:
        details = "; ".join(issue["message"] for issue in report["issues"][:3])
        raise HTTPException(422, f"교육 품질 검사에서 출판이 차단되었습니다: {details}")


def save_lesson_unit(book_id: int, lesson: dict, profile: dict, report: dict) -> None:
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO lesson_units(book_id,week,audience,profile_json,content_json,qa_json,approval_status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (book_id, lesson["week"], profile["audience"], json.dumps(profile, ensure_ascii=False), json.dumps(lesson, ensure_ascii=False), json.dumps(report, ensure_ascii=False), "pending", datetime.now().isoformat(timespec="seconds")))


def lesson_quality(book_id: int, week: int) -> dict | None:
    with connect() as conn: row = conn.execute("SELECT * FROM lesson_units WHERE book_id=? AND week=?", (book_id, week)).fetchone()
    return dict(row) if row else None


def load_lesson_unit(book_id: int, week: int) -> dict | None:
    """Load one lesson as an independent, parsed data-model record."""
    row = lesson_quality(book_id, week)
    if not row:
        return None
    for field in ("profile_json", "content_json", "qa_json"):
        row[field[:-5]] = json.loads(row.pop(field))
    return row


def set_approval(book_id: int, week: int, approved: bool, reviewer: str, note: str) -> dict:
    status = "approved" if approved else "changes_requested"
    if approved:
        record = lesson_quality(book_id, week)
        if not record:
            raise HTTPException(404, "검수할 차시를 찾을 수 없습니다.")
        try:
            report = json.loads(record.get("qa_json") or "{}")
        except json.JSONDecodeError:
            report = {}
        if report.get("validation_status") != "needs_review" or not report.get("publishable"):
            raise HTTPException(422, "품질 검사를 통과하지 못한 차시는 승인할 수 없습니다.")
    with connect() as conn:
        cur = conn.execute("UPDATE lesson_units SET approval_status=?, approved_at=? WHERE book_id=? AND week=?", (status, datetime.now().isoformat(timespec="seconds"), book_id, week))
        if not cur.rowcount: raise HTTPException(404, "검수할 차시를 찾을 수 없습니다.")
    return {"book_id": book_id, "week": week, "approval_status": status, "reviewer": reviewer, "note": note}

from studio.services.education_quality import enrich_lesson, load_lesson_unit, quality_report, save_lesson_unit
from studio.db import init_db


def _lesson():
    return {
        "topic": "AI 기초",
        "student": {"story": "이야기", "goals": ["AI 개념을 설명한다", "직접 실행한다"], "follow_along": ["예상", "실행", "검증"]},
        "teacher": {"teaching_goal": ["핵심 개념을 설명하고 직접 실행하게 한다"], "verification_points": ["검증 여부 확인"]},
        "exercises": [{"no": i, "task": "과제", "steps": ["하나", "둘", "셋"], "expected_result": "결과", "verification": "확인"} for i in range(1, 8)],
    }


def test_lesson_model_contains_independent_learning_design_fields():
    lesson = enrich_lesson(_lesson(), {"audience": "성인", "experience": "처음", "device_paths": ["pc_web"]}, "AI 연습", [12])
    design = lesson["learning_design"]
    assert design["estimated_minutes"] == 180
    assert design["materials"] and design["steps"] and design["instructor_notes"]
    assert design["source_ids"] == [12] and design["sources"][0]["source_id"] == 12
    assert quality_report(lesson)["checks"]["objective_alignment"] is True


def test_quality_report_blocks_student_teacher_objective_mismatch():
    lesson = enrich_lesson(_lesson(), {"audience": "성인", "experience": "처음", "device_paths": ["pc_web"]}, "AI 연습")
    lesson["teacher"]["teaching_goal"] = ["완전히 다른 주제의 역사 연표를 암기한다"]
    report = quality_report(lesson)
    assert report["checks"]["objective_alignment"] is False
    assert any(issue["field"] == "학생·강사 목표" for issue in report["issues"])


def test_lesson_unit_round_trips_as_independent_record():
    init_db()
    lesson = enrich_lesson(_lesson(), {"audience": "성인", "experience": "처음", "device_paths": ["pc_web"]}, "AI 연습", [12])
    lesson["week"] = 3
    profile = {"audience": "성인", "experience": "처음", "device_paths": ["pc_web"], "source_ids": [12]}
    save_lesson_unit(901, lesson, profile, quality_report(lesson))
    loaded = load_lesson_unit(901, 3)
    assert loaded and loaded["content"]["week"] == 3
    assert loaded["profile"]["source_ids"] == [12]

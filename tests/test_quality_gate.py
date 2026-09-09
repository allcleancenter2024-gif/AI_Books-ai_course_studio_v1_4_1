from studio.services.education_quality import enrich_lesson, quality_report


def _valid_lesson():
    lesson = {
        "topic": "AI 기초",
        "student": {"story": "이야기", "goals": ["개념을 설명한다"]},
        "teacher": {"teaching_goal": ["개념을 설명하게 한다"]},
        "exercises": [{"no": i, "task": "과제", "steps": ["하나", "둘", "셋"], "expected_result": "결과", "verification": "확인"} for i in range(1, 8)],
    }
    return enrich_lesson(lesson, {"audience": "성인", "experience": "처음", "device_paths": ["pc_web"]}, "AI 연습")


def test_quality_report_has_explicit_validation_state():
    report = quality_report(_valid_lesson())
    assert report["publishable"] is True
    assert report["validation_status"] == "needs_review"


def test_quality_failure_is_blocked_before_approval():
    lesson = _valid_lesson()
    lesson["learning_design"]["safety"] = {}
    report = quality_report(lesson)
    assert report["publishable"] is False
    assert report["validation_status"] == "validation_failed"

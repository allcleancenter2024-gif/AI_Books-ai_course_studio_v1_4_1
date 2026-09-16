"""Course-to-tool candidate discovery and human-approved linking."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from ..repositories.course_tool_reference_repository import CourseToolReferenceRepository
from ..repositories.learning_repository import LearningRepository


class CourseToolReferenceService:
    def __init__(self, repository=None, learning=None):
        self._repository = repository or CourseToolReferenceRepository()
        self._learning = learning or LearningRepository()

    def candidates(self, course_id: int) -> list[dict]:
        course = self._repository.course(course_id)
        if not course:
            raise HTTPException(404, "Course를 찾을 수 없습니다.")
        result = []
        for tool in self._learning.list_tools():
            matches = self._repository.candidate_lessons(course_id, tool["name_ko"])
            if matches:
                result.append({"tool_id": tool["id"], "tool_name": tool["name_ko"], "matches": matches, "requires_approval": True})
        return result

    def references(self, course_id: int) -> list[dict]:
        if not self._repository.course(course_id):
            raise HTTPException(404, "Course를 찾을 수 없습니다.")
        return self._repository.list_references(course_id)

    def add(self, course_id: int, tool_id: str, week_id: int | None, lesson_id: int | None, actor: str) -> dict:
        if not self._repository.course(course_id):
            raise HTTPException(404, "Course를 찾을 수 없습니다.")
        if not self._repository.tool_exists(tool_id):
            raise HTTPException(404, "학습 도구를 찾을 수 없습니다.")
        reference_id = f"course-tool-ref-{uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        self._repository.add_reference((reference_id, course_id, week_id, lesson_id, tool_id, "human_approved", "APPROVED", now))
        return {"reference_id": reference_id, "course_id": course_id, "tool_id": tool_id, "status": "APPROVED", "approved_by": actor}

    def scan(self, course_id: int, actor: str, tool_id: str | None = None) -> dict:
        if not self._repository.course(course_id):
            raise HTTPException(404, "Course를 찾을 수 없습니다.")
        matches = 0
        suggestions = 0
        now = datetime.now(timezone.utc).isoformat()
        for item in self._repository.scan_inputs(course_id, tool_id):
            for lesson in self._repository.lessons_for_scan(course_id, item.get("week_id"), item.get("lesson_id")):
                text = " ".join(str(lesson.get(key) or "") for key in ("topic", "student_text", "teacher_text"))
                needle = item["name_ko"]
                if needle not in text:
                    continue
                fingerprint = sha256(f"{course_id}|{item['tool_id']}|{item['update_event_id']}|{lesson['id']}|{needle}".encode()).hexdigest()[:24]
                match_id = f"match-{fingerprint}"
                suggestion_id = f"suggestion-{fingerprint}"
                self._repository.record_scan(
                    (match_id, course_id, item["tool_id"], item["update_event_id"], lesson["week"], lesson["id"], needle, text[:500], now),
                    (suggestion_id, course_id, lesson["week"], lesson["id"], item["tool_id"], match_id, needle, item["update_summary"], "검증된 업데이트 이벤트와 연결된 텍스트입니다. 사람의 검토가 필요합니다.", "MEDIUM", item.get("source_evidence_id"), now),
                )
                matches += 1
                suggestions += 1
        return {"course_id": course_id, "matches_created": matches, "suggestions_created": suggestions, "original_course_changed": False, "scanned_by": actor}


course_tool_reference_service = CourseToolReferenceService()

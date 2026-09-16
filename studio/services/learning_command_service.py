"""Human-approved command operations; never overwrite original Course data."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from ..repositories.learning_command_repository import LearningCommandRepository


class LearningCommandService:
    def __init__(self, repository: LearningCommandRepository | None = None):
        self._repository = repository or LearningCommandRepository()

    def decide(self, suggestion_id: str, decision: str, reviewer: str, reason: str) -> dict:
        suggestion = self._repository.get_suggestion(suggestion_id)
        if not suggestion:
            raise HTTPException(404, "업데이트 제안을 찾을 수 없습니다.")
        if suggestion.get("status") not in {"PENDING", "DEFERRED"}:
            raise HTTPException(409, "이미 처리된 업데이트 제안입니다.")
        now = datetime.now(timezone.utc).isoformat()
        source_version = f"course-{suggestion['course_id']}-original"
        target_version = f"course-{suggestion['course_id']}-{uuid4().hex[:12]}"
        self._repository.save_decision(suggestion_id, decision, reviewer, now, reason, source_version, target_version)
        self._repository.audit((
            f"audit_{uuid4().hex}", "suggestion_decision", reviewer, suggestion["course_id"],
            suggestion.get("tool_id"), source_version, target_version, decision, now,
            suggestion.get("source_evidence_id"), "recorded",
        ))
        return {"suggestion_id": suggestion_id, "decision": decision, "status": "recorded", "reviewed_at": now}

    def apply(self, suggestion_id: str, reviewer: str, reason: str) -> dict:
        suggestion = self._repository.get_suggestion(suggestion_id)
        if not suggestion:
            raise HTTPException(404, "업데이트 제안을 찾을 수 없습니다.")
        if suggestion.get("status") != "APPROVED":
            if suggestion.get("status") == "APPLIED":
                raise HTTPException(409, "이미 Course Version으로 적용된 제안입니다.")
            raise HTTPException(409, "승인된 제안만 새 Course Version으로 적용할 수 있습니다.")
        course = self._repository.course(int(suggestion["course_id"]))
        if not course:
            raise HTTPException(404, "원본 Course를 찾을 수 없습니다.")
        now = datetime.now(timezone.utc).isoformat()
        version_id = f"course-version-{uuid4().hex}"
        version_label = f"{suggestion['course_id']}.reviewed.{now[:10]}"
        content = json.loads(course.get("data_json") or "{}")
        content["_learning_update"] = {
            "suggestion_id": suggestion_id,
            "matched_text": suggestion.get("matched_text", ""),
            "suggested_text": suggestion.get("suggested_text", ""),
            "decision": "approved_for_version",
        }
        self._repository.create_version((
            version_id, course["id"], f"course-{course['id']}-original", version_label,
            json.dumps(content, ensure_ascii=False), now, reviewer, reason, "DRAFT",
        ))
        self._repository.mark_applied(suggestion_id)
        self._repository.audit((
            f"audit_{uuid4().hex}", "course_version_created", reviewer, course["id"],
            suggestion.get("tool_id"), f"course-{course['id']}-original", version_label,
            "APPLY", now, suggestion.get("source_evidence_id"), "version_created",
        ))
        return {"version_id": version_id, "course_id": course["id"], "version_label": version_label, "original_preserved": True}


learning_command_service = LearningCommandService()

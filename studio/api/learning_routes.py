"""Authenticated, read-only Learning Center API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_admin, require_authenticated
from ..config import FEATURE_AI_TOOL_LEARNING_CENTER
from ..schemas import CourseScanRequest, CourseToolReferenceRequest, UpdateApplyRequest, UpdateDecisionRequest
from ..services.course_tool_reference_service import course_tool_reference_service
from ..services.learning_command_service import learning_command_service
from ..services.learning_service import LearningService

router = APIRouter(prefix="/api/learning-tools", dependencies=[Depends(require_authenticated)])
command_router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])
service = LearningService()


def feature_enabled() -> None:
    if not FEATURE_AI_TOOL_LEARNING_CENTER:
        raise HTTPException(404, "AI 도구 학습관이 비활성화되어 있습니다.")


def _limit(value: int) -> int:
    return value


@router.get("")
def list_tools(limit: int = Query(default=50, ge=1, le=100), _: None = Depends(feature_enabled)):
    return service.list_tools()[:_limit(limit)]


@router.get("/{tool_id}")
def get_tool(tool_id: str, _: None = Depends(feature_enabled)):
    result = service.get_tool(tool_id)
    if result is None:
        raise HTTPException(404, "학습 도구를 찾을 수 없습니다.")
    return result


def _resource(table: str, order_by: str, tool_id: str, limit: int) -> list[dict]:
    result = service.resource(tool_id, table, order_by)
    if result is None:
        raise HTTPException(404, "학습 도구를 찾을 수 없습니다.")
    return result[:limit]


@router.get("/{tool_id}/timeline")
def timeline(tool_id: str, limit: int = Query(default=100, ge=1, le=200), _: None = Depends(feature_enabled)):
    return _resource("timeline_events", "event_date ASC, id", tool_id, limit)


@router.get("/{tool_id}/prompts")
def prompts(tool_id: str, limit: int = Query(default=100, ge=1, le=200), _: None = Depends(feature_enabled)):
    return _resource("prompt_examples", "level, example_no", tool_id, limit)


@router.get("/{tool_id}/modern-prompts")
def modern_prompts(tool_id: str, limit: int = Query(default=20, ge=1, le=50), _: None = Depends(feature_enabled)):
    return _resource("modern_prompt_examples", "effective_from DESC, modern_prompt_id", tool_id, limit)


@router.get("/{tool_id}/sources")
def sources(tool_id: str, limit: int = Query(default=50, ge=1, le=100), _: None = Depends(feature_enabled)):
    return _resource("source_evidence", "checked_at DESC, id", tool_id, limit)


@router.get("/{tool_id}/updates")
def updates(tool_id: str, limit: int = Query(default=50, ge=1, le=100), _: None = Depends(feature_enabled)):
    return _resource("update_events", "checked_at DESC, id", tool_id, limit)


@command_router.get("/courses/{course_id}/update-suggestions")
def course_suggestions(course_id: int, limit: int = Query(default=100, ge=1, le=200), _: None = Depends(feature_enabled)):
    return learning_command_service._repository.list_suggestions(course_id, limit)


@command_router.get("/courses/{course_id}/versions")
def course_versions(course_id: int, limit: int = Query(default=50, ge=1, le=100), _: None = Depends(feature_enabled)):
    return learning_command_service._repository.list_versions(course_id, limit)


@command_router.get("/courses/{course_id}/tool-references/candidates")
def tool_reference_candidates(course_id: int, _: None = Depends(feature_enabled)):
    return course_tool_reference_service.candidates(course_id)


@command_router.get("/courses/{course_id}/tool-references")
def tool_references(course_id: int, _: None = Depends(feature_enabled)):
    return course_tool_reference_service.references(course_id)


@command_router.post("/courses/{course_id}/tool-references", status_code=201)
def add_tool_reference(course_id: int, req: CourseToolReferenceRequest, _: None = Depends(feature_enabled), __: dict = Depends(require_admin)):
    return course_tool_reference_service.add(course_id, req.tool_id, req.week_id, req.lesson_id, __["username"])


@command_router.post("/courses/{course_id}/scan-updates")
def scan_updates(course_id: int, req: CourseScanRequest = CourseScanRequest(), _: None = Depends(feature_enabled), __: dict = Depends(require_admin)):
    return course_tool_reference_service.scan(course_id, __["username"], req.tool_id)


@command_router.post("/update-suggestions/{suggestion_id}/approve")
def approve_suggestion(suggestion_id: str, req: UpdateDecisionRequest, _: None = Depends(feature_enabled), __: dict = Depends(require_admin)):
    if req.decision not in {"PARTIAL_APPLY", "FULL_APPLY"}:
        raise HTTPException(422, "승인 API에는 PARTIAL_APPLY 또는 FULL_APPLY만 사용할 수 있습니다.")
    return learning_command_service.decide(suggestion_id, req.decision, req.reviewer, req.reason)


@command_router.post("/update-suggestions/{suggestion_id}/reject")
def reject_suggestion(suggestion_id: str, req: UpdateDecisionRequest, _: None = Depends(feature_enabled), __: dict = Depends(require_admin)):
    if req.decision not in {"KEEP", "REJECT", "DEFER"}:
        raise HTTPException(422, "거절 API에는 KEEP, REJECT 또는 DEFER만 사용할 수 있습니다.")
    return learning_command_service.decide(suggestion_id, req.decision, req.reviewer, req.reason)


@command_router.post("/update-suggestions/{suggestion_id}/apply")
def apply_suggestion(suggestion_id: str, req: UpdateApplyRequest, _: None = Depends(feature_enabled), __: dict = Depends(require_admin)):
    return learning_command_service.apply(suggestion_id, req.reviewer, req.reason)

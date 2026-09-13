"""Authenticated, read-only endpoints for the optional agent gateway."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from providers.agents.hermes import HermesIntegrationError
from ..schemas import AgentRagSearchRequest, AgentSkillTaskRequest, AgentTaskRequest
from ..services.agent_service import agent_service
from ..services.agent_draft_service import agent_draft_service
from ..services.agent_skills import build_skill_prompt, list_skills
from ..services.agent_job_service import agent_jobs

router = APIRouter(prefix="/api/agent", dependencies=[Depends(require_admin)])


@router.get("/health")
def agent_health():
    return agent_service.health()


@router.get("/capabilities")
def agent_capabilities():
    return agent_service.capabilities()


@router.get("/tools/course-materials")
def agent_course_materials():
    return {"items": agent_service.list_course_materials(), "read_only": True}


@router.get("/tools/course-materials/{book_id}")
def agent_course_outline(book_id: int):
    item = agent_service.course_outline(book_id)
    if not item:
        raise HTTPException(404, "교재를 찾을 수 없습니다.")
    return {"item": item, "read_only": True}


@router.post("/tools/rag/search")
def agent_rag_search(req: AgentRagSearchRequest):
    return {
        "items": agent_service.search_course_knowledge(req.source_ids, req.query, req.max_total),
        "read_only": True,
    }


def _agent_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, HermesIntegrationError):
        return HTTPException(503, str(exc))
    return HTTPException(423, "Hermes agent is disabled")


@router.post("/tasks", status_code=202)
def agent_task_start(req: AgentTaskRequest):
    try:
        return agent_service.run_task(req.prompt, req.idempotency_key)
    except Exception as exc:
        raise _agent_failure(exc) from exc


@router.get("/skills")
def agent_skills():
    return {"items": list_skills(), "read_only": True, "subagents_enabled": False}


@router.post("/skills/run", status_code=202)
def agent_skill_start(req: AgentSkillTaskRequest):
    try:
        return agent_jobs.start(build_skill_prompt(req.skill_id, req.request), req.idempotency_key, req.job_id)
    except KeyError as exc:
        raise HTTPException(404, "알 수 없는 Hermes Skill입니다.") from exc
    except Exception as exc:
        raise _agent_failure(exc) from exc


@router.get("/jobs/{job_id}")
def agent_job_status(job_id: str):
    job = agent_jobs.get(job_id)
    if not job or (job.get("payload") or {}).get("kind") != "agent_task":
        raise HTTPException(404, "Agent 작업 상태를 찾을 수 없습니다.")
    return job


@router.post("/jobs/{job_id}/cancel")
def agent_job_cancel(job_id: str):
    job = agent_jobs.cancel(job_id)
    if not job:
        raise HTTPException(404, "Agent 작업 상태를 찾을 수 없습니다.")
    return job


@router.get("/tasks/{task_id}")
def agent_task_status(task_id: str):
    try:
        return agent_service.get_task_status(task_id)
    except Exception as exc:
        raise _agent_failure(exc) from exc


@router.post("/tasks/{task_id}/cancel")
def agent_task_cancel(task_id: str):
    try:
        return agent_service.cancel_task(task_id)
    except Exception as exc:
        raise _agent_failure(exc) from exc


@router.post("/tasks/{task_id}/draft", status_code=201)
def agent_task_to_draft(task_id: str):
    return agent_draft_service.capture_completed_task(task_id)


@router.get("/drafts")
def agent_drafts():
    return {"items": agent_draft_service.list_recent()}


@router.get("/drafts/{draft_id}")
def agent_draft(draft_id: str):
    return agent_draft_service.get(draft_id)

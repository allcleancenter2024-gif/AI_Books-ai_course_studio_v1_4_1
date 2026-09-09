"""Protected reference-source ingestion, summarization, and export endpoints."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..auth import require_authenticated
from ..config import SOURCE_PACKS_DIR
from ..schemas import SourceIdsRequest, SourceSummaryRequest, VideoSourceRequest, WebSourceRequest
from ..services.generation_service import providers
from ..services.job_status import jobs
from ..services.source_service import add_video, add_web, delete_source, list_sources, make_source_pack, refresh_video_transcript, refresh_web_sources, save_upload, start_source_summary, summary_file

router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])

@router.get("/sources")
def sources_list(): return list_sources()

@router.post("/sources/upload")
def source_upload(file: UploadFile = File(...), job_id: str = Form(...), declared_size: int = Form(0), idempotency_key: str = Form('')): return save_upload(file, job_id, declared_size, idempotency_key)

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    value = jobs.get(job_id)
    if not value: raise HTTPException(404, "작업 상태를 찾을 수 없습니다.")
    return value

@router.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    value = jobs.cancel(job_id)
    if not value:
        raise HTTPException(404, "작업 상태를 찾을 수 없습니다.")
    return value

@router.post("/sources/web")
def source_web(req: WebSourceRequest): return add_web(req.url, req.title)

@router.post("/sources/video")
def source_video(req: VideoSourceRequest): return add_video(req.url, req.title)

@router.post("/sources/{source_id}/video-transcript")
def source_video_transcript(source_id: int): return refresh_video_transcript(source_id)

@router.post("/sources/refresh")
def source_refresh(req: SourceIdsRequest): return refresh_web_sources(req.source_ids, force=True)

@router.delete("/sources/{source_id}")
def source_delete(source_id: int): return delete_source(source_id)

@router.post("/sources/summary", status_code=202)
def source_summary(req: SourceSummaryRequest):
    try: return start_source_summary(req.source_id, providers, req.provider, req.job_id)
    except Exception as exc:
        if isinstance(exc, HTTPException): raise
        raise HTTPException(502, str(exc))

@router.get("/sources/{source_id}/summary-file")
def source_summary_download(source_id: int):
    path = summary_file(source_id)
    return FileResponse(path, filename=path.name, media_type="text/markdown")

@router.post("/sources/pack")
def source_pack(req: SourceIdsRequest): return make_source_pack(req.source_ids)

@router.get("/sources/pack/{filename}")
def source_pack_download(filename: str):
    path = SOURCE_PACKS_DIR / Path(filename).name
    if not path.exists(): raise HTTPException(404, "자료팩을 찾을 수 없습니다.")
    return FileResponse(path, filename=path.name, media_type="application/zip")

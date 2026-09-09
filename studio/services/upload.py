from __future__ import annotations

import mimetypes
import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .job_status import jobs
from .parsers import ALLOWED_EXTENSIONS, parse_file
from .storage import destination_for, safe_name, stream_upload


def stage_upload(file: UploadFile, job_id: str, declared_size: int) -> tuple[str, Path, int, str, str]:
    """Persist the request body; parsing is deliberately performed by a worker."""
    name = safe_name(file.filename or "source")
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "지원 파일: md, markdown, txt, html, pdf, pptx, png, jpg, jpeg, webp")
    destination = destination_for(name)
    try:
        size = stream_upload(file, destination, job_id, declared_size)
        mime = file.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
        return name, destination, size, ext, mime
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_staged_upload(name: str, destination: Path, size: int, ext: str, mime: str, job_id: str, insert) -> dict | None:
    """Parse a staged upload outside the browser request lifetime."""
    try:
        if jobs.is_cancelled(job_id):
            return None
        jobs.update(job_id, phase="parsing", message="파일 내용을 분석하는 중", progress=60)

        def on_progress(current, total, message):
            if jobs.is_cancelled(job_id):
                return
            jobs.update(job_id, message=message, progress=60 + int(35 * current / max(total, 1)))

        text, meta = parse_file(destination, on_progress)
        if jobs.is_cancelled(job_id):
            return None
        meta.update(size=size, extraction="bounded-stream")
        kind = "image" if ext in {".png", ".jpg", ".jpeg", ".webp"} else "file"
        # The temporary original is needed only while parsing. Keep compact,
        # extracted text and metadata in SQLite instead of retaining a second copy.
        meta.update(original_retained=False, storage_note="원본 파일은 분석 후 제거되고 텍스트·메타데이터·벡터만 DB에 저장됩니다.")
        result = insert(kind, name, name, "", mime, "", text, meta, "ready" if text else "needs_review")
        jobs.update(job_id, phase="complete", message="업로드와 분석 완료", progress=100, bytes_done=size, bytes_total=size)
        return result
    except Exception as exc:
        if not jobs.is_cancelled(job_id):
            jobs.update(job_id, phase="error", message="처리 실패", progress=100, error=str(getattr(exc, "detail", exc)))
        raise
    finally:
        destination.unlink(missing_ok=True)


def receive_and_parse(file: UploadFile, job_id: str, declared_size: int, insert) -> dict:
    """Compatibility helper for callers that intentionally require sync work."""
    name, destination, size, ext, mime = stage_upload(file, job_id, declared_size)
    result = parse_staged_upload(name, destination, size, ext, mime, job_id, insert)
    if result is None:
        raise HTTPException(409, "업로드 처리가 취소되었습니다.")
    return result

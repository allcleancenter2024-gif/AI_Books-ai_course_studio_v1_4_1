from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES, UPLOADS_DIR
from .job_status import jobs


def safe_name(name: str) -> str:
    base = Path(name or "source").name
    return re.sub(r"[^0-9A-Za-z가-힣._ -]+", "_", base)[:140]


def destination_for(name: str) -> Path:
    return UPLOADS_DIR / f"{uuid.uuid4().hex[:10]}_{safe_name(name)}"


def stream_upload(file: UploadFile, destination: Path, job_id: str, declared_size: int = 0) -> int:
    if declared_size > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "파일이 500MB 제한을 초과합니다. 파일을 나누거나 압축 크기를 줄여 주세요.")
    written = 0
    jobs.update(job_id, phase="uploading", message="파일을 안전하게 저장하는 중", bytes_total=declared_size, progress=2)
    try:
        with destination.open("xb") as output:
            while True:
                chunk = file.file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "파일이 500MB 제한을 초과했습니다. 저장된 임시 파일은 제거했습니다.")
                output.write(chunk)
                pct = min(55, 2 + int(53 * written / max(declared_size, written, 1)))
                jobs.update(job_id, bytes_done=written, bytes_total=max(declared_size, written), progress=pct)
        return written
    except Exception:
        destination.unlink(missing_ok=True)
        raise

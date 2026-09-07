from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_authenticated
from ..services.github_backup_service import status, upload_backup
router = APIRouter(prefix="/api/github", dependencies=[Depends(require_authenticated)])
@router.get("/status")
def github_status(): return status()
@router.post("/backup")
def github_backup():
    try: return upload_backup()
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc

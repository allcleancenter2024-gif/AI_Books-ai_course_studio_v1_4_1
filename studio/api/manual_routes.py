"""Protected operational manual update analysis and PDF endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..auth import require_authenticated
from ..schemas import ManualPDFRequest
from ..services.manual_service import apply_manual_updates, create_manual_pdf, manual_update_status

router = APIRouter(prefix="/api/manual", dependencies=[Depends(require_authenticated)])

@router.get("/updates")
def updates(): return manual_update_status()

@router.post("/updates/apply")
def apply_updates(): return apply_manual_updates()

@router.post("/pdf")
def manual_pdf(request: ManualPDFRequest):
    path = create_manual_pdf(request)
    return FileResponse(path, filename=path.name, media_type="application/pdf")

"""Protected local AI provider configuration and connectivity endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_authenticated
from ..schemas import ProviderConfigRequest, ProviderTestRequest
from ..services.generation_service import providers

router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])

@router.get("/providers")
def get_providers(): return providers.list_public()

@router.post("/providers/config")
def configure_provider(req: ProviderConfigRequest):
    providers.configure(req.provider, model=req.model, base_url=req.base_url, api_key=req.api_key, timeout=req.timeout)
    return {"ok": True}

@router.post("/providers/test")
def test_provider(req: ProviderTestRequest):
    try: return providers.test(req.provider)
    except Exception as exc: raise HTTPException(502, str(exc))

@router.get("/providers/{provider}/models")
def provider_models(provider: str):
    try: return {"models": providers.list_models(provider, strict=True)}
    except Exception as exc: raise HTTPException(502, str(exc))

@router.post("/providers/{provider}/auto-connect")
def provider_auto_connect(provider: str):
    try: return providers.auto_connect(provider)
    except Exception as exc: raise HTTPException(502, str(exc))

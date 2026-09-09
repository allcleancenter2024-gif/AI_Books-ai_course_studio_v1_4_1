"""Protected local AI provider configuration and connectivity endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from providers.errors import ProviderError
from ..auth import require_authenticated
from ..schemas import ProviderConfigRequest, ProviderTestRequest
from ..services.generation_service import providers
from ..services.provider_service import ProviderService

provider_service = ProviderService(providers)

router = APIRouter(prefix="/api", dependencies=[Depends(require_authenticated)])


def _provider_failure(exc: Exception) -> HTTPException:
    """Expose a stable, safe provider error contract without internal details."""
    if isinstance(exc, ProviderError):
        return HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": str(exc)},
        )
    logging.getLogger(__name__).warning("Provider endpoint failed: %s", type(exc).__name__)
    return HTTPException(
        status_code=502,
        detail={"code": "provider_request_failed", "message": "Provider 요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요."},
    )

@router.get("/providers")
def get_providers(): return provider_service.list_public()

@router.post("/providers/config")
def configure_provider(req: ProviderConfigRequest):
    try:
        provider_service.configure(req.provider, model=req.model, base_url=req.base_url, api_key=req.api_key, timeout=req.timeout)
    except Exception as exc:
        raise _provider_failure(exc) from exc
    return {"ok": True}

@router.post("/providers/test")
def test_provider(req: ProviderTestRequest):
    try: return provider_service.test(req.provider)
    except Exception as exc: raise _provider_failure(exc) from exc

@router.get("/providers/{provider}/models")
def provider_models(provider: str):
    try: return {"models": provider_service.list_models(provider)}
    except Exception as exc: raise _provider_failure(exc) from exc

@router.get("/providers/{provider}/health")
def provider_health(provider: str):
    try: return provider_service.probe_health(provider)
    except Exception as exc: raise _provider_failure(exc) from exc

@router.post("/providers/{provider}/auto-connect")
def provider_auto_connect(provider: str):
    try: return provider_service.auto_connect(provider)
    except Exception as exc: raise _provider_failure(exc) from exc

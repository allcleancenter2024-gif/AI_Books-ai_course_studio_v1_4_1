"""Opt-in adaptive RAG endpoints; local mode remains the default."""
from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_authenticated
from ..schemas import HybridEvaluateRequest, HybridSearchRequest
from ..services.evidence_router import evaluate_materials
from ..services.evidence_pack import build_evidence_pack, get_evidence_pack, evidence_quality
from ..services.web_search import SearchOptions, build_search_provider

router = APIRouter(prefix="/api/hybrid", dependencies=[Depends(require_authenticated)])

@router.post("/evaluate")
def evaluate(req: HybridEvaluateRequest):
    return evaluate_materials(req.topic, req.audience, req.source_ids).__dict__

@router.post("/search")
def search(req: HybridSearchRequest):
    if req.generation_mode == "local_only" or req.web_scope == "disabled":
        return {"status": "disabled", "items": [], "message": "완전 로컬 모드에서는 웹 검색을 실행하지 않습니다."}
    high_quality = req.web_scope == "high_quality"
    provider = build_search_provider(high_quality=high_quality)
    if provider.name == "disabled":
        return {"status": "disabled", "items": [], "message": "웹 검색 API 키가 없어 로컬 RAG로 계속 진행합니다."}
    try:
        results = provider.search(req.topic, SearchOptions(max_results=req.max_results, freshness_days=req.freshness_days, high_quality=high_quality))
        allowed = ("A",) if req.web_scope == "official_only" else ("A", "B", "C") if req.web_scope == "include_educational_video" else ("A", "B")
        return build_evidence_pack(req.topic, results, provider, max_items=5, allowed_grades=allowed)
    except Exception as exc:
        return {"status": "fallback_local", "items": [], "message": f"웹 근거 수집에 실패하여 로컬 RAG로 계속 진행합니다: {type(exc).__name__}"}

@router.get("/health")
def health(high_quality: bool = False): return build_search_provider(high_quality=high_quality).health_check()

@router.get("/evidence-packs/{pack_id}")
def evidence_pack(pack_id: int):
    pack = get_evidence_pack(pack_id)
    if not pack: raise HTTPException(404, "근거팩을 찾을 수 없습니다.")
    return pack

@router.get("/evidence-packs/{pack_id}/quality")
def evidence_pack_quality(pack_id: int):
    pack = get_evidence_pack(pack_id)
    if not pack: raise HTTPException(404, "근거팩을 찾을 수 없습니다.")
    return evidence_quality(pack)

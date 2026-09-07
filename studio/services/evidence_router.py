"""Adaptive routing for internal sources and optional web evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from .vector_index import retrieve
from .source_service import get_source

SCORE_INTERNAL_ONLY = 75
SCORE_INTERNAL_PLUS_WEB = 40

@dataclass(frozen=True)
class EvidenceDecision:
    score: int
    status: str
    route: str
    covered_topics: list[str]
    missing_topics: list[str]
    source_ids: list[int]

def _freshness_score(source: dict) -> int:
    value = source.get("updated_at") or source.get("created_at") or ""
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)).days
    except Exception:
        return 0
    return 15 if age <= 90 else 10 if age <= 365 else 4 if age <= 730 else 0

def evaluate_materials(topic: str, audience: str = "전체 초보자", source_ids: list[int] | None = None) -> EvidenceDecision:
    ids = [int(x) for x in (source_ids or []) if int(x) > 0]
    if not ids:
        return EvidenceDecision(0, "none", "web_only", [], [topic], [])
    blocks = retrieve(ids, topic, max_total=24_000, per_source=8_000)
    joined = " ".join(block.get("text", "") for block in blocks).lower()
    terms = [term for term in re.findall(r"[0-9A-Za-z가-힣]{2,}", f"{topic} {audience}".lower()) if len(term) > 1]
    related = sum(1 for term in set(terms) if term in joined)
    relevance = min(30, int(30 * related / max(len(set(terms)), 1)))
    coverage = min(25, int(25 * min(len(blocks), 3) / 3))
    freshness = min(15, sum(_freshness_score(get_source(i)) for i in ids) // max(len(ids), 1))
    education = 15 if any(token in joined for token in ("실습", "예시", "단계", "설명")) else 7 if joined else 0
    quality = 10 if len(joined) >= 1200 else 5 if len(joined) >= 300 else 0
    citation = 5 if any(get_source(i).get("url") or get_source(i).get("original_name") for i in ids) else 0
    score = max(0, min(100, relevance + coverage + freshness + education + quality + citation))
    if score >= SCORE_INTERNAL_ONLY:
        status, route, missing = "sufficient", "internal_only", []
    elif score >= SCORE_INTERNAL_PLUS_WEB:
        status, route, missing = "partially_sufficient", "internal_plus_web", [topic]
    else:
        status, route, missing = "insufficient", "web_only", [topic]
    return EvidenceDecision(score, status, route, [topic] if score else [], missing, ids)

"""Small, attributable evidence packs built from approved web results."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import urlparse

from .web_search import SearchResult, WebSearchProvider
from .source_context import sanitize_untrusted_reference
from ..db import connect, init_db

OFFICIAL_HOSTS = (
    "who.int", "un.org", "oecd.org", "unesco.org", "docs.python.org",
    "docs.github.com", "learn.microsoft.com", "support.google.com",
    "openai.com", "anthropic.com", "searxng.org",
)
TRUSTED_HOSTS = (
    "reuters.com", "apnews.com", "nature.com", "science.org",
    "kisa.or.kr", "nia.or.kr", "keris.or.kr", "kedi.re.kr",
)


def prune_expired_evidence_packs() -> int:
    """Remove expired web evidence cache rows; source/user records are untouched."""
    init_db()
    with connect() as conn:
        cur = conn.execute("DELETE FROM evidence_packs WHERE expires_at IS NOT NULL AND expires_at <= datetime('now')")
        return cur.rowcount


def source_grade(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host.endswith((".gov", ".go.kr", ".edu", ".ac.kr", ".int")) or any(host == item or host.endswith("." + item) for item in OFFICIAL_HOSTS):
        return "A"
    if any(host == item or host.endswith("." + item) for item in TRUSTED_HOSTS):
        return "B"
    return "C"

def build_evidence_pack(topic: str, results: list[SearchResult], provider: WebSearchProvider, max_items: int = 5, allowed_grades: tuple[str, ...] = ("A", "B", "C")) -> dict:
    init_db()
    prune_expired_evidence_packs()
    items = []
    seen = set()
    for result in results:
        if result.url in seen: continue
        seen.add(result.url)
        grade = source_grade(result.url)
        if grade not in allowed_grades: continue
        try:
            try: page = provider.extract(result.url, {"source_grade": grade})
            except TypeError: page = provider.extract(result.url)
        except Exception:
            if not result.snippet.strip(): continue
            page = {"title": result.title, "url": result.url, "text": result.snippet, "publisher": urlparse(result.url).netloc, "retrieved_at": datetime.now(timezone.utc).isoformat(), "extractor": "search_snippet"}
        text = sanitize_untrusted_reference(page.get("text", "")).replace("\n", " ")
        if not text: continue
        grade = source_grade(page.get("url", result.url))
        if grade not in allowed_grades: continue
        claim = text[:320]
        topic_terms = {token.casefold() for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", topic)}
        matched = sum(term in text.casefold() for term in topic_terms)
        relevance = round(100 * matched / max(len(topic_terms), 1), 1)
        freshness = 80.0 if result.published_at else 40.0
        trust = 95.0 if grade == "A" else 80.0 if grade == "B" else 45.0
        items.append({"id": hashlib.sha256(page["url"].encode()).hexdigest()[:20], "topic": topic, "claim": claim, "evidence_summary": text[:800], "source_title": page.get("title") or result.title, "source_url": page.get("url") or result.url, "publisher": page.get("publisher", ""), "published_at": result.published_at or "", "retrieved_at": page.get("retrieved_at") or datetime.now(timezone.utc).isoformat(), "source_grade": grade, "relevance_score": relevance, "freshness_score": freshness, "trust_score": trust, "lecture_use": "핵심 설명 또는 실습 전 확인", "extractor": page.get("extractor", "unknown")})
        if len(items) >= max_items: break
    payload = {"topic": topic, "created_at": datetime.now(timezone.utc).isoformat(), "status": "ready" if items else "insufficient", "items": items}
    payload["fingerprint"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with connect() as conn:
        cur = conn.execute("INSERT INTO evidence_packs(topic,status,fingerprint,created_at,expires_at) VALUES(?,?,?,?,datetime('now','+1 day'))", (topic, payload["status"], payload["fingerprint"], payload["created_at"]))
        pack_id = cur.lastrowid
        for item in items:
            conn.execute("INSERT INTO evidence_items(pack_id,evidence_key,source_type,source_grade,source_title,source_url,publisher,published_at,retrieved_at,claim,evidence_summary,relevance_score,freshness_score,trust_score,lecture_use) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pack_id, item["id"], "official_web_source" if item["source_grade"] == "A" else "trusted_web_source" if item["source_grade"] == "B" else "supplementary_web_source", item["source_grade"], item["source_title"], item["source_url"], item["publisher"], item["published_at"], item["retrieved_at"], item["claim"], item["evidence_summary"], item["relevance_score"], item["freshness_score"], item["trust_score"], item["lecture_use"]))
    payload["pack_id"] = pack_id
    return payload

def evidence_quality(pack: dict) -> dict:
    items = pack.get("items", []) if isinstance(pack, dict) else []
    issues = []
    for item in items:
        if not item.get("source_url") or not item.get("source_title"): issues.append({"severity": "critical", "message": "출처 URL과 제목이 필요합니다."})
        if not item.get("evidence_summary"): issues.append({"severity": "major", "message": "근거 요약이 비어 있습니다."})
        if not item.get("retrieved_at"): issues.append({"severity": "major", "message": "수집일이 없습니다."})
    if not items: issues.append({"severity": "critical", "message": "사용 가능한 근거가 없습니다."})
    score = max(0, 100 - 30 * sum(x["severity"] == "critical" for x in issues) - 10 * sum(x["severity"] == "major" for x in issues))
    return {"score": score, "publishable": bool(items) and not any(x["severity"] == "critical" for x in issues), "issues": issues, "checked_at": datetime.now(timezone.utc).isoformat()}

def get_evidence_pack(pack_id: int) -> dict | None:
    init_db()
    prune_expired_evidence_packs()
    with connect() as conn:
        pack = conn.execute("SELECT * FROM evidence_packs WHERE id=?", (pack_id,)).fetchone()
        if not pack: return None
        items = [dict(row) for row in conn.execute("SELECT * FROM evidence_items WHERE pack_id=? ORDER BY id", (pack_id,))]
    return {**dict(pack), "items": items}

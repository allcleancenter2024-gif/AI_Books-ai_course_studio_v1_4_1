"""Studio-owned Saturday official-release research; no Hermes Cron or SearXNG."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import time
import json
import os
from pathlib import Path
from .. import config
import httpx
from ..db import connect, init_db
from .agent_job_service import agent_jobs
from .agent_service import agent_service

SOURCES = {
 "openai": "https://help.openai.com/en/articles/9624314-model-release-notes",
 "anthropic": "https://docs.anthropic.com/en/release-notes/overview",
 "google": "https://ai.google.dev/gemini-api/docs/changelog",
}

def _init():
    init_db()

def due(now=None):
    now = now or datetime.now(timezone.utc)
    _init()
    with connect() as c: rows = {r['source']: r for r in c.execute('SELECT * FROM weekly_research_state')}
    return any(not rows.get(name) or datetime.fromisoformat(rows[name]['last_success_at']) < now - timedelta(days=6) for name in SOURCES)

def collect():
    """Allowlisted HTTPS only, bounded size/time; returns evidence, never raises provider-wide failure."""
    evidence=[]
    for name,url in SOURCES.items():
        try:
            response=httpx.get(url,timeout=20,follow_redirects=False,headers={'User-Agent':'AI-Course-Studio-Weekly-Research/1.0'})
            response.raise_for_status(); text=response.text[:120000]
            evidence.append({'source':name,'url':url,'digest':hashlib.sha256(text.encode()).hexdigest(),'text':text})
        except Exception as exc: evidence.append({'source':name,'url':url,'error':type(exc).__name__})
    return evidence


def _summary_prompt(changed: list[dict]) -> str:
    """Build the small, read-only weekly summary contract without provider knobs."""
    return (
        "다음 공식 Evidence Packet만 바탕으로 교육용 주간 업데이트 Draft를 작성하라.\n"
        "규칙: 제공된 Evidence 외 사실을 추측하지 말 것. 핵심 변화, 의미, 강의 반영 포인트만 쓸 것.\n"
        f"최대 {config.HERMES_WEEKLY_OUTPUT_CHAR_LIMIT}자 이내로 최종 Draft 본문만 반환할 것. "
        "내부 reasoning·분석 과정·도구 사용·외부 행동·게시를 하지 말 것.\n\n"
        + "\n\n".join(
            f"[{row['source']}] {row['url']}\n{row['text'][:config.HERMES_WEEKLY_SOURCE_CHAR_LIMIT]}"
            for row in changed
        )
    )


def _telemetry(started_monotonic: float) -> dict:
    """Return only timing facts observable at the Studio↔Hermes boundary.

    Hermes v0.17's run API does not expose token counts, first-token timing, or
    model-load timing. Those fields deliberately remain null instead of being
    estimated or fabricated.
    """
    return {
        "provider_connect_ms": None,
        "model_ready_ms": None,
        "request_start_at": None,
        "first_token_ms": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "tokens_per_second": None,
        "generation_ms": None,
        "draft_validation_ms": None,
        "total_elapsed_ms": int((time.monotonic() - started_monotonic) * 1000),
        "stop_reason": None,
        "timeout_stage": None,
        "unavailable_metrics": [
            "model_ready_ms", "first_token_ms", "prompt_tokens",
            "completion_tokens", "tokens_per_second", "draft_validation_ms",
        ],
    }


def _optional_fallback(phase: str, evidence_packet_id: int, draft_created: bool) -> dict:
    """Expose the stable optional-worker outcome without changing Job phases."""
    hermes_status = {
        "complete": "completed",
        "timed_out": "timed_out",
    }.get(phase, "failed")
    return {
        "hermes_status": hermes_status,
        "optional_fallback": hermes_status != "completed",
        "evidence_retained": bool(evidence_packet_id),
        "draft_created": draft_created,
        "publisher_changed": False,
    }

def run():
    started_monotonic = time.monotonic()
    telemetry = _telemetry(started_monotonic)

    def status(payload):
        telemetry["total_elapsed_ms"] = int((time.monotonic() - started_monotonic) * 1000)
        payload["telemetry"] = dict(telemetry)
        target=os.getenv('WEEKLY_RESEARCH_RESULT_PATH','')
        if target:
            path=Path(target); path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(payload,ensure_ascii=False,default=str),encoding='utf-8'); tmp.replace(path)
        return payload
    if not due(): return status({'status':'not_due'})
    evidence=collect(); changed=[]
    _init()
    with connect() as c:
        for row in evidence:
            if 'digest' not in row: continue
            old=c.execute('SELECT digest FROM weekly_research_state WHERE source=?',(row['source'],)).fetchone()
            if not old or old['digest'] != row['digest']: changed.append(row)
            c.execute("INSERT INTO weekly_research_state(source,digest,last_success_at) VALUES(?,?,?) ON CONFLICT(source) DO UPDATE SET digest=excluded.digest,last_success_at=excluded.last_success_at",(row['source'],row['digest'],datetime.now(timezone.utc).isoformat()))
        packet=c.execute("INSERT INTO evidence_packs(topic,status,fingerprint,created_at,expires_at) VALUES(?,?,?,?,datetime('now','+7 day'))",('weekly_official_release_notes','collected',hashlib.sha256(''.join(r.get('digest','') for r in evidence).encode()).hexdigest(),datetime.now(timezone.utc).isoformat())).lastrowid
        for row in changed:
            c.execute("INSERT INTO evidence_items(pack_id,evidence_key,source_type,source_grade,source_title,source_url,publisher,published_at,retrieved_at,claim,evidence_summary,relevance_score,freshness_score,trust_score,lecture_use) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(packet,row['digest'],'official_web_source','A',row['source']+' release notes',row['url'],row['source'],'',datetime.now(timezone.utc).isoformat(),'Official release-note change',row['text'][:2000],1,1,1,'review_required'))
    if not changed: return status({'status':'no_change','sources':[r['source'] for r in evidence],'evidence_packet_id':packet})
    prompt = _summary_prompt(changed)
    try:
        connect_started = time.monotonic()
        # This is the only provider-connect measurement exposed by the public
        # Hermes contract: its authenticated run endpoint exposes no separate
        # model-load or streaming-token lifecycle.
        agent_service.health()
        telemetry["provider_connect_ms"] = int((time.monotonic() - connect_started) * 1000)
        telemetry["request_start_at"] = datetime.now(timezone.utc).isoformat()
        generation_started = time.monotonic()
        job=agent_jobs.start(prompt, 'weekly-'+datetime.now(timezone.utc).strftime('%Y%m%d'), 'weekly-research-'+datetime.now(timezone.utc).strftime('%Y%m%d'), capture_draft=True)
        status({'status':'submitted','evidence_packet_id':packet,'job':job})
        # Scheduler processes must not exit before the Studio-owned poller has
        # persisted the terminal Job/Draft state.  This is deliberately bounded.
        until=time.monotonic()+config.HERMES_WEEKLY_SUMMARY_TIMEOUT_SECONDS
        while time.monotonic() < until:
            state=agent_jobs.get(job['job_id']) or {}
            if state.get('phase') in {'complete','error','cancelled','timed_out'}:
                telemetry["generation_ms"] = int((time.monotonic() - generation_started) * 1000)
                telemetry["stop_reason"] = state.get("error") or state.get("phase")
                if state.get("phase") == "timed_out":
                    telemetry["timeout_stage"] = "generation"
                draft_created = bool((state.get('result') or {}).get('draft_id'))
                return status({
                    'status': state.get('phase'), 'evidence_packet_id': packet,
                    'job': state, **_optional_fallback(state.get('phase', 'error'), packet, draft_created),
                })
            status({'status':'running','evidence_packet_id':packet,'job':state})
            time.sleep(1)
        agent_jobs.cancel(job['job_id'])
        from .job_status import jobs
        jobs.update(job['job_id'], phase='timed_out', message='주간 Hermes 요약 시간이 초과되었습니다.', progress=100, error='deadline_exceeded')
        telemetry["generation_ms"] = int((time.monotonic() - generation_started) * 1000)
        telemetry["stop_reason"] = "deadline_exceeded"
        telemetry["timeout_stage"] = "generation"
        return status({
            'status': 'timed_out', 'evidence_packet_id': packet,
            'job': agent_jobs.get(job['job_id']), **_optional_fallback('timed_out', packet, False),
        })
    except Exception as exc:
        telemetry["stop_reason"] = type(exc).__name__
        telemetry["timeout_stage"] = "provider_connect" if telemetry["request_start_at"] is None else "unknown"
        return status({
            'status': 'error', 'evidence_packet_id': packet, 'error': type(exc).__name__,
            'changed_sources': [r['source'] for r in changed], **_optional_fallback('error', packet, False),
        })

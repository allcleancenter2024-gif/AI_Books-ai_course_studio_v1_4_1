"""Explicit, opt-in OpenAI editing of an existing book export."""
from __future__ import annotations

import os
import re
from pathlib import Path

import httpx
from fastapi import HTTPException

from ..db import connect

_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")


def _anonymize(text: str) -> str:
    text = _EMAIL.sub("[EMAIL REDACTED]", text)
    return _PHONE.sub("[PHONE REDACTED]", text)


def _book_path(book_id: int) -> Path:
    with connect() as conn:
        row = conn.execute("SELECT md_path FROM books WHERE id=?", (book_id,)).fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "교재를 찾을 수 없습니다.")
    path = Path(row[0]).resolve()
    if not path.exists() or path.suffix.lower() != ".md":
        raise HTTPException(404, "교재 Markdown 파일을 찾을 수 없습니다.")
    return path


def edit_book(book_id: int, instruction: str, consent: bool, cost_limit_usd: float) -> dict:
    if not consent:
        raise HTTPException(400, "OpenAI 외부 편집은 명시적 전송 동의가 필요합니다.")
    if os.getenv("AI_COURSE_STUDIO_EXTERNAL_EDIT_ENABLED", "0") != "1":
        raise HTTPException(503, "외부 편집 기능이 비활성화되어 있습니다. 서버 환경 변수로 명시적으로 활성화하세요.")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OPENAI_API_KEY가 설정되지 않았습니다.")
    source = _anonymize(_book_path(book_id).read_text(encoding="utf-8"))
    if len(source) > 120_000:
        source = source[:120_000]
    prompt = f"편집 지시:\n{instruction}\n\n교재 원문(참고자료):\n{source}"
    body = {"model": os.getenv("OPENAI_EXTERNAL_EDIT_MODEL", "gpt-4o-mini"), "instructions": "교재 편집 보조자입니다. 원문에 없는 사실을 추가하지 말고, 편집 결과만 반환하세요.", "input": prompt, "max_output_tokens": 6000}
    try:
        response = httpx.post(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/responses", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body, timeout=120)
        if response.status_code >= 400:
            raise HTTPException(502, "OpenAI 외부 편집 요청이 거부되었습니다.")
        data = response.json()
        result = data.get("output_text", "")
        if not isinstance(result, str) or not result.strip():
            raise HTTPException(502, "OpenAI 응답에 편집 결과가 없습니다.")
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        return {"book_id": book_id, "provider": "openai", "model": body["model"], "edited_text": result, "usage": {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}, "cost_limit_usd": cost_limit_usd, "persisted": False}
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"OpenAI 연결 오류: {type(exc).__name__}") from exc

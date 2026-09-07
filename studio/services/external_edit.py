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
    try:
        input_price = float(os.environ["OPENAI_INPUT_USD_PER_1K"])
        output_price = float(os.environ["OPENAI_OUTPUT_USD_PER_1K"])
        if input_price < 0 or output_price < 0:
            raise ValueError
    except (KeyError, ValueError):
        raise HTTPException(503, "OpenAI 단가 환경변수 OPENAI_INPUT_USD_PER_1K/OPENAI_OUTPUT_USD_PER_1K가 필요합니다.")
    source = _anonymize(_book_path(book_id).read_text(encoding="utf-8"))
    if len(source) > 120_000:
        source = source[:120_000]
    prompt = f"편집 지시:\n{_anonymize(instruction)}\n\n교재 원문(참고자료):\n{source}"
    estimated_input = max(1, (len(prompt) + 3) // 4)
    input_cost = estimated_input / 1000 * input_price
    if input_cost >= cost_limit_usd:
        raise HTTPException(400, "요청 원문 예상 입력 비용이 설정한 비용 상한 이상입니다.")
    output_budget = int((cost_limit_usd - input_cost) / max(output_price, 1e-12) * 1000) if output_price else 6000
    body = {"model": os.getenv("OPENAI_EXTERNAL_EDIT_MODEL", "gpt-4o-mini"), "instructions": "교재 편집 보조자입니다. 원문에 없는 사실을 추가하지 말고, 편집 결과만 반환하세요.", "input": prompt, "max_output_tokens": max(64, min(6000, output_budget))}
    try:
        response = httpx.post(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/responses", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body, timeout=120)
        if response.status_code >= 400:
            raise HTTPException(502, "OpenAI 외부 편집 요청이 거부되었습니다.")
        data = response.json()
        result = data.get("output_text", "")
        if not isinstance(result, str) or not result.strip():
            raise HTTPException(502, "OpenAI 응답에 편집 결과가 없습니다.")
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        in_tokens, out_tokens = int(usage.get("input_tokens", estimated_input) or estimated_input), int(usage.get("output_tokens", 0) or 0)
        actual_cost = in_tokens / 1000 * input_price + out_tokens / 1000 * output_price
        if actual_cost > cost_limit_usd:
            raise HTTPException(502, "OpenAI 응답 사용량이 비용 상한을 초과해 결과를 폐기했습니다.")
        return {"book_id": book_id, "provider": "openai", "model": body["model"], "edited_text": result, "usage": {"input_tokens": in_tokens, "output_tokens": out_tokens}, "estimated_cost_usd": round(actual_cost, 8), "cost_limit_usd": cost_limit_usd, "persisted": False}
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"OpenAI 연결 오류: {type(exc).__name__}") from exc

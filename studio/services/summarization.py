from __future__ import annotations

from collections.abc import Callable
import re


class SummaryOutput(str):
    """A string result with safe metadata for the source-summary worker."""

    def __new__(cls, value: str, *, used_fallback: bool = False, reason: str = ""):
        result = super().__new__(cls, value)
        result.used_fallback = used_fallback
        result.reason = reason
        return result


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"[\t \u00a0]+", " ", text).strip()
    return [item.strip(" -•\n") for item in re.split(r"(?<=[.!?。！？])\s+|\n+", normalized) if len(item.strip()) >= 20]


def _extractive_digest(text: str, *, max_items: int, max_chars: int) -> str:
    """Produce a bounded, source-only fallback without calling an AI model."""
    candidates = _sentences(text) or [text.strip()]
    selected: list[str] = []
    # Preserve coverage across the original document instead of only using its
    # introduction.  Facts with numbers/dates are particularly useful in a
    # reference summary, so retain them when they fit.
    positions = sorted({round(index * (len(candidates) - 1) / max(1, max_items - 1)) for index in range(max_items)})
    for index in positions:
        candidate = candidates[index]
        if candidate and sum(len(item) for item in selected) + len(candidate) <= max_chars:
            selected.append(candidate)
    for candidate in candidates:
        if len(selected) >= max_items or sum(len(item) for item in selected) + len(candidate) > max_chars:
            continue
        if re.search(r"\d", candidate) and candidate not in selected:
            selected.append(candidate)
    return "\n".join(f"- {item}" for item in selected[:max_items]) or "- 원문에서 추출할 문장을 찾지 못했습니다."


def _bounded_source_chunks(source: str, chunk_size: int, max_chunks: int = 12) -> list[str]:
    """Limit model calls while retaining representative text from long files."""
    raw = [source[i:i + chunk_size] for i in range(0, len(source), chunk_size)] or [""]
    if len(raw) <= max_chunks:
        return raw
    span = (len(source) + max_chunks - 1) // max_chunks
    return [_extractive_digest(source[index:index + span], max_items=8, max_chars=chunk_size) for index in range(0, len(source), span)]


def _fallback_output(source: str, exc: Exception) -> SummaryOutput:
    fallback = _extractive_digest(source, max_items=10, max_chars=3_800)
    return SummaryOutput(
        "## 핵심 내용 5개\n" + fallback +
        "\n\n## 쉬운 설명\n원문에서 핵심 문장을 추출해 정리했습니다.\n"
        "\n## 원문 대조가 필요한 정보\nAI 모델 응답이 제한 시간 안에 끝나지 않아 추출 방식으로 완료했습니다. 숫자·날짜·해석은 원문과 다시 대조하세요.",
        used_fallback=True,
        reason=f"{type(exc).__name__}: {str(exc)[:240]}",
    )


def summarize_text(provider_manager, provider: str, text: str, progress: Callable[[int, int, str], None] | None = None) -> SummaryOutput | str:
    """Bound every model call so small local contexts cannot overflow.

    Long documents are summarized in small passes and reduced in groups of three.
    The callback reports the completed model-call count for the UI progress view.
    """
    system = "당신은 교육자료 조사·요약 보조자입니다. <SOURCE> 안의 자료에만 근거하며 숫자와 날짜를 보존합니다. 원문에 없는 내용은 만들지 마세요."
    local = provider in {"lmstudio", "ollama"}
    chunk_size = 2_400 if local else 7_000
    # Small local output budgets prevent a reasoning-capable model from using
    # most of a 4K context on a single intermediate summary.
    output_tokens = 220 if local else 650
    source = text[:120_000].strip()
    chunks = _bounded_source_chunks(source, chunk_size) if local else [source[i:i + chunk_size] for i in range(0, len(source), chunk_size)] or [""]
    # Upper bound used only for a stable, understandable progress bar.
    estimated_total = len(chunks) + max(1, (len(chunks) + 2) // 3) + 1
    completed = 0
    def report(message: str):
        nonlocal completed
        completed += 1
        if progress: progress(completed, estimated_total, message)
    partials = []
    for index, chunk in enumerate(chunks, 1):
        prompt = f"자료 조각 {index}/{len(chunks)}입니다. 핵심 사실, 숫자·날짜, 기능 또는 주의사항만 간결한 글머리표로 정리하세요.\n\n<SOURCE>\n{chunk}\n</SOURCE>"
        try:
            # A source summary must have a bounded completion path.  The
            # generic provider failover is valuable for lesson generation,
            # but trying every installed local model here can turn one slow
            # request into several sequential timeouts.  On any selected-model
            # failure we instead finish with the clearly-labelled, source-only
            # fallback below.
            partials.append(provider_manager.generate(
                provider, system, prompt, max_tokens=output_tokens,
                temperature=.2, allow_failover=False,
            ))
        except Exception as exc:
            # Do not make a usable source unavailable merely because every
            # local model is overloaded.  This is intentionally extractive and
            # clearly labelled below, so it never presents itself as AI output.
            return _fallback_output(source, exc)
        report(f"원문 조각 {index}/{len(chunks)} 요약 완료")
    round_no = 1
    while len(partials) > 1:
        next_partials = []
        groups = [partials[i:i + 3] for i in range(0, len(partials), 3)]
        for index, group in enumerate(groups, 1):
            prompt = f"요약 묶음 {index}/{len(groups)}을 중복 없이 통합하세요. 사실·수치·날짜를 보존하고, 원문에 없는 해석은 넣지 마세요.\n\n<SOURCE>\n" + "\n\n".join(group) + "\n</SOURCE>"
            try:
                next_partials.append(provider_manager.generate(
                    provider, system, prompt, max_tokens=output_tokens,
                    temperature=.2, allow_failover=False,
                ))
            except Exception as exc:
                return _fallback_output(source, exc)
            report(f"요약 통합 {round_no}-{index}/{len(groups)} 완료")
        partials = next_partials; round_no += 1
    final_prompt = "다음 요약을 교육용으로 정리하세요. '핵심 내용 5개', '쉬운 설명', '원문 대조가 필요한 정보' 제목을 반드시 사용하고 추측하지 마세요.\n\n<SOURCE>\n" + partials[0] + "\n</SOURCE>"
    try:
        result = provider_manager.generate(
            provider, system, final_prompt, max_tokens=500 if local else 1_100,
            temperature=.2, allow_failover=False,
        )
    except Exception as exc:
        return _fallback_output(source, exc)
    report("최종 교육용 요약 작성 완료")
    return result

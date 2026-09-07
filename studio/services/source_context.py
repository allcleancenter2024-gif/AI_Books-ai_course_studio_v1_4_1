from __future__ import annotations

import re

from .vector_index import retrieve


# Reference material can originate from public web pages, uploaded files, and
# video transcripts. It is data, never an instruction for the model.
_INJECTION_LINE = re.compile(
    r"(?ix)"
    r"(?:\b(?:ignore|disregard|forget|override)\b.{0,100}\b(?:instruction|prompt|system|rule|previous|above)\b"
    r"|\b(?:system\s*prompt|developer\s*message|jailbreak|assistant\s*:)\b"
    r"|(?:이전|앞|위|시스템).{0,80}(?:지시|명령|규칙).{0,80}(?:무시|따르|변경)"
    r"|(?:지시|명령|규칙).{0,80}(?:무시|따르|변경))"
)


def sanitize_untrusted_reference(text: str, *, max_chars: int | None = None) -> str:
    """Keep factual reference text while removing common prompt-injection lines.

    This is defence in depth, not a substitute for the instruction/data boundary
    supplied to the model. Escaping angle brackets prevents a source from
    manufacturing a closing prompt-data tag.
    """
    lines: list[str] = []
    for raw in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = " ".join(raw.split())
        if not line:
            continue
        if _INJECTION_LINE.search(line):
            continue
        lines.append(line.replace("<", "&lt;").replace(">", "&gt;"))
    value = "\n".join(lines)
    return value[:max_chars] if max_chars is not None else value


def build_source_context(ids: list[int], query: str = "", max_total: int = 24_000, per_source: int = 8_000) -> str:
    remaining = max(0, max_total)
    blocks: list[str] = []
    for block in retrieve(ids, query, max_total=max_total, per_source=per_source):
        text = sanitize_untrusted_reference(block.get("text", ""), max_chars=remaining)
        if not text:
            continue
        blocks.append(text)
        remaining -= len(text)
        if remaining <= 0:
            break
    return "\n\n".join(blocks)

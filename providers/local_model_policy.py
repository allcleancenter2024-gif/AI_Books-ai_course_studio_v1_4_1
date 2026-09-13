"""Resource policy shared by local AI provider adapters.

This module contains only deterministic classification rules.  Network and
model lifecycle operations remain in ``ProviderManager``.
"""

from __future__ import annotations

import re


MAX_AUTOMATIC_MODEL_BYTES = 8 * 1024**3
_REASONING_MODEL_RE = re.compile(
    r"(?:^|[/_.:-])(deepseek[-_.]?r1|qwq|reasoning|thinking)(?:$|[/_.:-])", re.I
)
_MODEL_PARAMETER_RE = re.compile(r"(?:^|[/_.:-])(\d+(?:\.\d+)?)b(?:$|[/_.:-])", re.I)


def is_reasoning_only_model(model: str) -> bool:
    """Return whether a model is dedicated to hidden-chain reasoning."""
    return bool(_REASONING_MODEL_RE.search(model.strip()))


def is_oversized_model(model: str, *, maximum_billions: float = 14) -> bool:
    """Conservatively classify model size from names when metadata is absent."""
    sizes = [float(value) for value in _MODEL_PARAMETER_RE.findall(model)]
    return bool(sizes and max(sizes) >= maximum_billions)


def is_safe_local_model_name(model: str) -> bool:
    return not is_reasoning_only_model(model) and not is_oversized_model(model)

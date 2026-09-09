"""Stable, transport-safe error contracts for AI provider operations."""
from __future__ import annotations


class ProviderError(RuntimeError):
    """Base error exposed by the provider boundary."""

    code = "provider_error"
    http_status = 502


class ProviderUnavailableError(ProviderError):
    code = "provider_unavailable"
    http_status = 503


class ProviderTimeoutError(ProviderError):
    code = "provider_timeout"
    http_status = 504


class ProviderCapabilityError(ProviderError):
    code = "provider_capability"
    http_status = 422


class ProviderModelNotFoundError(ProviderError):
    code = "provider_model_not_found"
    http_status = 422


class ProviderCancelledError(ProviderError):
    code = "provider_cancelled"
    http_status = 409


class ProviderExecutionBlockedError(ProviderError):
    """Raised when the operator explicitly disables provider-side actions."""

    code = "provider_execution_blocked"
    http_status = 423


__all__ = [
    "ProviderError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderCapabilityError",
    "ProviderModelNotFoundError",
    "ProviderCancelledError",
    "ProviderExecutionBlockedError",
]

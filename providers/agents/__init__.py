"""Replaceable agent-orchestration adapters, separate from LLM providers."""

from .base import AgentAdapter, AgentHealth
from .disabled import DisabledAgentAdapter
from .hermes import HermesAdapter

__all__ = ["AgentAdapter", "AgentHealth", "DisabledAgentAdapter", "HermesAdapter"]

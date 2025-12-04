"""
LLM Provider Abstraction Layer

This module provides a provider-agnostic interface for working with different
LLM backends (Anthropic, OpenAI, local models, etc.).

The abstraction allows swapping providers without changing business logic.
"""

from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall
from .anthropic_provider import AnthropicProvider

# Optional providers (require additional dependencies)
try:
    from .openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from .ollama_provider import OllamaProvider
except ImportError:
    OllamaProvider = None

__all__ = [
    'LLMProvider',
    'LLMMessage',
    'LLMResponse',
    'LLMToolCall',
    'AnthropicProvider',
    'OpenAIProvider',
    'OllamaProvider',
]

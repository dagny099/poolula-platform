"""
Base classes and interfaces for LLM providers

This module defines provider-agnostic data structures and the abstract
interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """Provider-agnostic message format"""
    role: str  # "user", "assistant", "system"
    content: Any  # Can be string or structured content (for tool results)


@dataclass
class LLMToolCall:
    """Provider-agnostic tool call representation"""
    id: str
    name: str
    parameters: Dict[str, Any]


@dataclass
class LLMResponse:
    """Provider-agnostic response from LLM"""
    text: Optional[str] = None
    tool_calls: Optional[List[LLMToolCall]] = None
    stop_reason: str = "complete"  # "complete", "tool_use", "max_tokens"
    raw_response: Any = None  # Original provider response for debugging

    # Content blocks (for Anthropic-style responses)
    content: List[Any] = field(default_factory=list)

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls"""
        return self.tool_calls is not None and len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers

    All provider implementations (Anthropic, OpenAI, Ollama, etc.) must
    implement this interface to ensure they can be used interchangeably.
    """

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.0,
        max_tokens: int = 800,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM

        Args:
            messages: Conversation history as LLMMessage objects
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse object with generated text and/or tool calls
        """
        pass

    @abstractmethod
    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate from internal tool format to provider-specific format

        Args:
            tool_def: Tool definition in Anthropic format (our internal standard)

        Returns:
            Tool definition in provider-specific format
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return provider name for logging/debugging

        Returns:
            String like "anthropic:claude-sonnet-4" or "openai:gpt-4o"
        """
        pass

    @property
    @abstractmethod
    def supports_native_tool_calling(self) -> bool:
        """
        Whether this provider supports native tool calling

        Returns:
            True if provider has native tool calling API, False if we need
            to use prompt engineering fallback
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is reachable and healthy

        This method performs a lightweight health check to verify the provider
        can accept requests. Useful for startup diagnostics and UI status.

        Returns:
            True if provider is available, False otherwise
        """
        pass

    @property
    def default_timeout(self) -> int:
        """
        Default timeout in seconds for generate() calls

        Override this property to set provider-specific timeouts.
        API providers typically use 60s, local models may need 120s+.

        Returns:
            Timeout value in seconds (default: 60)
        """
        return 60

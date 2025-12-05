"""
Anthropic Claude provider implementation

Wraps the Anthropic API to implement the LLMProvider interface.
"""

import anthropic
import logging
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude implementation of LLMProvider

    This adapter wraps the Anthropic SDK to provide a provider-agnostic
    interface for the rest of the application.
    """

    def __init__(self, api_key: str, model: str):
        """
        Initialize Anthropic provider

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., "claude-sonnet-4-20250514")
        """
        if not api_key:
            raise ValueError("Anthropic API key is required")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"AnthropicProvider initialized with model: {model}")

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
        Generate response using Anthropic Messages API

        Args:
            messages: Conversation history
            system_prompt: System prompt
            tools: Tool definitions (already in Anthropic format)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with text and/or tool calls
        """
        # Translate messages to Anthropic format
        anthropic_messages = self._translate_messages(messages)

        # Build API parameters
        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add system prompt if provided
        if system_prompt:
            params["system"] = system_prompt

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = {"type": "auto"}

        # Call Anthropic API
        try:
            response = self.client.messages.create(**params)
            return self._translate_response(response)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            raise

    def _translate_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        Translate LLMMessage objects to Anthropic message format

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of dicts in Anthropic format
        """
        anthropic_messages = []

        for msg in messages:
            # Skip system messages (handled separately)
            if msg.role == "system":
                continue

            # Handle content - can be string or structured (for tool results)
            if isinstance(msg.content, str):
                content = msg.content
            else:
                # Already in structured format (e.g., tool results)
                content = msg.content

            anthropic_messages.append({
                "role": msg.role,
                "content": content
            })

        return anthropic_messages

    def _translate_response(self, response) -> LLMResponse:
        """
        Translate Anthropic response to LLMResponse

        Args:
            response: Anthropic Messages API response

        Returns:
            LLMResponse object
        """
        # Extract text content and tool calls
        text = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(LLMToolCall(
                    id=block.id,
                    name=block.name,
                    parameters=block.input
                ))

        # Determine stop reason
        stop_reason = "complete"
        if response.stop_reason == "tool_use":
            stop_reason = "tool_use"
        elif response.stop_reason == "max_tokens":
            stop_reason = "max_tokens"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls if tool_calls else None,
            stop_reason=stop_reason,
            raw_response=response,
            content=response.content  # Preserve original content blocks
        )

    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate tool definition to Anthropic format

        Anthropic uses our internal format directly, so no translation needed.

        Args:
            tool_def: Tool definition in our internal format

        Returns:
            Same tool definition (pass-through)
        """
        return tool_def

    @property
    def provider_name(self) -> str:
        """Return provider name for logging"""
        return f"anthropic:{self.model}"

    @property
    def supports_native_tool_calling(self) -> bool:
        """Anthropic supports native tool calling"""
        return True

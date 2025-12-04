"""
OpenAI provider implementation

Wraps the OpenAI API to implement the LLMProvider interface.
"""

import json
import logging
from typing import List, Dict, Any, Optional

try:
    import openai
except ImportError:
    openai = None

from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT implementation of LLMProvider

    This adapter wraps the OpenAI SDK to provide a provider-agnostic
    interface for the rest of the application.
    """

    def __init__(self, api_key: str, model: str):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., "gpt-4o", "gpt-4o-mini")
        """
        if openai is None:
            raise ImportError(
                "OpenAI provider requires the 'openai' package. "
                "Install with: uv sync --group openai"
            )

        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAIProvider initialized with model: {model}")

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
        Generate response using OpenAI Chat Completions API

        Args:
            messages: Conversation history
            system_prompt: System prompt
            tools: Tool definitions (in Anthropic format, will be translated)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with text and/or tool calls
        """
        # Build messages (OpenAI includes system as first message)
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        # Translate LLMMessage objects to OpenAI format
        openai_messages.extend(self._translate_messages(messages))

        # Build API parameters
        params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add tools if provided (translate from Anthropic format)
        if tools:
            params["tools"] = [self._translate_tool_definition(t) for t in tools]
            params["tool_choice"] = "auto"

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(**params)
            return self._translate_response(response)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise

    def _translate_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        Translate LLMMessage objects to OpenAI message format

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of dicts in OpenAI format
        """
        openai_messages = []

        for msg in messages:
            # Skip system messages (handled separately)
            if msg.role == "system":
                continue

            # Handle content - can be string or structured (for tool results)
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list):
                # Tool results format - already in structured format
                content = msg.content
            else:
                # Convert to string if unknown type
                content = str(msg.content)

            openai_messages.append({
                "role": msg.role,
                "content": content
            })

        return openai_messages

    def _translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate from Anthropic tool format to OpenAI function format

        Anthropic format:
        {
            "name": "tool_name",
            "description": "...",
            "input_schema": {"type": "object", "properties": {...}, "required": [...]}
        }

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {"type": "object", "properties": {...}, "required": [...]}
            }
        }

        Args:
            tool_def: Tool definition in Anthropic format

        Returns:
            Tool definition in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": tool_def["input_schema"]
            }
        }

    def _translate_response(self, response) -> LLMResponse:
        """
        Translate OpenAI response to LLMResponse

        Args:
            response: OpenAI ChatCompletion response

        Returns:
            LLMResponse object
        """
        message = response.choices[0].message

        # Extract text content
        text = message.content

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    # Parse arguments (OpenAI returns them as JSON string)
                    parameters = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool arguments: {tc.function.arguments}")
                    parameters = {}

                tool_calls.append(LLMToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    parameters=parameters
                ))

        # Determine stop reason
        stop_reason = "complete"
        if message.tool_calls:
            stop_reason = "tool_use"
        elif response.choices[0].finish_reason == "length":
            stop_reason = "max_tokens"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls if tool_calls else None,
            stop_reason=stop_reason,
            raw_response=response,
            content=[message]  # Store message for compatibility
        )

    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate tool definition to OpenAI format

        Args:
            tool_def: Tool definition in our internal format

        Returns:
            Tool definition in OpenAI format
        """
        return self._translate_tool_definition(tool_def)

    @property
    def provider_name(self) -> str:
        """Return provider name for logging"""
        return f"openai:{self.model}"

    @property
    def supports_native_tool_calling(self) -> bool:
        """OpenAI supports native tool calling (function calling)"""
        return True

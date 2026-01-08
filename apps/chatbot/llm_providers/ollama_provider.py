"""
Ollama provider implementation for local models

Wraps the Ollama API to implement the LLMProvider interface.
Supports local model execution with optional prompt-based tool calling.
"""

import json
import logging
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama local model implementation of LLMProvider

    This adapter wraps the Ollama HTTP API to provide a provider-agnostic
    interface. Most local models don't support native tool calling, so we
    use prompt engineering as a fallback.
    """

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider

        Args:
            model: Model name (e.g., "llama3.1:8b-instruct-q4_K_M")
            base_url: Ollama API base URL (default: http://localhost:11434)
        """
        if requests is None:
            raise ImportError(
                "Ollama provider requires the 'requests' package. "
                "Install with: uv sync --group local"
            )

        self.model = model
        self.base_url = base_url.rstrip('/')
        logger.info(f"OllamaProvider initialized with model: {model} at {base_url}")

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
        Generate response using Ollama API

        Args:
            messages: Conversation history
            system_prompt: System prompt
            tools: Tool definitions (will use prompt engineering for tool calling)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with text and/or tool calls
        """
        # Build messages
        ollama_messages = []

        # Add system prompt
        if system_prompt:
            # If we have tools, augment system prompt with tool instructions
            if tools:
                tool_prompt = self._build_tool_prompt(tools)
                enhanced_system = f"{system_prompt}\n\n{tool_prompt}"
                ollama_messages.append({"role": "system", "content": enhanced_system})
            else:
                ollama_messages.append({"role": "system", "content": system_prompt})

        # Add conversation messages
        ollama_messages.extend(self._translate_messages(messages))

        # Build request payload
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        # Call Ollama API
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120  # Local models can be slow on CPU
            )
            response.raise_for_status()
            return self._translate_response(response.json(), tools is not None)
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}", exc_info=True)
            raise RuntimeError(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    def _translate_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        Translate LLMMessage objects to Ollama message format

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of dicts in Ollama format
        """
        ollama_messages = []

        for msg in messages:
            # Skip system messages (handled separately)
            if msg.role == "system":
                continue

            # Convert content to string if needed
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list):
                # For tool results, format them nicely
                content = self._format_tool_results(msg.content)
            else:
                content = str(msg.content)

            ollama_messages.append({
                "role": msg.role,
                "content": content
            })

        return ollama_messages

    def _format_tool_results(self, tool_results: List) -> str:
        """
        Format tool results as readable text for local models

        Args:
            tool_results: List of tool result dicts

        Returns:
            Formatted string
        """
        formatted = []
        for result in tool_results:
            if isinstance(result, dict) and result.get("type") == "tool_result":
                content = result.get("content", "")
                formatted.append(f"Tool result: {content}")
            else:
                formatted.append(str(result))

        return "\n\n".join(formatted)

    def _build_tool_prompt(self, tools: List[Dict]) -> str:
        """
        Build tool usage instructions for prompt engineering

        Since most local models don't support native tool calling, we
        teach them to respond with JSON when they need to use a tool.

        Args:
            tools: List of tool definitions

        Returns:
            Tool instruction prompt
        """
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(
                f"- **{tool['name']}**: {tool['description']}"
            )

        tool_list = "\n".join(tool_descriptions)

        return f"""# Available Tools

You have access to the following tools:

{tool_list}

## Tool Usage Protocol

When you need to use a tool, respond with ONLY a JSON object in this exact format:
```json
{{
  "tool": "tool_name",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

Important:
- Use tools when you need specific data from the system
- After receiving tool results, synthesize them into a natural response
- Do not mention the tools explicitly in your final response
- Keep responses brief, professional, and focused"""

    def _translate_response(self, response: Dict, expect_tools: bool) -> LLMResponse:
        """
        Translate Ollama response to LLMResponse

        Attempts to parse tool calls from JSON if tools were provided.

        Args:
            response: Ollama API response
            expect_tools: Whether tools were provided in the request

        Returns:
            LLMResponse object
        """
        content = response["message"]["content"]

        # Try to parse tool calls if we expect them
        tool_calls = None
        text = content

        if expect_tools and content.strip():
            # Try to extract JSON from code blocks or raw JSON
            tool_calls, remaining_text = self._parse_tool_call(content)
            if tool_calls:
                # If we successfully parsed a tool call, don't return text
                text = None
            else:
                # Otherwise, treat as regular text response
                text = remaining_text or content

        # Determine stop reason
        stop_reason = "tool_use" if tool_calls else "complete"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_response=response,
            content=[{"content": content}]  # Store original for debugging
        )

    def _parse_tool_call(self, content: str) -> tuple[Optional[List[LLMToolCall]], Optional[str]]:
        """
        Parse tool call from model response

        Looks for JSON in code blocks or as raw JSON.

        Args:
            content: Model response text

        Returns:
            Tuple of (tool_calls list or None, remaining text or None)
        """
        import re

        # Try to find JSON in code blocks first
        code_block_pattern = r'```(?:json)?\s*(\{[^`]+\})\s*```'
        match = re.search(code_block_pattern, content, re.DOTALL)

        if match:
            json_str = match.group(1)
            remaining = content[:match.start()] + content[match.end():]
        else:
            # Try to find raw JSON
            json_pattern = r'\{\s*"tool"\s*:'
            if re.search(json_pattern, content):
                # Content looks like it starts with JSON
                try:
                    # Try to parse the whole thing
                    json_str = content.strip()
                    remaining = None
                except:
                    return None, content
            else:
                return None, content

        # Try to parse the JSON
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "tool" in parsed:
                tool_call = LLMToolCall(
                    id=f"ollama-{hash(json_str) % 10000}",  # Generate stable ID
                    name=parsed["tool"],
                    parameters=parsed.get("parameters", {})
                )
                return [tool_call], remaining.strip() if remaining else None
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse tool call JSON: {e}")
            return None, content

        return None, content

    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ollama uses prompt-based tool calling, so we pass through the definition

        Args:
            tool_def: Tool definition in our internal format

        Returns:
            Same tool definition (pass-through)
        """
        return tool_def

    @property
    def provider_name(self) -> str:
        """Return provider name for logging"""
        return f"ollama:{self.model}"

    @property
    def supports_native_tool_calling(self) -> bool:
        """Ollama uses prompt engineering, not native tool calling"""
        return False

    def is_available(self) -> bool:
        """
        Check if Ollama is reachable and models are available

        Pattern adopted from montrose-marathon project.

        Returns:
            True if Ollama is running and accessible, False otherwise
        """
        try:
            # Quick health check - ping Ollama's tags endpoint
            # Using a 5-second timeout for health checks
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("Ollama is available")
            return True
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Ollama not available (connection error): {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.warning(f"Ollama not available (timeout): {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Ollama not available (HTTP error): {e}")
            return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    @property
    def default_timeout(self) -> int:
        """
        Default timeout for Ollama calls

        Local models can be slow on CPU, especially for first-time loads.

        Returns:
            Timeout in seconds (120s for local model flexibility)
        """
        return 120

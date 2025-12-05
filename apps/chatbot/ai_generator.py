import logging
from typing import List, Optional, Dict, Any
from .llm_providers.base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

class AIGenerationError(Exception):
    """Raised when AI generation fails"""
    pass

class AIGenerator:
    """
    Provider-agnostic AI generation orchestrator

    Handles interactions with LLM providers for generating responses.
    Supports multi-round tool calling and conversation history.
    """

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant for Poolula LLC, a rental property business. You help with questions about properties, financial transactions, documents, and compliance obligations.

Available Tools:
- **query_database**: Query structured business data (properties, transactions, documents, obligations)
- **search_document_content**: Search business document content (formation docs, insurance, leases, tax documents, contracts)
- **list_business_documents**: List available business documents and their types

Tool Usage Guidelines:
- **Up to 2 sequential tool calls per query** - Use multiple rounds for complex queries
- **Multi-round strategy examples**:
  - Query database for property list, then search documents for specific property details
  - Search documents for business terms, then query transactions matching those terms
  - Query obligations due soon, then search documents for related compliance requirements
- **Sequential reasoning**: Use first tool call results to inform second tool call parameters
- Synthesize all tool results into comprehensive, accurate responses
- If tool yields no results, state this clearly without offering alternatives

Tool Selection Logic:
- **query_database**: For structured data queries (property basis, transaction totals, obligation lists)
- **search_document_content**: For document text search (business purpose, insurance terms, contract clauses)
- **list_business_documents**: When user wants to know what documents are available

Database Query Result Format:
The query_database tool returns JSON with this structure:
```json
{
  "success": true/false,
  "count": <number>,
  "transactions": [...],  // or "properties", "documents", "obligations", "aggregations"
  "total_amount": <number>  // for aggregations
}
```

**CRITICAL**: Always check the "success" field and "count" field in database responses:
- If "success" is true and "count" > 0, there IS data - parse and use the results
- If "count" is 0, there is NO data for that query
- The actual data is in the "transactions", "properties", "documents", or "aggregations" array
- For aggregations, check the "aggregations" array and "total_amount" field

Response Protocol:
- **General business questions**: Answer using existing knowledge without tools
- **Data queries**: Use query_database for financial/property/transaction data
- **Document questions**: Use search_document_content for document text and clauses
- **Hybrid queries**: Use both database and document search tools sequentially
- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
  - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Professional** - Maintain business tone
3. **Clear** - Use accessible language
4. **Data-supported** - Include relevant numbers and facts when available
Provide only the direct answer to what was asked.
"""

    def __init__(self, provider: LLMProvider):
        """
        Initialize AI generator with an LLM provider

        Args:
            provider: LLMProvider implementation (Anthropic, OpenAI, etc.)
        """
        self.provider = provider
        logger.info(f"AIGenerator initialized with provider: {provider.provider_name}")

        # Pre-build base parameters for efficiency
        self.base_params = {
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential tool calling rounds for complex queries.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Translate tools to provider format if provided
        provider_tools = None
        if tools:
            provider_tools = [
                self.provider.translate_tool_definition(tool)
                for tool in tools
            ]

        # Initialize round tracking
        max_rounds = 2
        current_round = 0
        messages = [LLMMessage(role="user", content=query)]

        # Sequential tool calling loop
        while current_round < max_rounds:
            current_round += 1

            # Get response from provider
            response = self.provider.generate(
                messages=messages,
                system_prompt=system_content,
                tools=provider_tools,
                **self.base_params
            )

            # Add assistant response to message history
            # Use raw response content to preserve structure (e.g., for Anthropic)
            messages.append(LLMMessage(
                role="assistant",
                content=response.content if response.content else response.text
            ))

            # Check if we should continue with tool execution
            if response.stop_reason == "tool_use" and response.has_tool_calls() and tool_manager:
                # Execute tools and get results
                tool_results, should_continue = self._handle_tool_execution_round(
                    response, tool_manager
                )

                # Add tool results to message history
                if tool_results:
                    messages.append(LLMMessage(role="user", content=tool_results))

                # If tools failed or we shouldn't continue, break
                if not should_continue:
                    break

                # Continue to next round if we haven't hit max rounds
                continue
            else:
                # No tool use needed, return response
                return response.text or ""

        # Final round without tools to get synthesized response
        final_response = self.provider.generate(
            messages=messages,
            system_prompt=system_content,
            **self.base_params
        )

        return final_response.text or ""

    def _handle_tool_execution_round(self, response: LLMResponse, tool_manager):
        """
        Handle execution of tool calls for a single round.

        Args:
            response: The LLMResponse containing tool calls
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (tool_results_list, should_continue_flag)
        """
        tool_results = []

        # Execute all tool calls and collect results
        for tool_call in response.tool_calls:
            try:
                tool_result = tool_manager.execute_tool(
                    tool_call.name,
                    **tool_call.parameters
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": tool_result
                })

            except Exception as e:
                # Handle tool execution errors gracefully
                error_result = f"Tool execution failed: {str(e)}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": error_result
                })
                # Don't continue on tool errors
                return tool_results, False

        # Continue if we have successful tool results
        return tool_results, len(tool_results) > 0

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Legacy method for backward compatibility with existing tests.
        Handle execution of tool calls and get follow-up response.

        This method is deprecated and maintained only for test compatibility.
        New code should use the multi-round logic in generate_response().

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Convert to LLMResponse if needed
        if not isinstance(initial_response, LLMResponse):
            # Assume it's an Anthropic response and translate it
            # This is for backward compatibility with tests
            from .llm_providers.anthropic_provider import AnthropicProvider
            if isinstance(self.provider, AnthropicProvider):
                initial_response = self.provider._translate_response(initial_response)
            else:
                raise ValueError("Legacy _handle_tool_execution only supports Anthropic responses")

        # Start with existing messages
        messages = base_params.get("messages", [])
        if not isinstance(messages[0], LLMMessage):
            # Convert dict messages to LLMMessage objects
            messages = [LLMMessage(role=m["role"], content=m["content"]) for m in messages]

        # Add AI's tool use response
        messages.append(LLMMessage(
            role="assistant",
            content=initial_response.content if initial_response.content else initial_response.text
        ))

        # Execute all tool calls and collect results using new method
        tool_results, should_continue = self._handle_tool_execution_round(initial_response, tool_manager)

        # Add tool results as single message
        if tool_results:
            messages.append(LLMMessage(role="user", content=tool_results))

        # Get final response
        system_prompt = base_params.get("system", self.SYSTEM_PROMPT)
        final_response = self.provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            **self.base_params
        )

        return final_response.text or ""

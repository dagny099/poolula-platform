import anthropic
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class AIGenerationError(Exception):
    """Raised when AI generation fails"""
    pass

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
- **search_course_content**: For searching specific course content and educational materials
- **get_course_outline**: For retrieving course outlines including title, link, and complete lesson list

Tool Usage Guidelines:
- Use search tools **only** for questions about specific course content or course structure
- **Up to 2 sequential tool calls per query** - Use multiple rounds for complex queries
- **Multi-round strategy examples**:
  - Get course outline first, then search specific lesson content
  - Search broad topic, then refine with specific course/lesson details
  - Compare information from different courses using separate searches
- For outline queries: Use get_course_outline to return course title, course link, and numbered lesson list
- For content queries: Use search_course_content for detailed educational materials
- **Sequential reasoning**: Use first tool call results to inform second tool call parameters
- Synthesize all tool results into comprehensive, accurate responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline requests**: Use get_course_outline tool, optionally followed by content search for details
- **Course content questions**: Use search_course_content tool, optionally followed by refined search
- **Comparison queries**: Use separate tool calls to gather information from different sources
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"AIGenerator initialized with model: {model}")
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
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
        
        # Initialize round tracking
        max_rounds = 2
        current_round = 0
        messages = [{"role": "user", "content": query}]
        
        # Sequential tool calling loop
        while current_round < max_rounds:
            current_round += 1
            
            # Prepare API call parameters for current round
            api_params = {
                **self.base_params,
                "messages": messages.copy(),
                "system": system_content
            }
            
            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}
            
            # Get response from Claude
            response = self.client.messages.create(**api_params)
            
            # Add assistant response to message history
            messages.append({"role": "assistant", "content": response.content})
            
            # Check if we should continue with tool execution
            if response.stop_reason == "tool_use" and tool_manager:
                # Execute tools and get results
                tool_results, should_continue = self._handle_tool_execution_round(
                    response, tool_manager
                )
                
                # Add tool results to message history
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                
                # If tools failed or we shouldn't continue, break
                if not should_continue:
                    break
                    
                # Continue to next round if we haven't hit max rounds
                continue
            else:
                # No tool use needed, return response
                return response.content[0].text
        
        # Final round without tools to get synthesized response
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
    
    def _handle_tool_execution_round(self, response, tool_manager):
        """
        Handle execution of tool calls for a single round.
        
        Args:
            response: The response containing tool use requests
            tool_manager: Manager to execute tools
            
        Returns:
            Tuple of (tool_results_list, should_continue_flag)
        """
        tool_results = []
        
        # Execute all tool calls and collect results
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
                    
                except Exception as e:
                    # Handle tool execution errors gracefully
                    error_result = f"Tool execution failed: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
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
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results using new method
        tool_results, should_continue = self._handle_tool_execution_round(initial_response, tool_manager)
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
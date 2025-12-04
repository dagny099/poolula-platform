import unittest
from unittest.mock import Mock, MagicMock, patch

from apps.chatbot.ai_generator import AIGenerator
from apps.chatbot.llm_providers.anthropic_provider import AnthropicProvider
from apps.chatbot.search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from apps.chatbot.vector_store import VectorStore


class TestAIGeneratorIntegration(unittest.TestCase):
    """Test suite for AI generator integration with CourseSearchTool"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock the Anthropic client
        self.mock_client = Mock()

        # Create Anthropic provider with mocked client
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = self.mock_client
            self.provider = AnthropicProvider("fake-api-key", "claude-3-sonnet")

        # Create AI generator with the provider
        self.ai_generator = AIGenerator(self.provider)

        # Create mock vector store and tools
        self.mock_vector_store = Mock(spec=VectorStore)
        self.search_tool = CourseSearchTool(self.mock_vector_store)
        self.outline_tool = CourseOutlineTool(self.mock_vector_store)

        # Create tool manager with both tools
        self.tool_manager = ToolManager()
        self.tool_manager.register_tool(self.search_tool)
        self.tool_manager.register_tool(self.outline_tool)

    def _create_text_response(self, text, stop_reason="end_turn"):
        """Helper to create a properly structured text response"""
        response = Mock()
        response.stop_reason = stop_reason
        content_block = Mock()
        content_block.type = "text"
        content_block.text = text
        response.content = [content_block]
        return response

    def _create_tool_use_response(self, tool_name, tool_id, tool_input):
        """Helper to create a properly structured tool use response"""
        response = Mock()
        response.stop_reason = "tool_use"
        content_block = Mock()
        content_block.type = "tool_use"
        content_block.name = tool_name
        content_block.id = tool_id
        content_block.input = tool_input
        response.content = [content_block]
        return response
    
    def test_generate_response_without_tools(self):
        """Test response generation without tool usage"""
        # Mock Claude response without tool use
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content_block = Mock()
        mock_content_block.type = "text"
        mock_content_block.text = "This is a general knowledge response."
        mock_response.content = [mock_content_block]
        
        self.mock_client.messages.create.return_value = mock_response
        
        result = self.ai_generator.generate_response(
            query="What is machine learning?",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify response
        self.assertEqual(result, "This is a general knowledge response.")
        
        # Verify API call was made correctly
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args
        
        # Check that tools were passed to the API
        self.assertIn('tools', call_args.kwargs)
        self.assertIn('tool_choice', call_args.kwargs)
        self.assertEqual(call_args.kwargs['tool_choice'], {"type": "auto"})
    
    def test_generate_response_with_tool_usage(self):
        """Test response generation with tool usage"""
        # Mock initial response with tool use
        initial_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_123",
            tool_input={
                "query": "machine learning basics",
                "course_name": "Introduction to AI"
            }
        )

        # Mock final response after tool execution
        final_response = self._create_text_response("Based on the course content, machine learning is...")
        
        self.mock_client.messages.create.side_effect = [initial_response, final_response]
        
        # Mock tool execution result
        self.search_tool.execute = Mock(return_value="[Introduction to AI - Lesson 1]\nMachine learning basics content")
        
        result = self.ai_generator.generate_response(
            query="What are machine learning basics?",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify final response
        self.assertEqual(result, "Based on the course content, machine learning is...")
        
        # Verify tool was executed correctly
        self.search_tool.execute.assert_called_once_with(
            query="machine learning basics",
            course_name="Introduction to AI"
        )
        
        # Verify two API calls were made (initial + follow-up)
        self.assertEqual(self.mock_client.messages.create.call_count, 2)
        
        # Verify second call structure
        second_call_args = self.mock_client.messages.create.call_args_list[1]
        messages = second_call_args.kwargs['messages']
        
        # Should have original user message, assistant tool use, and tool result
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]['role'], 'user')
        self.assertEqual(messages[1]['role'], 'assistant')
        self.assertEqual(messages[2]['role'], 'user')
        
        # Verify tool result structure
        tool_result = messages[2]['content'][0]
        self.assertEqual(tool_result['type'], 'tool_result')
        self.assertEqual(tool_result['tool_use_id'], 'tool_use_123')
        self.assertIn("Machine learning basics content", tool_result['content'])
    
    def test_multiple_tool_usage_in_response(self):
        """Test handling of multiple tool calls in a single response"""
        # Mock response with multiple tool uses
        initial_response = Mock()
        initial_response.stop_reason = "tool_use"

        # Create two tool use content blocks
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.name = "search_course_content"
        tool_block_1.id = "tool_use_1"
        tool_block_1.input = {"query": "python basics"}

        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.name = "search_course_content"
        tool_block_2.id = "tool_use_2"
        tool_block_2.input = {"query": "advanced python", "course_name": "Python Course"}

        initial_response.content = [tool_block_1, tool_block_2]

        # Mock final response
        final_response = self._create_text_response("Here's information from both searches...")
        
        self.mock_client.messages.create.side_effect = [initial_response, final_response]
        
        # Mock tool execution results
        self.search_tool.execute = Mock(side_effect=[
            "Python basics content",
            "Advanced Python content"
        ])
        
        result = self.ai_generator.generate_response(
            query="Tell me about Python",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify final response
        self.assertEqual(result, "Here's information from both searches...")
        
        # Verify both tools were executed
        self.assertEqual(self.search_tool.execute.call_count, 2)
        
        # Verify tool calls
        expected_calls = [
            unittest.mock.call(query="python basics"),
            unittest.mock.call(query="advanced python", course_name="Python Course")
        ]
        self.search_tool.execute.assert_has_calls(expected_calls)
    
    def test_tool_execution_error_handling(self):
        """Test handling of errors during tool execution"""
        # Mock response with tool use
        initial_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_123",
            tool_input={"query": "test query"}
        )

        # Mock final response
        final_response = self._create_text_response("I encountered an error while searching...")
        
        self.mock_client.messages.create.side_effect = [initial_response, final_response]
        
        # Mock tool execution to return error
        self.search_tool.execute = Mock(return_value="Database connection failed")
        
        result = self.ai_generator.generate_response(
            query="Test query",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify error response
        self.assertEqual(result, "I encountered an error while searching...")
        
        # Verify tool was executed
        self.search_tool.execute.assert_called_once()
        
        # Verify error was passed to Claude in tool result
        second_call_args = self.mock_client.messages.create.call_args_list[1]
        tool_result = second_call_args.kwargs['messages'][2]['content'][0]
        self.assertEqual(tool_result['content'], "Database connection failed")
    
    def test_tool_definitions_format(self):
        """Test that tool definitions are correctly formatted for Anthropic API"""
        tools = self.tool_manager.get_tool_definitions()
        
        # Should have two tools (CourseSearchTool and CourseOutlineTool)
        self.assertEqual(len(tools), 2)
        
        # Check tool names
        tool_names = [tool['name'] for tool in tools]
        self.assertIn('search_course_content', tool_names)
        self.assertIn('get_course_outline', tool_names)
        
        # Test search tool definition
        search_tool = next(tool for tool in tools if tool['name'] == 'search_course_content')
        
        # Verify required fields
        self.assertIn('name', search_tool)
        self.assertIn('description', search_tool)
        self.assertIn('input_schema', search_tool)
        
        # Verify input schema structure
        schema = search_tool['input_schema']
        self.assertEqual(schema['type'], 'object')
        self.assertIn('properties', schema)
        self.assertIn('required', schema)
        
        # Verify required properties
        self.assertIn('query', schema['required'])
        self.assertIn('query', schema['properties'])
        
        # Verify optional properties exist
        self.assertIn('course_name', schema['properties'])
        self.assertIn('lesson_number', schema['properties'])
        
        # Test outline tool definition
        outline_tool = next(tool for tool in tools if tool['name'] == 'get_course_outline')
        
        # Verify required fields
        self.assertIn('name', outline_tool)
        self.assertIn('description', outline_tool)
        self.assertIn('input_schema', outline_tool)
        
        # Verify outline tool schema
        outline_schema = outline_tool['input_schema']
        self.assertEqual(outline_schema['type'], 'object')
        self.assertIn('properties', outline_schema)
        self.assertIn('required', outline_schema)
        self.assertIn('course_title', outline_schema['required'])
        self.assertIn('course_title', outline_schema['properties'])
    
    def test_conversation_history_integration(self):
        """Test that conversation history is properly included with tools"""
        # Mock response without tool use
        mock_response = self._create_text_response("Response with history context")
        
        self.mock_client.messages.create.return_value = mock_response
        
        conversation_history = "User: Previous question\nAssistant: Previous answer"
        
        result = self.ai_generator.generate_response(
            query="Follow-up question",
            conversation_history=conversation_history,
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify API call included conversation history
        call_args = self.mock_client.messages.create.call_args
        system_content = call_args.kwargs['system']
        
        self.assertIn("Previous conversation:", system_content)
        self.assertIn("Previous question", system_content)
        self.assertIn("Previous answer", system_content)
    
    def test_unknown_tool_handling(self):
        """Test handling of unknown tool names"""
        # Mock response requesting unknown tool
        initial_response = self._create_tool_use_response(
            tool_name="unknown_tool",
            tool_id="tool_use_123",
            tool_input={"query": "test"}
        )

        # Mock final response
        final_response = self._create_text_response("I apologize for the error...")
        
        self.mock_client.messages.create.side_effect = [initial_response, final_response]
        
        result = self.ai_generator.generate_response(
            query="Test query",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify error handling
        self.assertEqual(result, "I apologize for the error...")
        
        # Verify error message was passed to Claude
        second_call_args = self.mock_client.messages.create.call_args_list[1]
        tool_result = second_call_args.kwargs['messages'][2]['content'][0]
        self.assertIn("Tool 'unknown_tool' not found", tool_result['content'])
    
    def test_system_prompt_content(self):
        """Test that system prompt contains correct tool guidance"""
        # Mock response
        mock_response = self._create_text_response("Test response")
        
        self.mock_client.messages.create.return_value = mock_response
        
        self.ai_generator.generate_response(
            query="Test query",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify system prompt content
        call_args = self.mock_client.messages.create.call_args
        system_content = call_args.kwargs['system']
        
        # Check for key tool usage instructions
        # Note: The system prompt is for Poolula business, but the test is using course tools
        # We should check for the actual system prompt content regardless of tools registered
        self.assertIn("Up to 2 sequential tool calls per query", system_content)
        self.assertIn("query_database", system_content)
        self.assertIn("search_document_content", system_content)
        self.assertIn("list_business_documents", system_content)

    def test_sequential_tool_calling_two_rounds(self):
        """Test that sequential tool calling works across 2 rounds"""
        # Mock round 1 response with tool use
        round1_response = self._create_tool_use_response(
            tool_name="get_course_outline",
            tool_id="tool_use_1",
            tool_input={"course_title": "Machine Learning Basics"}
        )

        # Mock round 2 response with tool use
        round2_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_2",
            tool_input={"query": "lesson 3", "course_name": "Machine Learning Basics"}
        )

        # Mock final response without tools
        final_response = self._create_text_response("Lesson 3 covers supervised learning algorithms including...")
        
        self.mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
        
        # Mock tool execution results
        self.outline_tool.execute = Mock(return_value="Course: Machine Learning Basics\nLesson 1: Introduction\nLesson 2: Data Preprocessing\nLesson 3: Supervised Learning")
        self.search_tool.execute = Mock(return_value="Lesson 3 - Supervised Learning: Classification and regression algorithms...")
        
        result = self.ai_generator.generate_response(
            query="What does lesson 3 cover in the Machine Learning Basics course?",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify final response
        self.assertEqual(result, "Lesson 3 covers supervised learning algorithms including...")
        
        # Verify both tools were executed in sequence
        self.outline_tool.execute.assert_called_once_with(course_title="Machine Learning Basics")
        self.search_tool.execute.assert_called_once_with(query="lesson 3", course_name="Machine Learning Basics")
        
        # Verify three API calls were made (2 rounds + 1 final)
        self.assertEqual(self.mock_client.messages.create.call_count, 3)
        
        # Verify message accumulation across rounds
        final_call_args = self.mock_client.messages.create.call_args_list[2]
        messages = final_call_args.kwargs['messages']
        
        # Should have: user query → assistant round1 → user tool_results → assistant round2 → user tool_results
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0]['role'], 'user')  # Original query
        self.assertEqual(messages[1]['role'], 'assistant')  # Round 1 tool use
        self.assertEqual(messages[2]['role'], 'user')  # Round 1 tool results
        self.assertEqual(messages[3]['role'], 'assistant')  # Round 2 tool use
        self.assertEqual(messages[4]['role'], 'user')  # Round 2 tool results

    def test_sequential_tool_calling_early_termination(self):
        """Test that sequential tool calling terminates early when Claude doesn't need more tools"""
        # Mock round 1 response with tool use
        round1_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_1",
            tool_input={"query": "python basics"}
        )

        # Mock round 2 response without tool use (early termination)
        round2_response = self._create_text_response("Python basics include variables, data types, and control structures.")
        
        self.mock_client.messages.create.side_effect = [round1_response, round2_response]
        
        # Mock tool execution result
        self.search_tool.execute = Mock(return_value="Python fundamentals content...")
        
        result = self.ai_generator.generate_response(
            query="What are Python basics?",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify response from round 2 (early termination)
        self.assertEqual(result, "Python basics include variables, data types, and control structures.")
        
        # Verify only one tool was executed
        self.assertEqual(self.search_tool.execute.call_count, 1)
        self.search_tool.execute.assert_called_once_with(query="python basics")
        
        # Verify only two API calls were made (no final synthesis needed)
        self.assertEqual(self.mock_client.messages.create.call_count, 2)

    def test_sequential_tool_calling_error_handling(self):
        """Test error handling during sequential tool calling"""
        # Mock round 1 response with tool use
        round1_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_1",
            tool_input={"query": "test query"}
        )

        # Mock final response after error
        final_response = self._create_text_response("I encountered an error while searching.")
        
        self.mock_client.messages.create.side_effect = [round1_response, final_response]
        
        # Mock tool execution to raise an exception
        self.search_tool.execute = Mock(side_effect=Exception("Database connection failed"))
        
        result = self.ai_generator.generate_response(
            query="Test query",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify error response
        self.assertEqual(result, "I encountered an error while searching.")
        
        # Verify tool was called but failed
        self.search_tool.execute.assert_called_once()
        
        # Verify two API calls were made (round 1 + final synthesis)
        self.assertEqual(self.mock_client.messages.create.call_count, 2)
        
        # Verify error was passed to Claude in tool result
        final_call_args = self.mock_client.messages.create.call_args_list[1]
        messages = final_call_args.kwargs['messages']
        tool_result = messages[2]['content'][0]
        self.assertIn("Tool execution failed", tool_result['content'])

    def test_max_rounds_limit(self):
        """Test that sequential tool calling respects max rounds limit"""
        # Mock responses for both rounds with tool use
        round1_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_1",
            tool_input={"query": "first search"}
        )

        round2_response = self._create_tool_use_response(
            tool_name="search_course_content",
            tool_id="tool_use_2",
            tool_input={"query": "second search"}
        )

        # Mock final synthesis response
        final_response = self._create_text_response("Based on both searches, here's the comprehensive answer...")
        
        self.mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
        
        # Mock tool execution results
        self.search_tool.execute = Mock(side_effect=[
            "First search results...",
            "Second search results..."
        ])
        
        result = self.ai_generator.generate_response(
            query="Complex query requiring multiple searches",
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )
        
        # Verify final synthesized response
        self.assertEqual(result, "Based on both searches, here's the comprehensive answer...")
        
        # Verify both tools were executed
        self.assertEqual(self.search_tool.execute.call_count, 2)
        
        # Verify three API calls were made (2 rounds + 1 final synthesis)
        self.assertEqual(self.mock_client.messages.create.call_count, 3)
        
        # Verify final call has no tools (synthesis phase)
        final_call_args = self.mock_client.messages.create.call_args_list[2]
        self.assertNotIn('tools', final_call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
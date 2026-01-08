import unittest
from unittest.mock import Mock, MagicMock, patch

from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.vector_store import SearchResults


class MockConfig:
    """Mock configuration object for testing"""
    def __init__(self):
        self.CHUNK_SIZE = 1000
        self.CHUNK_OVERLAP = 100
        self.CHROMA_PATH = "/tmp/test_chroma"
        self.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        self.MAX_RESULTS = 5
        self.LLM_PROVIDER = "anthropic"  # Added for provider factory
        self.ANTHROPIC_API_KEY = "test-key"
        self.ANTHROPIC_MODEL = "claude-3-sonnet"
        self.MAX_HISTORY = 10
        self.METADATA_CSV_PATH = "/tmp/test_metadata.csv"
        self.CACHE_TTL_MINUTES = 5


class TestRAGSystem(unittest.TestCase):
    """Test suite for RAG system content-query handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig()
        
        # Mock all the dependencies
        with patch('apps.chatbot.rag_system.DocumentProcessor') as mock_doc_proc, \
             patch('apps.chatbot.rag_system.VectorStore') as mock_vector_store, \
             patch('apps.chatbot.rag_system.AIGenerator') as mock_ai_gen, \
             patch('apps.chatbot.rag_system.SessionManager') as mock_session_mgr:
            
            # Create mocked instances
            self.mock_doc_processor = mock_doc_proc.return_value
            self.mock_vector_store = mock_vector_store.return_value
            self.mock_ai_generator = mock_ai_gen.return_value
            self.mock_session_manager = mock_session_mgr.return_value
            
            # Create RAG system
            self.rag_system = RAGSystem(self.config)
    
    def test_query_content_search_success(self):
        """Test successful content query with course search"""
        # Mock AI generator to simulate tool usage
        self.mock_ai_generator.generate_response.return_value = "Based on the course content, machine learning is a subset of AI..."
        
        # Mock tool manager to return sources
        mock_sources = [
            {
                "text": "Introduction to AI - Lesson 1",
                "link": "https://example.com/lesson1",
                "course_title": "Introduction to AI",
                "lesson_number": 1
            }
        ]
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query
        response, sources = self.rag_system.query("What is machine learning?")
        
        # Verify AI generator was called correctly
        self.mock_ai_generator.generate_response.assert_called_once()
        call_args = self.mock_ai_generator.generate_response.call_args
        
        # Check query is passed through without modification (system prompt handles context)
        expected_prompt = "What is machine learning?"
        self.assertEqual(call_args.kwargs['query'], expected_prompt)
        
        # Check tools were provided
        self.assertIsNotNone(call_args.kwargs['tools'])
        self.assertIsNotNone(call_args.kwargs['tool_manager'])
        
        # Verify response and sources
        self.assertEqual(response, "Based on the course content, machine learning is a subset of AI...")
        self.assertEqual(sources, mock_sources)
        
        # Verify sources were reset after retrieval
        self.rag_system.tool_manager.reset_sources.assert_called_once()
    
    def test_query_with_session_history(self):
        """Test query with conversation history"""
        session_id = "test_session_123"
        mock_history = "User: Previous question\nAssistant: Previous answer"
        
        # Mock session manager
        self.mock_session_manager.get_conversation_history.return_value = mock_history
        self.mock_session_manager.add_exchange = Mock()
        
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Follow-up response"
        
        # Mock empty sources
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query with session
        response, sources = self.rag_system.query("Follow-up question", session_id)
        
        # Verify session history was retrieved
        self.mock_session_manager.get_conversation_history.assert_called_once_with(session_id)
        
        # Verify history was passed to AI generator
        call_args = self.mock_ai_generator.generate_response.call_args
        self.assertEqual(call_args.kwargs['conversation_history'], mock_history)
        
        # Verify conversation was updated
        self.mock_session_manager.add_exchange.assert_called_once_with(
            session_id, "Follow-up question", "Follow-up response"
        )
    
    def test_query_without_session(self):
        """Test query without session management"""
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Direct response"
        
        # Mock empty sources
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query without session
        response, sources = self.rag_system.query("Direct question")
        
        # Verify no session methods were called
        self.mock_session_manager.get_conversation_history.assert_not_called()
        self.mock_session_manager.add_exchange.assert_not_called()
        
        # Verify AI generator was called without history
        call_args = self.mock_ai_generator.generate_response.call_args
        self.assertIsNone(call_args.kwargs['conversation_history'])
    
    def test_query_tool_definitions_integration(self):
        """Test that tool definitions are properly integrated"""
        # Mock tool manager methods
        mock_tool_definitions = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object"}
            }
        ]
        self.rag_system.tool_manager.get_tool_definitions = Mock(return_value=mock_tool_definitions)
        
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Tool-based response"
        
        # Mock empty sources
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query
        response, sources = self.rag_system.query("Test query")
        
        # Verify tool definitions were retrieved and passed
        self.rag_system.tool_manager.get_tool_definitions.assert_called_once()
        
        call_args = self.mock_ai_generator.generate_response.call_args
        self.assertEqual(call_args.kwargs['tools'], mock_tool_definitions)
        self.assertEqual(call_args.kwargs['tool_manager'], self.rag_system.tool_manager)
    
    def test_query_sources_tracking(self):
        """Test source tracking through the query process"""
        # Mock multiple sources from different tools
        mock_sources = [
            {
                "text": "Course A - Lesson 1",
                "link": "https://example.com/courseA/lesson1",
                "course_title": "Course A",
                "lesson_number": 1
            },
            {
                "text": "Course B - Lesson 2",
                "link": None,
                "course_title": "Course B",
                "lesson_number": 2
            }
        ]
        
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Response based on multiple sources"
        
        # Mock sources retrieval
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query
        response, sources = self.rag_system.query("Multi-source query")
        
        # Verify sources are returned correctly
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["course_title"], "Course A")
        self.assertEqual(sources[1]["course_title"], "Course B")
        self.assertEqual(sources[0]["link"], "https://example.com/courseA/lesson1")
        self.assertIsNone(sources[1]["link"])
        
        # Verify reset was called
        self.rag_system.tool_manager.reset_sources.assert_called_once()
    
    def test_query_prompt_formatting(self):
        """Test that queries are passed through without modification (prompt formatting handled by system prompt)"""
        test_cases = [
            ("What is Python?", "What is Python?"),
            ("How do I use loops?", "How do I use loops?"),
            ("", ""),
            ("Complex query with symbols !@#$%", "Complex query with symbols !@#$%")
        ]
        
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Test response"
        
        # Mock empty sources
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        for input_query, expected_prompt in test_cases:
            with self.subTest(query=input_query):
                # Reset mock to clear previous calls
                self.mock_ai_generator.generate_response.reset_mock()
                
                # Execute query
                self.rag_system.query(input_query)
                
                # Verify prompt formatting
                call_args = self.mock_ai_generator.generate_response.call_args
                self.assertEqual(call_args.kwargs['query'], expected_prompt)
    
    def test_query_error_handling(self):
        """Test error handling in query processing"""
        # Mock AI generator to raise an exception
        self.mock_ai_generator.generate_response.side_effect = Exception("AI service error")
        
        # Mock empty sources (should still be called for cleanup)
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query and expect exception
        with self.assertRaises(Exception) as context:
            self.rag_system.query("Test query")
        
        self.assertIn("AI service error", str(context.exception))
        
        # Verify cleanup still happens
        self.rag_system.tool_manager.get_last_sources.assert_called_once()
        self.rag_system.tool_manager.reset_sources.assert_called_once()
    
    def test_query_session_error_handling(self):
        """Test error handling in session management"""
        session_id = "test_session"
        
        # Mock session manager to raise exception on history retrieval
        self.mock_session_manager.get_conversation_history.side_effect = Exception("Session error")
        
        # Mock AI response
        self.mock_ai_generator.generate_response.return_value = "Response despite session error"
        
        # Mock empty sources
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute query - should handle session error gracefully
        with self.assertRaises(Exception) as context:
            self.rag_system.query("Test query", session_id)
        
        self.assertIn("Session error", str(context.exception))
    
    def test_integration_component_initialization(self):
        """Test that all components are properly initialized"""
        # Verify all components exist
        self.assertIsNotNone(self.rag_system.document_processor)
        self.assertIsNotNone(self.rag_system.vector_store)
        self.assertIsNotNone(self.rag_system.ai_generator)
        self.assertIsNotNone(self.rag_system.session_manager)
        self.assertIsNotNone(self.rag_system.tool_manager)
        self.assertIsNotNone(self.rag_system.document_search_tool)
        self.assertIsNotNone(self.rag_system.document_list_tool)
        self.assertIsNotNone(self.rag_system.database_tool)

        # Verify tools are registered (now 3 tools: document_search, document_list, database)
        self.assertEqual(len(self.rag_system.tool_manager.tools), 3)
        self.assertIn('search_document_content', self.rag_system.tool_manager.tools)
        self.assertIn('list_business_documents', self.rag_system.tool_manager.tools)
        self.assertIn('query_database', self.rag_system.tool_manager.tools)
    
    @unittest.skip("Course outline functionality not implemented - business documents only")
    def test_query_course_outline_request(self):
        """Test handling of course outline requests"""
        # Mock AI response that would use outline tool
        self.mock_ai_generator.generate_response.return_value = """Course: Introduction to Python
Link: https://example.com/python-course
Lessons:
1. Python Basics
2. Variables and Data Types
3. Control Structures"""
        
        # Mock outline tool sources
        mock_sources = [
            {
                "text": "Introduction to Python - Course Outline",
                "link": "https://example.com/python-course",
                "course_title": "Introduction to Python",
                "lesson_number": None
            }
        ]
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        self.rag_system.tool_manager.reset_sources = Mock()
        
        # Execute outline query
        response, sources = self.rag_system.query("What is the outline for the Python course?")
        
        # Verify response formatting
        self.assertIn("Course: Introduction to Python", response)
        self.assertIn("Lessons:", response)
        self.assertIn("1. Python Basics", response)
        
        # Verify outline-specific sources
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["course_title"], "Introduction to Python")
        self.assertIsNone(sources[0]["lesson_number"])
    
    def test_query_content_vs_general_knowledge(self):
        """Test system handles both content queries and general knowledge"""
        # Test content query (should use tools)
        self.mock_ai_generator.generate_response.return_value = "Based on the course material, Python is..."
        mock_sources = [{"text": "Python Course - Lesson 1", "link": None, "course_title": "Python", "lesson_number": 1}]
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        self.rag_system.tool_manager.reset_sources = Mock()
        
        response, sources = self.rag_system.query("What is Python syntax from the course?")
        
        # Should have sources from course content
        self.assertEqual(len(sources), 1)
        
        # Reset mocks for general knowledge test
        self.mock_ai_generator.generate_response.reset_mock()
        self.rag_system.tool_manager.get_last_sources.reset_mock()
        self.rag_system.tool_manager.reset_sources.reset_mock()
        
        # Test general knowledge (should not use tools)
        self.mock_ai_generator.generate_response.return_value = "Generally speaking, Python is a programming language..."
        self.rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        self.rag_system.tool_manager.reset_sources = Mock()
        
        response, sources = self.rag_system.query("What is the weather today?")
        
        # Should have no sources (general knowledge)
        self.assertEqual(len(sources), 0)


if __name__ == '__main__':
    unittest.main()
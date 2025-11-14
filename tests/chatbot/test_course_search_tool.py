import unittest
from unittest.mock import Mock, MagicMock

from apps.chatbot.search_tools import CourseSearchTool
from apps.chatbot.vector_store import SearchResults


class TestCourseSearchTool(unittest.TestCase):
    """Test suite for CourseSearchTool.execute method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.tool = CourseSearchTool(self.mock_vector_store)
    
    def test_execute_basic_query_success(self):
        """Test basic query execution with successful results"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["Sample course content about machine learning"],
            metadata=[{
                'course_title': 'Introduction to AI',
                'lesson_number': 1
            }],
            distances=[0.15],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(query="machine learning")
        
        # Verify search was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="machine learning",
            course_name=None,
            lesson_number=None
        )
        
        # Verify result format
        self.assertIn("[Introduction to AI - Lesson 1]", result)
        self.assertIn("Sample course content about machine learning", result)
        
        # Verify sources are tracked
        self.assertEqual(len(self.tool.last_sources), 1)
        source = self.tool.last_sources[0]
        self.assertEqual(source['course_title'], 'Introduction to AI')
        self.assertEqual(source['lesson_number'], 1)
    
    def test_execute_with_course_name_filter(self):
        """Test query execution with course name filter"""
        mock_results = SearchResults(
            documents=["Course specific content"],
            metadata=[{
                'course_title': 'Advanced Python',
                'lesson_number': 3
            }],
            distances=[0.12],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="functions",
            course_name="Advanced Python"
        )
        
        # Verify search was called with course filter
        self.mock_vector_store.search.assert_called_once_with(
            query="functions",
            course_name="Advanced Python",
            lesson_number=None
        )
        
        # Verify result format includes course name
        self.assertIn("[Advanced Python - Lesson 3]", result)
        self.assertIn("Course specific content", result)
    
    def test_execute_with_lesson_number_filter(self):
        """Test query execution with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{
                'course_title': 'Data Science Basics',
                'lesson_number': 2
            }],
            distances=[0.08],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="pandas",
            lesson_number=2
        )
        
        # Verify search was called with lesson filter
        self.mock_vector_store.search.assert_called_once_with(
            query="pandas",
            course_name=None,
            lesson_number=2
        )
        
        # Verify result format
        self.assertIn("[Data Science Basics - Lesson 2]", result)
        self.assertIn("Lesson specific content", result)
    
    def test_execute_with_both_filters(self):
        """Test query execution with both course name and lesson number filters"""
        mock_results = SearchResults(
            documents=["Highly specific content"],
            metadata=[{
                'course_title': 'Web Development',
                'lesson_number': 5
            }],
            distances=[0.05],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="authentication",
            course_name="Web Development",
            lesson_number=5
        )
        
        # Verify search was called with both filters
        self.mock_vector_store.search.assert_called_once_with(
            query="authentication",
            course_name="Web Development",
            lesson_number=5
        )
        
        # Verify result format
        self.assertIn("[Web Development - Lesson 5]", result)
        self.assertIn("Highly specific content", result)
    
    def test_execute_search_error(self):
        """Test handling of search errors"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(query="test query")
        
        # Verify error is returned directly
        self.assertEqual(result, "Database connection failed")
        
        # Verify no sources are tracked for errors
        self.assertEqual(len(self.tool.last_sources), 0)
    
    def test_execute_empty_results_no_filters(self):
        """Test handling of empty results without filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(query="nonexistent topic")
        
        # Verify empty result message
        self.assertEqual(result, "No relevant content found.")
        
        # Verify no sources are tracked for empty results
        self.assertEqual(len(self.tool.last_sources), 0)
    
    def test_execute_empty_results_with_course_filter(self):
        """Test handling of empty results with course filter"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="nonexistent topic",
            course_name="Nonexistent Course"
        )
        
        # Verify empty result message includes course filter info
        self.assertEqual(result, "No relevant content found in course 'Nonexistent Course'.")
    
    def test_execute_empty_results_with_lesson_filter(self):
        """Test handling of empty results with lesson filter"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="nonexistent topic",
            lesson_number=99
        )
        
        # Verify empty result message includes lesson filter info
        self.assertEqual(result, "No relevant content found in lesson 99.")
    
    def test_execute_empty_results_with_both_filters(self):
        """Test handling of empty results with both filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(
            query="nonexistent topic",
            course_name="Test Course",
            lesson_number=5
        )
        
        # Verify empty result message includes both filter info
        self.assertEqual(result, "No relevant content found in course 'Test Course' in lesson 5.")
    
    def test_execute_multiple_results(self):
        """Test handling of multiple search results"""
        mock_results = SearchResults(
            documents=[
                "First result about topic",
                "Second result about topic"
            ],
            metadata=[
                {'course_title': 'Course A', 'lesson_number': 1},
                {'course_title': 'Course B', 'lesson_number': 2}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        # Mock get_lesson_link to return None (no links available)
        self.mock_vector_store.get_lesson_link.return_value = None
        
        result = self.tool.execute(query="topic")
        
        # Verify both results are formatted
        self.assertIn("[Course A - Lesson 1]", result)
        self.assertIn("First result about topic", result)
        self.assertIn("[Course B - Lesson 2]", result)
        self.assertIn("Second result about topic", result)
        
        # Verify both sources are tracked
        self.assertEqual(len(self.tool.last_sources), 2)
        self.assertEqual(self.tool.last_sources[0]['course_title'], 'Course A')
        self.assertEqual(self.tool.last_sources[1]['course_title'], 'Course B')
    
    def test_execute_with_lesson_links(self):
        """Test handling of lesson links in sources"""
        mock_results = SearchResults(
            documents=["Content with link"],
            metadata=[{
                'course_title': 'Linked Course',
                'lesson_number': 1
            }],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        # Mock get_lesson_link to return a URL
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        result = self.tool.execute(query="test")
        
        # Verify link is included in source
        source = self.tool.last_sources[0]
        self.assertEqual(source['link'], "https://example.com/lesson1")
        
        # Verify get_lesson_link was called correctly
        self.mock_vector_store.get_lesson_link.assert_called_once_with('Linked Course', 1)
    
    def test_execute_missing_metadata_fields(self):
        """Test handling of missing metadata fields"""
        mock_results = SearchResults(
            documents=["Content with incomplete metadata"],
            metadata=[{
                # Missing course_title and lesson_number
            }],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        result = self.tool.execute(query="test")
        
        # Verify default values are used
        self.assertIn("[unknown]", result)
        self.assertIn("Content with incomplete metadata", result)
        
        # Verify source uses default values
        source = self.tool.last_sources[0]
        self.assertEqual(source['course_title'], 'unknown')
        self.assertIsNone(source['lesson_number'])
    
    def test_sources_reset_between_calls(self):
        """Test that sources are properly managed between calls"""
        # First call
        mock_results_1 = SearchResults(
            documents=["First call result"],
            metadata=[{'course_title': 'Course 1', 'lesson_number': 1}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results_1
        
        self.tool.execute(query="first query")
        self.assertEqual(len(self.tool.last_sources), 1)
        
        # Second call with different results
        mock_results_2 = SearchResults(
            documents=["Second call result"],
            metadata=[{'course_title': 'Course 2', 'lesson_number': 2}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results_2
        
        self.tool.execute(query="second query")
        
        # Verify sources are replaced, not accumulated
        self.assertEqual(len(self.tool.last_sources), 1)
        self.assertEqual(self.tool.last_sources[0]['course_title'], 'Course 2')


if __name__ == '__main__':
    unittest.main()
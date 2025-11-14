import pytest
import tempfile
import os
from apps.chatbot.document_processor import DocumentProcessor
from apps.chatbot.models import Course, Lesson, CourseChunk

class TestDocumentProcessor:
    """Test cases for DocumentProcessor class"""

    def test_chunk_text_basic(self, document_processor):
        """Test basic sentence-based chunking"""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = document_processor.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        
        # All chunks should be within size limit
        for chunk in chunks:
            assert len(chunk) <= document_processor.chunk_size

    def test_chunk_text_with_overlap(self, document_processor):
        """Test overlap functionality"""
        # Use a longer text that will definitely be split
        text = ("This is the first sentence. " * 10 + 
                "This is the second sentence. " * 10)
        
        chunks = document_processor.chunk_text(text)
        
        assert len(chunks) >= 2  # Should create multiple chunks
        
        # Check that chunks respect size limits
        for chunk in chunks:
            assert len(chunk) <= document_processor.chunk_size

    def test_chunk_text_single_long_sentence(self, document_processor):
        """Test chunking with a single sentence longer than chunk_size"""
        long_sentence = "This is a very long sentence " * 20 + "."
        chunks = document_processor.chunk_text(long_sentence)
        
        # Should still create at least one chunk even if it exceeds size
        assert len(chunks) >= 1

    def test_chunk_text_empty_input(self, document_processor):
        """Test chunking with empty or whitespace input"""
        assert document_processor.chunk_text("") == []
        assert document_processor.chunk_text("   ") == []
        assert document_processor.chunk_text("\n\n\n") == []

    def test_read_file(self, document_processor):
        """Test file reading functionality"""
        test_content = "This is test content.\nSecond line."
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            content = document_processor.read_file(temp_path)
            assert content == test_content
        finally:
            os.unlink(temp_path)

    def test_read_file_encoding_fallback(self, document_processor):
        """Test file reading with encoding issues"""
        # Create a file with some content
        test_content = "This is test content with special chars: àáâã"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            content = document_processor.read_file(temp_path)
            assert "This is test content" in content
        finally:
            os.unlink(temp_path)

    def test_process_course_document_basic(self, document_processor):
        """Test basic course document processing"""
        content = """Course Title: Introduction to Machine Learning
Course Link: https://example.com/ml-course
Course Instructor: Dr. Jane Smith

Lesson 1: Introduction to ML
Lesson Link: https://example.com/lesson1
Machine learning is a subset of artificial intelligence.

Lesson 2: Supervised Learning
Lesson Link: https://example.com/lesson2
Supervised learning uses labeled training data."""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            course, chunks = document_processor.process_course_document(temp_path)
            
            # Verify course object
            assert isinstance(course, Course)
            assert course.title == "Introduction to Machine Learning"
            assert course.course_link == "https://example.com/ml-course"
            assert course.instructor == "Dr. Jane Smith"
            assert len(course.lessons) == 2
            
            # Verify lessons
            assert course.lessons[0].lesson_number == 1
            assert course.lessons[0].title == "Introduction to ML"
            assert course.lessons[0].lesson_link == "https://example.com/lesson1"
            
            assert course.lessons[1].lesson_number == 2
            assert course.lessons[1].title == "Supervised Learning"
            assert course.lessons[1].lesson_link == "https://example.com/lesson2"
            
            # Verify chunks
            assert len(chunks) > 0
            assert all(isinstance(chunk, CourseChunk) for chunk in chunks)
            assert all(chunk.course_title == course.title for chunk in chunks)
            
        finally:
            os.unlink(temp_path)

    def test_process_course_document_minimal(self, document_processor):
        """Test course document with minimal metadata"""
        content = """Basic Course Title

Some course content here.
More content follows."""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            course, chunks = document_processor.process_course_document(temp_path)
            
            # Should use first line as title
            assert course.title == "Basic Course Title"
            assert course.instructor is None
            assert course.course_link is None
            
            # Should create chunks even without lesson structure
            assert len(chunks) > 0
            
        finally:
            os.unlink(temp_path)

    def test_process_course_document_no_lessons(self, document_processor):
        """Test course document without lesson markers"""
        content = """Course Title: Test Course
Course Instructor: Test Instructor

This is content without lesson markers.
It should still be processed into chunks."""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            course, chunks = document_processor.process_course_document(temp_path)
            
            assert course.title == "Test Course"
            assert len(course.lessons) == 0  # No lessons found
            assert len(chunks) > 0  # But chunks should still be created
            
        finally:
            os.unlink(temp_path)

    def test_chunk_text_normalization(self, document_processor):
        """Test text normalization in chunking"""
        text_with_extra_spaces = "This  has   extra    spaces.\n\n\nAnd  extra\t\twhitespace."
        chunks = document_processor.chunk_text(text_with_extra_spaces)
        
        assert len(chunks) > 0
        # Verify whitespace is normalized
        for chunk in chunks:
            assert "  " not in chunk  # No double spaces
            assert "\n" not in chunk  # No newlines
            assert "\t" not in chunk  # No tabs

    def test_edge_cases(self, document_processor):
        """Test various edge cases"""
        # Empty file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write("")
            temp_path = f.name
        
        try:
            course, chunks = document_processor.process_course_document(temp_path)
            # Should handle empty file gracefully
            assert isinstance(course, Course)
            assert len(chunks) == 0
        finally:
            os.unlink(temp_path)

    def test_document_processor_custom_settings(self):
        """Test DocumentProcessor with custom chunk settings"""
        processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)
        
        assert processor.chunk_size == 50
        assert processor.chunk_overlap == 10
        
        text = "Short sentence. Another short sentence. Third sentence."
        chunks = processor.chunk_text(text)
        
        # Should respect the smaller chunk size
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_course_chunk_metadata(self, document_processor):
        """Test that CourseChunk objects have correct metadata"""
        content = """Course Title: Test Course

Lesson 1: Test Lesson
This is lesson content for testing chunk metadata."""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            course, chunks = document_processor.process_course_document(temp_path)
            
            assert len(chunks) > 0
            chunk = chunks[0]
            
            assert chunk.course_title == "Test Course"
            assert chunk.lesson_number == 1
            assert chunk.chunk_index == 0
            assert "Lesson 1 content:" in chunk.content
            
        finally:
            os.unlink(temp_path)
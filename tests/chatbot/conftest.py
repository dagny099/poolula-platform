import pytest
from apps.chatbot.session_manager import SessionManager
from apps.chatbot.document_processor import DocumentProcessor

@pytest.fixture
def session_manager():
    """Create a SessionManager instance with default settings"""
    return SessionManager(max_history=3)

@pytest.fixture
def document_processor():
    """Create a DocumentProcessor instance with test settings"""
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)
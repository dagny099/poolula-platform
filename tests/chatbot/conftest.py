import pytest
from unittest.mock import Mock, patch
from apps.chatbot.session_manager import SessionManager
from apps.chatbot.document_processor import DocumentProcessor
from apps.chatbot.ai_generator import AIGenerator
from apps.chatbot.llm_providers.anthropic_provider import AnthropicProvider

@pytest.fixture
def session_manager():
    """Create a SessionManager instance with default settings"""
    return SessionManager(max_history=3)

@pytest.fixture
def document_processor():
    """Create a DocumentProcessor instance with test settings"""
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)

@pytest.fixture
def mock_anthropic_provider():
    """Create a mocked Anthropic provider for testing"""
    with patch('anthropic.Anthropic') as mock_anthropic_class:
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        provider = AnthropicProvider("fake-api-key", "claude-3-sonnet")
        provider.mock_client = mock_client  # Expose for test manipulation
        yield provider

@pytest.fixture
def ai_generator(mock_anthropic_provider):
    """Create an AIGenerator with mocked Anthropic provider"""
    return AIGenerator(mock_anthropic_provider)
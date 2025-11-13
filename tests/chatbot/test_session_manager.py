import pytest
from apps.chatbot.session_manager import SessionManager, Message

class TestSessionManager:
    """Test cases for SessionManager class"""

    def test_create_session(self, session_manager):
        """Test session ID generation"""
        session_id = session_manager.create_session()
        
        assert session_id == "session_1"
        assert session_id in session_manager.sessions
        assert session_manager.sessions[session_id] == []
        
        # Test multiple sessions
        session_id2 = session_manager.create_session()
        assert session_id2 == "session_2"
        assert len(session_manager.sessions) == 2

    def test_add_message(self, session_manager):
        """Test message storage and ordering"""
        session_id = session_manager.create_session()
        
        # Add user message
        session_manager.add_message(session_id, "user", "Hello")
        messages = session_manager.sessions[session_id]
        
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        
        # Add assistant message
        session_manager.add_message(session_id, "assistant", "Hi there!")
        messages = session_manager.sessions[session_id]
        
        assert len(messages) == 2
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_add_message_to_nonexistent_session(self, session_manager):
        """Test adding message to session that doesn't exist creates it"""
        session_manager.add_message("nonexistent", "user", "Hello")
        
        assert "nonexistent" in session_manager.sessions
        assert len(session_manager.sessions["nonexistent"]) == 1
        assert session_manager.sessions["nonexistent"][0].content == "Hello"

    def test_conversation_history_limit(self, session_manager):
        """Test max_history enforcement"""
        session_id = session_manager.create_session()
        
        # Add more messages than the limit (max_history = 3, so 6 total messages allowed)
        for i in range(8):
            session_manager.add_message(session_id, "user", f"Message {i}")
        
        messages = session_manager.sessions[session_id]
        
        # Should keep only the last 6 messages (3 * 2)
        assert len(messages) == 6
        assert messages[0].content == "Message 2"  # First 2 messages should be removed
        assert messages[-1].content == "Message 7"

    def test_add_exchange(self, session_manager):
        """Test adding complete question-answer exchange"""
        session_id = session_manager.create_session()
        
        session_manager.add_exchange(session_id, "What is AI?", "AI is artificial intelligence.")
        messages = session_manager.sessions[session_id]
        
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "What is AI?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "AI is artificial intelligence."

    def test_get_formatted_history(self, session_manager):
        """Test history formatting"""
        session_id = session_manager.create_session()
        
        # Test with no messages
        history = session_manager.get_conversation_history(session_id)
        assert history is None
        
        # Add messages and test formatting
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi there!")
        
        history = session_manager.get_conversation_history(session_id)
        expected = "User: Hello\nAssistant: Hi there!"
        assert history == expected

    def test_get_history_nonexistent_session(self, session_manager):
        """Test getting history for nonexistent session"""
        history = session_manager.get_conversation_history("nonexistent")
        assert history is None
        
        history = session_manager.get_conversation_history(None)
        assert history is None

    def test_clear_session(self, session_manager):
        """Test clearing session messages"""
        session_id = session_manager.create_session()
        
        # Add some messages
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi!")
        
        assert len(session_manager.sessions[session_id]) == 2
        
        # Clear session
        session_manager.clear_session(session_id)
        assert len(session_manager.sessions[session_id]) == 0
        
        # Test clearing nonexistent session (should not error)
        session_manager.clear_session("nonexistent")

    def test_message_dataclass(self):
        """Test Message dataclass"""
        message = Message(role="user", content="Test message")
        
        assert message.role == "user"
        assert message.content == "Test message"

    def test_session_manager_custom_max_history(self):
        """Test SessionManager with custom max_history"""
        manager = SessionManager(max_history=2)
        session_id = manager.create_session()
        
        # Add more than max_history * 2 messages
        for i in range(6):
            manager.add_message(session_id, "user", f"Message {i}")
        
        messages = manager.sessions[session_id]
        
        # Should keep only 4 messages (2 * 2)
        assert len(messages) == 4
        assert messages[0].content == "Message 2"
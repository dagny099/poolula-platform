"""
Tests for chat route RAG system initialization

The chat router must not hard-require ANTHROPIC_API_KEY itself: credential
checks are provider-specific and live in RAGSystem's provider factory
(LLM_PROVIDER may be openai or ollama, which don't need an Anthropic key).
"""


def test_get_rag_system_defers_credentials_to_provider_factory(monkeypatch):
    from apps.api.routes import chat

    class DummyConfig:
        """Config with no Anthropic key (e.g. LLM_PROVIDER=ollama setup)"""
        ANTHROPIC_API_KEY = ""
        LLM_PROVIDER = "ollama"

    class DummyRAG:
        def __init__(self, config):
            self.config = config

    monkeypatch.setattr(chat, "Config", DummyConfig)
    monkeypatch.setattr(chat, "RAGSystem", DummyRAG)
    monkeypatch.setattr(chat, "_rag_system", None)

    rag = chat.get_rag_system()
    assert isinstance(rag, DummyRAG)

    # Singleton: second call returns the same instance
    assert chat.get_rag_system() is rag

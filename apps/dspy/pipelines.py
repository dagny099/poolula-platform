from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from apps.chatbot.config import Config
from apps.chatbot.rag_system import RAGSystem

logger = logging.getLogger(__name__)


class RAGBackedDSPyProgram:
    """
    Minimal DSPy-style program that delegates to the existing RAG system.
    This keeps the DSPy artifact format simple (pickled program + metadata) while
    reusing the baseline components for parity testing.
    """

    def __init__(self, signature: str = "question->answer", config_overrides: Optional[Dict[str, Any]] = None):
        self.signature = signature
        self.config_overrides = config_overrides or {}
        self._rag: Optional[RAGSystem] = None

    def _get_rag(self) -> RAGSystem:
        if self._rag is None:
            cfg = Config(**self.config_overrides)
            self._rag = RAGSystem(cfg)
        return self._rag

    def __call__(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        rag = self._get_rag()
        try:
            answer, sources = rag.query(query=question, session_id=session_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG-backed DSPy program failed: %s", exc, exc_info=True)
            raise

        return {
            "answer": answer,
            "sources": sources or [],
            "session_id": session_id,
        }

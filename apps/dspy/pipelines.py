"""
DSPy Pipelines for Poolula Platform

Real DSPy modules with signatures, optimization capability, and tool integration.
"""
import dspy
from typing import Optional, Dict, Any, List
from apps.dspy.signatures import SimpleQA, ContextualQA
from apps.dspy.lm_config import get_configured_lm


class SimpleDSPyQA(dspy.Module):
    """
    Minimal DSPy question-answering pipeline.

    This is a baseline DSPy implementation without tool integration.
    Uses Chain-of-Thought reasoning for answers.
    """

    def __init__(self):
        super().__init__()
        self.generate_answer = dspy.ChainOfThought(SimpleQA)

    def forward(self, question: str) -> dspy.Prediction:
        """
        Answer a question using Chain-of-Thought reasoning.

        Args:
            question: User's question

        Returns:
            dspy.Prediction with answer field
        """
        # Simple chain-of-thought generation
        prediction = self.generate_answer(question=question)
        return prediction


class RetrieveAndAnswerPipeline(dspy.Module):
    """
    DSPy pipeline with retrieval step (no real retrieval yet - placeholder).

    This demonstrates the retrieve → generate pattern we'll use with real tools.
    """

    def __init__(self, k: int = 5):
        super().__init__()
        self.k = k
        self.generate_answer = dspy.ChainOfThought(ContextualQA)

    def forward(self, question: str) -> dspy.Prediction:
        """
        Retrieve context and generate answer.

        Args:
            question: User's question

        Returns:
            dspy.Prediction with answer and context fields
        """
        # Placeholder retrieval (Phase 2 will add real tools)
        context = f"Placeholder context for: {question}"

        # Generate answer using context
        prediction = self.generate_answer(
            context=context,
            question=question
        )

        # Add context to prediction for inspection
        prediction.context = context

        return prediction


# Keep old wrapper for backward compatibility during transition
class RAGBackedDSPyProgram:
    """
    DEPRECATED: Legacy wrapper for baseline RAG system.
    Use SimpleDSPyQA or RetrieveAndAnswerPipeline instead.
    """

    def __init__(self, signature: str = "question->answer", config_overrides: Optional[Dict[str, Any]] = None):
        import warnings
        warnings.warn(
            "RAGBackedDSPyProgram is deprecated. Use SimpleDSPyQA or RetrieveAndAnswerPipeline.",
            DeprecationWarning
        )
        self.signature = signature
        self.config_overrides = config_overrides or {}
        self._rag: Optional[Any] = None

    def __call__(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        from apps.chatbot.rag_system import RAGSystem
        from apps.chatbot.config import Config
        import logging

        logger = logging.getLogger(__name__)

        if self._rag is None:
            config = Config()
            for key, value in self.config_overrides.items():
                setattr(config, key, value)
            self._rag = RAGSystem(config=config)

        try:
            answer, sources = self._rag.query(query=question, session_id=session_id)
        except Exception as exc:
            logger.error("RAG-backed DSPy program failed: %s", exc, exc_info=True)
            raise

        return {
            "answer": answer,
            "sources": sources or [],
            "session_id": session_id,
        }

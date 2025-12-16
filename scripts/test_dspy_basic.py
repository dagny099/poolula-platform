#!/usr/bin/env python3
"""
Test basic DSPy pipeline functionality.

Usage:
    uv run python scripts/test_dspy_basic.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
from apps.dspy.lm_config import configure_dspy_lm
from apps.dspy.pipelines import SimpleDSPyQA, RetrieveAndAnswerPipeline


def test_simple_qa():
    """Test SimpleDSPyQA pipeline"""
    print("\n=== Testing SimpleDSPyQA ===")

    # Configure DSPy
    configure_dspy_lm("anthropic")

    # Create pipeline
    pipeline = SimpleDSPyQA()

    # Test questions
    test_questions = [
        "What is Poolula LLC?",
        "How many rental properties do we own?",
        "What was our rental income last month?"
    ]

    for question in test_questions:
        print(f"\nQ: {question}")
        prediction = pipeline(question=question)
        print(f"A: {prediction.answer}")
        print(f"Rationale: {prediction.rationale if hasattr(prediction, 'rationale') else 'N/A'}")


def test_retrieve_and_answer():
    """Test RetrieveAndAnswerPipeline"""
    print("\n=== Testing RetrieveAndAnswerPipeline ===")

    configure_dspy_lm("anthropic")

    pipeline = RetrieveAndAnswerPipeline(k=5)

    question = "What properties does Poolula LLC own?"
    print(f"\nQ: {question}")

    prediction = pipeline(question=question)
    print(f"Context: {prediction.context}")
    print(f"A: {prediction.answer}")


if __name__ == "__main__":
    test_simple_qa()
    test_retrieve_and_answer()
    print("\n✅ Basic DSPy pipeline tests complete!")

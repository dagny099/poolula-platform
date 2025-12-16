#!/usr/bin/env python3
"""
Test DSPy pipeline with tool integration.

Usage:
    uv run python scripts/test_dspy_tools.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
from apps.dspy.lm_config import configure_dspy_lm
from apps.dspy.pipelines import PoolulaRAGPipeline
from apps.dspy.retrievers import DatabaseRetriever, VectorStoreRetriever


def test_database_retriever():
    """Test DatabaseRetriever"""
    print("\n" + "="*60)
    print("Testing DatabaseRetriever")
    print("="*60)

    retriever = DatabaseRetriever(k=5)

    test_queries = [
        "Show me all properties",
        "What was rental income in July 2025?",
        "List recent transactions"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = retriever(query)
        print(f"Retrieved {len(result.passages)} passages:")
        for i, passage in enumerate(result.passages[:2], 1):
            print(f"\n[Passage {i}]")
            print(passage[:200] + "..." if len(passage) > 200 else passage)


def test_vector_retriever():
    """Test VectorStoreRetriever"""
    print("\n" + "="*60)
    print("Testing VectorStoreRetriever")
    print("="*60)

    retriever = VectorStoreRetriever(k=3)

    query = "insurance coverage for rental property"
    print(f"\nQuery: {query}")

    result = retriever(query)
    print(f"Retrieved {len(result.passages)} passages:")
    for i, passage in enumerate(result.passages, 1):
        print(f"\n[Passage {i}]")
        print(passage[:200] + "..." if len(passage) > 200 else passage)


def test_full_pipeline():
    """Test complete PoolulaRAGPipeline"""
    print("\n" + "="*60)
    print("Testing PoolulaRAGPipeline")
    print("="*60)

    configure_dspy_lm("anthropic")

    pipeline = PoolulaRAGPipeline(use_hybrid=True, k=5)

    test_questions = [
        "What properties does Poolula LLC own?",
        "What was our rental income in August 2025?",
        "What insurance policies do we have?"
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print('='*60)

        prediction = pipeline(question=question)

        print(f"\nRetrieved Context ({len(prediction.passages)} passages):")
        for i, passage in enumerate(prediction.passages[:2], 1):
            print(f"\n[Passage {i}]")
            print(passage[:150] + "..." if len(passage) > 150 else passage)

        print(f"\nAnswer:")
        print(prediction.answer)

        if hasattr(prediction, 'reasoning'):
            print(f"\nReasoning:")
            print(prediction.reasoning)


if __name__ == "__main__":
    try:
        test_database_retriever()
        test_vector_retriever()
        test_full_pipeline()
        print("\n" + "="*60)
        print("✅ DSPy tool integration tests complete!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

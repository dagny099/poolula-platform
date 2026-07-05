#!/usr/bin/env python3
"""
Chatbot Evaluation Harness (CLI)

Runs the golden question set through the chatbot and scores the responses.
Scoring/reporting logic lives in apps/evaluator/chatbot_evaluator.py.

Usage:
    # Live evaluation (requires LLM credentials)
    uv run python scripts/evaluate_chatbot.py
    uv run python scripts/evaluate_chatbot.py --eval-set data/custom_eval.jsonl --verbose

    # Record live responses as a fixture for later offline runs
    uv run python scripts/evaluate_chatbot.py --record-fixture output/chatbot_fixture.json

    # Replay a recorded fixture (no LLM credentials needed)
    uv run python scripts/evaluate_chatbot.py --fixture output/chatbot_fixture.json

    # Also write a human-readable Markdown failure report
    uv run python scripts/evaluate_chatbot.py --markdown output/eval_report.md

Author: Poolula Platform
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.evaluator.base_evaluator import FixtureBackend, RecordingBackend
from apps.evaluator.chatbot_evaluator import ChatbotEvaluator


def build_backend(args):
    """Choose fixture replay or live RAG backend (imported lazily)"""
    if args.fixture:
        print(f"Using fixture backend: {args.fixture} (no LLM calls)")
        return FixtureBackend(args.fixture), None

    print("Initializing RAG system...")
    from apps.chatbot.rag_system import RAGSystem
    from apps.chatbot.config import Config

    rag = RAGSystem(Config())
    backend = lambda question: rag.query(question)  # noqa: E731

    if args.record_fixture:
        recorder = RecordingBackend(backend)
        return recorder, recorder
    return backend, None


def main():
    parser = argparse.ArgumentParser(description="Evaluate chatbot performance")
    parser.add_argument(
        "--eval-set",
        default="apps/evaluator/poolula_eval_set.jsonl",
        help="Path to evaluation question set (JSONL)",
    )
    parser.add_argument(
        "--output",
        default="apps/evaluator/eval_report.json",
        help="Path to save evaluation report (JSON)",
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Optional path to save a Markdown failure report",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Replay recorded responses from this JSON fixture instead of calling the LLM",
    )
    parser.add_argument(
        "--record-fixture",
        default=None,
        help="Record live responses to this JSON fixture for later offline replay",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed results")

    args = parser.parse_args()

    backend, recorder = build_backend(args)

    evaluator = ChatbotEvaluator(query_fn=backend, verbose=args.verbose)
    report = evaluator.run_evaluation(args.eval_set)

    evaluator.save_report(report, args.output)
    if args.markdown:
        evaluator.save_markdown(report, args.markdown)
    if recorder:
        recorder.save(args.record_fixture)

    # Exit with appropriate code
    avg_score = report["average_score"]
    if avg_score >= 0.9:
        print("🎉 Excellent! Score ≥90%")
        sys.exit(0)
    elif avg_score >= 0.7:
        print("✅ Good! Score ≥70%")
        sys.exit(0)
    else:
        print("⚠️  Needs improvement. Score <70%")
        sys.exit(1)


if __name__ == "__main__":
    main()

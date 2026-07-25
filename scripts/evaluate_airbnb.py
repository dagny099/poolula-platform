#!/usr/bin/env python3
"""
Airbnb-Specific Evaluation Harness (CLI)

Validates numerical accuracy of chatbot answers using CSV ground truth.
Scoring/reporting logic lives in apps/evaluator/airbnb_evaluator.py.

Usage:
    # Live evaluation (requires LLM credentials)
    uv run python scripts/evaluate_airbnb.py
    uv run python scripts/evaluate_airbnb.py --verbose

    # Record live responses as a fixture for later offline runs
    uv run python scripts/evaluate_airbnb.py --record-fixture output/airbnb_fixture.json

    # Replay a recorded fixture (no LLM credentials needed)
    uv run python scripts/evaluate_airbnb.py --fixture output/airbnb_fixture.json

    # Also write a human-readable Markdown failure report
    uv run python scripts/evaluate_airbnb.py --markdown output/airbnb_eval_report.md
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.evaluator.airbnb_evaluator import AirbnbEvaluator
from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth
from apps.evaluator.base_evaluator import FixtureBackend, RecordingBackend


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
    parser = argparse.ArgumentParser(
        description="Evaluate Airbnb queries with ground truth validation"
    )
    parser.add_argument(
        "--questions",
        default="apps/evaluator/airbnb_eval_set.jsonl",
        help="Path to Airbnb question set (JSONL)",
    )
    parser.add_argument(
        "--csv",
        default="data/airbnb_12_2024-11_2025.csv",
        help="Path to Airbnb CSV for ground truth",
    )
    parser.add_argument(
        "--output",
        default="data/airbnb_eval_report.json",
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

    print(f"Loading ground truth from {args.csv}...")
    ground_truth = AirbnbGroundTruth(args.csv)

    stats = ground_truth.get_all_statistics()
    print(f"  Loaded {stats['total_reservations']} reservations")
    print(f"  Total revenue: ${Decimal(stats['total_revenue']):,.2f}")
    print(f"  Date range: {stats['date_range']['min']} to {stats['date_range']['max']}\n")

    evaluator = AirbnbEvaluator(query_fn=backend, ground_truth=ground_truth, verbose=args.verbose)
    report = evaluator.run_evaluation(args.questions)

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

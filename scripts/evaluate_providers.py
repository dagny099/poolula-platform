#!/usr/bin/env python3
"""
Multi-Provider Evaluation Script

Runs the same evaluation set across multiple LLM providers and compares results.

Usage:
    python scripts/evaluate_providers.py --providers anthropic openai ollama
    python scripts/evaluate_providers.py --verbose --output comparison_report.json
    python scripts/evaluate_providers.py --providers anthropic openai  # Compare subset
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config
from scripts.evaluate_chatbot import ChatbotEvaluator


def run_provider_comparison(
    providers: List[str],
    eval_set: str = "apps/evaluator/poolula_eval_set.jsonl",
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run evaluation across multiple providers

    Args:
        providers: List of provider names to test
        eval_set: Path to evaluation set (JSONL file)
        verbose: Show detailed per-question output

    Returns:
        Comparison report dictionary
    """
    results = {}

    for provider_name in providers:
        print(f"\n{'='*60}")
        print(f"Evaluating provider: {provider_name}")
        print(f"{'='*60}\n")

        try:
            # Configure for this provider
            config = Config()
            config.LLM_PROVIDER = provider_name

            # Initialize RAG system with this provider
            rag = RAGSystem(config)

            # Run evaluation using existing ChatbotEvaluator
            evaluator = ChatbotEvaluator(rag, verbose=verbose)
            report = evaluator.run_evaluation(eval_set)

            results[provider_name] = report

            # Print summary for this provider
            print(f"\nAverage Score: {report['average_score']*100:.1f}%\n")

        except Exception as e:
            print(f"❌ Error evaluating {provider_name}: {e}")
            results[provider_name] = {
                "error": str(e),
                "average_score": 0.0,
                "total_questions": 0,
                "passed": 0,
                "warned": 0,
                "failed": 0
            }

    # Generate comparison report
    comparison = _build_comparison_report(results)
    return comparison


def _build_comparison_report(results: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Build side-by-side comparison from individual provider results

    Args:
        results: Dictionary mapping provider name to evaluation report

    Returns:
        Comparison report with overall scores, question breakdown, and category performance
    """
    providers = list(results.keys())

    # Overall scores (convert to percentage)
    scores = {}
    for provider in providers:
        if "error" in results[provider]:
            scores[provider] = 0.0
        else:
            scores[provider] = results[provider]["average_score"] * 100

    # Determine winner (highest score, excluding errors)
    valid_scores = {p: s for p, s in scores.items() if s > 0}
    winner = max(valid_scores, key=valid_scores.get) if valid_scores else None

    # Per-question comparison
    question_breakdown = []

    # Get questions from first successful provider
    first_successful_provider = None
    for provider in providers:
        if "results" in results[provider]:
            first_successful_provider = provider
            break

    if first_successful_provider:
        for i, result in enumerate(results[first_successful_provider]["results"]):
            question_data = {
                "question": result["question"],
                "category": result.get("category", "unknown"),
                "scores": {}
            }

            # Collect scores from all providers for this question
            for provider in providers:
                if "results" in results[provider] and i < len(results[provider]["results"]):
                    provider_result = results[provider]["results"][i]

                    # Extract component scores
                    tool_score = 0.0
                    relevance_score = 0.0
                    error_score = 0.0

                    for component in provider_result.get("score_components", []):
                        if component["component"] == "tool_usage":
                            tool_score = component["score"] * 100
                        elif component["component"] == "content_relevance":
                            relevance_score = component["score"] * 100
                        elif component["component"] == "completeness":
                            error_score = component["score"] * 100

                    question_data["scores"][provider] = {
                        "total": provider_result.get("total_score", 0) * 100,
                        "tool_usage": tool_score,
                        "relevance": relevance_score,
                        "error_handling": error_score
                    }
                else:
                    # Provider failed or didn't evaluate this question
                    question_data["scores"][provider] = {
                        "total": 0.0,
                        "tool_usage": 0.0,
                        "relevance": 0.0,
                        "error_handling": 0.0
                    }

            # Identify winner for this question
            question_scores = {p: s["total"] for p, s in question_data["scores"].items()}
            question_winner = max(question_scores, key=question_scores.get) if question_scores else None
            question_data["winner"] = question_winner

            question_breakdown.append(question_data)

    # Category performance aggregation
    category_performance = {}

    if first_successful_provider:
        # Get all unique categories
        categories = set()
        for result in results[first_successful_provider]["results"]:
            categories.add(result.get("category", "unknown"))

        # Calculate average score per category per provider
        for category in categories:
            category_performance[category] = {}

            for provider in providers:
                if "results" not in results[provider]:
                    category_performance[category][provider] = 0.0
                    continue

                # Find all questions in this category
                category_scores = []
                for result in results[provider]["results"]:
                    if result.get("category", "unknown") == category:
                        category_scores.append(result.get("total_score", 0) * 100)

                # Average score for this category
                if category_scores:
                    category_performance[category][provider] = sum(category_scores) / len(category_scores)
                else:
                    category_performance[category][provider] = 0.0

    return {
        "timestamp": datetime.now().isoformat(),
        "providers_tested": providers,
        "overall_scores": scores,
        "winner": winner,
        "question_breakdown": question_breakdown,
        "category_performance": category_performance,
        "detailed_results": results
    }


def print_comparison_summary(comparison: Dict[str, Any]):
    """
    Print formatted comparison summary to console

    Args:
        comparison: Comparison report dictionary
    """
    print(f"\n{'='*60}")
    print("Provider Comparison Summary")
    print(f"{'='*60}")

    # Sort providers by score
    sorted_providers = sorted(
        comparison["overall_scores"].items(),
        key=lambda x: x[1],
        reverse=True
    )

    for provider, score in sorted_providers:
        # Show trophy for winner
        status = "🏆" if provider == comparison["winner"] else "  "
        print(f"{status} {provider:15s}: {score:5.1f}%")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare LLM providers using evaluation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare all providers
  python scripts/evaluate_providers.py --providers anthropic openai ollama

  # Compare specific providers
  python scripts/evaluate_providers.py --providers anthropic openai

  # Verbose mode (show per-question details)
  python scripts/evaluate_providers.py --providers anthropic --verbose

  # Custom output path
  python scripts/evaluate_providers.py --output data/my_comparison.json
        """
    )

    parser.add_argument(
        "--providers",
        nargs="+",
        default=["anthropic"],
        choices=["anthropic", "openai", "ollama"],
        help="Providers to test (default: anthropic)"
    )
    parser.add_argument(
        "--eval-set",
        default="apps/evaluator/poolula_eval_set.jsonl",
        help="Path to evaluation set (default: apps/evaluator/poolula_eval_set.jsonl)"
    )
    parser.add_argument(
        "--output",
        default="data/provider_comparison.json",
        help="Output path for comparison report (default: data/provider_comparison.json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed per-question output"
    )

    args = parser.parse_args()

    # Validate eval set exists
    if not Path(args.eval_set).exists():
        print(f"❌ Evaluation set not found: {args.eval_set}")
        sys.exit(1)

    # Run comparison
    comparison = run_provider_comparison(
        providers=args.providers,
        eval_set=args.eval_set,
        verbose=args.verbose
    )

    # Print summary
    print_comparison_summary(comparison)

    # Save detailed report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"Detailed report saved to: {output_path}")

    # Also save timestamped version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = output_path.parent / f"{output_path.stem}_{timestamp}{output_path.suffix}"
    with open(timestamped_path, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"Timestamped report saved to: {timestamped_path}")


if __name__ == "__main__":
    main()

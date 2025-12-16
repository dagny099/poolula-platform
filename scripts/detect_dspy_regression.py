#!/usr/bin/env python3
"""
DSPy Regression Detection Script

This script monitors the performance of optimized DSPy programs and detects regressions.
It:
1. Evaluates both baseline RAG and optimized DSPy on dev set
2. Compares scores to detect regression (>10% drop)
3. Logs results to MLflow
4. Sends alerts if regression detected

Usage:
    # Run regression check
    uv run python scripts/detect_dspy_regression.py

    # With custom threshold
    uv run python scripts/detect_dspy_regression.py --threshold 0.15

    # Verbose output
    uv run python scripts/detect_dspy_regression.py --verbose

    # Specify MLflow tracking URI
    uv run python scripts/detect_dspy_regression.py --mlflow-uri file:./mlruns
"""
import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import mlflow
from apps.evaluator.dspy_dataset import load_dspy_examples
from apps.evaluator.dspy_metrics import weighted_metric
from core.logging_config import get_logger

logger = get_logger(__name__)


def evaluate_baseline_rag(questions: List[str], verbose: bool = False) -> Dict[str, Any]:
    """
    Evaluate baseline RAG system on questions.

    Args:
        questions: List of questions to evaluate
        verbose: Print detailed results

    Returns:
        Dict with score and per-question results
    """
    from apps.chatbot.rag_system import RAGSystem
    from apps.chatbot.config import Config

    logger.info("Evaluating baseline RAG system...")

    # Initialize RAG
    config = Config()
    rag = RAGSystem(config=config)

    results = []
    total_score = 0.0

    for i, example in enumerate(questions, 1):
        question = example.question
        expected_content = example.expected_content

        try:
            # Query RAG system
            answer, sources = rag.query(question)

            # Create prediction for scoring
            import dspy
            prediction = dspy.Prediction(answer=answer)

            # Score
            score = weighted_metric(example, prediction)
            total_score += score

            results.append({
                "question": question,
                "answer": answer,
                "score": score,
                "passed": score >= 0.7
            })

            if verbose:
                logger.info(f"[{i}/{len(questions)}] Score: {score:.2f} - {question[:60]}...")

        except Exception as e:
            logger.error(f"Baseline RAG failed on question: {question[:60]}... Error: {e}")
            results.append({
                "question": question,
                "answer": f"ERROR: {str(e)}",
                "score": 0.0,
                "passed": False
            })

    avg_score = total_score / len(questions) if questions else 0.0

    return {
        "average_score": avg_score,
        "total_questions": len(questions),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }


def evaluate_optimized_dspy(questions: List[str], verbose: bool = False) -> Dict[str, Any]:
    """
    Evaluate optimized DSPy program on questions.

    Args:
        questions: List of questions to evaluate
        verbose: Print detailed results

    Returns:
        Dict with score and per-question results, or None if program not available
    """
    from apps.dspy.runtime import load_optimized_program
    from apps.dspy.lm_config import configure_dspy_lm

    logger.info("Evaluating optimized DSPy program...")

    # Configure DSPy LM
    try:
        provider = os.getenv("LLM_PROVIDER", "anthropic")
        configure_dspy_lm(provider)
    except Exception as e:
        logger.error(f"Failed to configure DSPy LM: {e}")
        return None

    # Load optimized program
    program = load_optimized_program()

    if program is None:
        logger.warning("Optimized DSPy program not available")
        return None

    results = []
    total_score = 0.0

    for i, example in enumerate(questions, 1):
        question = example.question

        try:
            # Execute program
            prediction = program(question=question)

            # Score
            score = weighted_metric(example, prediction)
            total_score += score

            results.append({
                "question": question,
                "answer": prediction.answer,
                "score": score,
                "passed": score >= 0.7
            })

            if verbose:
                logger.info(f"[{i}/{len(questions)}] Score: {score:.2f} - {question[:60]}...")

        except Exception as e:
            logger.error(f"DSPy program failed on question: {question[:60]}... Error: {e}")
            results.append({
                "question": question,
                "answer": f"ERROR: {str(e)}",
                "score": 0.0,
                "passed": False
            })

    avg_score = total_score / len(questions) if questions else 0.0

    return {
        "average_score": avg_score,
        "total_questions": len(questions),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }


def detect_regression(
    baseline_score: float,
    optimized_score: float,
    threshold: float = 0.10
) -> Tuple[bool, str]:
    """
    Detect if optimized program has regressed.

    Args:
        baseline_score: Baseline RAG score
        optimized_score: Optimized DSPy score
        threshold: Regression threshold (default: 10%)

    Returns:
        (is_regression, message) tuple
    """
    difference = baseline_score - optimized_score

    if difference > threshold:
        # Regression detected
        regression_pct = difference * 100
        message = (
            f"⚠️  REGRESSION DETECTED! Optimized DSPy is {regression_pct:.1f}% worse than baseline "
            f"(baseline: {baseline_score:.1%}, optimized: {optimized_score:.1%})"
        )
        return True, message

    elif optimized_score > baseline_score:
        # Improvement
        improvement_pct = (optimized_score - baseline_score) * 100
        message = (
            f"✅ Optimized DSPy is {improvement_pct:.1f}% better than baseline "
            f"(baseline: {baseline_score:.1%}, optimized: {optimized_score:.1%})"
        )
        return False, message

    else:
        # Similar performance
        message = (
            f"➖ Performance similar (baseline: {baseline_score:.1%}, optimized: {optimized_score:.1%})"
        )
        return False, message


def save_regression_report(
    baseline_results: Dict[str, Any],
    optimized_results: Dict[str, Any],
    is_regression: bool,
    message: str,
    output_path: Path
):
    """
    Save regression detection report to disk.

    Args:
        baseline_results: Baseline evaluation results
        optimized_results: Optimized evaluation results
        is_regression: Whether regression was detected
        message: Regression detection message
        output_path: Output directory path
    """
    output_path.mkdir(parents=True, exist_ok=True)

    # Create report
    report = {
        "timestamp": datetime.now().isoformat(),
        "regression_detected": is_regression,
        "message": message,
        "baseline": {
            "average_score": baseline_results["average_score"],
            "passed_count": baseline_results["passed_count"],
            "total_questions": baseline_results["total_questions"]
        },
        "optimized": {
            "average_score": optimized_results["average_score"],
            "passed_count": optimized_results["passed_count"],
            "total_questions": optimized_results["total_questions"]
        } if optimized_results else None,
        "difference": baseline_results["average_score"] - optimized_results["average_score"] if optimized_results else None
    }

    # Save report
    report_file = output_path / f"regression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"📄 Saved regression report to {report_file}")

    # Also save latest report
    latest_file = output_path / "latest_regression_report.json"
    with open(latest_file, 'w') as f:
        json.dump(report, f, indent=2)

    return report_file


def main():
    parser = argparse.ArgumentParser(description="Detect DSPy performance regressions")
    parser.add_argument("--threshold", type=float, default=0.10,
                       help="Regression threshold (default: 0.10 = 10%%)")
    parser.add_argument("--output", default="artifacts/regression_reports",
                       help="Output directory for reports")
    parser.add_argument("--mlflow-uri", default=None,
                       help="MLflow tracking URI (default: from env or file:./mlruns)")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--use-combined-dataset", action="store_true",
                       help="Use combined Poolula + Airbnb dataset")

    args = parser.parse_args()

    # Configure MLflow
    tracking_uri = args.mlflow_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("dspy-regression-detection")

    # Start MLflow run
    run_name = f"regression-check-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"MLflow tracking URI: {tracking_uri}")
        logger.info(f"MLflow run: {run_name}")

        # Log parameters
        mlflow.log_params({
            "regression_threshold": args.threshold,
            "use_combined_dataset": args.use_combined_dataset,
            "timestamp": datetime.now().isoformat()
        })

        # Set tags
        mlflow.set_tags({
            "type": "regression_detection",
            "automated": "true"
        })

        # Load evaluation dataset
        logger.info("Loading evaluation dataset...")
        _, devset = load_dspy_examples()

        if args.use_combined_dataset:
            from apps.evaluator.dspy_dataset import load_airbnb_examples, combine_datasets
            _, airbnb_dev = load_airbnb_examples()
            _, devset = combine_datasets([], [], [], devset + airbnb_dev)

        mlflow.log_param("eval_questions", len(devset))

        # Evaluate baseline
        print("\n" + "="*60)
        print("BASELINE RAG EVALUATION")
        print("="*60)
        baseline_results = evaluate_baseline_rag(devset, verbose=args.verbose)

        print(f"\nBaseline Results:")
        print(f"  Average Score: {baseline_results['average_score']:.1%}")
        print(f"  Passed: {baseline_results['passed_count']}/{baseline_results['total_questions']}")

        # Log baseline metrics
        mlflow.log_metrics({
            "baseline_score": baseline_results["average_score"],
            "baseline_passed": baseline_results["passed_count"]
        })

        # Evaluate optimized DSPy
        print("\n" + "="*60)
        print("OPTIMIZED DSPY EVALUATION")
        print("="*60)
        optimized_results = evaluate_optimized_dspy(devset, verbose=args.verbose)

        if optimized_results is None:
            print("\n⚠️  Optimized DSPy program not available - cannot perform regression check")
            print("Run optimization first: uv run python scripts/optimize_dspy_pipeline.py")
            mlflow.set_tag("status", "no_optimized_program")
            mlflow.set_tag("regression_detected", "N/A")
            sys.exit(1)

        print(f"\nOptimized Results:")
        print(f"  Average Score: {optimized_results['average_score']:.1%}")
        print(f"  Passed: {optimized_results['passed_count']}/{optimized_results['total_questions']}")

        # Log optimized metrics
        mlflow.log_metrics({
            "optimized_score": optimized_results["average_score"],
            "optimized_passed": optimized_results["passed_count"]
        })

        # Detect regression
        print("\n" + "="*60)
        print("REGRESSION DETECTION")
        print("="*60)

        is_regression, message = detect_regression(
            baseline_score=baseline_results["average_score"],
            optimized_score=optimized_results["average_score"],
            threshold=args.threshold
        )

        print(f"\n{message}")

        # Log regression metrics
        difference = baseline_results["average_score"] - optimized_results["average_score"]
        mlflow.log_metrics({
            "score_difference": difference,
            "score_difference_pct": difference * 100
        })

        # Set tags
        mlflow.set_tag("regression_detected", str(is_regression))
        mlflow.set_tag("status", "regression" if is_regression else "ok")

        # Save report
        output_path = Path(args.output)
        report_file = save_regression_report(
            baseline_results=baseline_results,
            optimized_results=optimized_results,
            is_regression=is_regression,
            message=message,
            output_path=output_path
        )

        # Log report as artifact
        mlflow.log_artifact(str(report_file), artifact_path="regression_reports")

        print("\n" + "="*60)
        print(f"📊 MLflow run ID: {mlflow.active_run().info.run_id}")
        print(f"📊 View in MLflow UI: mlflow ui --backend-store-uri {tracking_uri}")
        print(f"📄 Report saved to: {report_file}")
        print("="*60)

        # Exit with appropriate code
        if is_regression:
            print("\n❌ Regression detected - exiting with code 1")
            sys.exit(1)
        else:
            print("\n✅ No regression detected")
            sys.exit(0)


if __name__ == "__main__":
    main()

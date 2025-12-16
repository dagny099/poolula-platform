#!/usr/bin/env python3
"""
Optimize DSPy pipeline using BootstrapFewShot.

This script:
1. Loads training examples from evaluation dataset
2. Compiles DSPy pipeline using BootstrapFewShot optimizer
3. Evaluates on dev set
4. Saves optimized program as artifact

Usage:
    uv run python scripts/optimize_dspy_pipeline.py
    uv run python scripts/optimize_dspy_pipeline.py --max-bootstrapped 4
    uv run python scripts/optimize_dspy_pipeline.py --verbose
"""
import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
import mlflow
from dspy.teleprompt import BootstrapFewShot
from apps.dspy.lm_config import configure_dspy_lm
from apps.dspy.pipelines import PoolulaRAGPipeline
from apps.evaluator.dspy_dataset import load_dspy_examples, create_few_shot_examples
from apps.evaluator.dspy_metrics import binary_keyword_metric, weighted_metric
from core.logging_config import get_logger

logger = get_logger(__name__)


def optimize_bootstrap_fewshot(
    student: dspy.Module,
    trainset: list,
    devset: list,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 3,
    metric=None
) -> dspy.Module:
    """
    Optimize pipeline using BootstrapFewShot.

    This optimizer generates demonstrations by running the student on training examples
    and keeping successful ones.

    Args:
        student: DSPy module to optimize
        trainset: Training examples
        devset: Development examples for validation
        max_bootstrapped_demos: Maximum bootstrapped demonstrations to generate
        max_labeled_demos: Maximum hand-crafted demonstrations to include
        metric: Metric function (default: binary_keyword_metric)

    Returns:
        Compiled DSPy module
    """
    metric = metric or binary_keyword_metric

    logger.info("Optimizing with BootstrapFewShot")
    logger.info(f"  Trainset: {len(trainset)} examples")
    logger.info(f"  Devset: {len(devset)} examples")
    logger.info(f"  Max bootstrapped demos: {max_bootstrapped_demos}")
    logger.info(f"  Max labeled demos: {max_labeled_demos}")

    # Create optimizer
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos
    )

    # Get hand-crafted examples
    labeled_demos = create_few_shot_examples()
    logger.info(f"  Using {len(labeled_demos)} hand-crafted demos")

    # Compile student
    try:
        compiled = optimizer.compile(
            student=student,
            trainset=trainset,
            teacher=student  # Use same model as teacher
        )
        logger.info("✅ Compilation complete")
        return compiled
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        raise


def evaluate_pipeline(pipeline: dspy.Module, examples: list, name: str = "Pipeline", metric=None) -> dict:
    """
    Evaluate pipeline on examples.

    Args:
        pipeline: DSPy module to evaluate
        examples: List of examples
        name: Name for logging
        metric: Metric function (default: weighted_metric)

    Returns:
        Dictionary with score and per-example results
    """
    metric = metric or weighted_metric

    logger.info(f"\nEvaluating {name}...")

    # Create evaluator
    evaluator = dspy.Evaluate(
        devset=examples,
        metric=metric,
        num_threads=1,
        display_progress=True,
        display_table=5
    )

    # Run evaluation
    score = evaluator(pipeline)

    logger.info(f"{name} Score: {score:.1%}")

    return {
        "score": score,
        "num_examples": len(examples)
    }


def save_optimized_program(program: dspy.Module, output_path: str = "artifacts/optimized_dspy_program", hyperparams: dict = None):
    """
    Save optimized program.

    Args:
        program: Optimized DSPy module
        output_path: Output directory path
        hyperparams: Optimization hyperparameters to include in metadata

    Returns:
        Tuple of (program_file_path, metadata_file_path)
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save program
    program_file = output_path / "program.json"
    try:
        program.save(str(program_file))
        logger.info(f"✅ Saved program to {program_file}")
    except Exception as e:
        logger.warning(f"Could not save program: {e}")
        # Save metadata only
        program_file = output_path / "program_metadata.json"

    # Save metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "program_class": program.__class__.__name__,
        "optimizer": "BootstrapFewShot",
        "dspy_version": "2.5.0",
        "hyperparameters": hyperparams or {}
    }

    metadata_file = output_path / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Saved metadata to {metadata_file}")
    logger.info(f"\n📁 Optimization artifacts saved to: {output_path}")

    return program_file, metadata_file


def main():
    parser = argparse.ArgumentParser(description="Optimize DSPy pipeline")
    parser.add_argument("--max-bootstrapped", type=int, default=4,
                       help="Max bootstrapped demonstrations (default: 4)")
    parser.add_argument("--max-labeled", type=int, default=3,
                       help="Max hand-crafted demonstrations (default: 3)")
    parser.add_argument("--output", default="artifacts/optimized_dspy_program",
                       help="Output directory for optimized program")
    parser.add_argument("--use-hybrid", action="store_true", default=True,
                       help="Use hybrid retrieval (database + vector)")
    parser.add_argument("--k", type=int, default=5,
                       help="Number of retrieval results (default: 5)")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--provider", default="anthropic",
                       choices=["anthropic", "openai", "ollama"],
                       help="LLM provider (default: anthropic)")

    args = parser.parse_args()

    # Configure MLflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("dspy-optimization")

    # Start MLflow run
    run_name = f"optimize-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"MLflow tracking URI: {tracking_uri}")
        logger.info(f"MLflow run: {run_name}")

        # Log parameters
        hyperparams = {
            "max_bootstrapped_demos": args.max_bootstrapped,
            "max_labeled_demos": args.max_labeled,
            "retrieval_k": args.k,
            "use_hybrid_retrieval": args.use_hybrid,
            "llm_provider": args.provider,
            "pipeline_class": "PoolulaRAGPipeline",
            "optimizer": "BootstrapFewShot",
            "metric": "binary_keyword_metric"
        }
        mlflow.log_params(hyperparams)

        # Set tags for searchability
        mlflow.set_tags({
            "stage": "optimization",
            "pipeline": "PoolulaRAGPipeline",
            "optimizer": "BootstrapFewShot",
            "provider": args.provider
        })

        # Configure DSPy
        logger.info(f"Configuring DSPy LM ({args.provider})...")
        configure_dspy_lm(args.provider)

        # Load dataset
        logger.info("Loading evaluation dataset...")
        trainset, devset = load_dspy_examples()

        mlflow.log_params({
            "train_examples": len(trainset),
            "dev_examples": len(devset),
            "total_examples": len(trainset) + len(devset)
        })

        # Create student program
        logger.info("Creating student pipeline...")
        student = PoolulaRAGPipeline(use_hybrid=args.use_hybrid, k=args.k)
        logger.info(f"  Pipeline: PoolulaRAGPipeline")
        logger.info(f"  Hybrid retrieval: {args.use_hybrid}")
        logger.info(f"  Retrieval k: {args.k}")

        # Evaluate baseline
        print("\n" + "="*60)
        print("BASELINE EVALUATION")
        print("="*60)
        baseline_score = evaluate_pipeline(student, devset, name="Baseline")

        # Log baseline metrics
        mlflow.log_metrics({
            "baseline_score": baseline_score['score'],
            "baseline_dev_examples": baseline_score['num_examples']
        })

        # Optimize
        print("\n" + "="*60)
        print("OPTIMIZATION")
        print("="*60)
        try:
            compiled_program = optimize_bootstrap_fewshot(
                student=student,
                trainset=trainset,
                devset=devset,
                max_bootstrapped_demos=args.max_bootstrapped,
                max_labeled_demos=args.max_labeled
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            mlflow.set_tag("status", "failed")
            mlflow.log_param("error", str(e))
            print("\n❌ Optimization failed. See logs for details.")
            sys.exit(1)

        # Evaluate optimized
        print("\n" + "="*60)
        print("OPTIMIZED EVALUATION")
        print("="*60)
        optimized_score = evaluate_pipeline(compiled_program, devset, name="Optimized")

        # Log optimized metrics
        mlflow.log_metrics({
            "optimized_score": optimized_score['score'],
            "optimized_dev_examples": optimized_score['num_examples']
        })

        # Compare
        improvement = optimized_score['score'] - baseline_score['score']
        improvement_pct = improvement * 100

        # Log improvement metrics
        mlflow.log_metrics({
            "improvement_absolute": improvement,
            "improvement_percentage": improvement_pct
        })

        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"  Baseline:    {baseline_score['score']:.1%}")
        print(f"  Optimized:   {optimized_score['score']:.1%}")
        print(f"  Improvement: {improvement:+.1%} ({improvement_pct:+.1f} percentage points)")

        if improvement > 0:
            print("\n✅ Optimization improved performance!")
            mlflow.set_tag("result", "improved")
        elif improvement < 0:
            print("\n⚠️  Optimization decreased performance (may need more data or tuning)")
            mlflow.set_tag("result", "regressed")
        else:
            print("\n➖ No change in performance")
            mlflow.set_tag("result", "no_change")

        print("="*60)

        # Save
        program_file, metadata_file = save_optimized_program(
            compiled_program,
            args.output,
            hyperparams=hyperparams
        )

        # Log artifacts to MLflow
        mlflow.log_artifact(str(metadata_file), artifact_path="optimized_program")
        if program_file.exists():
            mlflow.log_artifact(str(program_file), artifact_path="optimized_program")

        # Create and log results summary
        results_summary = {
            "timestamp": datetime.now().isoformat(),
            "baseline_score": baseline_score['score'],
            "optimized_score": optimized_score['score'],
            "improvement": improvement,
            "improvement_pct": improvement_pct,
            "hyperparameters": hyperparams,
            "train_examples": len(trainset),
            "dev_examples": len(devset)
        }

        results_file = Path(args.output) / "results_summary.json"
        with open(results_file, 'w') as f:
            json.dump(results_summary, f, indent=2)
        mlflow.log_artifact(str(results_file), artifact_path="results")

        # Set final status
        mlflow.set_tag("status", "success")

        logger.info(f"\n📊 MLflow run ID: {mlflow.active_run().info.run_id}")
        logger.info(f"📊 View in MLflow UI: mlflow ui --backend-store-uri {tracking_uri}")

        print("\n✅ Optimization complete!")
        print(f"📊 MLflow run ID: {mlflow.active_run().info.run_id}")
        print(f"📊 View results: mlflow ui")

        # Exit with appropriate code
        if optimized_score['score'] >= 0.7:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()

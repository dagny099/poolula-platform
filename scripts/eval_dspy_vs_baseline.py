"""
Evaluate baseline RAG vs DSPy program on the pooled eval set and log to MLflow.

Metrics are heuristic: coverage of expected_content tokens in the answer and latency.
Artifacts include per-example results and failures.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import mlflow

from apps.api.routes.chat import get_rag_system
from apps.dspy.artifacts import load_pickled_program
from apps.dspy.runtime import _dry_run as dspy_dry_run  # reuse minimal callable check


def _load_dataset(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _token_hits(answer: str, expected: List[str]) -> Tuple[int, bool]:
    answer_lower = answer.lower()
    hits = sum(1 for token in expected if token.lower() in answer_lower)
    return hits, hits == len(expected)


def _eval_predictor(
    name: str,
    predict_fn: Callable[[str], Tuple[str, list]],
    dataset: List[dict],
) -> Dict[str, Any]:
    results = []
    successes = 0
    total_hits = 0
    latencies = []

    for row in dataset:
        question = row.get("question", "")
        expected_content = row.get("expected_content", [])
        start = time.time()
        try:
            answer, sources = predict_fn(question)
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "question": question,
                    "model": name,
                    "error": str(exc),
                }
            )
            continue
        latency_ms = (time.time() - start) * 1000
        hits, success = _token_hits(answer, expected_content)
        total_hits += hits
        successes += 1 if success else 0
        latencies.append(latency_ms)
        results.append(
            {
                "question": question,
                "model": name,
                "answer": answer,
                "sources": sources,
                "expected_content": expected_content,
                "hits": hits,
                "success": success,
                "latency_ms": latency_ms,
            }
        )

    total = len(dataset)
    avg_hits = total_hits / total if total > 0 else 0.0
    hit_rate = successes / total if total > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "model": name,
        "total": total,
        "hit_rate": hit_rate,
        "avg_hits": avg_hits,
        "avg_latency_ms": avg_latency,
        "results": results,
    }


def _get_baseline_predictor():
    rag = get_rag_system()

    def predict(question: str) -> Tuple[str, list]:
        answer, sources = rag.query(query=question)
        return answer, sources

    return predict


def _get_dspy_predictor(artifact_dir: Path, expected_signature: Optional[str]) -> Callable[[str], Tuple[str, list]]:
    program = load_pickled_program(
        artifact_dir=artifact_dir,
        expected_signature=expected_signature,
        dry_run=dspy_dry_run,
    )

    def predict(question: str) -> Tuple[str, list]:
        result = program(question=question, session_id=None)
        if isinstance(result, dict):
            answer = result.get("answer") or result.get("response") or str(result)
            sources = result.get("sources") or []
        else:
            answer = str(result)
            sources = []
        return answer, sources

    return predict


def _log_results_artifact(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    mlflow.log_artifact(path, artifact_path="eval")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs DSPy on the eval dataset with MLflow logging.")
    parser.add_argument("--dataset-path", required=True, help="Path to eval dataset JSONL.")
    parser.add_argument("--dataset-name", default="poolula-eval", help="Dataset name.")
    parser.add_argument("--dataset-version", default="dev", help="Dataset version or commit.")
    parser.add_argument("--run-name", default="dspy-eval", help="MLflow run name.")
    parser.add_argument("--dspy-artifact-dir", default=None, help="Path to DSPy artifact directory (program.pkl + metadata.json).")
    parser.add_argument("--dspy-expected-signature", default=None, help="Optional expected signature for DSPy artifact validation.")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline RAG evaluation.")
    parser.add_argument("--no-dspy", action="store_true", help="Skip DSPy evaluation.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path).resolve()
    dataset = _load_dataset(dataset_path)

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:mlruns"))
    with mlflow.start_run(run_name=args.run_name):
        mlflow.log_params(
            {
                "dataset_name": args.dataset_name,
                "dataset_version": args.dataset_version,
                "dataset_path": str(dataset_path),
                "dspy_artifact_dir": args.dspy_artifact_dir or "none",
                "dspy_expected_signature": args.dspy_expected_signature or "unspecified",
            }
        )

        results_dir = Path(".mlflow_artifacts") / "eval_results"
        results_dir.mkdir(parents=True, exist_ok=True)

        if not args.no_baseline:
            baseline_pred = _get_baseline_predictor()
            baseline_metrics = _eval_predictor("baseline", baseline_pred, dataset)
            _log_results_artifact(results_dir / "baseline_results.json", baseline_metrics)
            mlflow.log_metrics(
                {
                    "baseline_hit_rate": baseline_metrics["hit_rate"],
                    "baseline_avg_hits": baseline_metrics["avg_hits"],
                    "baseline_avg_latency_ms": baseline_metrics["avg_latency_ms"],
                }
            )

        if not args.no_dspy and args.dspy_artifact_dir:
            dspy_pred = _get_dspy_predictor(Path(args.dspy_artifact_dir).resolve(), args.dspy_expected_signature)
            dspy_metrics = _eval_predictor("dspy", dspy_pred, dataset)
            _log_results_artifact(results_dir / "dspy_results.json", dspy_metrics)
            mlflow.log_metrics(
                {
                    "dspy_hit_rate": dspy_metrics["hit_rate"],
                    "dspy_avg_hits": dspy_metrics["avg_hits"],
                    "dspy_avg_latency_ms": dspy_metrics["avg_latency_ms"],
                }
            )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import os
from pathlib import Path

import mlflow

from apps.dspy.artifacts import ArtifactValidationError, load_pickled_program
from apps.evaluator.dataset_manifest import prepare_dataset_artifacts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DSPy experiment with MLflow logging.")
    parser.add_argument("--run-name", default="dspy-run", help="MLflow run name.")
    parser.add_argument("--dataset-path", required=True, help="Path to dataset JSONL.")
    parser.add_argument("--dataset-name", required=True, help="Dataset name (logged).")
    parser.add_argument("--dataset-version", required=True, help="Dataset version or commit SHA (logged).")
    parser.add_argument(
        "--dataset-source-uri",
        default=None,
        help="Source URI for dataset (repo path or object store). Defaults to dataset-path.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=".mlflow_artifacts",
        help="Local directory to stage dataset artifacts before logging.",
    )
    parser.add_argument(
        "--snapshot-mb",
        type=int,
        default=100,
        help="Max compressed snapshot size in MB before falling back to sample-only logging.",
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=0.02,
        help="Sample ratio (0-1) used when snapshot exceeds size budget.",
    )
    parser.add_argument(
        "--sample-cap",
        type=int,
        default=1000,
        help="Max rows in sampled dataset when snapshot exceeds size budget.",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=13,
        help="Seed for deterministic sampling.",
    )
    parser.add_argument(
        "--program-artifact-dir",
        default=None,
        help="Directory containing pickled DSPy program artifact and metadata.json.",
    )
    parser.add_argument(
        "--expected-signature",
        default=None,
        help="Optional expected signature string to validate the DSPy program.",
    )
    parser.add_argument(
        "--program-filename",
        default="program.pkl",
        help="Filename of the pickled DSPy program (within program-artifact-dir).",
    )
    parser.add_argument(
        "--metadata-filename",
        default="metadata.json",
        help="Filename of the DSPy artifact metadata (within program-artifact-dir).",
    )
    return parser.parse_args()


def _dry_run(program) -> None:
    """Minimal dry-run validator to ensure the program is callable."""
    if not callable(program):
        raise ArtifactValidationError("DSPy program is not callable for dry-run validation.")


def main() -> None:
    args = _parse_args()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:mlruns")
    mlflow.set_tracking_uri(tracking_uri)

    dataset_path = Path(args.dataset_path).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    dataset_artifact_dir = artifact_dir / "dataset"
    dataset_source_uri = args.dataset_source_uri or str(dataset_path)

    manifest = prepare_dataset_artifacts(
        dataset_path=dataset_path,
        output_dir=dataset_artifact_dir,
        dataset_name=args.dataset_name,
        version=args.dataset_version,
        source_uri=dataset_source_uri,
        max_snapshot_mb=args.snapshot_mb,
        sample_ratio=args.sample_ratio,
        sample_cap=args.sample_cap,
        seed=args.sample_seed,
    )

    with mlflow.start_run(run_name=args.run_name):
        mlflow.log_params(
            {
                "dataset_name": args.dataset_name,
                "dataset_version": args.dataset_version,
                "dataset_source_uri": dataset_source_uri,
                "dataset_path": str(dataset_path),
                "snapshot_mb_limit": args.snapshot_mb,
                "sample_ratio": args.sample_ratio,
                "sample_cap": args.sample_cap,
            }
        )

        # Log dataset artifacts (manifest always; snapshot or sample per helper logic).
        mlflow.log_artifact(dataset_artifact_dir / "manifest.json", artifact_path="dataset")
        if manifest.get("has_snapshot"):
            mlflow.log_artifact(dataset_artifact_dir / "dataset.jsonl.gz", artifact_path="dataset")
        if manifest.get("sample_path"):
            mlflow.log_artifact(dataset_artifact_dir / "dataset.sample.jsonl", artifact_path="dataset")

        if args.program_artifact_dir:
            program_dir = Path(args.program_artifact_dir).resolve()
            mlflow.log_param("dspy_program_artifact", str(program_dir))
            mlflow.log_param("dspy_expected_signature", args.expected_signature or "unspecified")
            program = load_pickled_program(
                artifact_dir=program_dir,
                program_filename=args.program_filename,
                metadata_filename=args.metadata_filename,
                expected_signature=args.expected_signature,
                dry_run=_dry_run,
            )
            # Log the DSPy artifact files for reproducibility.
            mlflow.log_artifact(program_dir / args.program_filename, artifact_path="dspy_program")
            metadata_file = program_dir / args.metadata_filename
            if metadata_file.exists():
                mlflow.log_artifact(metadata_file, artifact_path="dspy_program")
            mlflow.set_tag("dspy_program_validated", "true")
            mlflow.set_tag("dspy_program_class", program.__class__.__name__)


if __name__ == "__main__":
    main()

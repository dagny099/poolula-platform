"""
Build a DSPy program artifact (pickled program + metadata.json) using the
DSPy pipelines. Supports both real DSPy modules and legacy wrapper.
Intended for quick smoke tests and MLflow logging.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict

from apps.dspy.pipelines import RAGBackedDSPyProgram, SimpleDSPyQA, RetrieveAndAnswerPipeline
from apps.dspy.lm_config import configure_dspy_lm


def _get_dspy_version() -> str | None:
    try:
        return metadata.version("dspy-ai")
    except metadata.PackageNotFoundError:
        return None


def _build_config_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if args.llm_provider:
        overrides["LLM_PROVIDER"] = args.llm_provider
    if args.anthropic_model:
        overrides["ANTHROPIC_MODEL"] = args.anthropic_model
    if args.openai_model:
        overrides["OPENAI_MODEL"] = args.openai_model
    if args.local_model_path:
        overrides["LOCAL_MODEL_PATH"] = args.local_model_path
    if args.local_model_url:
        overrides["LOCAL_MODEL_URL"] = args.local_model_url
    return overrides


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a DSPy program artifact.")
    parser.add_argument(
        "--pipeline-type",
        default="simple",
        choices=["simple", "retrieve", "legacy"],
        help="Pipeline type: 'simple' (SimpleDSPyQA), 'retrieve' (RetrieveAndAnswerPipeline), 'legacy' (RAGBackedDSPyProgram)"
    )
    parser.add_argument("--output-dir", default="artifacts/dspy-program", help="Directory to write program.pkl and metadata.json")
    parser.add_argument("--signature", default="question->answer", help="Signature string to store in program + metadata")
    parser.add_argument("--llm-provider", default=None, help="Override LLM provider (default from env Config)")
    parser.add_argument("--anthropic-model", default=None, help="Optional Anthropic model override")
    parser.add_argument("--openai-model", default=None, help="Optional OpenAI model override")
    parser.add_argument("--local-model-path", default=None, help="Optional local model path override (for Ollama)")
    parser.add_argument("--local-model-url", default=None, help="Optional local model URL override (for Ollama)")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieval results (for retrieve pipeline)")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = _build_config_overrides(args)

    # Create the appropriate pipeline based on user choice
    if args.pipeline_type == "simple":
        # Configure DSPy LM for real DSPy modules
        provider = args.llm_provider if args.llm_provider else None
        configure_dspy_lm(provider)
        program = SimpleDSPyQA()
        print(f"Creating SimpleDSPyQA pipeline")
    elif args.pipeline_type == "retrieve":
        # Configure DSPy LM for real DSPy modules
        provider = args.llm_provider if args.llm_provider else None
        configure_dspy_lm(provider)
        program = RetrieveAndAnswerPipeline(k=args.k)
        print(f"Creating RetrieveAndAnswerPipeline (k={args.k})")
    else:  # legacy
        program = RAGBackedDSPyProgram(signature=args.signature, config_overrides=config_overrides)
        print(f"Creating RAGBackedDSPyProgram (DEPRECATED)")

    metadata_path = output_dir / "metadata.json"

    # Serialize the program
    # Use different methods for DSPy modules vs legacy wrapper
    if args.pipeline_type in ["simple", "retrieve"]:
        # Real DSPy modules: use dspy.save()
        program_path = output_dir / "program.json"
        try:
            program.save(str(program_path))
            print(f"   Serialized with dspy.save() to {program_path.name}")
        except Exception as e:
            print(f"⚠️  DSPy save failed: {e}")
            # Fallback: save metadata only
            with program_path.open("w") as handle:
                json.dump({
                    "class": program.__class__.__name__,
                    "pipeline_type": args.pipeline_type,
                    "k": args.k if args.pipeline_type == "retrieve" else None,
                    "note": "Program not serializable - recreate from class using metadata"
                }, handle, indent=2)
            print(f"   Saved metadata only - program must be recreated from class")
    else:
        # Legacy wrapper: use pickle
        program_path = output_dir / "program.pkl"
        try:
            with program_path.open("wb") as handle:
                pickle.dump(program, handle)
            print(f"   Serialized with pickle to {program_path.name}")
        except Exception as e:
            print(f"⚠️  Pickle serialization failed: {e}")
            raise

    meta = {
        "dspy_version": _get_dspy_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "signature": args.signature,
        "program_class": program.__class__.__name__,
        "pipeline_type": args.pipeline_type,
        "config_overrides": config_overrides if args.pipeline_type == "legacy" else {},
        "is_real_dspy_module": args.pipeline_type in ["simple", "retrieve"],
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"✅ DSPy artifact written to {output_dir}")
    print(f"   Program class: {program.__class__.__name__}")
    print(f"   Pipeline type: {args.pipeline_type}")
    print(f"   Real DSPy module: {args.pipeline_type in ['simple', 'retrieve']}")


if __name__ == "__main__":
    main()

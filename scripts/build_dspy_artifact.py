"""
Build a DSPy program artifact (pickled program + metadata.json) using the
RAG-backed DSPy program. Intended for quick smoke tests and MLflow logging.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict

from apps.dspy.pipelines import RAGBackedDSPyProgram


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
    parser = argparse.ArgumentParser(description="Build a RAG-backed DSPy program artifact.")
    parser.add_argument("--output-dir", default="artifacts/dspy-program", help="Directory to write program.pkl and metadata.json")
    parser.add_argument("--signature", default="question->answer", help="Signature string to store in program + metadata")
    parser.add_argument("--llm-provider", default=None, help="Override LLM provider (default from env Config)")
    parser.add_argument("--anthropic-model", default=None, help="Optional Anthropic model override")
    parser.add_argument("--openai-model", default=None, help="Optional OpenAI model override")
    parser.add_argument("--local-model-path", default=None, help="Optional local model path override (for Ollama)")
    parser.add_argument("--local-model-url", default=None, help="Optional local model URL override (for Ollama)")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = _build_config_overrides(args)
    program = RAGBackedDSPyProgram(signature=args.signature, config_overrides=config_overrides)

    program_path = output_dir / "program.pkl"
    metadata_path = output_dir / "metadata.json"

    with program_path.open("wb") as handle:
        pickle.dump(program, handle)

    meta = {
        "dspy_version": _get_dspy_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "signature": args.signature,
        "program_class": program.__class__.__name__,
        "config_overrides": config_overrides,
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"✅ DSPy artifact written to {output_dir}")


if __name__ == "__main__":
    main()

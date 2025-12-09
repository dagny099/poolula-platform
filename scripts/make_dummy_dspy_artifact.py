"""
Utility to generate a dummy DSPy-like artifact for loader smoke tests.

Produces:
 - program.pkl: a pickled callable with __call__(question, session_id) -> dict
 - metadata.json: includes dspy_version (if installed), python_version, signature
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from importlib import metadata
from pathlib import Path


class DummyDSPyProgram:
    """Minimal callable to mimic a DSPy program for loader validation."""

    def __init__(self, signature: str | None = None):
        self.signature = signature or "question->answer"

    def __call__(self, question: str, session_id: str):
        return {
            "answer": f"[dummy answer] {question}",
            "sources": [{"id": "dummy", "session_id": session_id}],
        }


def _get_dspy_version() -> str | None:
    try:
        return metadata.version("dspy-ai")
    except metadata.PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a dummy DSPy artifact for loader testing.")
    parser.add_argument("--output-dir", default="artifacts/dspy-dummy", help="Where to write the artifact files.")
    parser.add_argument("--signature", default="question->answer", help="Expected signature stored in metadata.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    program_path = output_dir / "program.pkl"
    metadata_path = output_dir / "metadata.json"

    program = DummyDSPyProgram(signature=args.signature)
    with program_path.open("wb") as handle:
        pickle.dump(program, handle)

    meta = {
        "dspy_version": _get_dspy_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "signature": args.signature,
        "program_class": program.__class__.__name__,
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Dummy DSPy artifact written to {output_dir}")


if __name__ == "__main__":
    main()

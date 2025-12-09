from __future__ import annotations

import importlib.metadata
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ArtifactValidationError(Exception):
    """Raised when a DSPy artifact fails validation."""


def _load_metadata(metadata_path: Path) -> Dict[str, Any]:
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_major_minor(version: str) -> Tuple[int, int]:
    parts = version.split(".")
    major = int(parts[0]) if parts and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return major, minor


def _installed_dspy_version() -> Optional[str]:
    try:
        return importlib.metadata.version("dspy-ai")
    except importlib.metadata.PackageNotFoundError:
        return None


def load_pickled_program(
    artifact_dir: Path | str,
    program_filename: str = "program.pkl",
    metadata_filename: str = "metadata.json",
    expected_signature: Optional[str] = None,
    dry_run: Optional[Callable[[Any], None]] = None,
) -> Any:
    """
    Load a pickled DSPy program with lightweight validation.

    - Checks DSPy major/minor and Python major/minor compatibility when metadata is present.
    - Optionally enforces an expected signature string.
    - Supports a dry_run callback for a quick smoke (e.g., compile or dummy call) before returning.
    """
    artifact_dir = Path(artifact_dir)
    program_path = artifact_dir / program_filename
    metadata_path = artifact_dir / metadata_filename

    if not program_path.exists():
        raise FileNotFoundError(f"Program artifact not found: {program_path}")

    metadata = _load_metadata(metadata_path)
    installed_dspy = _installed_dspy_version()

    artifact_dspy_version = metadata.get("dspy_version")
    if artifact_dspy_version and installed_dspy:
        artifact_major_minor = _parse_major_minor(artifact_dspy_version)
        installed_major_minor = _parse_major_minor(installed_dspy)
        if artifact_major_minor != installed_major_minor:
            raise ArtifactValidationError(
                f"DSPy version mismatch (artifact {artifact_major_minor} vs installed {installed_major_minor})."
            )

    artifact_python = metadata.get("python_version")
    if artifact_python:
        artifact_py_mm = artifact_python.split(".")[:2]
        runtime_py_mm = f"{sys.version_info.major}.{sys.version_info.minor}"
        if artifact_py_mm and ".".join(artifact_py_mm) != runtime_py_mm:
            raise ArtifactValidationError(
                f"Python version mismatch (artifact {'.'.join(artifact_py_mm)} vs runtime {runtime_py_mm})."
            )

    with program_path.open("rb") as handle:
        program = pickle.load(handle)

    if expected_signature is not None:
        signature = getattr(program, "signature", None)
        if signature is None or str(signature) != expected_signature:
            raise ArtifactValidationError("Artifact signature does not match expected signature.")

    if not callable(program):
        logger.warning("Loaded program is not directly callable; ensure DSPy program exposes __call__.")

    if dry_run:
        dry_run(program)

    program_name = getattr(program, "__class__", type("Unknown", (), {})).__name__
    logger.info(
        "Loaded DSPy program artifact %s (dspy=%s, python=%s)",
        program_name,
        artifact_dspy_version or installed_dspy or "unknown",
        artifact_python or f"{sys.version_info.major}.{sys.version_info.minor}",
    )
    return program

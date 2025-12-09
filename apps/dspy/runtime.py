from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Any

from apps.dspy.artifacts import ArtifactValidationError, load_pickled_program
from core.logging_config import get_logger

logger = get_logger(__name__)


def _is_enabled() -> bool:
    flag = os.getenv("DSPY_ENABLED", "false").lower()
    return flag in {"1", "true", "yes", "on"}


def _dry_run(program: Any) -> None:
    """Minimal dry-run validator to keep load-time cheap but safe."""
    if not callable(program):
        raise ArtifactValidationError("DSPy program is not callable during dry-run validation.")


@lru_cache(maxsize=1)
def get_dspy_program() -> Optional[Any]:
    """Load and cache a DSPy program artifact if enabled via env vars."""
    if not _is_enabled():
        return None

    artifact_dir = os.getenv("DSPY_ARTIFACT_DIR")
    expected_signature = os.getenv("DSPY_EXPECTED_SIGNATURE")
    if not artifact_dir:
        logger.warning("DSPY_ENABLED is set but DSPY_ARTIFACT_DIR is missing; skipping DSPy load.")
        return None

    try:
        program = load_pickled_program(
            artifact_dir=Path(artifact_dir),
            expected_signature=expected_signature,
            dry_run=_dry_run,
        )
        return program
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load DSPy program from %s: %s", artifact_dir, exc, exc_info=True)
        return None


def run_dspy_program(question: str, session_id: str) -> Optional[Tuple[str, list]]:
    """
    Execute the DSPy program if available. Falls back silently (returns None) on failure.
    Expected program output: dict with `answer` and optional `sources`/`citations`;
    otherwise the stringified result is used as the answer with empty sources.
    """
    program = get_dspy_program()
    if program is None:
        return None

    try:
        result = program(question=question, session_id=session_id)
    except TypeError:
        # Fallback call signature if program expects a single question argument.
        result = program(question)
    except Exception as exc:  # noqa: BLE001
        logger.error("DSPy program execution failed; falling back to baseline: %s", exc, exc_info=True)
        return None

    if isinstance(result, dict):
        answer = result.get("answer") or result.get("response") or str(result)
        sources = result.get("sources") or result.get("citations") or []
    else:
        answer = str(result)
        sources = []

    return answer, sources

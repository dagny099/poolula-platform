"""
DSPy Runtime - Load and Execute Optimized DSPy Programs

This module provides runtime loading and execution of optimized DSPy programs.
It supports:
- Loading optimized programs from artifacts directory
- Graceful fallback to baseline RAG system if optimized program unavailable
- Environment variable control (USE_OPTIMIZED_DSPY)
- MLflow artifact integration
- Proper DSPy LM configuration

Usage:
    export USE_OPTIMIZED_DSPY=true
    export OPTIMIZED_DSPY_PATH=artifacts/optimized_dspy_program
    export LLM_PROVIDER=anthropic
"""
from __future__ import annotations

import os
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

import dspy

from core.logging_config import get_logger

logger = get_logger(__name__)


def is_optimized_dspy_enabled() -> bool:
    """
    Check if optimized DSPy pipeline should be used.

    Returns:
        True if USE_OPTIMIZED_DSPY is set to true/1/yes/on
    """
    flag = os.getenv("USE_OPTIMIZED_DSPY", "false").lower()
    return flag in {"1", "true", "yes", "on"}


def get_optimized_program_path() -> Path:
    """
    Get path to optimized DSPy program artifacts.

    Returns:
        Path to artifacts directory (defaults to artifacts/optimized_dspy_program)
    """
    path_str = os.getenv("OPTIMIZED_DSPY_PATH", "artifacts/optimized_dspy_program")
    return Path(path_str)


def load_program_metadata(artifact_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Load metadata.json from optimized program directory.

    Args:
        artifact_dir: Path to artifacts directory

    Returns:
        Metadata dict or None if not found
    """
    metadata_file = artifact_dir / "metadata.json"

    if not metadata_file.exists():
        logger.warning(f"Metadata file not found: {metadata_file}")
        return None

    try:
        with open(metadata_file) as f:
            metadata = json.load(f)

        logger.info(f"Loaded metadata for optimized program:")
        logger.info(f"  Class: {metadata.get('program_class', 'Unknown')}")
        logger.info(f"  Optimizer: {metadata.get('optimizer', 'Unknown')}")
        logger.info(f"  Timestamp: {metadata.get('timestamp', 'Unknown')}")
        logger.info(f"  DSPy Version: {metadata.get('dspy_version', 'Unknown')}")

        return metadata

    except Exception as e:
        logger.error(f"Failed to load metadata: {e}", exc_info=True)
        return None


def validate_program_class(program: Any, expected_class: str = "PoolulaRAGPipeline") -> bool:
    """
    Validate that loaded program is the expected class.

    Args:
        program: Loaded DSPy module
        expected_class: Expected class name

    Returns:
        True if valid, False otherwise
    """
    # Check if it's a DSPy module
    if not isinstance(program, dspy.Module):
        logger.error(f"Loaded program is not a dspy.Module: {type(program)}")
        return False

    # Check class name
    actual_class = program.__class__.__name__
    if actual_class != expected_class:
        logger.warning(
            f"Loaded program class '{actual_class}' does not match expected '{expected_class}'. "
            f"This may still work but could indicate wrong artifact."
        )

    # Check if it has forward method
    if not hasattr(program, 'forward'):
        logger.error("Loaded program does not have forward() method")
        return False

    logger.info(f"✅ Validated program class: {actual_class}")
    return True


def configure_dspy_for_runtime(provider_name: str = None):
    """
    Configure DSPy LM for runtime execution.

    Args:
        provider_name: LLM provider (anthropic, openai, ollama)
                      Defaults to LLM_PROVIDER environment variable
    """
    from apps.dspy.lm_config import configure_dspy_lm

    provider_name = provider_name or os.getenv("LLM_PROVIDER", "anthropic")

    try:
        configure_dspy_lm(provider_name)
        logger.info(f"✅ Configured DSPy LM with provider: {provider_name}")
    except Exception as e:
        logger.error(f"Failed to configure DSPy LM: {e}", exc_info=True)
        raise


@lru_cache(maxsize=1)
def load_optimized_program() -> Optional[dspy.Module]:
    """
    Load optimized DSPy program from artifacts directory.

    This function:
    1. Checks if optimized DSPy is enabled
    2. Locates artifacts directory
    3. Loads program metadata
    4. Loads program from program.json
    5. Validates program class
    6. Configures DSPy LM

    Returns:
        Loaded and configured DSPy module, or None if unavailable
    """
    # Check if enabled
    if not is_optimized_dspy_enabled():
        logger.debug("Optimized DSPy not enabled (USE_OPTIMIZED_DSPY=false)")
        return None

    # Get artifact directory
    artifact_dir = get_optimized_program_path()

    if not artifact_dir.exists():
        logger.warning(
            f"Optimized DSPy artifacts directory not found: {artifact_dir}\n"
            f"Run optimization script first: uv run python scripts/optimize_dspy_pipeline.py"
        )
        return None

    # Load metadata
    metadata = load_program_metadata(artifact_dir)
    if not metadata:
        logger.warning("Could not load metadata, proceeding with program load anyway")

    # Locate program file
    program_file = artifact_dir / "program.json"

    if not program_file.exists():
        logger.error(
            f"Optimized program file not found: {program_file}\n"
            f"Expected file: program.json in {artifact_dir}"
        )
        return None

    # Configure DSPy LM before loading program
    try:
        configure_dspy_for_runtime()
    except Exception as e:
        logger.error(f"Failed to configure DSPy LM, cannot load program: {e}")
        return None

    # Load program
    try:
        # Import the pipeline class
        from apps.dspy.pipelines import PoolulaRAGPipeline

        # Create a base instance with same parameters
        # Note: DSPy .save()/.load() preserves learned parameters
        program = PoolulaRAGPipeline(use_hybrid=True, k=5)

        # Load optimized state
        program.load(str(program_file))

        logger.info(f"✅ Loaded optimized DSPy program from {program_file}")

        # Validate
        if not validate_program_class(program, "PoolulaRAGPipeline"):
            logger.error("Program validation failed")
            return None

        return program

    except Exception as e:
        logger.error(
            f"Failed to load optimized DSPy program from {program_file}: {e}",
            exc_info=True
        )
        return None


@lru_cache(maxsize=1)
def get_dspy_program() -> Optional[dspy.Module]:
    """
    Get cached DSPy program instance.

    This is the main entry point for getting an optimized DSPy program.
    Uses @lru_cache to load program only once per process.

    Returns:
        Optimized DSPy module or None if unavailable
    """
    return load_optimized_program()


def run_dspy_program(question: str, session_id: Optional[str] = None) -> Optional[Tuple[str, list]]:
    """
    Execute optimized DSPy program on a question.

    This function:
    1. Loads optimized program (cached)
    2. Executes program with question
    3. Extracts answer and passages
    4. Returns formatted response

    Falls back silently (returns None) if optimized program unavailable or fails.

    Args:
        question: User's question
        session_id: Optional session ID (not used by current DSPy pipeline)

    Returns:
        (answer, sources) tuple or None if execution failed
    """
    # Get program (cached)
    program = get_dspy_program()

    if program is None:
        logger.debug("No optimized DSPy program available, will use baseline RAG")
        return None

    try:
        # Execute program
        logger.info(f"Executing optimized DSPy program for question: {question[:50]}...")
        prediction = program(question=question)

        # Extract answer
        answer = prediction.answer if hasattr(prediction, 'answer') else str(prediction)

        # Extract sources/passages
        sources = []
        if hasattr(prediction, 'passages'):
            # Format passages as sources
            for i, passage in enumerate(prediction.passages, 1):
                sources.append({
                    "source": f"Retrieved Passage {i}",
                    "content": passage[:200] + "..." if len(passage) > 200 else passage
                })

        logger.info("✅ DSPy program execution successful")
        logger.debug(f"Answer length: {len(answer)} chars, Sources: {len(sources)}")

        return answer, sources

    except Exception as e:
        logger.error(
            f"DSPy program execution failed, falling back to baseline RAG: {e}",
            exc_info=True
        )
        return None


def get_runtime_info() -> Dict[str, Any]:
    """
    Get information about current DSPy runtime configuration.

    Returns:
        Dict with runtime status information
    """
    enabled = is_optimized_dspy_enabled()
    artifact_path = get_optimized_program_path()

    info = {
        "optimized_dspy_enabled": enabled,
        "artifact_path": str(artifact_path),
        "artifact_exists": artifact_path.exists(),
        "program_loaded": False,
        "program_class": None,
        "llm_provider": os.getenv("LLM_PROVIDER", "anthropic"),
    }

    if enabled:
        program = get_dspy_program()
        if program is not None:
            info["program_loaded"] = True
            info["program_class"] = program.__class__.__name__

            # Load metadata if available
            metadata = load_program_metadata(artifact_path)
            if metadata:
                info["metadata"] = metadata

    return info


# Legacy compatibility - maintain old function signature
def _is_enabled() -> bool:
    """DEPRECATED: Use is_optimized_dspy_enabled() instead"""
    return is_optimized_dspy_enabled()

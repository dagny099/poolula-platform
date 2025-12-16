"""
DSPy Language Model Configuration

Wraps existing LLM provider abstraction for DSPy compatibility.
"""
import dspy
from apps.chatbot.config import Config


def configure_dspy_lm(provider_name: str = None) -> dspy.LM:
    """
    Configure DSPy to use existing LLM provider infrastructure.

    Args:
        provider_name: "anthropic", "openai", or "ollama" (defaults to Config.LLM_PROVIDER)

    Returns:
        Configured DSPy LM instance
    """
    config = Config()
    provider_name = provider_name or config.LLM_PROVIDER

    # Map provider names to DSPy model strings
    # Use the actual model IDs from Config
    model_mapping = {
        "anthropic": f"anthropic/{config.ANTHROPIC_MODEL}",
        "openai": f"openai/{config.OPENAI_MODEL}",
        "ollama": "ollama/llama2"
    }

    model_string = model_mapping.get(provider_name)
    if not model_string:
        raise ValueError(f"Unknown provider: {provider_name}")

    # Create DSPy LM instance
    lm = dspy.LM(model_string, temperature=0, max_tokens=800)

    # Configure DSPy globally
    dspy.configure(lm=lm)

    return lm


def get_configured_lm() -> dspy.LM:
    """Get or create cached DSPy LM instance"""
    return configure_dspy_lm()

"""
DSPy Signatures for Poolula Platform

Defines structured input/output interfaces for DSPy modules.
"""
import dspy


class SimpleQA(dspy.Signature):
    """Answer business questions about Poolula LLC properties and finances."""

    question = dspy.InputField(desc="User's question about properties, transactions, or documents")
    answer = dspy.OutputField(desc="Detailed answer with specific numbers, dates, and citations")


class ContextualQA(dspy.Signature):
    """Answer questions using retrieved context."""

    context = dspy.InputField(desc="Retrieved documents, database results, or background information")
    question = dspy.InputField(desc="User's question")
    answer = dspy.OutputField(desc="Answer based on provided context with citations")


class ToolSelectionSignature(dspy.Signature):
    """Determine which tool(s) to use for a question."""

    question = dspy.InputField(desc="User's question")
    available_tools = dspy.InputField(desc="List of available tool names and descriptions")
    selected_tools = dspy.OutputField(desc="Comma-separated list of tools to use")
    reasoning = dspy.OutputField(desc="Explanation of why these tools were selected")

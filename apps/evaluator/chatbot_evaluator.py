"""
General chatbot evaluator

Scores responses to the golden question set (poolula_eval_set.jsonl) on:
- Tool usage correctness (40%)
- Response relevance via keyword matching (40%)
- Response completeness (20%)

Eval set item fields:
    question           (required)
    expected_tools     e.g. ["query_database"]
    expected_content   keywords that should appear in the answer
    gold_answer        optional reference answer, surfaced in failure records

Run via scripts/evaluate_chatbot.py.
"""

from typing import Any, Dict, List

from apps.evaluator.base_evaluator import BaseEvaluator


class ChatbotEvaluator(BaseEvaluator):
    """Evaluation harness for general chatbot quality assessment"""

    name = "chatbot"

    def evaluate_response(
        self, item: Dict[str, Any], response: str, sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        checks = {}
        components = []

        # Check 1: Tool usage (40%)
        tool_check = self.check_tool_usage(item.get("expected_tools", []), sources)
        checks["tool_usage"] = tool_check
        components.append(("tool_usage", tool_check["score"], 0.4))

        # Check 2: Response relevance via keyword matching (40%)
        content_check = self.check_content_relevance(item.get("expected_content", []), response)
        checks["content_relevance"] = content_check
        components.append(("content_relevance", content_check["score"], 0.4))

        # Check 3: Response completeness (20%)
        completeness_check = self.check_completeness(response)
        checks["completeness"] = completeness_check
        components.append(("completeness", completeness_check["score"], 0.2))

        total_score, score_components = self.total_from_components(components)

        return {
            "question": item["question"],
            "response": response,
            "sources": sources,
            "expected": item,
            "checks": checks,
            "score_components": score_components,
            "total_score": total_score,
        }

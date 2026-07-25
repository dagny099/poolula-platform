"""
Shared evaluation harness for Poolula chatbot evaluators

Provides the common machinery used by the general chatbot evaluation and the
Airbnb numerical-accuracy evaluation:

- pluggable query backends (live RAG, recorded fixtures, recording wrapper)
  so evaluations can run and be tested WITHOUT live LLM credentials
- the evaluation loop with per-question error capture
- actionable failure records (expected vs actual tools, expected vs extracted
  values, sources, human-readable failure reasons)
- JSON and Markdown report writers

Subclasses implement evaluate_response() by composing the shared checks with
their own scoring weights.

Usage:
    from apps.evaluator.chatbot_evaluator import ChatbotEvaluator
    evaluator = ChatbotEvaluator(query_fn=rag.query_fn_or_fixture, verbose=True)
    report = evaluator.run_evaluation("apps/evaluator/poolula_eval_set.jsonl")
    evaluator.save_report(report, "output/eval_report.json")
    evaluator.save_markdown(report, "output/eval_report.md")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from core.logging_config import get_logger

logger = get_logger(__name__)

# A query backend takes a question and returns (response_text, sources)
QueryFn = Callable[[str], Tuple[str, List[Dict[str, Any]]]]

PASS_THRESHOLD = 0.7
WARN_THRESHOLD = 0.4


# =============================================================================
# QUERY BACKENDS
# =============================================================================

class FixtureBackend:
    """
    Replay recorded responses from a JSON fixture instead of calling the LLM.

    Fixture format:
        {"<question>": {"response": "...", "sources": [...]}, ...}

    Enables offline evaluation runs and credential-free tests.
    """

    def __init__(self, fixture_path: str):
        self.fixture_path = fixture_path
        with open(fixture_path, "r") as f:
            self.fixtures: Dict[str, Dict[str, Any]] = json.load(f)

    def __call__(self, question: str) -> Tuple[str, List[Dict[str, Any]]]:
        entry = self.fixtures.get(question)
        if entry is None:
            raise KeyError(
                f"No fixture recorded for question: {question!r} "
                f"(fixture file: {self.fixture_path})"
            )
        return entry.get("response", ""), entry.get("sources", [])


class RecordingBackend:
    """
    Wrap a live query backend and record every exchange so it can be saved
    as a fixture for later offline replay.
    """

    def __init__(self, backend: QueryFn):
        self.backend = backend
        self.recorded: Dict[str, Dict[str, Any]] = {}

    def __call__(self, question: str) -> Tuple[str, List[Dict[str, Any]]]:
        response, sources = self.backend(question)
        self.recorded[question] = {"response": response, "sources": sources}
        return response, sources

    def save(self, fixture_path: str) -> None:
        path = Path(fixture_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.recorded, f, indent=2, default=str)
        logger.info(f"Recorded {len(self.recorded)} fixtures to {fixture_path}")


# =============================================================================
# BASE EVALUATOR
# =============================================================================

class BaseEvaluator:
    """
    Common evaluation loop, checks, and reporting.

    Subclasses set `name` and implement evaluate_response(item, response,
    sources) returning a details dict containing at least "checks",
    "score_components", and "total_score" (use the helpers below).
    """

    name = "base"

    def __init__(self, query_fn: QueryFn, verbose: bool = False):
        self.query_fn = query_fn
        self.verbose = verbose

    # ---------------------------------------------------------------- loading

    @staticmethod
    def load_eval_set(eval_path: str) -> List[Dict[str, Any]]:
        """Load evaluation questions from a JSONL file"""
        questions = []
        with open(eval_path, "r") as f:
            for line in f:
                if line.strip():
                    questions.append(json.loads(line))
        return questions

    # ----------------------------------------------------------- shared checks

    @staticmethod
    def extract_tools_used(sources: List[Dict[str, Any]]) -> List[str]:
        """Infer which tools ran from the source objects they emitted"""
        tools = []
        for source in sources:
            if "query_type" in source:
                tools.append("query_database")
            elif "document_title" in source:
                tools.append("search_document_content")
            elif "text" in source and "Database Query" in str(source.get("text", "")):
                tools.append("query_database")
            elif "text" in source and "documents" in str(source.get("text", "")).lower():
                tools.append("list_business_documents")
        return sorted(set(tools))

    def check_tool_usage(
        self, expected_tools: List[str], sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Score 1.0 if every expected tool was used, else 0.0 (with reason)"""
        tools_used = self.extract_tools_used(sources)
        if not expected_tools:
            return {"expected": [], "actual": tools_used, "correct": True, "score": 1.0}

        missing = [t for t in expected_tools if t not in tools_used]
        correct = not missing
        check = {
            "expected": expected_tools,
            "actual": tools_used,
            "correct": correct,
            "score": 1.0 if correct else 0.0,
        }
        if not correct:
            check["reason"] = (
                f"Expected tool(s) {missing} not used (actual: {tools_used or 'none'})"
            )
        return check

    @staticmethod
    def check_content_relevance(
        expected_keywords: List[str], response: str
    ) -> Dict[str, Any]:
        """Score by fraction of expected keywords present in the response"""
        if not expected_keywords:
            return {"expected_keywords": [], "score": 1.0}

        response_lower = (response or "").lower()
        found = [k for k in expected_keywords if k.lower() in response_lower]
        missing = [k for k in expected_keywords if k.lower() not in response_lower]
        score = len(found) / len(expected_keywords)
        check = {
            "expected_keywords": expected_keywords,
            "keywords_found": len(found),
            "keywords_missing": missing,
            "total_keywords": len(expected_keywords),
            "score": score,
        }
        if missing:
            check["reason"] = f"Missing expected keyword(s): {missing}"
        return check

    @staticmethod
    def check_completeness(response: str) -> Dict[str, Any]:
        """Score response for being non-empty and not an error message"""
        if not response:
            score, reason = 0.0, "Empty response"
        elif "error" in response.lower() or "failed" in response.lower():
            score, reason = 0.3, "Response contains error language"
        elif len(response) < 20:
            score, reason = 0.5, "Response suspiciously short (<20 chars)"
        else:
            score, reason = 1.0, None

        check = {"response_length": len(response) if response else 0, "score": score}
        if reason:
            check["reason"] = reason
        return check

    @staticmethod
    def total_from_components(
        components: List[Tuple[str, float, float]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Weighted sum plus serializable component list"""
        total = sum(score * weight for _, score, weight in components)
        serialized = [
            {"component": name, "score": score, "weight": weight}
            for name, score, weight in components
        ]
        return total, serialized

    # -------------------------------------------------------------- interface

    def evaluate_response(
        self, item: Dict[str, Any], response: str, sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate one response; subclasses must implement"""
        raise NotImplementedError

    # ------------------------------------------------------------------ loop

    def run_evaluation(self, eval_set_path: str) -> Dict[str, Any]:
        """Run all questions through the backend and build the report"""
        print(f"\n{'='*60}")
        print(f"Evaluation Harness: {self.name}")
        print(f"{'='*60}")
        print(f"Evaluation set: {eval_set_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        questions = self.load_eval_set(eval_set_path)
        print(f"Loaded {len(questions)} questions\n")

        results = []
        for i, item in enumerate(questions, 1):
            question = item["question"]
            print(f"[{i}/{len(questions)}] {question}")

            try:
                response, sources = self.query_fn(question)
                details = self.evaluate_response(item, response, sources)
            except Exception as e:
                logger.error(f"Error evaluating question {i}: {e}", exc_info=True)
                details = {
                    "question": question,
                    "error": str(e),
                    "checks": {},
                    "total_score": 0.0,
                }
                print(f"   ERROR: {e}\n")
                results.append(details)
                continue

            score = details["total_score"]
            status = "✅" if score >= PASS_THRESHOLD else "⚠️" if score >= WARN_THRESHOLD else "❌"
            print(f"   Score: {score*100:.1f}% {status}")
            if self.verbose:
                print(f"   Response: {(response or '')[:100]}...")
                tool_check = details["checks"].get("tool_usage", {})
                print(f"   Tools: {tool_check.get('actual', [])}")
            print()

            results.append(details)

        report = self.build_report(eval_set_path, results)
        self.print_summary(report)
        return report

    # -------------------------------------------------------------- reporting

    def build_failure_record(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Distill one failed/warned question into an actionable record:
        what was expected, what actually happened, and why it failed.
        """
        checks = details.get("checks", {})
        reasons = []
        if details.get("error"):
            reasons.append(f"Evaluation error: {details['error']}")
        for check_name, check in checks.items():
            if isinstance(check, dict) and check.get("reason"):
                reasons.append(f"[{check_name}] {check['reason']}")
            # Numerical checks embed a nested validation result
            validation = check.get("validation") if isinstance(check, dict) else None
            if validation and validation.get("error"):
                reasons.append(f"[{check_name}] {validation['error']}")

        tool_check = checks.get("tool_usage", {})
        numerical = checks.get("numerical_accuracy", {})
        validation = numerical.get("validation", {})

        record = {
            "question": details.get("question"),
            "score": round(details.get("total_score", 0.0), 3),
            "expected_tools": tool_check.get("expected"),
            "actual_tools": tool_check.get("actual"),
            "reasons": reasons or ["No individual check flagged; see component scores"],
            "sources": [
                s.get("text") or s.get("document_title") or str(s)
                for s in details.get("sources", [])
            ],
            "response_excerpt": (details.get("response") or "")[:300],
        }

        # Gold facts / expected answers when available
        expected = details.get("expected", {})
        if expected.get("expected_content"):
            record["expected_content"] = expected["expected_content"]
        if expected.get("gold_answer"):
            record["gold_answer"] = expected["gold_answer"]
        if numerical:
            expected_value = numerical.get("expected_amount")
            if expected_value is None:
                expected_value = numerical.get("expected_count")
            record["expected_value"] = expected_value
            record["extracted_value"] = validation.get("extracted")
        return record

    def build_report(
        self, eval_set_path: str, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate per-question results into the final report structure"""
        total = len(results)
        total_score = sum(r.get("total_score", 0.0) for r in results)
        avg_score = total_score / total if total else 0.0

        passed = sum(1 for r in results if r.get("total_score", 0) >= PASS_THRESHOLD)
        warned = sum(
            1 for r in results if WARN_THRESHOLD <= r.get("total_score", 0) < PASS_THRESHOLD
        )
        failed = sum(1 for r in results if r.get("total_score", 0) < WARN_THRESHOLD)

        failures = [
            self.build_failure_record(r)
            for r in results
            if r.get("total_score", 0) < PASS_THRESHOLD
        ]

        return {
            "evaluator": self.name,
            "timestamp": datetime.now().isoformat(),
            "eval_set": eval_set_path,
            "total_questions": total,
            "average_score": avg_score,
            "average_score_pct": avg_score * 100,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "failures": failures,
            "results": results,
        }

    @staticmethod
    def print_summary(report: Dict[str, Any]) -> None:
        print(f"{'='*60}")
        print("Evaluation Results")
        print(f"{'='*60}")
        print(f"Total Questions: {report['total_questions']}")
        print(f"Average Score: {report['average_score_pct']:.1f}%")
        print(f"Passed (≥70%): {report['passed']}")
        print(f"Warned (40-69%): {report['warned']}")
        print(f"Failed (<40%): {report['failed']}")
        print(f"{'='*60}\n")

    @staticmethod
    def save_report(report: Dict[str, Any], output_path: str) -> None:
        """Save evaluation report to JSON file"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {output_path}")

    @staticmethod
    def save_markdown(report: Dict[str, Any], output_path: str) -> None:
        """Save a human-readable Markdown report with failure diagnostics"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Evaluation Report — {report['evaluator']}",
            "",
            f"- **Timestamp:** {report['timestamp']}",
            f"- **Eval set:** `{report['eval_set']}`",
            f"- **Average score:** {report['average_score_pct']:.1f}%",
            "",
            "| Total | Passed (≥70%) | Warned (40–69%) | Failed (<40%) |",
            "|-------|---------------|-----------------|---------------|",
            f"| {report['total_questions']} | {report['passed']} | {report['warned']} | {report['failed']} |",
            "",
        ]

        failures = report.get("failures", [])
        if failures:
            lines.append(f"## Questions below pass threshold ({len(failures)})")
            lines.append("")
            for i, f_rec in enumerate(failures, 1):
                lines.append(f"### {i}. {f_rec['question']}")
                lines.append("")
                lines.append(f"- **Score:** {f_rec['score']*100:.1f}%")
                if f_rec.get("expected_tools") is not None:
                    lines.append(f"- **Expected tools:** {f_rec['expected_tools']}")
                    lines.append(f"- **Actual tools:** {f_rec['actual_tools']}")
                if f_rec.get("expected_value") is not None:
                    lines.append(f"- **Expected value:** {f_rec['expected_value']}")
                    lines.append(f"- **Extracted value:** {f_rec.get('extracted_value')}")
                if f_rec.get("expected_content"):
                    lines.append(f"- **Expected content:** {f_rec['expected_content']}")
                if f_rec.get("gold_answer"):
                    lines.append(f"- **Gold answer:** {f_rec['gold_answer']}")
                lines.append("- **Why it failed:**")
                for reason in f_rec["reasons"]:
                    lines.append(f"  - {reason}")
                if f_rec.get("sources"):
                    lines.append(f"- **Sources:** {', '.join(map(str, f_rec['sources']))}")
                if f_rec.get("response_excerpt"):
                    lines.append("- **Response excerpt:**")
                    lines.append("")
                    lines.append("  > " + f_rec["response_excerpt"].replace("\n", " "))
                lines.append("")
        else:
            lines.append("## 🎉 All questions passed")
            lines.append("")

        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"Markdown report saved to: {output_path}")

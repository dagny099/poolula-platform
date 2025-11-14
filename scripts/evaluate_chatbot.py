#!/usr/bin/env python3
"""
Chatbot Evaluation Harness

Runs a set of golden questions through the chatbot and scores the responses.

Usage:
    python scripts/evaluate_chatbot.py
    python scripts/evaluate_chatbot.py --eval-set data/custom_eval.jsonl
    python scripts/evaluate_chatbot.py --verbose

Author: Poolula Platform
Date: 2025-11-13
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config
from core.logging_config import get_logger

logger = get_logger(__name__)


class ChatbotEvaluator:
    """
    Evaluation harness for chatbot quality assessment

    Scores responses based on:
    - Tool usage correctness
    - Response relevance (keyword matching)
    - Error handling
    """

    def __init__(self, rag_system: RAGSystem, verbose: bool = False):
        self.rag = rag_system
        self.verbose = verbose
        self.results = []

    def load_eval_set(self, eval_path: str) -> List[Dict[str, Any]]:
        """Load evaluation questions from JSONL file"""
        questions = []
        with open(eval_path, 'r') as f:
            for line in f:
                if line.strip():
                    questions.append(json.loads(line))
        return questions

    def evaluate_response(
        self,
        question: str,
        response: str,
        sources: List[Dict[str, Any]],
        expected: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate a single response

        Returns:
            Tuple of (score 0.0-1.0, details dict)
        """
        details = {
            "question": question,
            "response": response,
            "sources": sources,
            "expected": expected,
            "checks": {}
        }

        score_components = []

        # Check 1: Tool usage (40% of score)
        expected_tools = expected.get("expected_tools", [])
        if expected_tools:
            tools_used = []
            for source in sources:
                if "query_type" in source:
                    tools_used.append("query_database")
                elif "document_title" in source:
                    tools_used.append("search_document_content")
                elif "text" in source and "Database Query" in source["text"]:
                    tools_used.append("query_database")
                elif "text" in source and "documents" in source["text"]:
                    tools_used.append("list_business_documents")

            # Remove duplicates
            tools_used = list(set(tools_used))

            # Check if expected tools were used
            tools_correct = all(tool in tools_used for tool in expected_tools)
            tool_score = 1.0 if tools_correct else 0.0

            details["checks"]["tool_usage"] = {
                "expected": expected_tools,
                "actual": tools_used,
                "correct": tools_correct,
                "score": tool_score
            }

            score_components.append(("tool_usage", tool_score, 0.4))
        else:
            # If no expected tools specified, give full credit
            score_components.append(("tool_usage", 1.0, 0.4))

        # Check 2: Response relevance via keyword matching (40% of score)
        expected_content = expected.get("expected_content", [])
        if expected_content and response:
            response_lower = response.lower()
            keywords_found = sum(1 for keyword in expected_content if keyword.lower() in response_lower)
            content_score = keywords_found / len(expected_content)

            details["checks"]["content_relevance"] = {
                "expected_keywords": expected_content,
                "keywords_found": keywords_found,
                "total_keywords": len(expected_content),
                "score": content_score
            }

            score_components.append(("content_relevance", content_score, 0.4))
        else:
            # If no expected content specified, give full credit
            score_components.append(("content_relevance", 1.0, 0.4))

        # Check 3: Response completeness (20% of score)
        # Response should be non-empty and not an error message
        if not response:
            completeness_score = 0.0
        elif "error" in response.lower() or "failed" in response.lower():
            completeness_score = 0.3  # Partial credit for error handling
        elif len(response) < 20:
            completeness_score = 0.5  # Very short response
        else:
            completeness_score = 1.0  # Normal response

        details["checks"]["completeness"] = {
            "response_length": len(response) if response else 0,
            "score": completeness_score
        }

        score_components.append(("completeness", completeness_score, 0.2))

        # Calculate weighted total score
        total_score = sum(score * weight for _, score, weight in score_components)

        details["score_components"] = [
            {"component": name, "score": score, "weight": weight}
            for name, score, weight in score_components
        ]
        details["total_score"] = total_score

        return total_score, details

    def run_evaluation(self, eval_set_path: str) -> Dict[str, Any]:
        """
        Run full evaluation on question set

        Returns:
            Evaluation report with scores and details
        """
        print(f"\n{'='*60}")
        print(f"Chatbot Evaluation Harness")
        print(f"{'='*60}")
        print(f"Evaluation set: {eval_set_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        # Load questions
        questions = self.load_eval_set(eval_set_path)
        print(f"Loaded {len(questions)} questions\n")

        # Run each question
        results = []
        total_score = 0.0

        for i, item in enumerate(questions, 1):
            question = item["question"]
            print(f"[{i}/{len(questions)}] {question}")

            try:
                # Query the chatbot
                response, sources = self.rag.query(question)

                # Evaluate response
                score, details = self.evaluate_response(
                    question=question,
                    response=response,
                    sources=sources,
                    expected=item
                )

                total_score += score
                results.append(details)

                # Print result
                score_pct = score * 100
                status = "✅" if score >= 0.7 else "⚠️" if score >= 0.4 else "❌"
                print(f"   Score: {score_pct:.1f}% {status}")

                if self.verbose:
                    print(f"   Response: {response[:100]}...")
                    print(f"   Tools: {details['checks'].get('tool_usage', {}).get('actual', [])}")

                print()

            except Exception as e:
                logger.error(f"Error evaluating question {i}: {e}", exc_info=True)
                results.append({
                    "question": question,
                    "error": str(e),
                    "total_score": 0.0
                })
                print(f"   ERROR: {e}\n")

        # Calculate final statistics
        avg_score = total_score / len(questions) if questions else 0.0
        passed_count = sum(1 for r in results if r.get("total_score", 0) >= 0.7)
        warned_count = sum(1 for r in results if 0.4 <= r.get("total_score", 0) < 0.7)
        failed_count = sum(1 for r in results if r.get("total_score", 0) < 0.4)

        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "eval_set": eval_set_path,
            "total_questions": len(questions),
            "average_score": avg_score,
            "average_score_pct": avg_score * 100,
            "passed": passed_count,
            "warned": warned_count,
            "failed": failed_count,
            "results": results
        }

        # Print summary
        print(f"{'='*60}")
        print(f"Evaluation Results")
        print(f"{'='*60}")
        print(f"Total Questions: {len(questions)}")
        print(f"Average Score: {avg_score*100:.1f}%")
        print(f"Passed (≥70%): {passed_count}")
        print(f"Warned (40-69%): {warned_count}")
        print(f"Failed (<40%): {failed_count}")
        print(f"{'='*60}\n")

        # Print detailed failures if verbose
        if self.verbose and failed_count > 0:
            print("\nFailed Questions:")
            print("-" * 60)
            for r in results:
                if r.get("total_score", 0) < 0.4:
                    print(f"Q: {r['question']}")
                    print(f"Score: {r['total_score']*100:.1f}%")
                    print(f"Response: {r.get('response', 'ERROR')[:150]}...")
                    print()

        return report

    def save_report(self, report: Dict[str, Any], output_path: str):
        """Save evaluation report to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {output_path}")


def main():
    """Main evaluation script"""
    parser = argparse.ArgumentParser(description="Evaluate chatbot performance")
    parser.add_argument(
        "--eval-set",
        default="data/poolula_eval_set.jsonl",
        help="Path to evaluation question set (JSONL)"
    )
    parser.add_argument(
        "--output",
        default="data/eval_report.json",
        help="Path to save evaluation report (JSON)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results"
    )

    args = parser.parse_args()

    # Initialize RAG system
    print("Initializing RAG system...")
    config = Config()
    rag = RAGSystem(config)

    # Run evaluation
    evaluator = ChatbotEvaluator(rag, verbose=args.verbose)
    report = evaluator.run_evaluation(args.eval_set)

    # Save report
    evaluator.save_report(report, args.output)

    # Exit with appropriate code
    avg_score = report["average_score"]
    if avg_score >= 0.9:
        print("🎉 Excellent! Score ≥90%")
        sys.exit(0)
    elif avg_score >= 0.7:
        print("✅ Good! Score ≥70%")
        sys.exit(0)
    else:
        print("⚠️  Needs improvement. Score <70%")
        sys.exit(1)


if __name__ == "__main__":
    main()

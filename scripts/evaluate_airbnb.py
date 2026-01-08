#!/usr/bin/env python3
"""
Airbnb-Specific Evaluation Harness

Validates numerical accuracy using CSV ground truth.

Usage:
    uv run python scripts/evaluate_airbnb.py
    uv run python scripts/evaluate_airbnb.py --questions apps/evaluator/airbnb_eval_set.jsonl
    uv run python scripts/evaluate_airbnb.py --verbose
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config
from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth
from apps.evaluator.numerical_validator import NumericalValidator
from core.logging_config import get_logger

logger = get_logger(__name__)


class AirbnbEvaluator:
    """
    Evaluation harness for Airbnb rental income queries

    Scores based on:
    - Tool usage (40%)
    - Numerical accuracy (50%) - validates against ground truth!
    - Completeness (10%)
    """

    def __init__(
        self,
        rag_system: RAGSystem,
        ground_truth: AirbnbGroundTruth,
        verbose: bool = False
    ):
        self.rag = rag_system
        self.ground_truth = ground_truth
        self.validator = NumericalValidator(tolerance_pct=1.0)
        self.verbose = verbose

    def load_questions(self, questions_path: str) -> List[Dict[str, Any]]:
        """Load Airbnb evaluation questions from JSONL"""
        questions = []
        with open(questions_path, 'r') as f:
            for line in f:
                if line.strip():
                    questions.append(json.loads(line))
        return questions

    def evaluate_response(
        self,
        question_data: Dict[str, Any],
        response: str,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate a single response with ground truth validation

        Args:
            question_data: Question metadata including:
                - question: str
                - validation_type: "monthly_income" | "count" | "date_range" | "quarterly"
                - validation_params: dict (month, start_date, end_date, etc.)
                - expected_tools: list
            response: Chatbot response text
            sources: Tool usage sources

        Returns:
            Evaluation result with scores and details
        """
        details = {
            "question": question_data["question"],
            "response": response,
            "validation_type": question_data.get("validation_type"),
            "checks": {}
        }

        score_components = []

        # Check 1: Tool usage (40%)
        expected_tools = question_data.get("expected_tools", [])
        if expected_tools:
            tools_used = self._extract_tools_used(sources)
            tools_correct = all(tool in tools_used for tool in expected_tools)

            details["checks"]["tool_usage"] = {
                "expected": expected_tools,
                "actual": tools_used,
                "correct": tools_correct,
                "score": 1.0 if tools_correct else 0.0
            }
            score_components.append(("tool_usage", 1.0 if tools_correct else 0.0, 0.4))
        else:
            score_components.append(("tool_usage", 1.0, 0.4))

        # Check 2: Numerical accuracy (50%) - CORE VALIDATION
        validation_type = question_data.get("validation_type")
        validation_params = question_data.get("validation_params", {})

        if validation_type == "monthly_income":
            # Validate monthly income amount
            month = validation_params["month"]
            ground_truth = self.ground_truth.get_monthly_income(month)
            expected_amount = ground_truth["amount"]

            validation_result = self.validator.validate_amount(response, expected_amount)

            details["checks"]["numerical_accuracy"] = {
                "type": "monthly_income",
                "month": month,
                "expected_amount": str(expected_amount),
                "expected_count": ground_truth["count"],
                "validation": validation_result,
                "score": 1.0 if validation_result["matches"] else 0.0
            }
            score_components.append(("numerical_accuracy", 1.0 if validation_result["matches"] else 0.0, 0.5))

        elif validation_type == "count":
            # Validate reservation count
            month = validation_params["month"]
            ground_truth = self.ground_truth.get_monthly_income(month)
            expected_count = ground_truth["count"]

            validation_result = self.validator.validate_count(response, expected_count)

            details["checks"]["numerical_accuracy"] = {
                "type": "count",
                "month": month,
                "expected_count": expected_count,
                "validation": validation_result,
                "score": 1.0 if validation_result["matches"] else 0.0
            }
            score_components.append(("numerical_accuracy", 1.0 if validation_result["matches"] else 0.0, 0.5))

        elif validation_type == "date_range":
            # Validate date range income
            start_date = validation_params["start_date"]
            end_date = validation_params["end_date"]
            ground_truth = self.ground_truth.get_date_range_income(start_date, end_date)
            expected_amount = ground_truth["amount"]

            validation_result = self.validator.validate_amount(response, expected_amount)

            details["checks"]["numerical_accuracy"] = {
                "type": "date_range",
                "start_date": start_date,
                "end_date": end_date,
                "expected_amount": str(expected_amount),
                "expected_count": ground_truth["count"],
                "validation": validation_result,
                "score": 1.0 if validation_result["matches"] else 0.0
            }
            score_components.append(("numerical_accuracy", 1.0 if validation_result["matches"] else 0.0, 0.5))

        elif validation_type == "quarterly":
            # Validate quarterly income
            quarter = validation_params["quarter"]
            ground_truth = self.ground_truth.get_quarterly_income(quarter)
            expected_amount = ground_truth["amount"]

            validation_result = self.validator.validate_amount(response, expected_amount)

            details["checks"]["numerical_accuracy"] = {
                "type": "quarterly",
                "quarter": quarter,
                "expected_amount": str(expected_amount),
                "expected_count": ground_truth["count"],
                "validation": validation_result,
                "score": 1.0 if validation_result["matches"] else 0.0
            }
            score_components.append(("numerical_accuracy", 1.0 if validation_result["matches"] else 0.0, 0.5))

        elif validation_type == "reservations_list":
            # For per-reservation details, just check if response contains guest names
            # This is less precise but still useful
            month = validation_params["month"]
            reservations = self.ground_truth.get_reservations_by_month(month)
            expected_guests = [r["guest"] for r in reservations]

            # Check if at least one guest name appears in response
            found_guests = [guest for guest in expected_guests if guest.lower() in response.lower()]
            match_ratio = len(found_guests) / len(expected_guests) if expected_guests else 1.0

            details["checks"]["numerical_accuracy"] = {
                "type": "reservations_list",
                "month": month,
                "expected_guests": expected_guests,
                "found_guests": found_guests,
                "match_ratio": match_ratio,
                "score": match_ratio
            }
            score_components.append(("numerical_accuracy", match_ratio, 0.5))

        else:
            # No numerical validation for this question type
            score_components.append(("numerical_accuracy", 1.0, 0.5))

        # Check 3: Completeness (10%)
        if not response:
            completeness_score = 0.0
        elif "error" in response.lower() or "failed" in response.lower():
            completeness_score = 0.3
        elif len(response) < 20:
            completeness_score = 0.5
        else:
            completeness_score = 1.0

        details["checks"]["completeness"] = {
            "response_length": len(response),
            "score": completeness_score
        }
        score_components.append(("completeness", completeness_score, 0.1))

        # Calculate total score
        total_score = sum(score * weight for _, score, weight in score_components)

        details["score_components"] = [
            {"component": name, "score": score, "weight": weight}
            for name, score, weight in score_components
        ]
        details["total_score"] = total_score

        return details

    def _extract_tools_used(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Extract tool names from sources"""
        tools = []
        for source in sources:
            if "query_type" in source:
                tools.append("query_database")
            elif "document_title" in source:
                tools.append("search_document_content")
        return list(set(tools))

    def run_evaluation(self, questions_path: str) -> Dict[str, Any]:
        """Run full evaluation on Airbnb question set"""
        print(f"\n{'='*60}")
        print(f"Airbnb Evaluation Harness")
        print(f"{'='*60}")
        print(f"Questions: {questions_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        questions = self.load_questions(questions_path)
        print(f"Loaded {len(questions)} questions\n")

        results = []
        total_score = 0.0

        for i, question_data in enumerate(questions, 1):
            question = question_data["question"]
            print(f"[{i}/{len(questions)}] {question}")

            try:
                # Query chatbot
                response, sources = self.rag.query(question)

                # Evaluate with ground truth
                details = self.evaluate_response(question_data, response, sources)

                score = details["total_score"]
                total_score += score
                results.append(details)

                # Print result
                score_pct = score * 100
                status = "✅" if score >= 0.7 else "⚠️" if score >= 0.4 else "❌"
                print(f"   Score: {score_pct:.1f}% {status}")

                # Show numerical validation details
                if "numerical_accuracy" in details["checks"]:
                    na_check = details["checks"]["numerical_accuracy"]
                    if "validation" in na_check:
                        val = na_check["validation"]
                        if val["matches"]:
                            print(f"   ✓ Numerical accuracy: {val['extracted']} matches expected")
                        else:
                            print(f"   ✗ Numerical accuracy: {val.get('error', 'Mismatch')}")
                    elif "match_ratio" in na_check:
                        ratio = na_check["match_ratio"]
                        print(f"   ✓ Guest names: {len(na_check['found_guests'])}/{len(na_check['expected_guests'])} found ({ratio*100:.0f}%)")

                if self.verbose:
                    print(f"   Response: {response[:100]}...")

                print()

            except Exception as e:
                logger.error(f"Error evaluating question {i}: {e}", exc_info=True)
                results.append({
                    "question": question,
                    "error": str(e),
                    "total_score": 0.0
                })
                print(f"   ERROR: {e}\n")

        # Calculate statistics
        avg_score = total_score / len(questions) if questions else 0.0
        passed = sum(1 for r in results if r.get("total_score", 0) >= 0.7)
        warned = sum(1 for r in results if 0.4 <= r.get("total_score", 0) < 0.7)
        failed = sum(1 for r in results if r.get("total_score", 0) < 0.4)

        report = {
            "timestamp": datetime.now().isoformat(),
            "questions_file": questions_path,
            "total_questions": len(questions),
            "average_score": avg_score,
            "average_score_pct": avg_score * 100,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "results": results
        }

        # Print summary
        print(f"{'='*60}")
        print(f"Evaluation Results")
        print(f"{'='*60}")
        print(f"Total Questions: {len(questions)}")
        print(f"Average Score: {avg_score*100:.1f}%")
        print(f"Passed (≥70%): {passed}")
        print(f"Warned (40-69%): {warned}")
        print(f"Failed (<40%): {failed}")
        print(f"{'='*60}\n")

        return report

    def save_report(self, report: Dict[str, Any], output_path: str):
        """Save evaluation report to JSON"""
        # Create output directory if needed
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {output_path}")


def main():
    """Main evaluation script"""
    parser = argparse.ArgumentParser(description="Evaluate Airbnb queries with ground truth validation")
    parser.add_argument(
        "--questions",
        default="apps/evaluator/airbnb_eval_set.jsonl",
        help="Path to Airbnb question set (JSONL)"
    )
    parser.add_argument(
        "--csv",
        default="data/airbnb_12_2024-11_2025.csv",
        help="Path to Airbnb CSV for ground truth"
    )
    parser.add_argument(
        "--output",
        default="data/airbnb_eval_report.json",
        help="Path to save evaluation report (JSON)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results"
    )

    args = parser.parse_args()

    # Initialize components
    print("Initializing RAG system...")
    config = Config()
    rag = RAGSystem(config)

    print(f"Loading ground truth from {args.csv}...")
    ground_truth = AirbnbGroundTruth(args.csv)

    stats = ground_truth.get_all_statistics()
    print(f"  Loaded {stats['total_reservations']} reservations")
    print(f"  Total revenue: ${Decimal(stats['total_revenue']):,.2f}")
    print(f"  Date range: {stats['date_range']['min']} to {stats['date_range']['max']}\n")

    # Run evaluation
    evaluator = AirbnbEvaluator(rag, ground_truth, verbose=args.verbose)
    report = evaluator.run_evaluation(args.questions)

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

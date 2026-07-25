"""
Airbnb-specific evaluator with CSV ground-truth numerical validation

Scores responses to the Airbnb question set (airbnb_eval_set.jsonl) on:
- Tool usage (40%)
- Numerical accuracy vs. ground truth (50%)
- Response completeness (10%)

Eval set item fields:
    question           (required)
    validation_type    "monthly_income" | "count" | "date_range" | "quarterly"
                       | "reservations_list"
    validation_params  dict (month, start_date/end_date, quarter)
    expected_tools     e.g. ["query_database"]

Run via scripts/evaluate_airbnb.py.
"""

from typing import Any, Dict, List

from apps.evaluator.base_evaluator import BaseEvaluator
from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth
from apps.evaluator.numerical_validator import NumericalValidator


class AirbnbEvaluator(BaseEvaluator):
    """Evaluation harness for Airbnb rental income queries"""

    name = "airbnb"

    def __init__(
        self,
        query_fn,
        ground_truth: AirbnbGroundTruth,
        verbose: bool = False,
        tolerance_pct: float = 1.0,
    ):
        super().__init__(query_fn, verbose=verbose)
        self.ground_truth = ground_truth
        self.validator = NumericalValidator(tolerance_pct=tolerance_pct)

    def _check_numerical_accuracy(
        self, item: Dict[str, Any], response: str
    ) -> Dict[str, Any]:
        """Validate numbers in the response against CSV ground truth"""
        validation_type = item.get("validation_type")
        params = item.get("validation_params", {})

        if validation_type == "monthly_income":
            truth = self.ground_truth.get_monthly_income(params["month"])
            validation = self.validator.validate_amount(response, truth["amount"])
            return {
                "type": validation_type,
                "month": params["month"],
                "expected_amount": str(truth["amount"]),
                "expected_count": truth["count"],
                "validation": validation,
                "score": 1.0 if validation["matches"] else 0.0,
            }

        if validation_type == "count":
            truth = self.ground_truth.get_monthly_income(params["month"])
            validation = self.validator.validate_count(response, truth["count"])
            return {
                "type": validation_type,
                "month": params["month"],
                "expected_count": truth["count"],
                "validation": validation,
                "score": 1.0 if validation["matches"] else 0.0,
            }

        if validation_type == "date_range":
            truth = self.ground_truth.get_date_range_income(
                params["start_date"], params["end_date"]
            )
            validation = self.validator.validate_amount(response, truth["amount"])
            return {
                "type": validation_type,
                "start_date": params["start_date"],
                "end_date": params["end_date"],
                "expected_amount": str(truth["amount"]),
                "expected_count": truth["count"],
                "validation": validation,
                "score": 1.0 if validation["matches"] else 0.0,
            }

        if validation_type == "quarterly":
            truth = self.ground_truth.get_quarterly_income(params["quarter"])
            validation = self.validator.validate_amount(response, truth["amount"])
            return {
                "type": validation_type,
                "quarter": params["quarter"],
                "expected_amount": str(truth["amount"]),
                "expected_count": truth["count"],
                "validation": validation,
                "score": 1.0 if validation["matches"] else 0.0,
            }

        if validation_type == "reservations_list":
            reservations = self.ground_truth.get_reservations_by_month(params["month"])
            expected_guests = [r["guest"] for r in reservations]
            found = [g for g in expected_guests if g.lower() in (response or "").lower()]
            missing = [g for g in expected_guests if g.lower() not in (response or "").lower()]
            match_ratio = len(found) / len(expected_guests) if expected_guests else 1.0
            check = {
                "type": validation_type,
                "month": params["month"],
                "expected_guests": expected_guests,
                "found_guests": found,
                "match_ratio": match_ratio,
                "score": match_ratio,
            }
            if missing:
                check["reason"] = f"Guest name(s) missing from response: {missing}"
            return check

        # No numerical validation for this question type
        return {"type": None, "score": 1.0}

    def evaluate_response(
        self, item: Dict[str, Any], response: str, sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        checks = {}
        components = []

        # Check 1: Tool usage (40%)
        tool_check = self.check_tool_usage(item.get("expected_tools", []), sources)
        checks["tool_usage"] = tool_check
        components.append(("tool_usage", tool_check["score"], 0.4))

        # Check 2: Numerical accuracy vs ground truth (50%) - CORE VALIDATION
        numerical_check = self._check_numerical_accuracy(item, response)
        checks["numerical_accuracy"] = numerical_check
        components.append(("numerical_accuracy", numerical_check["score"], 0.5))

        # Check 3: Completeness (10%)
        completeness_check = self.check_completeness(response)
        checks["completeness"] = completeness_check
        components.append(("completeness", completeness_check["score"], 0.1))

        total_score, score_components = self.total_from_components(components)

        return {
            "question": item["question"],
            "response": response,
            "sources": sources,
            "expected": item,
            "validation_type": item.get("validation_type"),
            "checks": checks,
            "score_components": score_components,
            "total_score": total_score,
        }

"""
Tests for the Airbnb evaluator and numerical validator

Uses a tiny synthetic Airbnb CSV as ground truth; all offline.
"""

import json
from decimal import Decimal

import pytest

from apps.evaluator.airbnb_evaluator import AirbnbEvaluator
from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth
from apps.evaluator.base_evaluator import FixtureBackend
from apps.evaluator.numerical_validator import NumericalValidator


AIRBNB_CSV = """Date,Type,Confirmation code,Start date,End date,Nights,Guest,Gross earnings,Service fee,Cleaning fee,Pet fee,Occupancy taxes
06/01/2025,Reservation,HM001,05/28/2025,06/01/2025,4,Alice Johnson,"$1,200.00",$36.00,$100.00,$0.00,$50.00
06/15/2025,Reservation,HM002,06/10/2025,06/15/2025,5,Bob Smith,"$1,800.00",$54.00,$100.00,$0.00,$75.00
07/04/2025,Reservation,HM003,07/01/2025,07/04/2025,3,Carol Danvers,"$920.45",$27.00,$100.00,$0.00,$40.00
"""


@pytest.fixture(name="ground_truth")
def ground_truth_fixture(tmp_path):
    csv_path = tmp_path / "airbnb.csv"
    csv_path.write_text(AIRBNB_CSV)
    return AirbnbGroundTruth(str(csv_path))


# =============================================================================
# NUMERICAL VALIDATOR
# =============================================================================

def test_validator_extracts_and_matches_amount():
    validator = NumericalValidator(tolerance_pct=1.0)
    result = validator.validate_amount(
        "Your rental income was $3,000.00 in June.", Decimal("3000.00")
    )
    assert result["matches"] is True
    assert result["extracted"] == "3000.00"


def test_validator_flags_mismatch_with_diff():
    validator = NumericalValidator(tolerance_pct=1.0)
    result = validator.validate_amount(
        "Your rental income was $2,500.00 in June.", Decimal("3000.00")
    )
    assert result["matches"] is False
    assert "exceeds tolerance" in result["error"]


def test_validator_no_amount_found():
    validator = NumericalValidator(tolerance_pct=1.0)
    result = validator.validate_amount("I do not know.", Decimal("3000.00"))
    assert result["matches"] is False
    assert result["extracted"] is None


def test_validator_count_extraction():
    validator = NumericalValidator()
    assert validator.validate_count("There were 2 reservations.", 2)["matches"] is True
    assert validator.validate_count("There were two reservations.", 2)["matches"] is True
    assert validator.validate_count("There were 5 bookings.", 2)["matches"] is False


# =============================================================================
# GROUND TRUTH
# =============================================================================

def test_ground_truth_monthly_income(ground_truth):
    june = ground_truth.get_monthly_income("2025-06")
    assert june["amount"] == Decimal("3000.00")
    assert june["count"] == 2


def test_ground_truth_quarterly_income(ground_truth):
    q3 = ground_truth.get_quarterly_income("2025-Q3")
    assert q3["amount"] == Decimal("920.45")
    assert q3["count"] == 1


# =============================================================================
# AIRBNB EVALUATOR END-TO-END (FIXTURE BACKEND)
# =============================================================================

@pytest.fixture(name="airbnb_eval_run")
def airbnb_eval_run_fixture(tmp_path, ground_truth):
    """Run a 3-question Airbnb evaluation against fixture responses"""
    eval_file = tmp_path / "airbnb_eval.jsonl"
    items = [
        {  # correct amount, correct tool -> pass
            "question": "What was my rental income in June 2025?",
            "validation_type": "monthly_income",
            "validation_params": {"month": "2025-06"},
            "expected_tools": ["query_database"],
        },
        {  # wrong amount -> numerical failure
            "question": "What was my rental income in July 2025?",
            "validation_type": "monthly_income",
            "validation_params": {"month": "2025-07"},
            "expected_tools": ["query_database"],
        },
        {  # correct count -> pass
            "question": "How many reservations in June 2025?",
            "validation_type": "count",
            "validation_params": {"month": "2025-06"},
            "expected_tools": ["query_database"],
        },
    ]
    eval_file.write_text("\n".join(json.dumps(i) for i in items))

    fixture_file = tmp_path / "responses.json"
    fixture_file.write_text(json.dumps({
        "What was my rental income in June 2025?": {
            "response": "Your rental income in June 2025 was $3,000.00 from 2 reservations.",
            "sources": [{"query_type": "transactions", "text": "Database Query: transactions"}],
        },
        "What was my rental income in July 2025?": {
            "response": "Your rental income in July 2025 was $1,500.00.",
            "sources": [{"query_type": "transactions", "text": "Database Query: transactions"}],
        },
        "How many reservations in June 2025?": {
            "response": "You had 2 reservations in June 2025.",
            "sources": [{"query_type": "transactions", "text": "Database Query: transactions"}],
        },
    }))

    evaluator = AirbnbEvaluator(
        query_fn=FixtureBackend(str(fixture_file)), ground_truth=ground_truth
    )
    return evaluator.run_evaluation(str(eval_file))


def test_airbnb_evaluation_scores(airbnb_eval_run):
    report = airbnb_eval_run
    assert report["total_questions"] == 3
    assert report["passed"] == 2
    assert report["failed"] + report["warned"] == 1


def test_airbnb_failure_record_is_actionable(airbnb_eval_run):
    failures = airbnb_eval_run["failures"]
    assert len(failures) == 1
    failure = failures[0]

    assert failure["question"] == "What was my rental income in July 2025?"
    # Ground truth for July is 920.45; response said 1500.00
    assert failure["expected_value"] == "920.45"
    assert failure["extracted_value"] == "1500.00"
    assert any("tolerance" in r for r in failure["reasons"])
    assert failure["actual_tools"] == ["query_database"]

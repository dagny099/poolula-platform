"""
Tests for the demo-persona dataset and its generator.

Guards three invariants:
1. The generator is deterministic and the committed demo CSV / ground-truth
   JSON match what the current generator code produces (no silent drift).
2. The generated CSV round-trips through the real import and evaluation
   code paths (import_airbnb_csv, AirbnbGroundTruth).
3. The demo eval set's numeric expectations stay in sync with the committed
   ground truth, and seed_database parses both the demo and real facts YAML
   correctly (backward compatibility).
"""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DEMO_CSV = PROJECT_ROOT / "demo" / "airbnb_demo_2024-12_2025-11.csv"
DEMO_GROUND_TRUTH = PROJECT_ROOT / "demo" / "ground_truth.json"
DEMO_FACTS = PROJECT_ROOT / "demo" / "demo_facts.yml"
DEMO_EVAL_SET = PROJECT_ROOT / "demo" / "demo_eval_set.jsonl"
CHATBOT_FIXTURE = PROJECT_ROOT / "demo" / "fixtures" / "chatbot_fixture.json"

sys.path.insert(0, str(PROJECT_ROOT))

from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth


def load_ground_truth() -> dict:
    return json.loads(DEMO_GROUND_TRUTH.read_text())


class TestGeneratorDeterminism:
    def test_committed_artifacts_match_generator_output(self, tmp_path):
        """Regenerating with the default seed must reproduce the committed
        CSV and ground truth byte-for-byte — catches both nondeterminism and
        drift between generator code and committed artifacts."""
        out_csv = tmp_path / DEMO_CSV.name  # same basename -> same generated_from
        out_gt = tmp_path / "ground_truth.json"
        result = subprocess.run(
            [
                sys.executable, "scripts/generate_demo_airbnb.py",
                "--seed", "42",
                "--out", str(out_csv),
                "--ground-truth", str(out_gt),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert out_csv.read_text() == DEMO_CSV.read_text()
        assert out_gt.read_text() == DEMO_GROUND_TRUTH.read_text()


class TestGeneratedCsvThroughEvaluator:
    def test_ground_truth_parser_loads_csv(self):
        gt = AirbnbGroundTruth(str(DEMO_CSV))
        assert len(gt.reservations) > 0

    def test_every_month_has_reservations(self):
        """The untouched airbnb_eval_set.jsonl asks about specific 2025
        months; each month in the range must have data behind it."""
        monthly = load_ground_truth()["monthly_income"]
        assert sorted(monthly) == [
            "2024-12", "2025-01", "2025-02", "2025-03", "2025-04", "2025-05",
            "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
        ]
        for month, values in monthly.items():
            assert values["count"] >= 2, f"{month} has fewer than 2 reservations"

    def test_committed_ground_truth_matches_csv(self):
        gt = AirbnbGroundTruth(str(DEMO_CSV))
        data = load_ground_truth()
        for month, expected in data["monthly_income"].items():
            result = gt.get_monthly_income(month)
            assert str(result["amount"]) == expected["amount"]
            assert result["count"] == expected["count"]
        assert data["statistics"]["total_revenue"] == str(
            sum(r.gross_earnings for r in gt.reservations)
        )


class TestGeneratedCsvThroughImporter:
    def test_import_mapping(self):
        from scripts.import_airbnb_transactions import import_airbnb_csv

        transactions, summary = import_airbnb_csv(
            str(DEMO_CSV), property_id=uuid4(), dry_run=True
        )
        stats = load_ground_truth()["statistics"]

        # One revenue transaction per reservation + resolution payout
        assert summary["revenue_count"] == stats["total_reservations"]
        # One service-fee expense per Reservation row (fee is always > 0)
        assert summary["expense_count"] == stats["total_reservations"] - 2
        # Revenue equals total gross earnings from ground truth
        assert summary["revenue_total"] == Decimal(stats["total_revenue"])
        # Amount validator forbids zero-amount transactions
        assert all(t.amount != 0 for t in transactions)


class TestDemoFactsYaml:
    def test_demo_property_fields(self):
        from scripts.seed_database import create_property_from_yaml

        prop = create_property_from_yaml(yaml.safe_load(DEMO_FACTS.read_text()))
        assert prop.address == "742 Juniper Bend Court, Granite Pass, CO 81249"
        assert prop.acquisition_date == date(2024, 5, 20)
        assert prop.purchase_price_total == Decimal("517500.00")
        assert prop.land_basis == Decimal("93150.00")
        assert prop.building_basis == Decimal("424350.00")
        assert prop.ffe_basis == Decimal("12000.00")
        assert prop.placed_in_service == date(2025, 1, 15)

    def test_real_yaml_backward_compatible(self):
        """The real facts YAML has no city/state/zip and an UNKNOWN
        placed-in-service date; legacy fallbacks must still apply."""
        from scripts.seed_database import create_property_from_yaml

        real_facts = PROJECT_ROOT / "poolula_facts.yml"
        prop = create_property_from_yaml(yaml.safe_load(real_facts.read_text()))
        assert prop.address.endswith(", Montrose, CO 81401")
        assert prop.placed_in_service == date(2025, 2, 1)


class TestDemoEvalSetSync:
    def test_airbnb_numeric_keywords_match_ground_truth(self):
        """The airbnb_* questions embed numbers from ground_truth.json; if
        the CSV is regenerated with different data, this pins the eval set
        until it is updated too."""
        data = load_ground_truth()
        expected_by_category = {
            "airbnb_monthly": str(int(Decimal(data["monthly_income"]["2025-07"]["amount"]))),
            "airbnb_count": str(data["monthly_income"]["2025-08"]["count"]),
            "airbnb_range": str(int(Decimal(data["date_range_2025-05-01_2025-07-31"]))),
            "airbnb_quarterly": str(int(Decimal(data["quarterly_income_2025"]["Q3"]))),
        }
        items = [
            json.loads(line)
            for line in DEMO_EVAL_SET.read_text().splitlines()
            if line.strip()
        ]
        assert len(items) == 20
        for category, expected in expected_by_category.items():
            matching = [i for i in items if i["category"] == category]
            assert matching, f"no eval question with category {category}"
            for item in matching:
                assert expected in item["expected_content"], (
                    f"{category}: expected keyword {expected!r} "
                    f"not in {item['expected_content']}"
                )


@pytest.mark.skipif(
    not CHATBOT_FIXTURE.exists(),
    reason="fixture not recorded yet (scripts/evaluate_chatbot.py --record-fixture)",
)
class TestFixtureCoverage:
    def test_fixture_covers_all_demo_questions(self):
        """FixtureBackend replays by exact question lookup; every eval-set
        question must be present or offline replay raises KeyError."""
        recorded = json.loads(CHATBOT_FIXTURE.read_text())
        for line in DEMO_EVAL_SET.read_text().splitlines():
            if not line.strip():
                continue
            question = json.loads(line)["question"]
            assert question in recorded, f"fixture missing question: {question!r}"

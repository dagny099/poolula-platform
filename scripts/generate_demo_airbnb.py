#!/usr/bin/env python3
"""
Generate Synthetic Airbnb Transaction CSV for Demo Mode

Produces a fictional-but-realistic Airbnb earnings export for the demo
persona (property "Juniper Bend Hideaway"), matching the real 22-column
export format that scripts/import_airbnb_transactions.py expects.

After writing the CSV, the script loads it back through
apps.evaluator.airbnb_ground_truth.AirbnbGroundTruth and writes the true
aggregates to a ground-truth JSON, so demo eval expectations match the
generated data by construction.

Usage:
    uv run python scripts/generate_demo_airbnb.py \\
        --out demo/airbnb_demo_2024-12_2025-11.csv \\
        --ground-truth demo/ground_truth.json \\
        --seed 42

Deterministic: the same --seed always produces byte-identical output.

Author: Poolula Platform
Date: 2026-07-05
"""

import argparse
import csv
import json
import random
import string
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth

LISTING_NAME = "Juniper Bend Hideaway"
PAYOUT_DETAILS = "Transfer to Poolula LLC, Checking 4410 (USD)"
CLEANING_FEE = Decimal("50.00")
PET_FEE = Decimal("25.00")
SERVICE_FEE_RATE = Decimal("0.03")
OCCUPANCY_TAX_RATE = Decimal("0.1508")

# Exact header of a real Airbnb earnings export (what the importer reads)
CSV_COLUMNS = [
    "Date", "Arriving by date", "Type", "Confirmation code", "Booking date",
    "Start date", "End date", "Nights", "Guest", "Listing", "Details",
    "Reference code", "Currency", "Amount", "Paid out", "Service fee",
    "Fast pay fee", "Cleaning fee", "Pet fee", "Gross earnings",
    "Occupancy taxes", "Earnings year",
]

FIRST_NAMES = [
    "Avery", "Bennett", "Camila", "Dario", "Elena", "Franklin", "Gwen",
    "Hiro", "Imani", "Jonas", "Katya", "Leandro", "Maren", "Nadia",
    "Otis", "Priya", "Quentin", "Rosa", "Silas", "Tamsin", "Ulysses",
    "Vera", "Wendell", "Ximena", "Yusuf", "Zora", "Callum", "Delphine",
    "Ember", "Farid",
]
LAST_NAMES = [
    "Ashford", "Boulanger", "Castellanos", "Dvorak", "Ellingson", "Fairweather",
    "Grimaldi", "Holloway", "Ivanova", "Jarrett", "Kowalczyk", "Lindqvist",
    "Marchetti", "Nakamura", "Okafor", "Pemberton", "Quintana", "Rasmussen",
    "Sagara", "Thackeray", "Umberto", "Vandermeer", "Whitlock", "Xiang",
    "Yarrow", "Zielinski", "Abernathy", "Beaumont", "Calloway", "Delacroix",
]

# Seasonal profile for a Colorado mountain STR: ski-season peaks (Dec-Mar),
# mud-season troughs (Apr-May, Nov), summer secondary peak (Jun-Aug).
# Values: (nightly rate range, gap-days range between stays, nights range)
SEASON_PROFILE = {
    12: ((190, 265), (0, 2), (2, 4)),
    1:  ((190, 265), (0, 2), (2, 4)),
    2:  ((190, 265), (0, 2), (2, 4)),
    3:  ((180, 250), (1, 3), (2, 4)),
    4:  ((120, 175), (5, 11), (2, 4)),
    5:  ((120, 175), (5, 10), (2, 5)),
    6:  ((160, 220), (1, 4), (2, 5)),
    7:  ((160, 220), (1, 3), (2, 5)),
    8:  ((160, 220), (1, 4), (2, 5)),
    9:  ((140, 190), (3, 6), (2, 5)),
    10: ((140, 190), (3, 6), (2, 4)),
    11: ((120, 170), (6, 12), (2, 4)),
}


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt_date(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def confirmation_code(rng: random.Random) -> str:
    return "HM" + "".join(rng.choices(string.ascii_uppercase + string.digits, k=8))


def blank_row() -> dict:
    return {col: "" for col in CSV_COLUMNS}


def generate_reservations(rng: random.Random, start: date, end: date) -> list[dict]:
    """Generate non-overlapping fictional stays between start and end."""
    reservations = []
    cursor = start + timedelta(days=rng.randint(0, 2))
    guest_pool = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
    rng.shuffle(guest_pool)

    while True:
        profile = SEASON_PROFILE[cursor.month]
        (rate_lo, rate_hi), (gap_lo, gap_hi), (nights_lo, nights_hi) = profile
        nights = rng.randint(nights_lo, nights_hi)
        checkout = cursor + timedelta(days=nights)
        if checkout > end:
            break

        first, last = guest_pool[len(reservations) % len(guest_pool)]
        nightly = money(rng.randint(rate_lo, rate_hi))
        pet_fee = PET_FEE if rng.random() < 0.20 else Decimal("0.00")
        gross = money(nightly * nights + CLEANING_FEE + pet_fee)
        service_fee = money(gross * SERVICE_FEE_RATE)

        reservations.append({
            "confirmation": confirmation_code(rng),
            "guest": f"{first} {last}",
            "booking_date": cursor - timedelta(days=rng.randint(5, 45)),
            "start": cursor,
            "end": checkout,
            "nights": nights,
            "gross": gross,
            "service_fee": service_fee,
            "amount": money(gross - service_fee),
            "cleaning_fee": CLEANING_FEE,
            "pet_fee": pet_fee,
            "occupancy_taxes": money(gross * OCCUPANCY_TAX_RATE),
        })

        cursor = checkout + timedelta(days=rng.randint(gap_lo, gap_hi))

    return reservations


def build_rows(rng: random.Random, reservations: list[dict]) -> list[dict]:
    """Build CSV rows: a Payout + Reservation pair per stay, plus two
    Resolution Payout rows, in descending payout-date order like the real
    export."""
    rows = []
    for res in reservations:
        payout_date = res["end"] + timedelta(days=1)

        payout = blank_row()
        payout.update({
            "Date": fmt_date(payout_date),
            "Arriving by date": fmt_date(payout_date + timedelta(days=4)),
            "Type": "Payout",
            "Details": PAYOUT_DETAILS,
            "Reference code": "".join(rng.choices(string.digits, k=15)),
            "Currency": "USD",
            "Paid out": str(res["amount"]),
        })

        reservation = blank_row()
        reservation.update({
            "Date": fmt_date(payout_date),
            "Type": "Reservation",
            "Confirmation code": res["confirmation"],
            "Booking date": fmt_date(res["booking_date"]),
            "Start date": fmt_date(res["start"]),
            "End date": fmt_date(res["end"]),
            "Nights": str(res["nights"]),
            "Guest": res["guest"],
            "Listing": LISTING_NAME,
            "Currency": "USD",
            "Amount": str(res["amount"]),
            "Service fee": str(res["service_fee"]),
            "Cleaning fee": str(res["cleaning_fee"]),
            "Pet fee": str(res["pet_fee"]),
            "Gross earnings": str(res["gross"]),
            "Occupancy taxes": str(res["occupancy_taxes"]),
            "Earnings year": str(res["end"].year),
        })

        rows.append((payout_date, 1, payout))
        rows.append((payout_date, 0, reservation))

    # Two Resolution Payout rows (damage reimbursements) tied to mid-list
    # stays. Date and End date must land in the same month: the importer
    # books resolution income on Date while ground truth uses End date.
    candidates = [
        r for r in reservations
        if (r["end"] + timedelta(days=5)).month == r["end"].month
    ]
    for res in rng.sample(candidates, k=2):
        resolution_date = res["end"] + timedelta(days=5)
        amount = money(rng.randint(40, 120))
        resolution = blank_row()
        resolution.update({
            "Date": fmt_date(resolution_date),
            "Type": "Resolution Payout",
            "Confirmation code": res["confirmation"],
            "Start date": fmt_date(res["start"]),
            "End date": fmt_date(res["end"]),
            "Nights": str(res["nights"]),
            "Guest": res["guest"],
            "Listing": LISTING_NAME,
            "Details": f"AirCover damage reimbursement for resolution CLSF-{rng.randint(10000000, 99999999)}",
            "Currency": "USD",
            "Amount": str(amount),
            "Gross earnings": str(amount),
            "Earnings year": str(res["end"].year),
        })
        rows.append((resolution_date, 2, resolution))

    rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [row for _, _, row in rows]


def write_ground_truth(csv_path: Path, ground_truth_path: Path) -> dict:
    """Compute true aggregates from the generated CSV using the evaluator's
    own parser, so demo eval expectations match by construction."""
    gt = AirbnbGroundTruth(str(csv_path))

    months = []
    year, month = 2024, 12
    while (year, month) <= (2025, 11):
        months.append(f"{year}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

    monthly = {}
    for m in months:
        result = gt.get_monthly_income(m)
        monthly[m] = {
            "amount": str(result["amount"]),
            "count": result["count"],
        }

    date_range = gt.get_date_range_income("2025-05-01", "2025-07-31")
    data = {
        "generated_from": csv_path.name,
        "monthly_income": monthly,
        "quarterly_income_2025": {
            q: str(gt.get_quarterly_income(f"2025-{q}")["amount"]) for q in ("Q1", "Q2", "Q3")
        },
        "date_range_2025-05-01_2025-07-31": str(date_range["amount"]),
        "statistics": gt.get_all_statistics(),
    }

    ground_truth_path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Airbnb CSV for demo mode")
    parser.add_argument("--out", default="demo/airbnb_demo_2024-12_2025-11.csv",
                        help="Output CSV path")
    parser.add_argument("--ground-truth", default="demo/ground_truth.json",
                        help="Output ground-truth JSON path")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (same seed -> identical output)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    reservations = generate_reservations(rng, date(2024, 12, 1), date(2025, 11, 30))
    rows = build_rows(rng, reservations)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    data = write_ground_truth(out_path, Path(args.ground_truth))

    # Every month must have at least 2 reservations so the existing
    # airbnb_eval_set.jsonl month/quarter questions have data behind them.
    thin_months = [m for m, v in data["monthly_income"].items() if v["count"] < 2]
    if thin_months:
        raise SystemExit(
            f"Months with <2 reservations: {thin_months} — adjust --seed or SEASON_PROFILE"
        )

    print(f"Wrote {len(reservations)} reservations ({len(rows)} rows) to {out_path}")
    print(f"Ground truth -> {args.ground_truth}")
    for m, v in data["monthly_income"].items():
        print(f"  {m}: {v['count']:>2} stays  ${v['amount']}")


if __name__ == "__main__":
    main()

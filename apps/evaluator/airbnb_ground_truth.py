"""
Airbnb Ground Truth Calculator

Computes expected answers from CSV data for numerical validation.

Usage:
    from apps.evaluator.airbnb_ground_truth import AirbnbGroundTruth

    gt = AirbnbGroundTruth("documents/airbnb_12_2024-11_2025.csv")
    answer = gt.get_monthly_income("2025-07")
    # Returns: {"amount": Decimal("3960.00"), "count": 8, "reservations": [...]}
"""

import csv
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Reservation:
    """Single Airbnb reservation record"""
    confirmation: str
    guest: str
    start_date: date
    end_date: date  # Revenue recognition date (accrual accounting)
    nights: int
    gross_earnings: Decimal
    service_fee: Decimal
    cleaning_fee: Decimal
    pet_fee: Decimal
    occupancy_taxes: Decimal

    @property
    def month(self) -> str:
        """Month for aggregation (YYYY-MM)"""
        return self.end_date.strftime("%Y-%m")

    @property
    def quarter(self) -> str:
        """Quarter for aggregation (YYYY-Q#)"""
        q = (self.end_date.month - 1) // 3 + 1
        return f"{self.end_date.year}-Q{q}"


class AirbnbGroundTruth:
    """
    Calculate ground truth answers from Airbnb CSV data

    Handles accrual accounting: revenue recognized on END DATE (checkout),
    not booking date or payout date.
    """

    def __init__(self, csv_path: str):
        """Load and parse CSV data"""
        self.csv_path = Path(csv_path)
        self.reservations: List[Reservation] = []
        self._load_csv()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse MM/DD/YYYY format"""
        if not date_str or not date_str.strip():
            return None
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
        except ValueError:
            return None

    def _parse_amount(self, amount_str: str) -> Decimal:
        """Parse dollar amount"""
        if not amount_str or not amount_str.strip():
            return Decimal("0.00")
        cleaned = amount_str.replace("$", "").replace(",", "").strip()
        return Decimal(cleaned) if cleaned else Decimal("0.00")

    def _parse_int(self, int_str: str) -> int:
        """Parse integer value"""
        if not int_str or not int_str.strip():
            return 0
        try:
            return int(int_str.strip())
        except ValueError:
            return 0

    def _load_csv(self):
        """Load reservations from CSV"""
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trans_type = row.get('Type', '').strip()

                # Process both Reservation and Resolution Payout rows
                # (Resolution Payouts are also rental income - damage reimbursements)
                if trans_type not in ['Reservation', 'Resolution Payout']:
                    continue

                end_date = self._parse_date(row.get('End date'))
                if not end_date:
                    continue  # Skip if no end date

                start_date = self._parse_date(row.get('Start date'))

                reservation = Reservation(
                    confirmation=row.get('Confirmation code', '').strip(),
                    guest=row.get('Guest', '').strip(),
                    start_date=start_date if start_date else end_date,  # Fallback to end_date
                    end_date=end_date,
                    nights=self._parse_int(row.get('Nights', '0')),
                    gross_earnings=self._parse_amount(row.get('Gross earnings')),
                    service_fee=self._parse_amount(row.get('Service fee')),
                    cleaning_fee=self._parse_amount(row.get('Cleaning fee')),
                    pet_fee=self._parse_amount(row.get('Pet fee')),
                    occupancy_taxes=self._parse_amount(row.get('Occupancy taxes'))
                )

                self.reservations.append(reservation)

    def get_monthly_income(self, month: str) -> Dict:
        """
        Get total income for a specific month (YYYY-MM)

        Args:
            month: Month string like "2025-07"

        Returns:
            {
                "amount": Decimal,
                "count": int,
                "reservations": List[Dict]
            }
        """
        reservations = [r for r in self.reservations if r.month == month]

        return {
            "amount": sum(r.gross_earnings for r in reservations),
            "count": len(reservations),
            "reservations": [
                {
                    "guest": r.guest,
                    "confirmation": r.confirmation,
                    "end_date": r.end_date.isoformat(),
                    "amount": str(r.gross_earnings)
                }
                for r in reservations
            ]
        }

    def get_date_range_income(self, start_date: str, end_date: str) -> Dict:
        """
        Get total income for date range (inclusive)

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD

        Returns:
            {
                "amount": Decimal,
                "count": int,
                "months": Dict[str, Decimal]  # Monthly breakdown
            }
        """
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        reservations = [
            r for r in self.reservations
            if start <= r.end_date <= end
        ]

        # Monthly breakdown
        monthly = {}
        for r in reservations:
            month = r.month
            if month not in monthly:
                monthly[month] = Decimal("0.00")
            monthly[month] += r.gross_earnings

        return {
            "amount": sum(r.gross_earnings for r in reservations),
            "count": len(reservations),
            "months": {k: str(v) for k, v in sorted(monthly.items())}
        }

    def get_quarterly_income(self, quarter: str) -> Dict:
        """
        Get total income for a quarter (YYYY-Q#)

        Args:
            quarter: Quarter string like "2025-Q3"

        Returns:
            {
                "amount": Decimal,
                "count": int,
                "months": List[str]  # Months in quarter
            }
        """
        reservations = [r for r in self.reservations if r.quarter == quarter]

        # Get unique months in quarter
        months = sorted(set(r.month for r in reservations))

        return {
            "amount": sum(r.gross_earnings for r in reservations),
            "count": len(reservations),
            "months": months
        }

    def get_reservations_by_month(self, month: str) -> List[Dict]:
        """
        Get detailed reservation list for a month

        Args:
            month: Month string like "2025-10"

        Returns:
            List of reservation dicts with guest names, dates, amounts
        """
        reservations = [r for r in self.reservations if r.month == month]

        return [
            {
                "confirmation": r.confirmation,
                "guest": r.guest,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
                "nights": r.nights,
                "gross_earnings": str(r.gross_earnings)
            }
            for r in sorted(reservations, key=lambda x: x.end_date)
        ]

    def get_all_statistics(self) -> Dict:
        """Get comprehensive statistics for testing"""
        if not self.reservations:
            return {
                "total_reservations": 0,
                "total_revenue": "0.00",
                "date_range": {"min": None, "max": None},
                "monthly_breakdown": {}
            }

        return {
            "total_reservations": len(self.reservations),
            "total_revenue": str(sum(r.gross_earnings for r in self.reservations)),
            "date_range": {
                "min": min(r.end_date for r in self.reservations).isoformat(),
                "max": max(r.end_date for r in self.reservations).isoformat()
            },
            "monthly_breakdown": {
                month: str(self.get_monthly_income(month)["amount"])
                for month in sorted(set(r.month for r in self.reservations))
            }
        }

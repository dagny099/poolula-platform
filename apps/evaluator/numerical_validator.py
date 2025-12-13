"""
Numerical Accuracy Validator

Extracts and validates numerical values from chatbot responses.

Usage:
    from apps.evaluator.numerical_validator import NumericalValidator

    validator = NumericalValidator(tolerance_pct=1.0)
    match = validator.validate_amount(
        response="The total rental income was $3,920.45 in July.",
        expected_amount=Decimal("3920.00")
    )
    # Returns: {"matches": True, "extracted": Decimal("3920.45"), "diff_pct": 0.01}
"""

import re
from decimal import Decimal
from typing import Dict, Optional


class NumericalValidator:
    """
    Validate numerical accuracy in chatbot responses

    Handles:
    - Dollar amount extraction ($3,920.00 or $3920 or 3920.00)
    - Count extraction (5 reservations, five bookings)
    - Tolerance for rounding errors
    """

    def __init__(self, tolerance_pct: float = 1.0):
        """
        Args:
            tolerance_pct: Acceptable percentage difference (default 1%)
        """
        self.tolerance_pct = tolerance_pct

        # Regex patterns
        # Match dollar amounts with optional commas and decimals
        self.dollar_pattern = re.compile(r'\$\s*(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)')
        self.count_pattern = re.compile(r'(\d+)\s*(?:reservation|booking|stay|transaction)', re.IGNORECASE)

    def extract_dollar_amount(self, text: str) -> Optional[Decimal]:
        """
        Extract first dollar amount from text

        Handles formats:
        - $3,920.00
        - $3920
        - 3920.00
        - 3,920
        """
        if not text:
            return None

        match = self.dollar_pattern.search(text)
        if not match:
            return None

        # Remove commas and parse
        amount_str = match.group(1).replace(',', '')
        try:
            return Decimal(amount_str)
        except:
            return None

    def extract_count(self, text: str) -> Optional[int]:
        """
        Extract reservation count from text

        Handles formats:
        - "5 reservations"
        - "7 bookings"
        - "three stays"
        """
        if not text:
            return None

        match = self.count_pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except:
                pass

        # Try word-to-number conversion for small numbers
        word_map = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15
        }

        for word, num in word_map.items():
            if re.search(rf'\b{word}\s+(?:reservation|booking|stay|transaction)', text, re.IGNORECASE):
                return num

        return None

    def validate_amount(
        self,
        response: str,
        expected_amount: Decimal
    ) -> Dict:
        """
        Validate dollar amount in response

        Returns:
            {
                "matches": bool,
                "extracted": Optional[Decimal],
                "expected": Decimal,
                "diff_pct": Optional[float],
                "error": Optional[str]
            }
        """
        extracted = self.extract_dollar_amount(response)

        if extracted is None:
            return {
                "matches": False,
                "extracted": None,
                "expected": str(expected_amount),
                "diff_pct": None,
                "error": "No dollar amount found in response"
            }

        # Calculate percentage difference
        if expected_amount == Decimal("0.00"):
            diff_pct = 100.0 if extracted != Decimal("0.00") else 0.0
        else:
            diff = abs(extracted - expected_amount)
            diff_pct = float(diff / expected_amount * 100)

        matches = diff_pct <= self.tolerance_pct

        return {
            "matches": matches,
            "extracted": str(extracted),
            "expected": str(expected_amount),
            "diff_pct": round(diff_pct, 2),
            "error": None if matches else f"Difference {diff_pct:.2f}% exceeds tolerance {self.tolerance_pct}%"
        }

    def validate_count(
        self,
        response: str,
        expected_count: int
    ) -> Dict:
        """
        Validate reservation count in response

        Returns:
            {
                "matches": bool,
                "extracted": Optional[int],
                "expected": int,
                "error": Optional[str]
            }
        """
        extracted = self.extract_count(response)

        if extracted is None:
            return {
                "matches": False,
                "extracted": None,
                "expected": expected_count,
                "error": "No count found in response"
            }

        matches = extracted == expected_count

        return {
            "matches": matches,
            "extracted": extracted,
            "expected": expected_count,
            "error": None if matches else f"Count mismatch: got {extracted}, expected {expected_count}"
        }

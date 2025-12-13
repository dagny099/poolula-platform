#!/usr/bin/env python3
"""
Verify Airbnb data import status

Checks if Airbnb transaction data has been imported to the database.
Shows transaction count, total revenue, and date range.

Usage:
    uv run python scripts/verify_airbnb_import.py
"""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, func
from core.database.connection import get_engine
from core.database.models import Transaction
from core.database.enums import TransactionCategory, TransactionType
from core.logging_config import get_logger

logger = get_logger(__name__)


def verify_airbnb_import() -> bool:
    """
    Check if Airbnb data has been imported

    Returns:
        bool: True if data is imported, False otherwise
    """
    engine = get_engine()

    with Session(engine) as session:
        # Count RENTAL_INCOME REVENUE transactions
        revenue_query = (
            select(func.count(Transaction.id))
            .where(Transaction.category == TransactionCategory.RENTAL_INCOME)
            .where(Transaction.transaction_type == TransactionType.REVENUE)
        )
        revenue_count = session.exec(revenue_query).one()

        # Count PROPERTY_MANAGEMENT EXPENSE transactions (service fees)
        expense_query = (
            select(func.count(Transaction.id))
            .where(Transaction.category == TransactionCategory.PROPERTY_MANAGEMENT)
            .where(Transaction.transaction_type == TransactionType.EXPENSE)
            .where(Transaction.source_account == "Airbnb")
        )
        expense_count = session.exec(expense_query).one()

        # Get date range if data exists
        if revenue_count > 0:
            date_query = select(
                func.min(Transaction.transaction_date),
                func.max(Transaction.transaction_date)
            ).where(
                Transaction.category == TransactionCategory.RENTAL_INCOME
            ).where(
                Transaction.transaction_type == TransactionType.REVENUE
            )
            min_date, max_date = session.exec(date_query).one()
        else:
            min_date, max_date = None, None

        # Get total revenue
        if revenue_count > 0:
            total_query = select(func.sum(Transaction.amount)).where(
                Transaction.category == TransactionCategory.RENTAL_INCOME
            ).where(
                Transaction.transaction_type == TransactionType.REVENUE
            )
            total_revenue = session.exec(total_query).one() or Decimal("0.00")
        else:
            total_revenue = Decimal("0.00")

    # Print results
    print("\n" + "="*60)
    print("Airbnb Import Verification")
    print("="*60)
    print(f"RENTAL_INCOME REVENUE transactions: {revenue_count}")
    print(f"Service fee EXPENSE transactions: {expense_count}")

    if revenue_count > 0:
        print(f"\nDate range: {min_date} to {max_date}")
        print(f"Total revenue: ${total_revenue:,.2f}")
        print(f"\n✅ Data is imported - ready for evaluation")
        print(f"\nTo re-import fresh data, run:")
        print(f"  uv run python scripts/import_airbnb_transactions.py \\")
        print(f"    documents/airbnb_12_2024-11_2025.csv --auto-property")
        return True
    else:
        print(f"\n❌ NO DATA IMPORTED")
        print(f"\nTo import data, run:")
        print(f"  uv run python scripts/import_airbnb_transactions.py \\")
        print(f"    documents/airbnb_12_2024-11_2025.csv --auto-property")
        print(f"\nThis will import:")
        print(f"  - 31 Airbnb reservations (May-Oct 2025)")
        print(f"  - 62 total transactions (31 revenue + 31 expense)")
        print(f"  - $16,079.00 total revenue")
        return False


if __name__ == "__main__":
    imported = verify_airbnb_import()
    sys.exit(0 if imported else 1)

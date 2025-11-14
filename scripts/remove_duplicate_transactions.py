#!/usr/bin/env python3
"""
Remove Duplicate Transactions

Identifies and removes duplicate transactions based on:
- Same transaction_date
- Same description
- Same amount
- Same category

Keeps the oldest transaction (earliest created_at timestamp) and removes duplicates.

Usage:
    # Preview duplicates (dry run)
    python scripts/remove_duplicate_transactions.py --dry-run

    # Remove duplicates
    python scripts/remove_duplicate_transactions.py

Author: Poolula Platform
Date: 2025-11-14
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, func
from core.database.connection import get_engine, check_connection
from core.database.models import Transaction
from core.logging_config import get_logger

logger = get_logger(__name__)


def find_duplicate_groups(session: Session) -> List[Dict[str, Any]]:
    """
    Find groups of duplicate transactions

    Returns list of dicts with duplicate group info
    """
    # Query to find duplicates based on key fields
    duplicate_query = (
        select(
            Transaction.transaction_date,
            Transaction.description,
            Transaction.amount,
            Transaction.category,
            func.count(Transaction.id).label('count')
        )
        .group_by(
            Transaction.transaction_date,
            Transaction.description,
            Transaction.amount,
            Transaction.category
        )
        .having(func.count(Transaction.id) > 1)
    )

    duplicate_groups = session.exec(duplicate_query).all()

    result = []
    for group in duplicate_groups:
        result.append({
            'transaction_date': group[0],
            'description': group[1],
            'amount': group[2],
            'category': group[3],
            'count': group[4]
        })

    return result


def get_duplicate_transactions(session: Session, group: Dict[str, Any]) -> List[Transaction]:
    """
    Get all transactions in a duplicate group, ordered by created_at
    """
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.transaction_date == group['transaction_date'])
        .where(Transaction.description == group['description'])
        .where(Transaction.amount == group['amount'])
        .where(Transaction.category == group['category'])
        .order_by(Transaction.created_at)  # Oldest first
    ).all()

    return transactions


def remove_duplicates(dry_run: bool = False) -> Dict[str, Any]:
    """
    Remove duplicate transactions, keeping the oldest one

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Summary dict with stats
    """
    engine = get_engine()

    with Session(engine) as session:
        # Find duplicate groups
        duplicate_groups = find_duplicate_groups(session)

        if not duplicate_groups:
            logger.info("✅ No duplicate transactions found")
            return {
                'duplicate_groups': 0,
                'transactions_kept': 0,
                'transactions_removed': 0
            }

        logger.info(f"Found {len(duplicate_groups)} duplicate transaction groups")

        total_kept = 0
        total_removed = 0

        for i, group in enumerate(duplicate_groups, 1):
            # Get all transactions in this group
            transactions = get_duplicate_transactions(session, group)

            if len(transactions) <= 1:
                continue  # Shouldn't happen, but skip if no duplicates

            # Keep the first (oldest), remove the rest
            keep_transaction = transactions[0]
            remove_transactions = transactions[1:]

            logger.info(f"\n=== Group {i}/{len(duplicate_groups)} ===")
            logger.info(f"  Date: {group['transaction_date']}")
            logger.info(f"  Description: {group['description'][:60]}...")
            logger.info(f"  Amount: ${group['amount']}")
            logger.info(f"  Count: {group['count']} duplicates")
            logger.info(f"  ✓ Keeping: {keep_transaction.id} (created {keep_transaction.created_at})")

            for dup in remove_transactions:
                logger.info(f"  ✗ Removing: {dup.id} (created {dup.created_at})")

                if not dry_run:
                    session.delete(dup)
                    total_removed += 1
                else:
                    total_removed += 1  # Count what would be removed

            total_kept += 1

        if not dry_run:
            session.commit()
            logger.info(f"\n✅ Removed {total_removed} duplicate transactions")
        else:
            logger.info(f"\n🔍 DRY RUN - Would remove {total_removed} duplicate transactions")

        return {
            'duplicate_groups': len(duplicate_groups),
            'transactions_kept': total_kept,
            'transactions_removed': total_removed
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove duplicate transactions from database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be deleted
    python scripts/remove_duplicate_transactions.py --dry-run

    # Actually remove duplicates
    python scripts/remove_duplicate_transactions.py

What Counts as a Duplicate:
    Transactions with identical:
    - Transaction date
    - Description
    - Amount
    - Category

    The oldest transaction (by created_at) is kept, duplicates are removed.
        """
    )

    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without making changes")

    args = parser.parse_args()

    # Check database connection
    if not check_connection():
        logger.error("❌ Database connection failed")
        sys.exit(1)

    try:
        # Run duplicate removal
        summary = remove_duplicates(dry_run=args.dry_run)

        # Print summary
        print("\n" + "=" * 60)
        print("Duplicate Removal Summary")
        print("=" * 60)
        print(f"Duplicate Groups Found: {summary['duplicate_groups']}")
        print(f"Transactions Kept: {summary['transactions_kept']}")
        print(f"Transactions Removed: {summary['transactions_removed']}")

        if args.dry_run:
            print("\n🔍 DRY RUN - No changes made to database")
            print("Run without --dry-run to actually remove duplicates")
        else:
            print("\n✅ Duplicates removed successfully")

        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ Failed to remove duplicates: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

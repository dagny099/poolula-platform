#!/usr/bin/env python3
"""
Import Airbnb transactions from CSV

Supports Airbnb transaction export format and converts to Poolula transaction records.

Usage:
    # Import from Airbnb CSV export
    python scripts/import_airbnb_transactions.py airbnb_transactions.csv --property-id <UUID>

    # Dry run (preview without saving)
    python scripts/import_airbnb_transactions.py airbnb_transactions.csv --property-id <UUID> --dry-run

    # Auto-detect property (if you only have one)
    python scripts/import_airbnb_transactions.py airbnb_transactions.csv --auto-property

CSV Format Expected:
    Date,Type,Confirmation Code,Amount,Paid Out,Currency
    2024-11-01,Reservation,HM123ABC,150.00,142.50,USD
    2024-11-15,Reservation,HM456DEF,200.00,190.00,USD

Author: Poolula Platform
Date: 2025-11-13
"""

import argparse
import csv
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.database.connection import get_engine, check_connection
from core.database.models import Property, Transaction, create_provenance
from core.database.enums import TransactionCategory, TransactionType, ProvenanceSourceType
from core.logging_config import get_logger

logger = get_logger(__name__)


def parse_airbnb_date(date_str: str) -> datetime.date:
    """Parse Airbnb date format (YYYY-MM-DD or MM/DD/YYYY)"""
    # Try common formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {date_str}")


def parse_airbnb_amount(amount_str: str) -> Decimal:
    """Parse Airbnb amount (removes $, commas)"""
    # Remove $, commas, spaces
    cleaned = amount_str.replace("$", "").replace(",", "").replace(" ", "").strip()
    return Decimal(cleaned)


def categorize_airbnb_transaction(transaction_type: str, description: str) -> tuple:
    """
    Categorize Airbnb transaction

    Returns:
        (TransactionCategory, TransactionType)
    """
    transaction_type_lower = transaction_type.lower()

    # Revenue transactions
    if "reservation" in transaction_type_lower or "payout" in transaction_type_lower:
        return TransactionCategory.RENTAL_INCOME, TransactionType.REVENUE

    # Airbnb fees (expenses)
    elif "service fee" in transaction_type_lower or "host fee" in transaction_type_lower:
        return TransactionCategory.FEES_PLATFORM, TransactionType.EXPENSE

    # Resolution center (could be refund or expense)
    elif "resolution" in transaction_type_lower or "adjustment" in transaction_type_lower:
        return TransactionCategory.OTHER_REVENUE, TransactionType.REVENUE

    # Default to rental income
    else:
        return TransactionCategory.RENTAL_INCOME, TransactionType.REVENUE


def import_airbnb_csv(
    csv_path: str,
    property_id: UUID,
    dry_run: bool = False
) -> List[Transaction]:
    """
    Import transactions from Airbnb CSV

    Args:
        csv_path: Path to Airbnb CSV export
        property_id: Property UUID to associate transactions with
        dry_run: If True, don't save to database

    Returns:
        List of Transaction objects created
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Reading Airbnb CSV: {csv_path}")

    transactions = []

    with open(csv_file, 'r') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter

        reader = csv.DictReader(f, delimiter=delimiter)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Extract fields (handle various CSV formats)
                date_str = row.get('Date') or row.get('date') or row.get('Transaction Date')
                type_str = row.get('Type') or row.get('type') or row.get('Transaction Type')
                confirmation = row.get('Confirmation Code') or row.get('Confirmation') or row.get('confirmation_code') or f"ROW_{row_num}"
                amount_str = row.get('Amount') or row.get('amount') or row.get('Total')

                # Skip if missing critical fields
                if not date_str or not amount_str:
                    logger.warning(f"Row {row_num}: Missing date or amount, skipping")
                    continue

                # Parse values
                transaction_date = parse_airbnb_date(date_str)
                amount = parse_airbnb_amount(amount_str)

                # Skip zero amounts
                if amount == Decimal("0.00"):
                    logger.warning(f"Row {row_num}: Zero amount, skipping")
                    continue

                # Categorize
                category, trans_type = categorize_airbnb_transaction(
                    type_str or "Reservation",
                    confirmation
                )

                # Build description
                description = f"Airbnb {type_str or 'Reservation'}"
                if confirmation:
                    description += f" - {confirmation}"

                # Create provenance
                provenance = create_provenance(
                    source_type=ProvenanceSourceType.CSV_IMPORT,
                    source_id=csv_file.name,
                    source_field=f"row_{row_num}",
                    created_by="user:csv_import",
                    confidence=0.9,
                    notes=f"Imported from Airbnb CSV export"
                )

                # Create transaction
                transaction = Transaction(
                    property_id=property_id,
                    transaction_date=transaction_date,
                    amount=amount,
                    category=category,
                    transaction_type=trans_type,
                    description=description,
                    source_account="Airbnb",
                    provenance=provenance,
                    extra_metadata={
                        "airbnb_confirmation": confirmation,
                        "airbnb_type": type_str,
                        "csv_file": csv_file.name,
                        "csv_row": row_num,
                        "imported_at": datetime.utcnow().isoformat()
                    }
                )

                transactions.append(transaction)

                logger.info(f"  ✓ Row {row_num}: {transaction_date} - ${amount} - {description}")

            except Exception as e:
                logger.error(f"  ✗ Row {row_num}: Error - {e}")
                continue

    logger.info(f"\nParsed {len(transactions)} transactions from CSV")

    # Save to database if not dry run
    if not dry_run:
        engine = get_engine()
        with Session(engine) as session:
            for transaction in transactions:
                session.add(transaction)

            session.commit()
            logger.info(f"✅ Saved {len(transactions)} transactions to database")
    else:
        logger.info("🔍 DRY RUN - No changes saved to database")

    return transactions


def get_property_by_address(address_fragment: str) -> Property:
    """Find property by partial address match"""
    engine = get_engine()
    with Session(engine) as session:
        properties = session.exec(select(Property)).all()

        for prop in properties:
            if address_fragment.lower() in prop.address.lower():
                return prop

        raise ValueError(f"No property found matching: {address_fragment}")


def get_first_property() -> Property:
    """Get first (and possibly only) property"""
    engine = get_engine()
    with Session(engine) as session:
        property_obj = session.exec(select(Property)).first()

        if not property_obj:
            raise ValueError("No properties found in database. Add a property first.")

        return property_obj


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Import Airbnb transactions from CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Import with specific property ID
    python scripts/import_airbnb_transactions.py airbnb_nov_2024.csv \\
        --property-id 12345678-1234-1234-1234-123456789012

    # Auto-detect property (if you only have one)
    python scripts/import_airbnb_transactions.py airbnb_nov_2024.csv --auto-property

    # Dry run (preview without saving)
    python scripts/import_airbnb_transactions.py airbnb_nov_2024.csv \\
        --auto-property --dry-run

CSV Format:
    Date,Type,Confirmation Code,Amount
    2024-11-01,Reservation,HM123ABC,150.00
    2024-11-15,Reservation,HM456DEF,200.00
        """
    )

    parser.add_argument("csv_file", help="Path to Airbnb CSV export")
    parser.add_argument("--property-id", help="Property UUID to associate transactions with")
    parser.add_argument("--auto-property", action="store_true", help="Auto-detect property (if only one exists)")
    parser.add_argument("--dry-run", action="store_true", help="Preview import without saving to database")

    args = parser.parse_args()

    # Check database connection
    if not check_connection():
        logger.error("❌ Database connection failed")
        sys.exit(1)

    # Determine property ID
    try:
        if args.property_id:
            property_id = UUID(args.property_id)
            logger.info(f"Using property ID: {property_id}")
        elif args.auto_property:
            property_obj = get_first_property()
            property_id = property_obj.id
            logger.info(f"Auto-detected property: {property_obj.address}")
            logger.info(f"  Property ID: {property_id}")
        else:
            logger.error("❌ Must specify --property-id or --auto-property")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Property error: {e}")
        sys.exit(1)

    # Import transactions
    try:
        transactions = import_airbnb_csv(
            csv_path=args.csv_file,
            property_id=property_id,
            dry_run=args.dry_run
        )

        # Print summary
        print("\n" + "=" * 60)
        print("Import Summary")
        print("=" * 60)
        print(f"CSV File: {args.csv_file}")
        print(f"Transactions: {len(transactions)}")

        if transactions:
            total_amount = sum(t.amount for t in transactions)
            print(f"Total Amount: ${total_amount:,.2f}")
            print(f"Date Range: {min(t.transaction_date for t in transactions)} to {max(t.transaction_date for t in transactions)}")

        if args.dry_run:
            print("\n🔍 DRY RUN - No changes saved")
            print("Remove --dry-run to save to database")
        else:
            print("\n✅ Import completed successfully")

        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

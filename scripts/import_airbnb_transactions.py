#!/usr/bin/env python3
"""
Import Airbnb transactions from CSV

Supports real Airbnb transaction export format with all fields.

Usage:
    # Import from Airbnb CSV export
    python scripts/import_airbnb_transactions.py airbnb_12_2024-11_2025.csv --auto-property

    # Dry run (preview without saving)
    python scripts/import_airbnb_transactions.py airbnb_12_2024-11_2025.csv --auto-property --dry-run

Real Airbnb CSV Format:
    Date,Arriving by date,Type,Confirmation code,Booking date,Start date,End date,
    Nights,Guest,Listing,Details,Reference code,Currency,Amount,Paid out,
    Service fee,Fast pay fee,Cleaning fee,Pet fee,Gross earnings,Occupancy taxes,Earnings year

Import Strategy (Accrual Accounting):
    - SKIP "Payout" rows (just bank transfers, not revenue)
    - IMPORT "Reservation" rows as TWO transactions:
        * RENTAL_INCOME on check-out date (End date) - when service provided
        * PROPERTY_MANAGEMENT expense on payout date (Date) - when fee charged
    - IMPORT "Resolution Payout" rows as RENTAL_INCOME (damage reimbursements)
    - TRACK cleaning fees, pet fees, and taxes in metadata for analysis

Author: Poolula Platform
Date: 2025-11-13
"""

import argparse
import csv
import sys
from datetime import datetime, UTC
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
    """Parse Airbnb date format (MM/DD/YYYY)"""
    if not date_str or date_str.strip() == "":
        return None

    # Try common formats
    for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {date_str}")


def parse_airbnb_amount(amount_str: str) -> Decimal:
    """Parse Airbnb amount (handles empty, $, commas)"""
    if not amount_str or amount_str.strip() == "":
        return Decimal("0.00")

    # Remove $, commas, spaces
    cleaned = amount_str.replace("$", "").replace(",", "").replace(" ", "").strip()

    if cleaned == "":
        return Decimal("0.00")

    return Decimal(cleaned)


def import_airbnb_csv(
    csv_path: str,
    property_id: UUID,
    dry_run: bool = False
) -> tuple[List[Transaction], Dict[str, Any]]:
    """
    Import transactions from real Airbnb CSV export

    Handles the full Airbnb format with all fields including:
    - Reservations (convert to revenue + service fee expense)
    - Resolution Payouts (damage reimbursements)
    - Skips "Payout" rows (just bank transfers)

    Args:
        csv_path: Path to Airbnb CSV export
        property_id: Property UUID to associate transactions with
        dry_run: If True, don't save to database

    Returns:
        Tuple of (transactions list, summary dict)
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Reading Airbnb CSV: {csv_path}")

    transactions = []

    # Read CSV with UTF-8 BOM handling
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Extract key fields
                date_str = row.get('Date', '')
                trans_type = row.get('Type', '').strip()
                confirmation = row.get('Confirmation code', '').strip()

                # Skip empty rows
                if not date_str or not trans_type:
                    continue

                # Parse date
                transaction_date = parse_airbnb_date(date_str)
                if not transaction_date:
                    logger.warning(f"Row {row_num}: No date, skipping")
                    continue

                # Handle different transaction types
                if trans_type == "Payout":
                    # SKIP payouts - they're just bank transfers, not revenue
                    logger.debug(f"Row {row_num}: Skipping Payout (bank transfer)")
                    continue

                elif trans_type == "Reservation":
                    # Import reservation as revenue (using accrual dates)
                    transactions.extend(
                        process_reservation(row, row_num, transaction_date, property_id, csv_file.name)
                    )

                elif trans_type == "Resolution Payout":
                    # Import damage reimbursements
                    transaction = process_resolution_payout(row, row_num, transaction_date, property_id, csv_file.name)
                    if transaction:
                        transactions.append(transaction)

                else:
                    logger.warning(f"Row {row_num}: Unknown type '{trans_type}', skipping")
                    continue

            except Exception as e:
                logger.error(f"  ✗ Row {row_num}: Error - {e}")
                continue

    logger.info(f"\nParsed {len(transactions)} transactions from CSV")

    # Calculate summary statistics BEFORE session operations (to avoid detached instance errors)
    summary = {}
    if transactions:
        revenue_transactions = [t for t in transactions if t.transaction_type == TransactionType.REVENUE]
        expense_transactions = [t for t in transactions if t.transaction_type == TransactionType.EXPENSE]

        summary = {
            "total_count": len(transactions),
            "revenue_count": len(revenue_transactions),
            "expense_count": len(expense_transactions),
            "revenue_total": sum(t.amount for t in revenue_transactions),
            "expense_total": sum(t.amount for t in expense_transactions),
            "date_min": min(t.transaction_date for t in transactions),
            "date_max": max(t.transaction_date for t in transactions)
        }

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

    return transactions, summary


def process_reservation(row: dict, row_num: int, payout_date, property_id: UUID, csv_file: str) -> List[Transaction]:
    """
    Process a Reservation row into transactions using accrual accounting

    Creates:
    1. RENTAL_INCOME transaction for gross earnings on END DATE (when service provided)
    2. PROPERTY_MANAGEMENT expense for service fee on PAYOUT DATE (when fee charged)

    Args:
        payout_date: Date from "Date" column (when Airbnb paid out)

    Returns list of 1-2 transactions
    """
    transactions = []

    # Extract fields
    confirmation = row.get('Confirmation code', '').strip()
    guest = row.get('Guest', '').strip()
    nights = row.get('Nights', '')
    start_date_str = row.get('Start date', '')
    end_date_str = row.get('End date', '')

    # Parse check-out date for revenue recognition
    checkout_date = parse_airbnb_date(end_date_str)
    if not checkout_date:
        logger.warning(f"Row {row_num}: No end date for revenue recognition, using payout date")
        checkout_date = payout_date

    # Financial fields
    gross_earnings_str = row.get('Gross earnings', '0')
    service_fee_str = row.get('Service fee', '0')
    cleaning_fee_str = row.get('Cleaning fee', '0')
    pet_fee_str = row.get('Pet fee', '0')
    occupancy_taxes_str = row.get('Occupancy taxes', '0')

    # Parse amounts
    gross_earnings = parse_airbnb_amount(gross_earnings_str)
    service_fee = parse_airbnb_amount(service_fee_str)
    cleaning_fee = parse_airbnb_amount(cleaning_fee_str)
    pet_fee = parse_airbnb_amount(pet_fee_str)
    occupancy_taxes = parse_airbnb_amount(occupancy_taxes_str)

    # Skip if no gross earnings
    if gross_earnings == Decimal("0.00"):
        logger.warning(f"Row {row_num}: Zero gross earnings, skipping")
        return []

    # Build description
    description = f"Airbnb Reservation - {confirmation}"
    if guest:
        description += f" - {guest}"
    if nights:
        description += f" ({nights} nights)"

    # Create provenance
    provenance = create_provenance(
        source_type=ProvenanceSourceType.CSV_IMPORT,
        source_id=csv_file,
        source_field=f"row_{row_num}",
        created_by="user:csv_import",
        confidence=1.0,
        notes=f"Imported from Airbnb CSV export (Reservation)"
    )

    # Transaction 1: Gross earnings as RENTAL_INCOME on check-out date (accrual)
    revenue_transaction = Transaction(
        property_id=property_id,
        transaction_date=checkout_date,  # Revenue recognized when earned (check-out)
        amount=gross_earnings,
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description=description,
        source_account="Airbnb",
        provenance=provenance,
        extra_metadata={
            "airbnb_confirmation": confirmation,
            "airbnb_type": "Reservation",
            "guest": guest,
            "nights": nights,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "payout_date": str(payout_date),
            "gross_earnings": str(gross_earnings),
            "service_fee": str(service_fee),
            "cleaning_fee": str(cleaning_fee),
            "pet_fee": str(pet_fee),
            "occupancy_taxes": str(occupancy_taxes),
            "csv_file": csv_file,
            "csv_row": row_num,
            "imported_at": datetime.now(UTC).isoformat()
        }
    )

    transactions.append(revenue_transaction)
    logger.info(f"  ✓ Row {row_num}: {checkout_date} - REVENUE ${gross_earnings} - {confirmation} ({guest})")

    # Transaction 2: Service fee as EXPENSE on payout date (when charged)
    if service_fee > Decimal("0.00"):
        fee_description = f"Airbnb Service Fee - {confirmation}"
        if guest:
            fee_description += f" ({guest})"

        fee_transaction = Transaction(
            property_id=property_id,
            transaction_date=payout_date,  # Expense when actually charged by Airbnb
            amount=service_fee,
            category=TransactionCategory.PROPERTY_MANAGEMENT,
            transaction_type=TransactionType.EXPENSE,
            description=fee_description,
            source_account="Airbnb",
            provenance=provenance,
            extra_metadata={
                "airbnb_confirmation": confirmation,
                "airbnb_type": "Service Fee",
                "related_reservation": confirmation,
                "related_checkout_date": str(checkout_date),
                "guest": guest,
                "csv_file": csv_file,
                "csv_row": row_num,
                "imported_at": datetime.now(UTC).isoformat()
            }
        )

        transactions.append(fee_transaction)
        logger.info(f"  ✓ Row {row_num}: {payout_date} - EXPENSE ${service_fee} - Service Fee")

    return transactions


def process_resolution_payout(row: dict, row_num: int, transaction_date, property_id: UUID, csv_file: str):
    """
    Process a Resolution Payout row (damage reimbursements)

    Returns single OTHER_REVENUE transaction
    """
    # Extract fields
    confirmation = row.get('Confirmation code', '').strip()
    details = row.get('Details', '').strip()
    amount_str = row.get('Gross earnings', '0')  # Resolution payouts use gross earnings field

    # Parse amount
    amount = parse_airbnb_amount(amount_str)

    if amount == Decimal("0.00"):
        logger.warning(f"Row {row_num}: Zero resolution payout, skipping")
        return None

    # Build description
    description = f"Airbnb Resolution Payout - {confirmation}"
    if details:
        description += f" - {details}"

    # Create provenance
    provenance = create_provenance(
        source_type=ProvenanceSourceType.CSV_IMPORT,
        source_id=csv_file,
        source_field=f"row_{row_num}",
        created_by="user:csv_import",
        confidence=1.0,
        notes=f"Imported from Airbnb CSV export (Resolution Payout)"
    )

    transaction = Transaction(
        property_id=property_id,
        transaction_date=transaction_date,
        amount=amount,
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description=description,
        source_account="Airbnb",
        provenance=provenance,
        extra_metadata={
            "airbnb_confirmation": confirmation,
            "airbnb_type": "Resolution Payout",
            "details": details,
            "csv_file": csv_file,
            "csv_row": row_num,
            "imported_at": datetime.now(UTC).isoformat()
        }
    )

    logger.info(f"  ✓ Row {row_num}: {transaction_date} - RESOLUTION ${amount} - {confirmation}")

    return transaction


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
    # Import with auto-detect property
    python scripts/import_airbnb_transactions.py airbnb_12_2024-11_2025.csv --auto-property

    # Dry run (preview without saving)
    python scripts/import_airbnb_transactions.py airbnb_12_2024-11_2025.csv --auto-property --dry-run

    # Import with specific property ID
    python scripts/import_airbnb_transactions.py airbnb_12_2024-11_2025.csv \\
        --property-id 12345678-1234-1234-1234-123456789012

What Gets Imported (Accrual Accounting):
    - Reservations → TWO transactions:
        * Revenue on CHECK-OUT date (End date field)
        * Expense on PAYOUT date (Date field)
    - Resolution Payouts → RENTAL_INCOME on payout date
    - Payouts → SKIPPED (just bank transfers)

Why Accrual Dates:
    - Revenue: Recognized when EARNED (guest checks out)
    - Expense: Recognized when CHARGED (Airbnb processes fee)
    - Better for: "How much did I earn in October?" vs "When did money hit my bank?"
    - IRS Schedule E compatible (gross revenue + itemized expenses)

Metadata Tracked:
    - Guest names, nights, stay dates, payout dates
    - Confirmation codes
    - Gross earnings, service fees, cleaning fees, pet fees, taxes
    - CSV file and row number for audit trail
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
        transactions, summary = import_airbnb_csv(
            csv_path=args.csv_file,
            property_id=property_id,
            dry_run=args.dry_run
        )

        # Print summary
        print("\n" + "=" * 60)
        print("Import Summary")
        print("=" * 60)
        print(f"CSV File: {args.csv_file}")
        print(f"Transactions: {summary.get('total_count', 0)}")

        if summary:
            print(f"\nRevenue Transactions: {summary['revenue_count']}")
            print(f"  Total Revenue: ${summary['revenue_total']:,.2f}")
            print(f"\nExpense Transactions: {summary['expense_count']}")
            print(f"  Total Expenses: ${summary['expense_total']:,.2f}")
            print(f"\nNet: ${summary['revenue_total'] - summary['expense_total']:,.2f}")

            print(f"\nDate Range: {summary['date_min']} to {summary['date_max']}")

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

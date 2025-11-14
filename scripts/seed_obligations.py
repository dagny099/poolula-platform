#!/usr/bin/env python3
"""
Seed Obligations Script for Poolula Platform

Seeds common recurring obligations for LLC compliance and property management.

Usage:
    # Seed all common obligations
    uv run python scripts/seed_obligations.py

    # Seed with specific year
    uv run python scripts/seed_obligations.py --year 2025

    # Clear all obligations and reseed
    uv run python scripts/seed_obligations.py --clear

Author: Poolula Platform
Date: 2024-11-14
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.database.connection import get_engine, check_connection
from core.database.models import Obligation, Property
from core.database.enums import ObligationStatus, ObligationType, RecurrencePattern
from core.logging_config import get_logger

logger = get_logger(__name__)


class ObligationSeeder:
    """
    Seeds common recurring obligations for LLC and property management

    Creates obligations for:
    - Colorado periodic report (annual)
    - Federal tax deadlines (quarterly estimates, annual return)
    - Property tax deadlines
    - Insurance renewal
    - Lease reviews
    """

    def __init__(self, year: int = 2025):
        """
        Initialize obligation seeder

        Args:
            year: Year to seed obligations for (default: 2025)
        """
        self.year = year
        self.engine = get_engine()

    def get_property_id(self) -> Optional[UUID]:
        """
        Get first active property ID from database

        Returns:
            Property UUID or None if no properties exist
        """
        with Session(self.engine) as session:
            statement = select(Property).where(Property.status == "ACTIVE").limit(1)
            property = session.exec(statement).first()

            if property:
                logger.info(f"Using property: {property.address} ({property.id})")
                return property.id
            else:
                logger.warning("No active properties found - creating property-level obligations")
                return None

    def clear_all_obligations(self) -> int:
        """
        Clear all existing obligations

        Returns:
            Number of obligations deleted
        """
        with Session(self.engine) as session:
            statement = select(Obligation)
            obligations = session.exec(statement).all()
            count = len(obligations)

            for obligation in obligations:
                session.delete(obligation)

            session.commit()
            logger.info(f"Cleared {count} existing obligations")
            return count

    def seed_llc_compliance_obligations(self) -> List[Obligation]:
        """
        Seed LLC compliance obligations

        Returns:
            List of created obligations
        """
        obligations = []

        # Colorado Periodic Report (due annually by anniversary of formation)
        # Assuming May 15 formation date (adjust as needed)
        obligations.append(Obligation(
            property_id=None,  # LLC-level, not property-specific
            obligation_type=ObligationType.STATE_FILING,
            due_date=date(self.year, 5, 15),
            status=ObligationStatus.PENDING,
            description="Colorado Periodic Report - Annual LLC filing with Colorado Secretary of State. $10 filing fee. Must be completed to maintain good standing.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=30
        ))

        logger.info("Created LLC compliance obligations")
        return obligations

    def seed_tax_obligations(self, property_id: Optional[UUID]) -> List[Obligation]:
        """
        Seed tax-related obligations

        Args:
            property_id: Property UUID or None for LLC-level

        Returns:
            List of created obligations
        """
        obligations = []

        # Quarterly estimated tax payments (if required)
        # Q1: April 15, Q2: June 15, Q3: September 15, Q4: January 15 of following year
        quarters = [
            (date(self.year, 4, 15), "Q1"),
            (date(self.year, 6, 15), "Q2"),
            (date(self.year, 9, 15), "Q3"),
            (date(self.year + 1, 1, 15), "Q4")
        ]

        for due_date, quarter in quarters:
            obligations.append(Obligation(
                property_id=property_id,
                obligation_type=ObligationType.TAX_FILING,
                due_date=due_date,
                status=ObligationStatus.PENDING,
                description=f"Quarterly Estimated Tax Payment - {quarter} {self.year}. If annual tax liability exceeds $1,000, quarterly payments required to avoid penalties.",
                recurrence=RecurrencePattern.QUARTERLY,
                reminder_days_before=14
            ))

        # Annual tax return (Form 1065 for partnership)
        # Due March 15 (or April 15 with extension)
        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.TAX_FILING,
            due_date=date(self.year + 1, 3, 15),
            status=ObligationStatus.PENDING,
            description=f"Form 1065 Partnership Return - Annual federal tax return due March 15, {self.year + 1}. Can extend to September 15 with Form 7004.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=60
        ))

        # Schedule E for individual members
        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.TAX_FILING,
            due_date=date(self.year + 1, 4, 15),
            status=ObligationStatus.PENDING,
            description=f"Schedule E (Form 1040) - Individual tax return reporting rental income. Due April 15, {self.year + 1}. Can extend to October 15 with Form 4868.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=60
        ))

        logger.info(f"Created {len(obligations)} tax obligations")
        return obligations

    def seed_property_tax_obligations(self, property_id: Optional[UUID]) -> List[Obligation]:
        """
        Seed property tax obligations

        Args:
            property_id: Property UUID

        Returns:
            List of created obligations
        """
        if not property_id:
            logger.warning("Skipping property tax obligations - no property ID provided")
            return []

        obligations = []

        # Property tax payments (Colorado - typically due in installments)
        # First half: February 28, Second half: June 15
        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.PROPERTY_TAX,
            due_date=date(self.year, 2, 28),
            status=ObligationStatus.PENDING,
            description=f"Property Tax - First Half {self.year}. Payment to Montrose County Treasurer. Check county website for exact amount.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=30
        ))

        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.PROPERTY_TAX,
            due_date=date(self.year, 6, 15),
            status=ObligationStatus.PENDING,
            description=f"Property Tax - Second Half {self.year}. Payment to Montrose County Treasurer. Check county website for exact amount.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=30
        ))

        logger.info(f"Created {len(obligations)} property tax obligations")
        return obligations

    def seed_insurance_obligations(self, property_id: Optional[UUID]) -> List[Obligation]:
        """
        Seed insurance review and renewal obligations

        Args:
            property_id: Property UUID

        Returns:
            List of created obligations
        """
        if not property_id:
            logger.warning("Skipping insurance obligations - no property ID provided")
            return []

        obligations = []

        # Insurance policy review (assuming May 1 renewal - adjust as needed)
        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.INSURANCE_RENEWAL,
            due_date=date(self.year, 5, 1),
            status=ObligationStatus.PENDING,
            description=f"Property Insurance Renewal - {self.year}. Review coverage with Travelers Insurance. Ensure adequate liability and property coverage.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=60
        ))

        logger.info(f"Created {len(obligations)} insurance obligations")
        return obligations

    def seed_operational_obligations(self, property_id: Optional[UUID]) -> List[Obligation]:
        """
        Seed operational obligations (inspections, reviews, etc.)

        Args:
            property_id: Property UUID

        Returns:
            List of created obligations
        """
        if not property_id:
            logger.warning("Skipping operational obligations - no property ID provided")
            return []

        obligations = []

        # Annual LLC meeting
        obligations.append(Obligation(
            property_id=None,  # LLC-level
            obligation_type=ObligationType.COMPLIANCE_CHECK,
            due_date=date(self.year, 12, 31),
            status=ObligationStatus.PENDING,
            description=f"Annual LLC Meeting - Hold annual member meeting and document meeting minutes. Review financial performance, approve budgets, and document key decisions.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=30
        ))

        # Property inspection / maintenance review
        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.INSPECTION,
            due_date=date(self.year, 6, 30),
            status=ObligationStatus.PENDING,
            description=f"Semi-Annual Property Inspection - Inspect property condition, HVAC systems, plumbing, electrical. Document repairs needed. Schedule before peak season.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=14
        ))

        obligations.append(Obligation(
            property_id=property_id,
            obligation_type=ObligationType.INSPECTION,
            due_date=date(self.year, 12, 31),
            status=ObligationStatus.PENDING,
            description=f"Semi-Annual Property Inspection - Year-end property condition review. Check weatherization, heating systems. Document maintenance for tax purposes.",
            recurrence=RecurrencePattern.YEARLY,
            reminder_days_before=14
        ))

        logger.info(f"Created {len(obligations)} operational obligations")
        return obligations

    def seed_all_obligations(self) -> dict:
        """
        Seed all common obligations

        Returns:
            Summary dict with counts by category
        """
        logger.info(f"Seeding obligations for year: {self.year}")

        # Get property ID (if available)
        property_id = self.get_property_id()

        all_obligations = []

        # Seed each category
        all_obligations.extend(self.seed_llc_compliance_obligations())
        all_obligations.extend(self.seed_tax_obligations(property_id))
        all_obligations.extend(self.seed_property_tax_obligations(property_id))
        all_obligations.extend(self.seed_insurance_obligations(property_id))
        all_obligations.extend(self.seed_operational_obligations(property_id))

        # Save to database
        with Session(self.engine) as session:
            for obligation in all_obligations:
                session.add(obligation)
            session.commit()
            logger.info(f"✅ Saved {len(all_obligations)} obligations to database")

        # Calculate summary by type
        summary = {}
        for obligation in all_obligations:
            ob_type = obligation.obligation_type
            if ob_type not in summary:
                summary[ob_type] = 0
            summary[ob_type] += 1

        return summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Seed common obligations for Poolula LLC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Seed obligations for 2025
  uv run python scripts/seed_obligations.py

  # Seed for specific year
  uv run python scripts/seed_obligations.py --year 2026

  # Clear all and reseed
  uv run python scripts/seed_obligations.py --clear --year 2025

Obligation Categories:
  - LLC Compliance: Colorado periodic report
  - Tax Filings: Quarterly estimates, annual returns (1065, Schedule E)
  - Property Taxes: Semi-annual payments
  - Insurance: Annual renewal review
  - Operations: Annual meetings, property inspections
        """
    )

    parser.add_argument('--year', type=int, default=2025, help='Year to seed obligations for')
    parser.add_argument('--clear', action='store_true', help='Clear all existing obligations before seeding')

    args = parser.parse_args()

    # Check database connection
    if not check_connection():
        logger.error("❌ Database connection failed")
        sys.exit(1)

    try:
        seeder = ObligationSeeder(year=args.year)

        # Clear existing obligations if requested
        if args.clear:
            count = seeder.clear_all_obligations()
            logger.info(f"Cleared {count} existing obligations")

        # Seed obligations
        summary = seeder.seed_all_obligations()

        # Print summary
        print("\n" + "=" * 60)
        print(f"Obligations Seeded for {args.year}")
        print("=" * 60)

        total = 0
        for ob_type, count in sorted(summary.items()):
            print(f"{ob_type}: {count}")
            total += count

        print(f"\nTotal Obligations: {total}")
        print("=" * 60)

        logger.info("✅ Obligation seeding completed successfully")

    except Exception as e:
        logger.error(f"❌ Failed to seed obligations: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

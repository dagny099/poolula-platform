"""
Seed database from poolula_facts.yml

Imports property data from the YAML source of truth into the database.

Usage:
    # Initial seed (only if DB empty or property doesn't exist)
    python scripts/seed_database.py --initial

    # Update from YAML (safe, won't overwrite manual edits)
    python scripts/seed_database.py --update

UNKNOWN Handling:
    Values marked "UNKNOWN" in YAML are skipped (left as NULL in database).
    Update YAML with actual values and re-run with --update to fill them in.

See: docs/workflows/data-import.md for full workflow

Author: Poolula Platform
Date: 2025-11-13
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import yaml
from sqlmodel import Session, select

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.connection import get_engine, check_connection
from core.database.models import Property, create_provenance
from core.database.enums import PropertyStatus, ProvenanceSourceType
from core.logging_config import get_logger

logger = get_logger(__name__)

# Path to poolula_facts.yml
YAML_PATH = Path("poolula_facts.yml")


def load_yaml() -> dict:
    """
    Load poolula_facts.yml

    Returns:
        Dictionary with YAML contents

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if not YAML_PATH.exists():
        raise FileNotFoundError(f"poolula_facts.yml not found at: {YAML_PATH}")

    logger.info(f"Loading YAML from: {YAML_PATH}")

    with open(YAML_PATH, "r") as f:
        data = yaml.safe_load(f)

    logger.info("✅ YAML loaded successfully")
    return data


def parse_value(value, field_type):
    """
    Smart parser for YAML values with UNKNOWN handling

    Args:
        value: Raw value from YAML
        field_type: Expected Python type (date, Decimal, etc.)

    Returns:
        Parsed value or None if UNKNOWN

    Examples:
        >>> parse_value("UNKNOWN", date)
        None
        >>> parse_value("2024-04-15", date)
        date(2024, 4, 15)
    """
    # Handle UNKNOWN values -> return None
    if isinstance(value, str) and value.strip().upper() == "UNKNOWN":
        return None

    # Handle None/null
    if value is None:
        return None

    # Parse by type
    if field_type == date:
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        return value

    elif field_type == Decimal:
        return Decimal(str(value))

    else:
        return value


def create_property_from_yaml(yaml_data: dict) -> Property:
    """
    Create Property object from YAML data

    Args:
        yaml_data: Dictionary from poolula_facts.yml

    Returns:
        Property object ready to be added to database

    Note:
        UNKNOWN values in YAML become None in the Property object
    """
    assets = yaml_data.get("assets", {}).get("as_of_2024_12_31", {})
    real_property = assets.get("real_property", {})
    allocation = real_property.get("allocation", {})
    other_assets = assets.get("other_assets", {})

    # Extract FF&E value (may have annotation text)
    ffe_raw = other_assets.get("furniture_FF&E_usd", "0")
    if isinstance(ffe_raw, str):
        # Extract numeric part from strings like "10000.00 (CLOSE STATEMENT LINE; confirm final)"
        ffe_numeric = ffe_raw.split()[0] if ffe_raw else "0"
    else:
        ffe_numeric = str(ffe_raw)

    # Build full address with city/state
    address_street = real_property.get("address", "UNKNOWN")
    address_full = f"{address_street}, Montrose, CO 81401"

    # Parse placed_in_service (corrected date: 2025-02-01)
    placed_in_service_raw = assets.get("placed_in_service_date_for_depreciation", "UNKNOWN")

    # Override UNKNOWN with actual known date
    if placed_in_service_raw == "UNKNOWN":
        placed_in_service = date(2025, 2, 1)  # Actual date provided by user
    else:
        placed_in_service = parse_value(placed_in_service_raw, date)

    # Create provenance
    provenance = create_provenance(
        source_type=ProvenanceSourceType.MANUAL_ENTRY,
        source_id="poolula_facts.yml",
        created_by="system:seed_script",
        confidence=1.0,
        notes=f"Imported from source of truth YAML (last_updated: {yaml_data.get('meta', {}).get('last_updated', 'unknown')})",
    )

    # Create Property
    property_obj = Property(
        address=address_full,
        acquisition_date=parse_value(real_property.get("acquisition_date"), date),
        purchase_price_total=parse_value(real_property.get("purchase_price_total_usd"), Decimal),
        land_basis=parse_value(allocation.get("land_usd"), Decimal),
        building_basis=parse_value(allocation.get("building_and_improvements_usd"), Decimal),
        ffe_basis=parse_value(ffe_numeric, Decimal),
        placed_in_service=placed_in_service,
        status=PropertyStatus.ACTIVE,
        provenance=provenance,
        extra_metadata={
            "yaml_last_updated": yaml_data.get("meta", {}).get("last_updated"),
            "imported_at": datetime.utcnow().isoformat(),
        },
    )

    return property_obj


def seed_initial(session: Session, yaml_data: dict) -> bool:
    """
    Initial seed: Create property if it doesn't exist

    Args:
        session: Database session
        yaml_data: Dictionary from poolula_facts.yml

    Returns:
        True if property was created, False if already exists
    """
    logger.info("Running initial seed (--initial mode)")

    # Create property from YAML
    property_obj = create_property_from_yaml(yaml_data)

    # Check if property already exists by address
    existing = session.exec(
        select(Property).where(Property.address == property_obj.address)
    ).first()

    if existing:
        logger.info(f"Property already exists: {property_obj.address}")
        logger.info(f"  ID: {existing.id}")
        logger.info(f"  Status: {existing.status}")
        logger.info("Skipping creation (use --update to resync from YAML)")
        return False

    # Add property to database
    session.add(property_obj)
    session.commit()
    session.refresh(property_obj)

    logger.info(f"✅ Property created: {property_obj.address}")
    logger.info(f"  ID: {property_obj.id}")
    logger.info(f"  Purchase price: ${property_obj.purchase_price_total}")
    logger.info(f"  Acquisition date: {property_obj.acquisition_date}")
    logger.info(f"  Placed in service: {property_obj.placed_in_service}")

    return True


def seed_update(session: Session, yaml_data: dict) -> bool:
    """
    Update mode: Update existing property from YAML

    Only updates NULL fields (preserves manual edits)

    Args:
        session: Database session
        yaml_data: Dictionary from poolula_facts.yml

    Returns:
        True if property was updated, False if not found or no changes
    """
    logger.info("Running update seed (--update mode)")

    # Create property object from YAML (for comparison)
    yaml_property = create_property_from_yaml(yaml_data)

    # Find existing property by address
    existing = session.exec(
        select(Property).where(Property.address == yaml_property.address)
    ).first()

    if not existing:
        logger.warning(f"Property not found: {yaml_property.address}")
        logger.warning("Run with --initial to create it")
        return False

    logger.info(f"Found existing property: {existing.address}")
    logger.info(f"  ID: {existing.id}")

    # Update only NULL fields
    changes = []
    fields_to_check = [
        "placed_in_service",
        "land_basis",
        "building_basis",
        "ffe_basis",
    ]

    for field in fields_to_check:
        existing_value = getattr(existing, field)
        yaml_value = getattr(yaml_property, field)

        # Only update if existing is NULL and YAML has a value
        if existing_value is None and yaml_value is not None:
            setattr(existing, field, yaml_value)
            changes.append(f"{field}: None → {yaml_value}")
            logger.info(f"  Updating {field}: None → {yaml_value}")

    if not changes:
        logger.info("No changes needed (all fields already filled)")
        return False

    # Update metadata
    existing.extra_metadata["last_resynced"] = datetime.utcnow().isoformat()
    existing.updated_at = datetime.utcnow()

    # Commit changes
    session.add(existing)
    session.commit()

    logger.info(f"✅ Property updated with {len(changes)} changes")
    for change in changes:
        logger.info(f"    - {change}")

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Seed database from poolula_facts.yml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Initial seed (create property if doesn't exist)
    python scripts/seed_database.py --initial

    # Update from YAML (fill in NULL fields)
    python scripts/seed_database.py --update

See: docs/workflows/data-import.md for full workflow
        """,
    )

    parser.add_argument(
        "--initial",
        action="store_true",
        help="Initial seed mode (create property if doesn't exist)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update mode (update existing property from YAML, preserves manual edits)",
    )

    args = parser.parse_args()

    # Default to --initial if no mode specified
    if not args.initial and not args.update:
        args.initial = True

    # Check database connection
    logger.info("Checking database connection...")
    if not check_connection():
        logger.error("❌ Database connection failed")
        logger.error("Run 'alembic upgrade head' to create tables")
        sys.exit(1)

    # Load YAML
    try:
        yaml_data = load_yaml()
    except Exception as e:
        logger.error(f"❌ Failed to load YAML: {e}")
        sys.exit(1)

    # Get database session
    engine = get_engine()
    with Session(engine) as session:
        try:
            if args.initial:
                success = seed_initial(session, yaml_data)
            else:  # args.update
                success = seed_update(session, yaml_data)

            if success:
                logger.info("🎉 Seeding completed successfully")
            else:
                logger.info("Seeding completed (no changes made)")

        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()

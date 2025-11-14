"""
Property CRUD endpoints

Provides REST API for property management with direct SQLModel usage
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from core.database.connection import get_session
from core.database.models import Property
from core.database.enums import PropertyStatus
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/properties", response_model=List[Property])
def list_properties(
    status: Optional[PropertyStatus] = Query(None, description="Filter by property status"),
    session: Session = Depends(get_session),
) -> List[Property]:
    """
    List all properties

    Optionally filter by status (ACTIVE, UNDER_CONTRACT, SOLD, INACTIVE)

    Args:
        status: Optional status filter
        session: Database session (injected)

    Returns:
        List of properties matching the filter

    Example:
        >>> GET /api/v1/properties
        >>> GET /api/v1/properties?status=ACTIVE
    """
    logger.info(f"Listing properties with status filter: {status}")

    # Build query
    query = select(Property)
    if status:
        query = query.where(Property.status == status)

    # Execute query
    properties = session.exec(query).all()

    logger.info(f"Found {len(properties)} properties")
    return properties


@router.post("/properties", response_model=Property, status_code=201)
def create_property(
    property_data: Property,
    session: Session = Depends(get_session),
) -> Property:
    """
    Create a new property

    Automatically sets created_at and updated_at timestamps

    Args:
        property_data: Property data
        session: Database session (injected)

    Returns:
        Created property with generated ID

    Raises:
        HTTPException: If creation fails

    Example:
        >>> POST /api/v1/properties
        {
            "address": "900 S 9th St, Montrose, CO 81401",
            "acquisition_date": "2024-04-15",
            "purchase_price_total": "442300.00",
            "land_basis": "78200.00",
            "building_basis": "364100.00",
            "ffe_basis": "10000.00",
            "placed_in_service": "2025-02-01",
            "status": "ACTIVE"
        }
    """
    logger.info(f"Creating property: {property_data.address}")

    try:
        # Add to session and commit
        session.add(property_data)
        session.commit()
        session.refresh(property_data)

        logger.info(f"✅ Property created: {property_data.id}")
        return property_data

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to create property: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create property: {str(e)}")


@router.get("/properties/{property_id}", response_model=Property)
def get_property(
    property_id: UUID,
    session: Session = Depends(get_session),
) -> Property:
    """
    Get a single property by ID

    Args:
        property_id: Property UUID
        session: Database session (injected)

    Returns:
        Property with the given ID

    Raises:
        HTTPException: 404 if property not found

    Example:
        >>> GET /api/v1/properties/{uuid}
    """
    logger.info(f"Fetching property: {property_id}")

    property_obj = session.get(Property, property_id)

    if not property_obj:
        logger.warning(f"Property not found: {property_id}")
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")

    logger.info(f"✅ Property found: {property_obj.address}")
    return property_obj


@router.patch("/properties/{property_id}", response_model=Property)
def update_property(
    property_id: UUID,
    property_update: dict,
    session: Session = Depends(get_session),
) -> Property:
    """
    Update a property

    Allows updating any field. Updates the updated_at timestamp automatically.

    Note: Currently allows updating all fields including acquisition_date and basis.
    Phase 5: Consider protecting immutable fields for accounting integrity.

    Args:
        property_id: Property UUID
        property_update: Dictionary of fields to update
        session: Database session (injected)

    Returns:
        Updated property

    Raises:
        HTTPException: 404 if property not found, 500 if update fails

    Example:
        >>> PATCH /api/v1/properties/{uuid}
        {
            "placed_in_service": "2025-03-01",
            "status": "ACTIVE"
        }
    """
    logger.info(f"Updating property: {property_id}")

    # Fetch existing property
    property_obj = session.get(Property, property_id)
    if not property_obj:
        logger.warning(f"Property not found: {property_id}")
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")

    try:
        # Update fields
        for field, value in property_update.items():
            if hasattr(property_obj, field):
                setattr(property_obj, field, value)

        # Update timestamp
        property_obj.updated_at = datetime.utcnow()

        # Commit changes
        session.add(property_obj)
        session.commit()
        session.refresh(property_obj)

        logger.info(f"✅ Property updated: {property_id}")
        return property_obj

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update property: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update property: {str(e)}")


@router.delete("/properties/{property_id}", status_code=204)
def delete_property(
    property_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    """
    Soft delete a property

    Sets status to INACTIVE instead of deleting the record

    Args:
        property_id: Property UUID
        session: Database session (injected)

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if property not found

    Example:
        >>> DELETE /api/v1/properties/{uuid}
    """
    logger.info(f"Soft deleting property: {property_id}")

    # Fetch property
    property_obj = session.get(Property, property_id)
    if not property_obj:
        logger.warning(f"Property not found: {property_id}")
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")

    # Soft delete
    property_obj.status = PropertyStatus.INACTIVE
    property_obj.updated_at = datetime.utcnow()

    session.add(property_obj)
    session.commit()

    logger.info(f"✅ Property soft deleted: {property_id}")

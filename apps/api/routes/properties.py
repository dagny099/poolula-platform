"""
Property CRUD endpoints

Provides REST API for property management with direct SQLModel usage
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel, field_validator

from core.database.connection import get_session
from core.database.models import Property
from core.database.enums import PropertyStatus
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class PropertyCreate(BaseModel):
    """Request model for creating a property"""
    address: str
    acquisition_date: date
    purchase_price_total: Decimal
    land_basis: Decimal
    building_basis: Decimal
    ffe_basis: Decimal = Decimal("0.00")
    placed_in_service: Optional[date] = None
    status: PropertyStatus = PropertyStatus.ACTIVE
    provenance: Dict[str, Any] = {}
    extra_metadata: Dict[str, Any] = {}

    @field_validator('status', mode='before')
    @classmethod
    def parse_status(cls, v):
        """Accept both enum name (ACTIVE) and value (active)"""
        if isinstance(v, str):
            # Try uppercase name first (e.g., "ACTIVE")
            try:
                return PropertyStatus[v.upper()]
            except KeyError:
                # Fall back to value (e.g., "active")
                return PropertyStatus(v.lower())
        return v


class PropertyUpdate(BaseModel):
    """Request model for updating a property"""
    address: Optional[str] = None
    acquisition_date: Optional[date] = None
    purchase_price_total: Optional[Decimal] = None
    land_basis: Optional[Decimal] = None
    building_basis: Optional[Decimal] = None
    ffe_basis: Optional[Decimal] = None
    placed_in_service: Optional[date] = None
    status: Optional[PropertyStatus] = None
    provenance: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

    @field_validator('status', mode='before')
    @classmethod
    def parse_status(cls, v):
        """Accept both enum name (ACTIVE) and value (active)"""
        if v is None:
            return v
        if isinstance(v, str):
            # Try uppercase name first (e.g., "ACTIVE")
            try:
                return PropertyStatus[v.upper()]
            except KeyError:
                # Fall back to value (e.g., "active")
                return PropertyStatus(v.lower())
        return v


@router.get("/properties", response_model=List[Property])
def list_properties(
    status: Optional[str] = Query(None, description="Filter by property status (ACTIVE, UNDER_CONTRACT, SOLD, INACTIVE)"),
    session: Session = Depends(get_session),
) -> List[Property]:
    """
    List all properties

    Optionally filter by status (ACTIVE, UNDER_CONTRACT, SOLD, INACTIVE)

    Args:
        status: Optional status filter (accepts both uppercase names like "ACTIVE" or lowercase values like "active")
        session: Database session (injected)

    Returns:
        List of properties matching the filter

    Example:
        >>> GET /api/v1/properties
        >>> GET /api/v1/properties?status=ACTIVE
        >>> GET /api/v1/properties?status=active
    """
    logger.info(f"Listing properties with status filter: {status}")

    # Build query
    query = select(Property)
    if status:
        # Parse status string to enum (accept both name and value)
        try:
            status_enum = PropertyStatus[status.upper()]
        except KeyError:
            try:
                status_enum = PropertyStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid status: {status}. Must be one of: ACTIVE, UNDER_CONTRACT, SOLD, INACTIVE"
                )
        query = query.where(Property.status == status_enum)

    # Execute query
    properties = session.exec(query).all()

    logger.info(f"Found {len(properties)} properties")
    return properties


@router.post("/properties", response_model=Property, status_code=201)
def create_property(
    property_data: PropertyCreate,
    session: Session = Depends(get_session),
) -> Property:
    """
    Create a new property

    Automatically sets created_at and updated_at timestamps

    Args:
        property_data: Property data (parsed from JSON)
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
        # Convert Pydantic model to SQLModel (with proper types)
        property_obj = Property(**property_data.model_dump())

        # Add to session and commit
        session.add(property_obj)
        session.commit()
        session.refresh(property_obj)

        logger.info(f"✅ Property created: {property_obj.id}")
        return property_obj

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
    property_update: PropertyUpdate,
    session: Session = Depends(get_session),
) -> Property:
    """
    Update a property

    Allows updating any field. Updates the updated_at timestamp automatically.

    Note: Currently allows updating all fields including acquisition_date and basis.
    Phase 5: Consider protecting immutable fields for accounting integrity.

    Args:
        property_id: Property UUID
        property_update: Fields to update (parsed from JSON)
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
        # Update fields (only non-None values from PropertyUpdate)
        update_data = property_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
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

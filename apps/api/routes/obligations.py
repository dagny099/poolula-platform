"""
Obligation CRUD endpoints

Provides REST API for compliance obligations (tax filings, renewals, reports).

Conventions:
- Enum inputs accept both names (TAX_FILING) and values (tax:filing);
  responses emit enum values.
- DELETE soft-deletes by setting status=CANCELLED.
- property_id is optional: LLC-wide obligations (e.g. periodic report) have none.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel, field_validator

from core.database.connection import get_session
from core.database.models import Property, Obligation
from core.database.enums import ObligationType, ObligationStatus
from core.logging_config import get_logger
from apps.api.routes.common import parse_enum, parse_enum_for_validator, record_audit

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ObligationCreate(BaseModel):
    """Request model for creating an obligation"""
    obligation_type: ObligationType
    due_date: date
    description: str
    property_id: Optional[UUID] = None
    status: ObligationStatus = ObligationStatus.PENDING
    recurrence: Optional[str] = None
    provenance: Dict[str, Any] = {}
    extra_metadata: Dict[str, Any] = {}

    @field_validator('obligation_type', mode='before')
    @classmethod
    def parse_obligation_type(cls, v):
        return parse_enum_for_validator(ObligationType, v)

    @field_validator('status', mode='before')
    @classmethod
    def parse_status(cls, v):
        return parse_enum_for_validator(ObligationStatus, v)


class ObligationUpdate(BaseModel):
    """Request model for updating an obligation"""
    obligation_type: Optional[ObligationType] = None
    due_date: Optional[date] = None
    description: Optional[str] = None
    property_id: Optional[UUID] = None
    status: Optional[ObligationStatus] = None
    recurrence: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

    @field_validator('obligation_type', mode='before')
    @classmethod
    def parse_obligation_type(cls, v):
        return parse_enum_for_validator(ObligationType, v)

    @field_validator('status', mode='before')
    @classmethod
    def parse_status(cls, v):
        return parse_enum_for_validator(ObligationStatus, v)


def _require_property(session: Session, property_id: UUID) -> Property:
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")
    return property_obj


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/obligations", response_model=List[Obligation])
def list_obligations(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, DUE_SOON, OVERDUE, COMPLETED, CANCELLED)"),
    obligation_type: Optional[str] = Query(None, description="Filter by type (name or value, e.g. TAX_FILING or tax:filing)"),
    property_id: Optional[UUID] = Query(None, description="Filter by property"),
    due_before: Optional[date] = Query(None, description="Include obligations due on/before this date"),
    due_after: Optional[date] = Query(None, description="Include obligations due on/after this date"),
    session: Session = Depends(get_session),
) -> List[Obligation]:
    """
    List obligations ordered by due date (soonest first), with optional filters.

    Example:
        >>> GET /api/v1/obligations?status=pending&due_before=2026-12-31
        >>> GET /api/v1/obligations?obligation_type=tax:filing
    """
    logger.info(
        f"Listing obligations (status={status}, type={obligation_type}, "
        f"property={property_id}, due={due_after}..{due_before})"
    )

    query = select(Obligation)
    if status:
        query = query.where(Obligation.status == parse_enum(ObligationStatus, status, "status"))
    if obligation_type:
        query = query.where(
            Obligation.obligation_type == parse_enum(ObligationType, obligation_type, "obligation_type")
        )
    if property_id:
        query = query.where(Obligation.property_id == property_id)
    if due_before:
        query = query.where(Obligation.due_date <= due_before)
    if due_after:
        query = query.where(Obligation.due_date >= due_after)
    query = query.order_by(Obligation.due_date)

    obligations = session.exec(query).all()
    logger.info(f"Found {len(obligations)} obligations")
    return obligations


@router.post("/obligations", response_model=Obligation, status_code=201)
def create_obligation(
    obligation_data: ObligationCreate,
    session: Session = Depends(get_session),
) -> Obligation:
    """
    Create a new obligation

    property_id is optional (omit for LLC-wide obligations); when provided,
    the property must exist (404 otherwise).

    Example:
        >>> POST /api/v1/obligations
        {
            "obligation_type": "compliance:periodic_report",
            "due_date": "2026-05-31",
            "description": "Colorado periodic report for Poolula LLC",
            "recurrence": "FREQ=YEARLY;BYMONTH=5"
        }
    """
    if obligation_data.property_id:
        _require_property(session, obligation_data.property_id)

    try:
        obligation = Obligation(**obligation_data.model_dump())
        session.add(obligation)
        record_audit(session, "INSERT", obligation, reason="Created via REST API")
        session.commit()
        session.refresh(obligation)
        logger.info(f"✅ Obligation created: {obligation.id}")
        return obligation
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to create obligation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create obligation: {str(e)}")


@router.get("/obligations/{obligation_id}", response_model=Obligation)
def get_obligation(
    obligation_id: UUID,
    session: Session = Depends(get_session),
) -> Obligation:
    """Get a single obligation by ID (404 if not found)"""
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail=f"Obligation not found: {obligation_id}")
    return obligation


@router.patch("/obligations/{obligation_id}", response_model=Obligation)
def update_obligation(
    obligation_id: UUID,
    obligation_update: ObligationUpdate,
    session: Session = Depends(get_session),
) -> Obligation:
    """
    Update an obligation (e.g. mark COMPLETED)

    Only provided fields are changed; the change is recorded in the audit log.

    Example:
        >>> PATCH /api/v1/obligations/{uuid}
        {"status": "completed"}
    """
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail=f"Obligation not found: {obligation_id}")

    update_data = obligation_update.model_dump(exclude_unset=True)
    if update_data.get("property_id"):
        _require_property(session, update_data["property_id"])

    old_value = obligation.model_dump(mode="json")

    try:
        for field, value in update_data.items():
            setattr(obligation, field, value)
        obligation.updated_at = datetime.utcnow()

        session.add(obligation)
        record_audit(session, "UPDATE", obligation, reason="Updated via REST API", old_value=old_value)
        session.commit()
        session.refresh(obligation)
        logger.info(f"✅ Obligation updated: {obligation_id}")
        return obligation
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update obligation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update obligation: {str(e)}")


@router.delete("/obligations/{obligation_id}", status_code=204)
def cancel_obligation(
    obligation_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    """
    Soft delete an obligation by setting status to CANCELLED
    """
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail=f"Obligation not found: {obligation_id}")

    old_value = obligation.model_dump(mode="json")
    obligation.status = ObligationStatus.CANCELLED
    obligation.updated_at = datetime.utcnow()

    session.add(obligation)
    record_audit(session, "UPDATE", obligation, reason="Cancelled (soft delete) via REST API", old_value=old_value)
    session.commit()
    logger.info(f"✅ Obligation cancelled: {obligation_id}")

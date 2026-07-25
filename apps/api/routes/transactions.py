"""
Transaction CRUD endpoints

Provides REST API for financial transactions with direct SQLModel usage.

Conventions:
- Enum inputs accept both names (UTILITIES_GAS) and values (utilities:gas);
  responses emit enum values (the canonical DB representation).
- DELETE archives instead of hard-deleting: transactions are financial records,
  so we set extra_metadata["archived"] = true and write an audit log entry.
  Archived transactions are excluded from listings unless include_archived=true.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel, field_validator

from core.database.connection import get_session
from core.database.models import Property, Transaction
from core.database.enums import TransactionCategory, TransactionType
from core.logging_config import get_logger
from apps.api.routes.common import parse_enum, parse_enum_for_validator, record_audit

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class TransactionCreate(BaseModel):
    """Request model for creating a transaction"""
    property_id: UUID
    transaction_date: date
    amount: Decimal
    category: TransactionCategory
    transaction_type: TransactionType
    description: str
    source_account: str
    provenance: Dict[str, Any] = {}
    extra_metadata: Dict[str, Any] = {}

    @field_validator('category', mode='before')
    @classmethod
    def parse_category(cls, v):
        return parse_enum_for_validator(TransactionCategory, v)

    @field_validator('transaction_type', mode='before')
    @classmethod
    def parse_type(cls, v):
        return parse_enum_for_validator(TransactionType, v)


class TransactionUpdate(BaseModel):
    """Request model for updating a transaction"""
    property_id: Optional[UUID] = None
    transaction_date: Optional[date] = None
    amount: Optional[Decimal] = None
    category: Optional[TransactionCategory] = None
    transaction_type: Optional[TransactionType] = None
    description: Optional[str] = None
    source_account: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

    @field_validator('category', mode='before')
    @classmethod
    def parse_category(cls, v):
        return parse_enum_for_validator(TransactionCategory, v)

    @field_validator('transaction_type', mode='before')
    @classmethod
    def parse_type(cls, v):
        return parse_enum_for_validator(TransactionType, v)


def _is_archived(txn: Transaction) -> bool:
    return bool((txn.extra_metadata or {}).get("archived"))


def _require_property(session: Session, property_id: UUID) -> Property:
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")
    return property_obj


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/transactions", response_model=List[Transaction])
def list_transactions(
    property_id: Optional[UUID] = Query(None, description="Filter by property"),
    start_date: Optional[date] = Query(None, description="Include transactions on/after this date"),
    end_date: Optional[date] = Query(None, description="Include transactions on/before this date"),
    category: Optional[str] = Query(None, description="Filter by category (name or value, e.g. UTILITIES_GAS or utilities:gas)"),
    transaction_type: Optional[str] = Query(None, description="Filter by type (REVENUE, EXPENSE, CAPITAL, EQUITY, TRANSFER)"),
    include_archived: bool = Query(False, description="Include archived (soft-deleted) transactions"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of results"),
    session: Session = Depends(get_session),
) -> List[Transaction]:
    """
    List transactions, newest first, with optional filters.

    Example:
        >>> GET /api/v1/transactions?start_date=2025-01-01&end_date=2025-03-31
        >>> GET /api/v1/transactions?category=rental_income&transaction_type=revenue
    """
    logger.info(
        f"Listing transactions (property={property_id}, dates={start_date}..{end_date}, "
        f"category={category}, type={transaction_type})"
    )

    query = select(Transaction)
    if property_id:
        query = query.where(Transaction.property_id == property_id)
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)
    if category:
        query = query.where(Transaction.category == parse_enum(TransactionCategory, category, "category"))
    if transaction_type:
        query = query.where(
            Transaction.transaction_type == parse_enum(TransactionType, transaction_type, "transaction_type")
        )
    query = query.order_by(Transaction.transaction_date.desc())
    if include_archived:
        query = query.limit(limit)

    transactions = session.exec(query).all()

    # Archived flag lives in the JSON extra_metadata column; filter in Python
    # (small-scale deployment, avoids dialect-specific JSON queries). Limit is
    # applied after filtering so archived rows don't consume the result budget.
    if not include_archived:
        transactions = [t for t in transactions if not _is_archived(t)][:limit]

    logger.info(f"Found {len(transactions)} transactions")
    return transactions


@router.post("/transactions", response_model=Transaction, status_code=201)
def create_transaction(
    transaction_data: TransactionCreate,
    session: Session = Depends(get_session),
) -> Transaction:
    """
    Create a new transaction

    The referenced property must exist (404 otherwise). Amount cannot be zero.

    Example:
        >>> POST /api/v1/transactions
        {
            "property_id": "{property-uuid}",
            "transaction_date": "2025-08-15",
            "amount": "1614.00",
            "category": "rental_income",
            "transaction_type": "revenue",
            "description": "August Airbnb payout",
            "source_account": "NuVista Checking"
        }
    """
    _require_property(session, transaction_data.property_id)

    try:
        transaction = Transaction(**transaction_data.model_dump())
    except ValueError as e:
        # Model-level validation (e.g. zero amount)
        raise HTTPException(status_code=422, detail=str(e))

    try:
        session.add(transaction)
        record_audit(session, "INSERT", transaction, reason="Created via REST API")
        session.commit()
        session.refresh(transaction)
        logger.info(f"✅ Transaction created: {transaction.id}")
        return transaction
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to create transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")


@router.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: UUID,
    session: Session = Depends(get_session),
) -> Transaction:
    """Get a single transaction by ID (404 if not found)"""
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    return transaction


@router.patch("/transactions/{transaction_id}", response_model=Transaction)
def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    session: Session = Depends(get_session),
) -> Transaction:
    """
    Update a transaction

    Only provided fields are changed; updated_at is refreshed automatically
    and the change is recorded in the audit log.
    """
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    update_data = transaction_update.model_dump(exclude_unset=True)
    if "property_id" in update_data:
        _require_property(session, update_data["property_id"])

    old_value = transaction.model_dump(mode="json")

    try:
        for field, value in update_data.items():
            setattr(transaction, field, value)
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    transaction.updated_at = datetime.utcnow()

    try:
        session.add(transaction)
        record_audit(session, "UPDATE", transaction, reason="Updated via REST API", old_value=old_value)
        session.commit()
        session.refresh(transaction)
        logger.info(f"✅ Transaction updated: {transaction_id}")
        return transaction
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update transaction: {str(e)}")


@router.delete("/transactions/{transaction_id}", status_code=204)
def archive_transaction(
    transaction_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    """
    Archive (soft delete) a transaction

    Financial records are never hard-deleted; the transaction is flagged as
    archived and the previous state is preserved in the audit log.
    """
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    old_value = transaction.model_dump(mode="json")

    # Reassign the dict (not mutate in place) so the JSON column change is tracked
    transaction.extra_metadata = {
        **(transaction.extra_metadata or {}),
        "archived": True,
        "archived_at": datetime.utcnow().isoformat(),
    }
    transaction.updated_at = datetime.utcnow()

    session.add(transaction)
    record_audit(session, "UPDATE", transaction, reason="Archived (soft delete) via REST API", old_value=old_value)
    session.commit()
    logger.info(f"✅ Transaction archived: {transaction_id}")

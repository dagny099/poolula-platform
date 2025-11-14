"""
SQLModel database models for Poolula Platform

All models use:
- UUIDs for primary keys (better for distributed systems)
- Embedded provenance (JSON column) for data lineage
- Timestamps for created_at and updated_at
- Type hints for IDE support and validation

Design principles:
- Property-centric model (everything relates to properties)
- Immutable audit log (append-only)
- Soft deletes where appropriate (mark inactive, don't delete)

Author: Poolula Platform
Date: 2025-11-13
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import JSON, Text
from pydantic import field_validator

from .enums import (
    TransactionCategory,
    TransactionType,
    DocumentType,
    DocumentVersion,
    DocumentConfidentiality,
    ObligationType,
    ObligationStatus,
    PropertyStatus,
    ProvenanceSourceType,
    VerificationStatus,
)


# =============================================================================
# BASE MODELS
# =============================================================================

class ProvenanceData(SQLModel):
    """
    Embedded provenance data structure

    Stored as JSON in the database, provides data lineage tracking

    Attributes:
        source_type: How was this data created/imported
        source_id: Identifier of the source (filename, document ID, etc.)
        source_field: Specific field in source (e.g., "row_15", "page_3")
        created_at: When this data was created
        created_by: Who/what created it ("user:123", "system:importer")
        confidence: 0.0-1.0, with 1.0 being verified fact
        verification_status: Has this been checked?
        notes: Optional human-readable context
    """
    source_type: ProvenanceSourceType
    source_id: str  # e.g., "airbnb_nov_2024.csv", "settlement_statement.pdf"
    source_field: Optional[str] = None  # e.g., "row_15", "page_3_section_A"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"  # e.g., "user:uuid", "system:importer", "ai:claude"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: Optional[str] = None


# =============================================================================
# PROPERTY MODEL
# =============================================================================

class Property(SQLModel, table=True):
    """
    Rental property owned by Poolula LLC

    Central entity - all transactions, documents, and obligations relate to properties

    Attributes:
        id: UUID primary key
        address: Full street address
        acquisition_date: When property was acquired
        purchase_price_total: Total purchase price
        land_basis: Cost allocated to land (non-depreciable)
        building_basis: Cost allocated to building (27.5yr depreciation)
        ffe_basis: Furniture, fixtures & equipment basis
        placed_in_service: Date rental operations began (for depreciation)
        status: Current status (active, sold, etc.)
        provenance: Data lineage (JSON)
        extra_metadata: Flexible JSON for additional fields
        created_at: When record was created
        updated_at: When record was last updated
    """
    __tablename__ = "properties"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core attributes
    address: str = Field(max_length=255, nullable=False, index=True)
    acquisition_date: date = Field(nullable=False, index=True)

    # Financial basis
    purchase_price_total: Decimal = Field(decimal_places=2, max_digits=12, nullable=False)
    land_basis: Decimal = Field(decimal_places=2, max_digits=12, nullable=False)
    building_basis: Decimal = Field(decimal_places=2, max_digits=12, nullable=False)
    ffe_basis: Decimal = Field(decimal_places=2, max_digits=12, default=Decimal("0.00"))

    # Depreciation
    placed_in_service: Optional[date] = Field(default=None, nullable=True)

    # Status
    status: PropertyStatus = Field(default=PropertyStatus.ACTIVE, nullable=False)

    # Provenance and metadata
    provenance: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    extra_metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships (populated by SQLModel)
    transactions: List["Transaction"] = Relationship(back_populates="property_obj")
    documents: List["Document"] = Relationship(back_populates="property_obj")
    obligations: List["Obligation"] = Relationship(back_populates="property_obj")

    @property
    def total_basis(self) -> Decimal:
        """Calculate total depreciable + non-depreciable basis"""
        return self.land_basis + self.building_basis + self.ffe_basis

    @property
    def depreciable_basis(self) -> Decimal:
        """Calculate only depreciable basis (excludes land)"""
        return self.building_basis + self.ffe_basis

    def __repr__(self) -> str:
        return f"<Property {self.address} (${self.purchase_price_total})>"


# =============================================================================
# TRANSACTION MODEL
# =============================================================================

class Transaction(SQLModel, table=True):
    """
    Financial transaction (revenue, expense, capital, equity)

    Tracks all money flowing through the LLC

    Attributes:
        id: UUID primary key
        property_id: FK to Property
        transaction_date: When transaction occurred
        amount: Dollar amount (positive for revenue/contributions, can be negative)
        category: Chart of accounts category
        transaction_type: High-level type (revenue, expense, capital, equity)
        description: Human-readable description
        source_account: Which account (NuVista checking, Chase Ink, etc.)
        provenance: Data lineage (JSON)
        extra_metadata: Flexible JSON (e.g., {"airbnb_confirmation": "HM123"})
    """
    __tablename__ = "transactions"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign key
    property_id: UUID = Field(foreign_key="properties.id", nullable=False, index=True)

    # Core attributes
    transaction_date: date = Field(nullable=False, index=True)
    amount: Decimal = Field(decimal_places=2, max_digits=12, nullable=False)
    category: TransactionCategory = Field(nullable=False, index=True)
    transaction_type: TransactionType = Field(nullable=False, index=True)
    description: str = Field(max_length=500, nullable=False)
    source_account: str = Field(max_length=100, nullable=False)  # e.g., "NuVista Checking"

    # Provenance and metadata
    provenance: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    extra_metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    property_obj: Property = Relationship(back_populates="transactions")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is not zero (would be meaningless)"""
        if v == Decimal("0.00"):
            raise ValueError("Transaction amount cannot be zero")
        return v

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_date} ${self.amount} {self.category}>"


# =============================================================================
# DOCUMENT MODEL
# =============================================================================

class Document(SQLModel, table=True):
    """
    Document storage and metadata

    Stores metadata about documents (PDFs, Word docs, images)
    Actual file content stored separately (filesystem or S3)

    Attributes:
        id: UUID primary key
        property_id: FK to Property (nullable for LLC-wide docs)
        filename: Original filename
        doc_type: Category (formation, insurance, lease, etc.)
        effective_date: When document became effective/valid
        entities: Array of legal entities mentioned (for filtering)
        version: Document version status
        confidentiality: Security level
        content_hash: SHA-256 hash for deduplication and integrity
        provenance: Data lineage (JSON)
        extra_metadata: Flexible JSON (e.g., {"pages": 5, "ocr_done": true})
    """
    __tablename__ = "documents"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign key (nullable for LLC-wide documents)
    property_id: Optional[UUID] = Field(
        foreign_key="properties.id",
        nullable=True,
        index=True
    )

    # Core attributes
    filename: str = Field(max_length=255, nullable=False)
    doc_type: DocumentType = Field(nullable=False, index=True)
    effective_date: Optional[date] = Field(default=None, nullable=True, index=True)

    # Entities mentioned in document (for filtering)
    entities: List[str] = Field(sa_column=Column(JSON), default_factory=list)

    # Version control
    version: DocumentVersion = Field(default=DocumentVersion.FINAL, nullable=False)
    confidentiality: DocumentConfidentiality = Field(
        default=DocumentConfidentiality.INTERNAL,
        nullable=False
    )

    # Content tracking
    content_hash: str = Field(max_length=64, nullable=False)  # SHA-256 hex string

    # Provenance and metadata
    provenance: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    extra_metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    property_obj: Optional[Property] = Relationship(back_populates="documents")

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Ensure hash is valid SHA-256 format"""
        if len(v) != 64:
            raise ValueError("content_hash must be 64-character SHA-256 hex string")
        try:
            int(v, 16)  # Verify it's hexadecimal
        except ValueError:
            raise ValueError("content_hash must be hexadecimal")
        return v.lower()

    def __repr__(self) -> str:
        return f"<Document {self.filename} ({self.doc_type})>"


# =============================================================================
# OBLIGATION MODEL
# =============================================================================

class Obligation(SQLModel, table=True):
    """
    Compliance obligation / calendar item

    Tracks tasks, deadlines, and recurring obligations

    Attributes:
        id: UUID primary key
        property_id: FK to Property (nullable for LLC-wide obligations)
        obligation_type: Category (tax filing, insurance renewal, etc.)
        due_date: When obligation is due
        status: Current status (pending, completed, etc.)
        recurrence: RRULE format for recurring obligations (or null for one-time)
        description: Human-readable description
        provenance: Data lineage (JSON)
        extra_metadata: Flexible JSON (e.g., {"reminder_sent": true, "amount_due": 500})
    """
    __tablename__ = "obligations"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign key (nullable for LLC-wide obligations like tax filing)
    property_id: Optional[UUID] = Field(
        foreign_key="properties.id",
        nullable=True,
        index=True
    )

    # Core attributes
    obligation_type: ObligationType = Field(nullable=False, index=True)
    due_date: date = Field(nullable=False, index=True)
    status: ObligationStatus = Field(default=ObligationStatus.PENDING, nullable=False, index=True)

    # Recurrence (RRULE format, null for one-time obligations)
    # Example: "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=1" for April 1 annually
    recurrence: Optional[str] = Field(max_length=500, default=None, nullable=True)

    description: str = Field(sa_column=Column(Text, nullable=False))

    # Provenance and metadata
    provenance: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    extra_metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    property_obj: Optional[Property] = Relationship(back_populates="obligations")

    @property
    def is_overdue(self) -> bool:
        """Check if obligation is past due"""
        return (
            self.status in [ObligationStatus.PENDING, ObligationStatus.DUE_SOON]
            and self.due_date < date.today()
        )

    @property
    def days_until_due(self) -> int:
        """Calculate days until due date (negative if overdue)"""
        delta = self.due_date - date.today()
        return delta.days

    def __repr__(self) -> str:
        return f"<Obligation {self.obligation_type} due {self.due_date}>"


# =============================================================================
# AUDIT LOG MODEL
# =============================================================================

class AuditLog(SQLModel, table=True):
    """
    Immutable audit trail of all data changes

    Append-only log, never delete or modify entries

    Captures WHO changed WHAT, WHEN, and WHY

    Attributes:
        id: UUID primary key
        timestamp: When change occurred (auto-generated)
        user: Who made the change ("user:uuid", "system:importer", "ai:claude")
        action: What was done (INSERT, UPDATE, DELETE)
        entity_type: Which table/model (Property, Transaction, etc.)
        entity_id: UUID of the affected record
        old_value: Previous state (JSON, null for INSERT)
        new_value: New state (JSON, null for DELETE)
        reason: Why the change was made (user-provided or auto-generated)
        context: Additional context (JSON: request_id, ip_address, etc.)
    """
    __tablename__ = "audit_log"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Audit fields
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    user: str = Field(max_length=100, nullable=False, index=True)
    action: str = Field(max_length=20, nullable=False, index=True)  # INSERT, UPDATE, DELETE

    # Entity tracking (polymorphic)
    entity_type: str = Field(max_length=50, nullable=False, index=True)  # "Property", "Transaction"
    entity_id: UUID = Field(nullable=False, index=True)

    # Change tracking
    old_value: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON), default=None)
    new_value: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON), default=None)

    # Context
    reason: str = Field(sa_column=Column(Text, nullable=False))
    context: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}:{self.entity_id} by {self.user}>"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_provenance(
    source_type: ProvenanceSourceType,
    source_id: str,
    created_by: str = "system",
    source_field: Optional[str] = None,
    confidence: float = 1.0,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a provenance dictionary for embedding in models

    Args:
        source_type: How data was created
        source_id: Identifier of source (filename, doc ID)
        created_by: Who/what created it
        source_field: Specific field reference
        confidence: 0.0-1.0 confidence level
        notes: Optional context

    Returns:
        Dictionary ready for JSON column

    Example:
        >>> prov = create_provenance(
        ...     source_type=ProvenanceSourceType.CSV_IMPORT,
        ...     source_id="airbnb_nov_2024.csv",
        ...     source_field="row_15",
        ...     created_by="system:csv_importer"
        ... )
        >>> transaction = Transaction(
        ...     amount=Decimal("150.00"),
        ...     provenance=prov,
        ...     ...
        ... )
    """
    provenance_data = ProvenanceData(
        source_type=source_type,
        source_id=source_id,
        source_field=source_field,
        created_by=created_by,
        confidence=confidence,
        verification_status=VerificationStatus.UNVERIFIED,
        notes=notes,
    )
    return provenance_data.model_dump(mode="json")

"""
Tests for database models

Tests model validation, computed properties, and relationships
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.database.models import (
    Property,
    Transaction,
    Document,
    Obligation,
    AuditLog,
    create_provenance,
)
from core.database.enums import (
    PropertyStatus,
    TransactionCategory,
    TransactionType,
    DocumentType,
    DocumentVersion,
    DocumentConfidentiality,
    ObligationType,
    ObligationStatus,
    ProvenanceSourceType,
    VerificationStatus,
)


# =============================================================================
# PROPERTY MODEL TESTS
# =============================================================================

def test_property_creation():
    """Test creating a valid Property"""
    property_obj = Property(
        address="900 S 9th St, Montrose, CO 81401",
        acquisition_date=date(2024, 4, 15),
        purchase_price_total=Decimal("442300.00"),
        land_basis=Decimal("78200.00"),
        building_basis=Decimal("364100.00"),
        ffe_basis=Decimal("10000.00"),
        status=PropertyStatus.ACTIVE,
    )

    assert property_obj.address == "900 S 9th St, Montrose, CO 81401"
    assert property_obj.purchase_price_total == Decimal("442300.00")
    assert property_obj.status == PropertyStatus.ACTIVE


def test_property_total_basis():
    """Test Property.total_basis computed property"""
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
    )

    assert property_obj.total_basis == Decimal("100000.00")


def test_property_depreciable_basis():
    """Test Property.depreciable_basis computed property (excludes land)"""
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
    )

    # Depreciable = building + ffe (land excluded)
    assert property_obj.depreciable_basis == Decimal("80000.00")


# =============================================================================
# TRANSACTION MODEL TESTS
# =============================================================================

def test_transaction_creation():
    """Test creating a valid Transaction"""
    transaction = Transaction(
        property_id=uuid4(),
        transaction_date=date(2024, 5, 1),
        amount=Decimal("150.00"),
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description="Airbnb booking",
        source_account="NuVista Checking",
    )

    assert transaction.amount == Decimal("150.00")
    assert transaction.category == TransactionCategory.RENTAL_INCOME


def test_transaction_amount_cannot_be_zero():
    """Test Transaction.validate_amount rejects zero amounts"""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            property_id=uuid4(),
            transaction_date=date(2024, 5, 1),
            amount=Decimal("0.00"),  # Invalid
            category=TransactionCategory.RENTAL_INCOME,
            transaction_type=TransactionType.REVENUE,
            description="Test",
            source_account="Test Account",
        )

    assert "amount cannot be zero" in str(exc_info.value).lower()


# =============================================================================
# DOCUMENT MODEL TESTS
# =============================================================================

def test_document_creation():
    """Test creating a valid Document"""
    document = Document(
        property_id=uuid4(),
        filename="deed.pdf",
        doc_type=DocumentType.DEED,
        content_hash="a" * 64,  # Valid 64-char hex
        version=DocumentVersion.FINAL,
        confidentiality=DocumentConfidentiality.RESTRICTED,
    )

    assert document.filename == "deed.pdf"
    assert document.doc_type == DocumentType.DEED


def test_document_hash_validation_length():
    """Test Document.validate_hash requires 64 characters"""
    with pytest.raises(ValidationError) as exc_info:
        Document(
            property_id=uuid4(),
            filename="test.pdf",
            doc_type=DocumentType.DEED,
            content_hash="abc123",  # Too short
        )

    assert "64-character" in str(exc_info.value)


def test_document_hash_validation_hex():
    """Test Document.validate_hash requires hexadecimal"""
    with pytest.raises(ValidationError) as exc_info:
        Document(
            property_id=uuid4(),
            filename="test.pdf",
            doc_type=DocumentType.DEED,
            content_hash="z" * 64,  # Not hex
        )

    assert "hexadecimal" in str(exc_info.value)


def test_document_hash_normalized_lowercase():
    """Test Document.validate_hash normalizes to lowercase"""
    document = Document(
        property_id=uuid4(),
        filename="test.pdf",
        doc_type=DocumentType.DEED,
        content_hash="A" * 64,  # Uppercase
    )

    assert document.content_hash == "a" * 64  # Normalized to lowercase


# =============================================================================
# OBLIGATION MODEL TESTS
# =============================================================================

def test_obligation_creation():
    """Test creating a valid Obligation"""
    obligation = Obligation(
        property_id=uuid4(),
        obligation_type=ObligationType.TAX_FILING,
        due_date=date(2025, 4, 15),
        status=ObligationStatus.PENDING,
        description="File annual tax return",
    )

    assert obligation.obligation_type == ObligationType.TAX_FILING
    assert obligation.due_date == date(2025, 4, 15)


def test_obligation_is_overdue():
    """Test Obligation.is_overdue property"""
    # Past due date, pending status
    overdue_obligation = Obligation(
        obligation_type=ObligationType.TAX_FILING,
        due_date=date(2020, 1, 1),  # In the past
        status=ObligationStatus.PENDING,
        description="Test",
    )
    assert overdue_obligation.is_overdue is True

    # Future due date
    not_overdue_obligation = Obligation(
        obligation_type=ObligationType.TAX_FILING,
        due_date=date(2099, 12, 31),  # In the future
        status=ObligationStatus.PENDING,
        description="Test",
    )
    assert not_overdue_obligation.is_overdue is False

    # Past due but completed
    completed_obligation = Obligation(
        obligation_type=ObligationType.TAX_FILING,
        due_date=date(2020, 1, 1),
        status=ObligationStatus.COMPLETED,  # Completed
        description="Test",
    )
    assert completed_obligation.is_overdue is False


def test_obligation_days_until_due():
    """Test Obligation.days_until_due property"""
    today = date.today()

    obligation = Obligation(
        obligation_type=ObligationType.TAX_FILING,
        due_date=today,
        description="Test",
    )

    assert obligation.days_until_due == 0


# =============================================================================
# PROVENANCE HELPER TESTS
# =============================================================================

def test_create_provenance():
    """Test create_provenance helper function"""
    provenance = create_provenance(
        source_type=ProvenanceSourceType.CSV_IMPORT,
        source_id="airbnb_nov_2024.csv",
        source_field="row_15",
        created_by="system:csv_importer",
        confidence=0.95,
        notes="Imported from Airbnb report",
    )

    assert provenance["source_type"] == "csv_import"
    assert provenance["source_id"] == "airbnb_nov_2024.csv"
    assert provenance["source_field"] == "row_15"
    assert provenance["confidence"] == 0.95
    assert provenance["verification_status"] == "unverified"


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================

def test_property_relationships(session_test):
    """Test Property relationships with transactions, documents, obligations"""
    # Create property
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
    )
    session_test.add(property_obj)
    session_test.commit()
    session_test.refresh(property_obj)

    # Create transaction
    transaction = Transaction(
        property_id=property_obj.id,
        transaction_date=date(2024, 5, 1),
        amount=Decimal("150.00"),
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description="Test income",
        source_account="Test Account",
    )
    session_test.add(transaction)

    # Create document
    document = Document(
        property_id=property_obj.id,
        filename="test.pdf",
        doc_type=DocumentType.DEED,
        content_hash="a" * 64,
    )
    session_test.add(document)

    # Create obligation
    obligation = Obligation(
        property_id=property_obj.id,
        obligation_type=ObligationType.TAX_FILING,
        due_date=date(2025, 4, 15),
        description="Test obligation",
    )
    session_test.add(obligation)

    session_test.commit()
    session_test.refresh(property_obj)

    # Test relationships
    assert len(property_obj.transactions) == 1
    assert len(property_obj.documents) == 1
    assert len(property_obj.obligations) == 1
    assert property_obj.transactions[0].description == "Test income"

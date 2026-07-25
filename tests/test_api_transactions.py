"""
Tests for Transaction API endpoints

Tests full CRUD operations, filtering, and archive (soft delete) behavior
via FastAPI test client
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import select

from core.database.models import Property, Transaction, AuditLog
from core.database.enums import PropertyStatus, TransactionCategory, TransactionType


@pytest.fixture(name="property_obj")
def property_fixture(session_test):
    """Create a property for transactions to reference"""
    prop = Property(
        address="900 S 9th St, Montrose, CO 81401",
        acquisition_date=date(2024, 4, 15),
        purchase_price_total=Decimal("442300.00"),
        land_basis=Decimal("78200.00"),
        building_basis=Decimal("364100.00"),
        ffe_basis=Decimal("10000.00"),
        status=PropertyStatus.ACTIVE,
    )
    session_test.add(prop)
    session_test.commit()
    session_test.refresh(prop)
    return prop


def make_transaction(property_id, **overrides):
    """Build a Transaction with sensible defaults"""
    defaults = dict(
        property_id=property_id,
        transaction_date=date(2025, 8, 15),
        amount=Decimal("1614.00"),
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description="August Airbnb payout",
        source_account="NuVista Checking",
    )
    defaults.update(overrides)
    return Transaction(**defaults)


# =============================================================================
# LIST TESTS
# =============================================================================

def test_list_transactions_empty(client):
    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_transactions(client, session_test, property_obj):
    session_test.add(make_transaction(property_obj.id))
    session_test.add(make_transaction(
        property_obj.id,
        transaction_date=date(2025, 9, 1),
        amount=Decimal("-120.50"),
        category=TransactionCategory.UTILITIES_GAS,
        transaction_type=TransactionType.EXPENSE,
        description="Black Hills Energy",
    ))
    session_test.commit()

    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Newest first
    assert data[0]["transaction_date"] == "2025-09-01"
    assert data[0]["category"] == "utilities:gas"
    assert data[1]["category"] == "rental_income"


def test_list_transactions_filter_by_date_range(client, session_test, property_obj):
    session_test.add(make_transaction(property_obj.id, transaction_date=date(2025, 1, 15)))
    session_test.add(make_transaction(property_obj.id, transaction_date=date(2025, 6, 15)))
    session_test.add(make_transaction(property_obj.id, transaction_date=date(2025, 12, 15)))
    session_test.commit()

    response = client.get("/api/v1/transactions?start_date=2025-03-01&end_date=2025-09-30")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["transaction_date"] == "2025-06-15"


def test_list_transactions_filter_by_category_and_type(client, session_test, property_obj):
    session_test.add(make_transaction(property_obj.id))
    session_test.add(make_transaction(
        property_obj.id,
        amount=Decimal("-85.00"),
        category=TransactionCategory.UTILITIES_GAS,
        transaction_type=TransactionType.EXPENSE,
    ))
    session_test.commit()

    # Filter by enum value
    response = client.get("/api/v1/transactions?category=utilities:gas")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Filter by enum name (uppercase)
    response = client.get("/api/v1/transactions?category=UTILITIES_GAS")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Filter by transaction type
    response = client.get("/api/v1/transactions?transaction_type=revenue")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["transaction_type"] == "revenue"


def test_list_transactions_filter_by_property(client, session_test, property_obj):
    other = Property(
        address="Other Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("80000.00"),
    )
    session_test.add(other)
    session_test.commit()
    session_test.refresh(other)

    session_test.add(make_transaction(property_obj.id))
    session_test.add(make_transaction(other.id, description="Other property txn"))
    session_test.commit()

    response = client.get(f"/api/v1/transactions?property_id={property_obj.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["property_id"] == str(property_obj.id)


def test_list_transactions_invalid_category(client):
    response = client.get("/api/v1/transactions?category=not_a_category")
    assert response.status_code == 422


# =============================================================================
# CREATE TESTS
# =============================================================================

def test_create_transaction(client, session_test, property_obj):
    payload = {
        "property_id": str(property_obj.id),
        "transaction_date": "2025-08-15",
        "amount": "1614.00",
        "category": "rental_income",
        "transaction_type": "REVENUE",  # name form should be accepted
        "description": "August Airbnb payout",
        "source_account": "NuVista Checking",
        "provenance": {"source_type": "manual_entry", "source_id": "test"},
    }
    response = client.post("/api/v1/transactions", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "rental_income"
    assert data["transaction_type"] == "revenue"
    assert Decimal(data["amount"]) == Decimal("1614.00")
    assert data["id"] is not None

    # Audit log entry written
    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "INSERT"
    assert audits[0].entity_type == "Transaction"


def test_create_transaction_missing_property(client):
    payload = {
        "property_id": str(uuid4()),
        "transaction_date": "2025-08-15",
        "amount": "100.00",
        "category": "rental_income",
        "transaction_type": "revenue",
        "description": "Orphan transaction",
        "source_account": "NuVista Checking",
    }
    response = client.post("/api/v1/transactions", json=payload)
    assert response.status_code == 404


def test_create_transaction_zero_amount_rejected(client, property_obj):
    payload = {
        "property_id": str(property_obj.id),
        "transaction_date": "2025-08-15",
        "amount": "0.00",
        "category": "rental_income",
        "transaction_type": "revenue",
        "description": "Zero amount",
        "source_account": "NuVista Checking",
    }
    response = client.post("/api/v1/transactions", json=payload)
    assert response.status_code == 422


def test_create_transaction_invalid_category(client, property_obj):
    payload = {
        "property_id": str(property_obj.id),
        "transaction_date": "2025-08-15",
        "amount": "100.00",
        "category": "bogus_category",
        "transaction_type": "revenue",
        "description": "Bad category",
        "source_account": "NuVista Checking",
    }
    response = client.post("/api/v1/transactions", json=payload)
    assert response.status_code == 422


# =============================================================================
# GET BY ID TESTS
# =============================================================================

def test_get_transaction(client, session_test, property_obj):
    txn = make_transaction(property_obj.id)
    session_test.add(txn)
    session_test.commit()

    response = client.get(f"/api/v1/transactions/{txn.id}")
    assert response.status_code == 200
    assert response.json()["description"] == "August Airbnb payout"


def test_get_transaction_not_found(client):
    response = client.get(f"/api/v1/transactions/{uuid4()}")
    assert response.status_code == 404


# =============================================================================
# UPDATE TESTS
# =============================================================================

def test_update_transaction(client, session_test, property_obj):
    txn = make_transaction(property_obj.id)
    session_test.add(txn)
    session_test.commit()

    response = client.patch(
        f"/api/v1/transactions/{txn.id}",
        json={"description": "Corrected description", "category": "cleaning"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Corrected description"
    assert data["category"] == "cleaning"
    # Unchanged fields preserved
    assert data["source_account"] == "NuVista Checking"

    # Audit log captured old value
    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "UPDATE"
    assert audits[0].old_value["description"] == "August Airbnb payout"


def test_update_transaction_not_found(client):
    response = client.patch(
        f"/api/v1/transactions/{uuid4()}", json={"description": "nope"}
    )
    assert response.status_code == 404


# =============================================================================
# ARCHIVE (SOFT DELETE) TESTS
# =============================================================================

def test_archive_transaction(client, session_test, property_obj):
    txn = make_transaction(property_obj.id)
    session_test.add(txn)
    session_test.commit()

    response = client.delete(f"/api/v1/transactions/{txn.id}")
    assert response.status_code == 204

    # Record still exists, flagged as archived
    session_test.refresh(txn)
    assert txn.extra_metadata.get("archived") is True

    # Excluded from default listing
    response = client.get("/api/v1/transactions")
    assert response.json() == []

    # Included when requested
    response = client.get("/api/v1/transactions?include_archived=true")
    assert len(response.json()) == 1

    # Still retrievable by ID
    response = client.get(f"/api/v1/transactions/{txn.id}")
    assert response.status_code == 200


def test_archive_transaction_not_found(client):
    response = client.delete(f"/api/v1/transactions/{uuid4()}")
    assert response.status_code == 404


def test_list_transactions_limit_applied_after_archive_filter(client, session_test, property_obj):
    """Archived rows must not consume the limit budget for default listings"""
    newest = make_transaction(property_obj.id, transaction_date=date(2025, 8, 20))
    middle = make_transaction(property_obj.id, transaction_date=date(2025, 8, 10))
    oldest = make_transaction(property_obj.id, transaction_date=date(2025, 8, 1))
    session_test.add_all([newest, middle, oldest])
    session_test.commit()

    # Archive the newest transaction
    response = client.delete(f"/api/v1/transactions/{newest.id}")
    assert response.status_code == 204

    # limit=2 should return both remaining live transactions, not just one
    response = client.get("/api/v1/transactions?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {t["id"] for t in data} == {str(middle.id), str(oldest.id)}

    # include_archived still honors the limit in SQL (newest first)
    response = client.get("/api/v1/transactions?include_archived=true&limit=2")
    assert {t["id"] for t in response.json()} == {str(newest.id), str(middle.id)}

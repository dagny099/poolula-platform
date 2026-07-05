"""
Tests for Obligation API endpoints

Tests full CRUD operations, filtering, and cancel (soft delete) behavior
via FastAPI test client
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import select

from core.database.models import Property, Obligation, AuditLog
from core.database.enums import PropertyStatus, ObligationType, ObligationStatus


@pytest.fixture(name="property_obj")
def property_fixture(session_test):
    """Create a property for obligations to reference"""
    prop = Property(
        address="900 S 9th St, Montrose, CO 81401",
        acquisition_date=date(2024, 4, 15),
        purchase_price_total=Decimal("442300.00"),
        land_basis=Decimal("78200.00"),
        building_basis=Decimal("364100.00"),
        status=PropertyStatus.ACTIVE,
    )
    session_test.add(prop)
    session_test.commit()
    session_test.refresh(prop)
    return prop


def make_obligation(**overrides):
    """Build an Obligation with sensible defaults (LLC-wide, no property)"""
    defaults = dict(
        obligation_type=ObligationType.PERIODIC_REPORT,
        due_date=date(2026, 5, 31),
        status=ObligationStatus.PENDING,
        description="Colorado periodic report for Poolula LLC",
    )
    defaults.update(overrides)
    return Obligation(**defaults)


# =============================================================================
# LIST TESTS
# =============================================================================

def test_list_obligations_empty(client):
    response = client.get("/api/v1/obligations")
    assert response.status_code == 200
    assert response.json() == []


def test_list_obligations_ordered_by_due_date(client, session_test):
    session_test.add(make_obligation(due_date=date(2026, 9, 15), description="Q3 estimated tax"))
    session_test.add(make_obligation(due_date=date(2026, 3, 15), description="Form 1065 filing",
                                     obligation_type=ObligationType.TAX_FILING))
    session_test.commit()

    response = client.get("/api/v1/obligations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["due_date"] == "2026-03-15"
    assert data[0]["obligation_type"] == "tax:filing"


def test_list_obligations_filter_by_status(client, session_test):
    session_test.add(make_obligation())
    session_test.add(make_obligation(status=ObligationStatus.COMPLETED, description="Done item"))
    session_test.commit()

    response = client.get("/api/v1/obligations?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"

    # Name form also accepted
    response = client.get("/api/v1/obligations?status=COMPLETED")
    assert len(response.json()) == 1


def test_list_obligations_filter_by_type_and_due_range(client, session_test):
    session_test.add(make_obligation(obligation_type=ObligationType.TAX_FILING,
                                     due_date=date(2026, 3, 15)))
    session_test.add(make_obligation(obligation_type=ObligationType.INSURANCE_RENEWAL,
                                     due_date=date(2026, 11, 1), description="Travelers renewal"))
    session_test.commit()

    response = client.get("/api/v1/obligations?obligation_type=tax:filing")
    assert len(response.json()) == 1

    response = client.get("/api/v1/obligations?due_before=2026-06-30")
    data = response.json()
    assert len(data) == 1
    assert data[0]["due_date"] == "2026-03-15"

    response = client.get("/api/v1/obligations?due_after=2026-06-30")
    assert len(response.json()) == 1


def test_list_obligations_filter_by_property(client, session_test, property_obj):
    session_test.add(make_obligation())  # LLC-wide
    session_test.add(make_obligation(property_id=property_obj.id, description="Property tax payment",
                                     obligation_type=ObligationType.TAX_PAYMENT))
    session_test.commit()

    response = client.get(f"/api/v1/obligations?property_id={property_obj.id}")
    data = response.json()
    assert len(data) == 1
    assert data[0]["property_id"] == str(property_obj.id)


def test_list_obligations_invalid_status(client):
    response = client.get("/api/v1/obligations?status=nonsense")
    assert response.status_code == 422


# =============================================================================
# CREATE TESTS
# =============================================================================

def test_create_obligation_llc_wide(client, session_test):
    payload = {
        "obligation_type": "compliance:periodic_report",
        "due_date": "2026-05-31",
        "description": "Colorado periodic report",
        "recurrence": "FREQ=YEARLY;BYMONTH=5",
    }
    response = client.post("/api/v1/obligations", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["obligation_type"] == "compliance:periodic_report"
    assert data["status"] == "pending"
    assert data["property_id"] is None
    assert data["recurrence"] == "FREQ=YEARLY;BYMONTH=5"

    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].entity_type == "Obligation"


def test_create_obligation_with_property(client, property_obj):
    payload = {
        "obligation_type": "TAX_PAYMENT",  # name form accepted
        "due_date": "2026-04-30",
        "description": "Montrose County property tax",
        "property_id": str(property_obj.id),
    }
    response = client.post("/api/v1/obligations", json=payload)
    assert response.status_code == 201
    assert response.json()["property_id"] == str(property_obj.id)


def test_create_obligation_missing_property(client):
    payload = {
        "obligation_type": "tax:payment",
        "due_date": "2026-04-30",
        "description": "Orphan obligation",
        "property_id": str(uuid4()),
    }
    response = client.post("/api/v1/obligations", json=payload)
    assert response.status_code == 404


def test_create_obligation_invalid_type(client):
    payload = {
        "obligation_type": "not_a_type",
        "due_date": "2026-04-30",
        "description": "Bad type",
    }
    response = client.post("/api/v1/obligations", json=payload)
    assert response.status_code == 422


# =============================================================================
# GET BY ID TESTS
# =============================================================================

def test_get_obligation(client, session_test):
    obligation = make_obligation()
    session_test.add(obligation)
    session_test.commit()

    response = client.get(f"/api/v1/obligations/{obligation.id}")
    assert response.status_code == 200
    assert response.json()["description"] == "Colorado periodic report for Poolula LLC"


def test_get_obligation_not_found(client):
    response = client.get(f"/api/v1/obligations/{uuid4()}")
    assert response.status_code == 404


# =============================================================================
# UPDATE TESTS
# =============================================================================

def test_update_obligation_mark_completed(client, session_test):
    obligation = make_obligation()
    session_test.add(obligation)
    session_test.commit()

    response = client.patch(
        f"/api/v1/obligations/{obligation.id}", json={"status": "completed"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].old_value["status"] == "pending"


def test_update_obligation_not_found(client):
    response = client.patch(
        f"/api/v1/obligations/{uuid4()}", json={"status": "completed"}
    )
    assert response.status_code == 404


# =============================================================================
# CANCEL (SOFT DELETE) TESTS
# =============================================================================

def test_cancel_obligation(client, session_test):
    obligation = make_obligation()
    session_test.add(obligation)
    session_test.commit()

    response = client.delete(f"/api/v1/obligations/{obligation.id}")
    assert response.status_code == 204

    # Record still exists with CANCELLED status
    session_test.refresh(obligation)
    assert obligation.status == ObligationStatus.CANCELLED

    # Visible when filtering for cancelled
    response = client.get("/api/v1/obligations?status=cancelled")
    assert len(response.json()) == 1


def test_cancel_obligation_not_found(client):
    response = client.delete(f"/api/v1/obligations/{uuid4()}")
    assert response.status_code == 404

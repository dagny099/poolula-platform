"""
Tests for Property API endpoints

Tests full CRUD operations via FastAPI test client
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from core.database.models import Property
from core.database.enums import PropertyStatus


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

def test_health_check(client):
    """Test /health endpoint returns healthy status"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database_connected" in data
    assert "api_version" in data


# =============================================================================
# LIST PROPERTIES TESTS
# =============================================================================

def test_list_properties_empty(client):
    """Test GET /api/v1/properties returns empty list when no properties"""
    response = client.get("/api/v1/properties")

    assert response.status_code == 200
    assert response.json() == []


def test_list_properties(client, session_test):
    """Test GET /api/v1/properties returns all properties"""
    # Create test properties
    property1 = Property(
        address="Property 1",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
        status=PropertyStatus.ACTIVE,
    )
    property2 = Property(
        address="Property 2",
        acquisition_date=date(2024, 2, 1),
        purchase_price_total=Decimal("200000.00"),
        land_basis=Decimal("40000.00"),
        building_basis=Decimal("140000.00"),
        ffe_basis=Decimal("20000.00"),
        status=PropertyStatus.INACTIVE,
    )

    session_test.add(property1)
    session_test.add(property2)
    session_test.commit()

    # List all properties
    response = client.get("/api/v1/properties")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["address"] == "Property 1"
    assert data[1]["address"] == "Property 2"


def test_list_properties_filter_by_status(client, session_test):
    """Test GET /api/v1/properties?status=ACTIVE filters correctly"""
    # Create test properties
    property1 = Property(
        address="Active Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
        status=PropertyStatus.ACTIVE,
    )
    property2 = Property(
        address="Inactive Property",
        acquisition_date=date(2024, 2, 1),
        purchase_price_total=Decimal("200000.00"),
        land_basis=Decimal("40000.00"),
        building_basis=Decimal("140000.00"),
        ffe_basis=Decimal("20000.00"),
        status=PropertyStatus.INACTIVE,
    )

    session_test.add(property1)
    session_test.add(property2)
    session_test.commit()

    # Filter by ACTIVE status
    response = client.get("/api/v1/properties?status=ACTIVE")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["address"] == "Active Property"
    assert data[0]["status"] == "ACTIVE"


# =============================================================================
# CREATE PROPERTY TESTS
# =============================================================================

def test_create_property(client):
    """Test POST /api/v1/properties creates a new property"""
    property_data = {
        "address": "900 S 9th St, Montrose, CO 81401",
        "acquisition_date": "2024-04-15",
        "purchase_price_total": "442300.00",
        "land_basis": "78200.00",
        "building_basis": "364100.00",
        "ffe_basis": "10000.00",
        "placed_in_service": "2025-02-01",
        "status": "ACTIVE",
        "provenance": {},
        "extra_metadata": {},
    }

    response = client.post("/api/v1/properties", json=property_data)

    assert response.status_code == 201
    data = response.json()
    assert data["address"] == "900 S 9th St, Montrose, CO 81401"
    assert data["purchase_price_total"] == "442300.00"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_property_validation_error(client):
    """Test POST /api/v1/properties with invalid data returns 422"""
    property_data = {
        "address": "Test Property",
        # Missing required fields
    }

    response = client.post("/api/v1/properties", json=property_data)

    assert response.status_code == 422  # Validation error


# =============================================================================
# GET PROPERTY TESTS
# =============================================================================

def test_get_property(client, session_test):
    """Test GET /api/v1/properties/{id} returns single property"""
    # Create test property
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

    # Get property by ID
    response = client.get(f"/api/v1/properties/{property_obj.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(property_obj.id)
    assert data["address"] == "Test Property"
    assert data["purchase_price_total"] == "100000.00"


def test_get_property_not_found(client):
    """Test GET /api/v1/properties/{id} returns 404 for non-existent property"""
    fake_id = uuid4()

    response = client.get(f"/api/v1/properties/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# =============================================================================
# UPDATE PROPERTY TESTS
# =============================================================================

def test_update_property(client, session_test):
    """Test PATCH /api/v1/properties/{id} updates property"""
    # Create test property
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
        placed_in_service=None,
        status=PropertyStatus.UNDER_CONTRACT,
    )
    session_test.add(property_obj)
    session_test.commit()
    session_test.refresh(property_obj)

    # Update property
    update_data = {
        "placed_in_service": "2025-02-01",
        "status": "ACTIVE",
    }

    response = client.patch(f"/api/v1/properties/{property_obj.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["placed_in_service"] == "2025-02-01"
    assert data["status"] == "ACTIVE"
    # updated_at should be newer than created_at
    assert data["updated_at"] > data["created_at"]


def test_update_property_not_found(client):
    """Test PATCH /api/v1/properties/{id} returns 404 for non-existent property"""
    fake_id = uuid4()

    response = client.patch(f"/api/v1/properties/{fake_id}", json={"status": "ACTIVE"})

    assert response.status_code == 404


# =============================================================================
# DELETE PROPERTY TESTS
# =============================================================================

def test_delete_property(client, session_test):
    """Test DELETE /api/v1/properties/{id} soft deletes property"""
    # Create test property
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
        status=PropertyStatus.ACTIVE,
    )
    session_test.add(property_obj)
    session_test.commit()
    session_test.refresh(property_obj)

    # Delete property
    response = client.delete(f"/api/v1/properties/{property_obj.id}")

    assert response.status_code == 204

    # Verify soft delete (status changed to INACTIVE)
    session_test.refresh(property_obj)
    assert property_obj.status == PropertyStatus.INACTIVE


def test_delete_property_not_found(client):
    """Test DELETE /api/v1/properties/{id} returns 404 for non-existent property"""
    fake_id = uuid4()

    response = client.delete(f"/api/v1/properties/{fake_id}")

    assert response.status_code == 404


# =============================================================================
# PROVENANCE TRACKING TESTS
# =============================================================================

def test_property_includes_provenance(client, session_test):
    """Test that property responses include provenance data"""
    # Create property with provenance
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
        provenance={
            "source_type": "manual_entry",
            "source_id": "test_import",
            "confidence": 1.0,
        },
    )
    session_test.add(property_obj)
    session_test.commit()
    session_test.refresh(property_obj)

    # Get property
    response = client.get(f"/api/v1/properties/{property_obj.id}")

    assert response.status_code == 200
    data = response.json()
    assert "provenance" in data
    assert data["provenance"]["source_type"] == "manual_entry"
    assert data["provenance"]["confidence"] == 1.0

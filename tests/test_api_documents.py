"""
Tests for Document metadata API endpoints (database-backed registry)

Tests CRUD operations, filtering, duplicate detection, and archive
(soft delete) behavior via FastAPI test client
"""

import hashlib
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import select

from core.database.models import Property, Document, AuditLog
from core.database.enums import (
    PropertyStatus,
    DocumentType,
    DocumentVersion,
    DocumentConfidentiality,
)


def fake_hash(seed: str) -> str:
    """Deterministic 64-char SHA-256 hex string for tests"""
    return hashlib.sha256(seed.encode()).hexdigest()


@pytest.fixture(name="property_obj")
def property_fixture(session_test):
    """Create a property for documents to reference"""
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


def make_document(**overrides):
    """Build a Document with sensible defaults (LLC-wide, no property)"""
    defaults = dict(
        filename="articles_of_organization.pdf",
        doc_type=DocumentType.FORMATION,
        content_hash=fake_hash("articles"),
        entities=["Poolula LLC"],
    )
    defaults.update(overrides)
    return Document(**defaults)


# =============================================================================
# LIST TESTS
# =============================================================================

def test_list_documents_empty(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_documents(client, session_test):
    session_test.add(make_document())
    session_test.add(make_document(
        filename="travelers_policy_2025.pdf",
        doc_type=DocumentType.INSURANCE_POLICY,
        content_hash=fake_hash("policy"),
    ))
    session_test.commit()

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_documents_filter_by_doc_type(client, session_test):
    session_test.add(make_document())
    session_test.add(make_document(
        filename="travelers_policy_2025.pdf",
        doc_type=DocumentType.INSURANCE_POLICY,
        content_hash=fake_hash("policy"),
    ))
    session_test.commit()

    # Value form (with colon)
    response = client.get("/api/v1/documents?doc_type=insurance:policy")
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_type"] == "insurance:policy"

    # Name form
    response = client.get("/api/v1/documents?doc_type=FORMATION")
    assert len(response.json()) == 1


def test_list_documents_filename_search(client, session_test):
    session_test.add(make_document())
    session_test.add(make_document(
        filename="travelers_policy_2025.pdf",
        doc_type=DocumentType.INSURANCE_POLICY,
        content_hash=fake_hash("policy"),
    ))
    session_test.commit()

    response = client.get("/api/v1/documents?search=TRAVELERS")
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "travelers_policy_2025.pdf"


def test_list_documents_filter_by_property(client, session_test, property_obj):
    session_test.add(make_document())  # LLC-wide
    session_test.add(make_document(
        filename="settlement_statement.pdf",
        doc_type=DocumentType.CLOSING,
        content_hash=fake_hash("closing"),
        property_id=property_obj.id,
    ))
    session_test.commit()

    response = client.get(f"/api/v1/documents?property_id={property_obj.id}")
    data = response.json()
    assert len(data) == 1
    assert data[0]["property_id"] == str(property_obj.id)


def test_list_documents_invalid_doc_type(client):
    response = client.get("/api/v1/documents?doc_type=nonsense")
    assert response.status_code == 422


# =============================================================================
# CREATE TESTS
# =============================================================================

def test_create_document(client, session_test):
    payload = {
        "filename": "operating_agreement.pdf",
        "doc_type": "operating_agreement",
        "content_hash": fake_hash("oa"),
        "entities": ["Poolula LLC", "Hidalgo-Sotelo Living Trust"],
        "effective_date": "2024-05-15",
        "provenance": {"source_type": "manual_entry", "source_id": "test"},
    }
    response = client.post("/api/v1/documents", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "operating_agreement.pdf"
    assert data["doc_type"] == "operating_agreement"
    assert data["version"] == "final"
    assert data["confidentiality"] == "internal"

    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].entity_type == "Document"


def test_create_document_duplicate_hash_rejected(client, session_test):
    doc = make_document()
    session_test.add(doc)
    session_test.commit()

    payload = {
        "filename": "articles_copy.pdf",
        "doc_type": "formation",
        "content_hash": doc.content_hash,
    }
    response = client.post("/api/v1/documents", json=payload)
    assert response.status_code == 409


def test_create_document_invalid_hash(client):
    payload = {
        "filename": "bad_hash.pdf",
        "doc_type": "formation",
        "content_hash": "nothex",
    }
    response = client.post("/api/v1/documents", json=payload)
    assert response.status_code == 422


def test_create_document_missing_property(client):
    payload = {
        "filename": "orphan.pdf",
        "doc_type": "formation",
        "content_hash": fake_hash("orphan"),
        "property_id": str(uuid4()),
    }
    response = client.post("/api/v1/documents", json=payload)
    assert response.status_code == 404


# =============================================================================
# GET BY ID TESTS
# =============================================================================

def test_get_document(client, session_test):
    doc = make_document()
    session_test.add(doc)
    session_test.commit()

    response = client.get(f"/api/v1/documents/{doc.id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "articles_of_organization.pdf"


def test_get_document_not_found(client):
    response = client.get(f"/api/v1/documents/{uuid4()}")
    assert response.status_code == 404


# =============================================================================
# UPDATE TESTS
# =============================================================================

def test_update_document(client, session_test):
    doc = make_document()
    session_test.add(doc)
    session_test.commit()

    response = client.patch(
        f"/api/v1/documents/{doc.id}",
        json={"confidentiality": "restricted", "effective_date": "2024-06-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["confidentiality"] == "restricted"
    assert data["effective_date"] == "2024-06-01"

    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].old_value["confidentiality"] == "internal"


def test_update_document_not_found(client):
    response = client.patch(
        f"/api/v1/documents/{uuid4()}", json={"filename": "nope.pdf"}
    )
    assert response.status_code == 404


# =============================================================================
# ARCHIVE (SOFT DELETE) TESTS
# =============================================================================

def test_archive_document(client, session_test):
    doc = make_document()
    session_test.add(doc)
    session_test.commit()

    response = client.delete(f"/api/v1/documents/{doc.id}")
    assert response.status_code == 204

    # Record still exists with ARCHIVED version
    session_test.refresh(doc)
    assert doc.version == DocumentVersion.ARCHIVED

    # Excluded from default listing
    response = client.get("/api/v1/documents")
    assert response.json() == []

    # Included when requested
    response = client.get("/api/v1/documents?include_archived=true")
    assert len(response.json()) == 1


def test_archive_document_not_found(client):
    response = client.delete(f"/api/v1/documents/{uuid4()}")
    assert response.status_code == 404


def test_update_document_invalid_filename_returns_422(client, session_test):
    """Model-level validation failures on update surface as 422, not 500"""
    doc = make_document()
    session_test.add(doc)
    session_test.commit()

    response = client.patch(
        f"/api/v1/documents/{doc.id}",
        json={"filename": "x" * 300},  # exceeds 255-char limit
    )
    assert response.status_code == 422

    # Document unchanged
    session_test.refresh(doc)
    assert doc.filename == "articles_of_organization.pdf"

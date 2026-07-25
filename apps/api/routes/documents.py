"""
Document metadata CRUD endpoints (database-backed)

Provides REST API for the document registry stored in the `documents` table.
This is distinct from GET /api/documents (chat router), which lists documents
in the ChromaDB vector store; rows here are the system-of-record metadata with
provenance, and are created automatically when files are processed through
POST /api/process-incoming.

Conventions:
- Enum inputs accept both names (INSURANCE_POLICY) and values (insurance:policy);
  responses emit enum values.
- DELETE soft-deletes by setting version=ARCHIVED. Archived documents are
  excluded from listings unless include_archived=true.
- property_id is optional: LLC-wide documents (formation docs, etc.) have none.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel, field_validator

from core.database.connection import get_session
from core.database.models import Property, Document
from core.database.enums import DocumentType, DocumentVersion, DocumentConfidentiality
from core.logging_config import get_logger
from apps.api.routes.common import parse_enum, parse_enum_for_validator, record_audit

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DocumentCreate(BaseModel):
    """Request model for registering a document's metadata"""
    filename: str
    doc_type: DocumentType
    content_hash: str  # SHA-256 hex of file content
    property_id: Optional[UUID] = None
    effective_date: Optional[date] = None
    entities: List[str] = []
    version: DocumentVersion = DocumentVersion.FINAL
    confidentiality: DocumentConfidentiality = DocumentConfidentiality.INTERNAL
    provenance: Dict[str, Any] = {}
    extra_metadata: Dict[str, Any] = {}

    @field_validator('doc_type', mode='before')
    @classmethod
    def parse_doc_type(cls, v):
        return parse_enum_for_validator(DocumentType, v)

    @field_validator('version', mode='before')
    @classmethod
    def parse_version(cls, v):
        return parse_enum_for_validator(DocumentVersion, v)

    @field_validator('confidentiality', mode='before')
    @classmethod
    def parse_confidentiality(cls, v):
        return parse_enum_for_validator(DocumentConfidentiality, v)


class DocumentUpdate(BaseModel):
    """Request model for updating document metadata"""
    filename: Optional[str] = None
    doc_type: Optional[DocumentType] = None
    property_id: Optional[UUID] = None
    effective_date: Optional[date] = None
    entities: Optional[List[str]] = None
    version: Optional[DocumentVersion] = None
    confidentiality: Optional[DocumentConfidentiality] = None
    provenance: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

    @field_validator('doc_type', mode='before')
    @classmethod
    def parse_doc_type(cls, v):
        return parse_enum_for_validator(DocumentType, v)

    @field_validator('version', mode='before')
    @classmethod
    def parse_version(cls, v):
        return parse_enum_for_validator(DocumentVersion, v)

    @field_validator('confidentiality', mode='before')
    @classmethod
    def parse_confidentiality(cls, v):
        return parse_enum_for_validator(DocumentConfidentiality, v)


def _require_property(session: Session, property_id: UUID) -> Property:
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")
    return property_obj


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/documents", response_model=List[Document])
def list_documents(
    property_id: Optional[UUID] = Query(None, description="Filter by property"),
    doc_type: Optional[str] = Query(None, description="Filter by document type (name or value, e.g. INSURANCE_POLICY or insurance:policy)"),
    search: Optional[str] = Query(None, description="Case-insensitive substring match on filename"),
    confidentiality: Optional[str] = Query(None, description="Filter by confidentiality (public, internal, restricted)"),
    include_archived: bool = Query(False, description="Include archived documents"),
    session: Session = Depends(get_session),
) -> List[Document]:
    """
    List registered documents, newest first, with optional filters.

    Example:
        >>> GET /api/v1/documents?doc_type=formation
        >>> GET /api/v1/documents?search=insurance
    """
    logger.info(
        f"Listing documents (property={property_id}, doc_type={doc_type}, search={search})"
    )

    query = select(Document)
    if property_id:
        query = query.where(Document.property_id == property_id)
    if doc_type:
        query = query.where(Document.doc_type == parse_enum(DocumentType, doc_type, "doc_type"))
    if search:
        query = query.where(Document.filename.ilike(f"%{search}%"))
    if confidentiality:
        query = query.where(
            Document.confidentiality == parse_enum(DocumentConfidentiality, confidentiality, "confidentiality")
        )
    if not include_archived:
        query = query.where(Document.version != DocumentVersion.ARCHIVED)
    query = query.order_by(Document.created_at.desc())

    documents = session.exec(query).all()
    logger.info(f"Found {len(documents)} documents")
    return documents


@router.post("/documents", response_model=Document, status_code=201)
def create_document(
    document_data: DocumentCreate,
    session: Session = Depends(get_session),
) -> Document:
    """
    Register a document's metadata

    Registers metadata only; file content lives on the filesystem and in the
    vector store (see POST /api/upload + /api/process-incoming for the full
    ingestion path). Duplicate content hashes are rejected with 409.
    """
    if document_data.property_id:
        _require_property(session, document_data.property_id)

    # Reject duplicates by content hash (normalized to lowercase by the model)
    existing = session.exec(
        select(Document).where(Document.content_hash == document_data.content_hash.lower())
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Document with identical content already registered: {existing.filename} ({existing.id})",
        )

    try:
        document = Document(**document_data.model_dump())
    except ValueError as e:
        # Model-level validation (e.g. malformed content_hash)
        raise HTTPException(status_code=422, detail=str(e))

    try:
        session.add(document)
        record_audit(session, "INSERT", document, reason="Registered via REST API")
        session.commit()
        session.refresh(document)
        logger.info(f"✅ Document registered: {document.id} ({document.filename})")
        return document
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to register document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register document: {str(e)}")


@router.get("/documents/{document_id}", response_model=Document)
def get_document(
    document_id: UUID,
    session: Session = Depends(get_session),
) -> Document:
    """Get a single document's metadata by ID (404 if not found)"""
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    return document


@router.patch("/documents/{document_id}", response_model=Document)
def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    session: Session = Depends(get_session),
) -> Document:
    """
    Update document metadata

    Only provided fields are changed; the change is recorded in the audit log.
    content_hash is immutable (re-ingest the file to change content).
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    update_data = document_update.model_dump(exclude_unset=True)
    if update_data.get("property_id"):
        _require_property(session, update_data["property_id"])

    old_value = document.model_dump(mode="json")

    try:
        for field, value in update_data.items():
            setattr(document, field, value)
    except ValueError as e:
        # Model-level validation (validate_assignment), e.g. filename too long
        session.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    document.updated_at = datetime.utcnow()

    try:
        session.add(document)
        record_audit(session, "UPDATE", document, reason="Updated via REST API", old_value=old_value)
        session.commit()
        session.refresh(document)
        logger.info(f"✅ Document updated: {document_id}")
        return document
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


@router.delete("/documents/{document_id}", status_code=204)
def archive_document(
    document_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    """
    Soft delete a document by setting version to ARCHIVED

    The file itself and any vector store entries are not removed.
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    old_value = document.model_dump(mode="json")
    document.version = DocumentVersion.ARCHIVED
    document.updated_at = datetime.utcnow()

    session.add(document)
    record_audit(session, "UPDATE", document, reason="Archived (soft delete) via REST API", old_value=old_value)
    session.commit()
    logger.info(f"✅ Document archived: {document_id}")

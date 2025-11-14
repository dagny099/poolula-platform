from typing import List, Dict, Optional, Literal
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Document type enumeration based on Poolula requirements
class DocumentType(str, Enum):
    """Enumeration of supported document types for business documents"""
    FORMATION = "formation"
    AUTHORITY = "authority"
    DEED = "deed"
    INSURANCE = "insurance"
    BANKING = "banking"
    ACCOUNTING = "accounting"
    MINUTES = "minutes"
    CONSENT = "consent"
    COMPLIANCE = "compliance"
    LEASE = "lease"
    VENDOR = "vendor"
    TAX = "tax"
    INDEX = "index"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid document type"""
        return value in [item.value for item in cls]

# Version status enumeration
class VersionStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"

# Confidentiality level enumeration
class ConfidentialityLevel(str, Enum):
    INTERNAL = "internal"
    RESTRICTED = "restricted"

class BusinessDocument(BaseModel):
    """Represents a business document with rich metadata for Poolula LLC"""
    # Basic file information
    title: str                                    # Document title/filename
    file_path: str                               # Path to the original file
    file_type: str                               # File extension: 'pdf', 'docx', 'txt', 'xlsx', 'csv'
    created_date: Optional[datetime] = None       # When document was created
    file_size: Optional[int] = None              # File size in bytes
    content_hash: Optional[str] = None           # SHA-256 hash for deduplication
    
    # Business document classification (from PRD requirements)
    doc_type: DocumentType                       # Business document classification
    effective_date: Optional[datetime] = None    # When document becomes effective
    entities: List[str] = []                     # Related entities (LLC, Trust, individuals)
    address: Optional[str] = None                # Property/business address if applicable
    version: VersionStatus = VersionStatus.FINAL # Document version status
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL  # Access level
    notes: Optional[str] = None                  # Additional notes or comments
    
    # Legacy metadata field for backward compatibility
    metadata: Dict = {}                          # Additional document metadata

class DocumentChunk(BaseModel):
    """Represents a text chunk from a business document for vector storage"""
    content: str                          # The actual text content
    document_title: str                   # Which document this chunk belongs to
    file_type: str                        # File extension: 'pdf', 'docx', 'txt', 'xlsx', 'csv'
    doc_type: DocumentType                # Business document classification
    section_title: Optional[str] = None   # Section or heading this chunk is from
    chunk_index: int                      # Position of this chunk in the document
    
    # Enhanced source attribution
    page_number: Optional[int] = None     # Page number for PDFs
    sheet_name: Optional[str] = None      # Sheet name for Excel files
    cell_range: Optional[str] = None      # Cell range for Excel data (e.g., "A1:C10")
    row_number: Optional[int] = None      # Row number for CSV/Excel
    
    # Business metadata for filtering
    effective_date: Optional[datetime] = None  # Document effective date
    entities: List[str] = []              # Related entities
    version: VersionStatus = VersionStatus.FINAL  # Document version status

class DocumentMetadata(BaseModel):
    """Metadata structure for CSV-based document ingestion"""
    doc_id: str                           # Filename/document identifier
    title: str                            # Human-readable title
    doc_type: DocumentType                # Business document classification
    effective_date: Optional[datetime] = None  # When document becomes effective
    entities: List[str] = []              # Related entities (array)
    address: Optional[str] = None         # Property/business address
    version: VersionStatus = VersionStatus.FINAL  # Document version status
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL  # Access level
    notes: Optional[str] = None           # Additional notes

class QueryFilter(BaseModel):
    """Filters for structured document search"""
    doc_types: Optional[List[DocumentType]] = None  # Filter by document types
    entities: Optional[List[str]] = None             # Filter by entities
    address: Optional[str] = None                    # Filter by address
    date_from: Optional[datetime] = None             # Filter by effective date range
    date_to: Optional[datetime] = None               # Filter by effective date range
    version: Optional[VersionStatus] = None          # Filter by version status
    confidentiality: Optional[ConfidentialityLevel] = None  # Filter by access level
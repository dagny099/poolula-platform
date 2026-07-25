"""
Document upload and incoming-file processing

Implements the vertical slice behind the chat router's document endpoints:

1. POST /api/upload           -> save_upload_file()      (file lands in incoming/)
2. GET  /api/incoming-files   -> list_incoming_files()
3. POST /api/process-incoming -> process_incoming_files()
   - chunks + embeds the file into the ChromaDB vector store (same path as
     scripts/ingest_documents.py, no LLM required)
   - registers a Document row in the database with content hash + provenance
   - moves the file to processed/ so it is not re-processed

Duplicates are detected by SHA-256 content hash against both the vector store
and the documents table; duplicate files are moved aside and reported as skipped.

Storage is plain local filesystem (documents/incoming and documents/processed
by default, overridable via POOLULA_INCOMING_DIR / POOLULA_PROCESSED_DIR).
"""

import os
import re
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from core.database.models import Document, create_provenance
from core.database.enums import DocumentType as CoreDocumentType, ProvenanceSourceType
from core.logging_config import get_logger
from apps.api.routes.common import record_audit

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB is plenty for business documents

# The chatbot-side document classifier uses its own type vocabulary
# (apps/chatbot/models.DocumentType); map it onto the core database enum.
CHATBOT_TO_CORE_DOC_TYPE = {
    "formation": CoreDocumentType.FORMATION,
    "authority": CoreDocumentType.AUTHORITY,
    "deed": CoreDocumentType.DEED,
    "insurance": CoreDocumentType.INSURANCE_POLICY,
    "banking": CoreDocumentType.BANK_STATEMENT,
    "accounting": CoreDocumentType.OTHER,
    "minutes": CoreDocumentType.MINUTES,
    "consent": CoreDocumentType.CONSENT,
    "compliance": CoreDocumentType.PERIODIC_REPORT,
    "lease": CoreDocumentType.LEASE,
    "vendor": CoreDocumentType.VENDOR_CONTRACT,
    "tax": CoreDocumentType.TAX_RETURN,
    "index": CoreDocumentType.OTHER,
}

PROVENANCE_BY_EXTENSION = {
    ".pdf": ProvenanceSourceType.PDF_EXTRACT,
    ".csv": ProvenanceSourceType.CSV_IMPORT,
    ".xlsx": ProvenanceSourceType.CSV_IMPORT,
    ".xls": ProvenanceSourceType.CSV_IMPORT,
}


def incoming_dir() -> Path:
    """Directory where uploaded files wait for processing"""
    return Path(os.getenv("POOLULA_INCOMING_DIR", "documents/incoming"))


def processed_dir() -> Path:
    """Directory where files are moved after successful processing"""
    return Path(os.getenv("POOLULA_PROCESSED_DIR", "documents/processed"))


def sanitize_filename(filename: str) -> str:
    """
    Reduce an uploaded filename to a safe basename.

    Strips any path components (defeats ../ traversal) and characters outside
    a conservative whitelist. Raises HTTP 400 if nothing usable remains.
    """
    # Take basename across both separators, then whitelist characters
    basename = Path(filename.replace("\\", "/")).name
    basename = re.sub(r"[^A-Za-z0-9._\- ()]", "_", basename).strip()
    if not basename or basename.startswith("."):
        raise HTTPException(status_code=400, detail=f"Invalid filename: {filename}")
    return basename


def _unique_destination(directory: Path, filename: str) -> Path:
    """Return a path in directory that does not collide with existing files"""
    destination = directory / filename
    if not destination.exists():
        return destination
    stem, suffix = Path(filename).stem, Path(filename).suffix
    for i in range(1, 1000):
        candidate = directory / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise HTTPException(status_code=500, detail=f"Could not find unique name for {filename}")


async def save_upload_file(upload: UploadFile) -> str:
    """
    Save an uploaded file into the incoming folder.

    Returns the stored filename (may differ from the original if a file with
    that name already exists). Raises 400/413/415 for bad input.
    """
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Upload is missing a filename")

    filename = sanitize_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {extension or '(none)'}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    directory = incoming_dir()
    directory.mkdir(parents=True, exist_ok=True)
    destination = _unique_destination(directory, filename)

    size = 0
    try:
        with open(destination, "wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)} MB",
                    )
                out.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as e:
        destination.unlink(missing_ok=True)
        logger.error(f"Failed to save upload {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    logger.info(f"📥 Upload saved: {destination} ({size} bytes)")
    return destination.name


def list_incoming_files() -> List[str]:
    """List supported files waiting in the incoming folder (sorted by name)"""
    directory = incoming_dir()
    if not directory.exists():
        return []
    return sorted(
        f.name
        for f in directory.iterdir()
        if f.is_file()
        and not f.name.startswith(".")
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# =============================================================================
# INGESTION COMPONENTS (vector store + document processor, no LLM required)
# =============================================================================

_components: Optional[Tuple[Any, Any, Any]] = None


def get_ingest_components() -> Tuple[Any, Any, Any]:
    """
    Lazily build (DocumentProcessor, VectorStore, MetadataManager).

    Imported lazily so that the API can start (and tests can run) without
    loading ChromaDB/embedding dependencies until a file is actually processed.
    Tests replace this via reset_ingest_components(mock_tuple).
    """
    global _components
    if _components is None:
        from apps.chatbot.config import Config
        from apps.chatbot.document_processor import DocumentProcessor
        from apps.chatbot.vector_store import VectorStore
        from apps.chatbot.metadata_manager import MetadataManager

        config = Config()
        _components = (
            DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP),
            VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS),
            MetadataManager(config.METADATA_CSV_PATH),
        )
    return _components


def reset_ingest_components(components: Optional[Tuple[Any, Any, Any]] = None) -> None:
    """Reset or inject ingestion components (used by tests)"""
    global _components
    _components = components


def _to_date(value: Any) -> Optional[date]:
    """Normalize datetime/date metadata values to date for the DB column"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def process_incoming_files(session: Session) -> Dict[str, Any]:
    """
    Process every pending file in the incoming folder.

    For each file:
      1. Extract text + chunks (DocumentProcessor) and compute content hash
      2. Skip if the hash already exists in the vector store or documents table
      3. Add chunks to the vector store and register a Document row (with
         provenance and audit log entry)
      4. Move the file to the processed folder

    Failed files stay in incoming/ so they can be fixed and retried.

    Returns:
        {"message": str, "processed_files": [...], "skipped_files": [...],
         "failed_files": [{"filename": ..., "error": ...}]}
    """
    pending = list_incoming_files()
    if not pending:
        return {
            "message": "No files to process",
            "processed_files": [],
            "skipped_files": [],
            "failed_files": [],
        }

    doc_processor, vector_store, metadata_manager = get_ingest_components()
    out_dir = processed_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    processed: List[str] = []
    skipped: List[str] = []
    failed: List[Dict[str, str]] = []

    for filename in pending:
        file_path = incoming_dir() / filename
        try:
            doc_metadata = metadata_manager.get_metadata_for_file(str(file_path))
            document, chunks = doc_processor.process_business_document(str(file_path), doc_metadata)

            duplicate_in_vector_store = vector_store.document_exists(document.content_hash)
            duplicate_in_db = session.exec(
                select(Document).where(Document.content_hash == document.content_hash)
            ).first() is not None

            if duplicate_in_vector_store and duplicate_in_db:
                logger.info(f"⏭️  Duplicate content, skipping: {filename}")
                shutil.move(str(file_path), str(_unique_destination(out_dir, filename)))
                skipped.append(filename)
                continue

            if not duplicate_in_vector_store:
                vector_store.add_document_metadata(document)
                vector_store.add_document_content(chunks)

            if not duplicate_in_db:
                extension = file_path.suffix.lower()
                db_document = Document(
                    filename=filename,
                    doc_type=CHATBOT_TO_CORE_DOC_TYPE.get(
                        document.doc_type.value, CoreDocumentType.OTHER
                    ),
                    effective_date=_to_date(document.effective_date),
                    entities=document.entities or [],
                    content_hash=document.content_hash,
                    provenance=create_provenance(
                        source_type=PROVENANCE_BY_EXTENSION.get(
                            extension, ProvenanceSourceType.MANUAL_ENTRY
                        ),
                        source_id=filename,
                        created_by="system:incoming_processor",
                        notes="Uploaded via /api/upload, processed by /api/process-incoming",
                    ),
                    extra_metadata={
                        "title": document.title,
                        "file_type": document.file_type,
                        "chunks": len(chunks),
                        "chatbot_doc_type": document.doc_type.value,
                    },
                )
                session.add(db_document)
                record_audit(
                    session,
                    "INSERT",
                    db_document,
                    reason=f"Ingested from incoming folder: {filename}",
                    user="system:incoming_processor",
                )
                session.commit()

            shutil.move(str(file_path), str(_unique_destination(out_dir, filename)))
            processed.append(filename)
            logger.info(f"✅ Processed incoming file: {filename} ({len(chunks)} chunks)")

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to process {filename}: {e}", exc_info=True)
            failed.append({"filename": filename, "error": str(e)})

    parts = []
    if processed:
        parts.append(f"processed {len(processed)}")
    if skipped:
        parts.append(f"skipped {len(skipped)} duplicate(s)")
    if failed:
        parts.append(f"failed {len(failed)}")
    message = f"Successfully {parts[0]} document(s)" if processed else "No new documents processed"
    if len(parts) > 1 or not processed:
        message = "Processing complete: " + ", ".join(parts)

    return {
        "message": message,
        "processed_files": processed,
        "skipped_files": skipped,
        "failed_files": failed,
    }

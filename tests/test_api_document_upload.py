"""
Tests for the document upload / incoming / process-incoming vertical slice

Covers:
- POST /api/upload (happy path, unsupported type, filename sanitization, collisions)
- GET /api/incoming-files
- POST /api/process-incoming (ingestion, DB registration, dedup, file movement)

The vector store is faked so tests need no ChromaDB/embedding models or
network access; text extraction and chunking use the real DocumentProcessor.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import select

from apps.api import ingestion
from apps.chatbot.document_processor import DocumentProcessor
from apps.chatbot.metadata_manager import MetadataManager
from core.database.models import Document, AuditLog


class FakeVectorStore:
    """In-memory stand-in for the ChromaDB-backed VectorStore"""

    def __init__(self):
        self.hashes = set()
        self.documents = []
        self.chunks = []

    def document_exists(self, content_hash: str) -> bool:
        return content_hash in self.hashes

    def add_document_metadata(self, document):
        self.hashes.add(document.content_hash)
        self.documents.append(document)

    def add_document_content(self, chunks):
        self.chunks.extend(chunks)


@pytest.fixture(name="upload_dirs")
def upload_dirs_fixture(tmp_path, monkeypatch):
    """Point incoming/processed folders at a temp directory"""
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    monkeypatch.setenv("POOLULA_INCOMING_DIR", str(incoming))
    monkeypatch.setenv("POOLULA_PROCESSED_DIR", str(processed))
    return incoming, processed


@pytest.fixture(name="fake_components")
def fake_components_fixture(tmp_path):
    """Inject real text processing with a fake vector store"""
    fake_store = FakeVectorStore()
    components = (
        DocumentProcessor(chunk_size=500, chunk_overlap=50),
        fake_store,
        MetadataManager(str(tmp_path / "no_metadata.csv")),  # falls back to inference
    )
    ingestion.reset_ingest_components(components)
    yield fake_store
    ingestion.reset_ingest_components(None)


# =============================================================================
# UPLOAD TESTS
# =============================================================================

def test_upload_file(client, upload_dirs):
    incoming, _ = upload_dirs

    response = client.post(
        "/api/upload",
        files={"file": ("meeting_minutes.txt", b"Annual meeting was held in May.", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "meeting_minutes.txt"
    assert (incoming / "meeting_minutes.txt").read_bytes() == b"Annual meeting was held in May."


def test_upload_unsupported_type(client, upload_dirs):
    response = client.post(
        "/api/upload",
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_name_collision_gets_suffix(client, upload_dirs):
    incoming, _ = upload_dirs

    first = client.post("/api/upload", files={"file": ("notes.txt", b"v1", "text/plain")})
    second = client.post("/api/upload", files={"file": ("notes.txt", b"v2", "text/plain")})

    assert first.json()["filename"] == "notes.txt"
    assert second.json()["filename"] == "notes-1.txt"
    assert (incoming / "notes.txt").read_bytes() == b"v1"
    assert (incoming / "notes-1.txt").read_bytes() == b"v2"


def test_sanitize_filename_strips_path_traversal():
    assert ingestion.sanitize_filename("../../etc/passwd.txt") == "passwd.txt"
    assert ingestion.sanitize_filename("..\\..\\evil.txt") == "evil.txt"
    assert ingestion.sanitize_filename("weird$na;me.pdf") == "weird_na_me.pdf"

    with pytest.raises(HTTPException):
        ingestion.sanitize_filename(".hidden")


# =============================================================================
# INCOMING FILES TESTS
# =============================================================================

def test_incoming_files_empty(client, upload_dirs):
    response = client.get("/api/incoming-files")
    assert response.status_code == 200
    assert response.json() == {"count": 0, "files": []}


def test_incoming_files_lists_pending(client, upload_dirs):
    incoming, _ = upload_dirs
    incoming.mkdir(parents=True)
    (incoming / "b_doc.txt").write_text("beta")
    (incoming / "a_doc.txt").write_text("alpha")
    (incoming / "ignored.zip").write_text("not supported")
    (incoming / ".hidden.txt").write_text("hidden")

    response = client.get("/api/incoming-files")
    data = response.json()
    assert data["count"] == 2
    assert data["files"] == ["a_doc.txt", "b_doc.txt"]


# =============================================================================
# PROCESS-INCOMING TESTS
# =============================================================================

def test_process_incoming_no_files(client, upload_dirs, fake_components):
    response = client.post("/api/process-incoming")
    assert response.status_code == 200
    data = response.json()
    assert data["processed_files"] == []
    assert "No files" in data["message"]


def test_process_incoming_happy_path(client, session_test, upload_dirs, fake_components):
    incoming, processed = upload_dirs
    incoming.mkdir(parents=True)
    (incoming / "operating_notes.txt").write_text(
        "Poolula LLC operating notes. The company operates a rental property in Montrose."
    )

    response = client.post("/api/process-incoming")

    assert response.status_code == 200
    data = response.json()
    assert data["processed_files"] == ["operating_notes.txt"]
    assert data["failed_files"] == []

    # Chunks landed in the vector store
    assert len(fake_components.chunks) > 0
    assert len(fake_components.documents) == 1

    # Document row registered with hash + provenance + audit entry
    docs = session_test.exec(select(Document)).all()
    assert len(docs) == 1
    assert docs[0].filename == "operating_notes.txt"
    assert len(docs[0].content_hash) == 64
    assert docs[0].provenance["created_by"] == "system:incoming_processor"
    audits = session_test.exec(select(AuditLog)).all()
    assert len(audits) == 1

    # File moved out of incoming into processed
    assert not (incoming / "operating_notes.txt").exists()
    assert (processed / "operating_notes.txt").exists()

    # Incoming folder is now empty
    assert client.get("/api/incoming-files").json()["count"] == 0

    # Visible through the document registry API
    listing = client.get("/api/v1/documents").json()
    assert len(listing) == 1
    assert listing[0]["filename"] == "operating_notes.txt"


def test_process_incoming_skips_duplicates(client, session_test, upload_dirs, fake_components):
    incoming, processed = upload_dirs
    incoming.mkdir(parents=True)
    content = "Identical content that should only be ingested once."

    (incoming / "original.txt").write_text(content)
    first = client.post("/api/process-incoming").json()
    assert first["processed_files"] == ["original.txt"]

    # Same content under a different name
    (incoming / "copy.txt").write_text(content)
    second = client.post("/api/process-incoming").json()

    assert second["processed_files"] == []
    assert second["skipped_files"] == ["copy.txt"]

    # Only one Document row, and the duplicate was still moved aside
    docs = session_test.exec(select(Document)).all()
    assert len(docs) == 1
    assert not (incoming / "copy.txt").exists()
    assert (processed / "copy.txt").exists()


def test_process_incoming_failure_keeps_file(client, session_test, upload_dirs, fake_components):
    incoming, _ = upload_dirs
    incoming.mkdir(parents=True)
    # Empty file: DocumentProcessor raises "No content extracted"
    (incoming / "empty.txt").write_text("")

    response = client.post("/api/process-incoming")

    assert response.status_code == 200
    data = response.json()
    assert data["processed_files"] == []
    assert len(data["failed_files"]) == 1
    assert data["failed_files"][0]["filename"] == "empty.txt"

    # File stays in incoming for retry; nothing registered
    assert (incoming / "empty.txt").exists()
    assert session_test.exec(select(Document)).all() == []

# Documents API Reference

API endpoints for managing business documents and metadata.

## Overview

Documents live in **two** places, served by two sets of endpoints:

1. **Document registry (database)** — `/api/v1/documents`: system-of-record metadata rows (`documents` table) with content hash, provenance, and audit trail.
2. **Vector store (ChromaDB)** — `/api/documents` (chat router): titles/metadata of documents ingested for semantic search.

The upload → process pipeline (below) populates **both** automatically.

## Upload & Processing Pipeline

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/api/upload` | Upload a file (multipart) to the incoming folder | ✅ Implemented |
| GET | `/api/incoming-files` | List files waiting to be processed | ✅ Implemented |
| POST | `/api/process-incoming` | Chunk + embed pending files, register metadata, dedupe | ✅ Implemented |

```bash
# 1. Upload a file (pdf, docx, txt, md, xlsx, xls, csv; max 50 MB)
curl -X POST http://localhost:8082/api/upload -F "file=@/path/to/document.pdf"

# 2. See what's pending
curl http://localhost:8082/api/incoming-files

# 3. Process everything pending
curl -X POST http://localhost:8082/api/process-incoming
```

Processing behavior:

- Files are chunked and embedded into the ChromaDB vector store (no LLM call needed).
- A `Document` row is registered in the database with SHA-256 `content_hash`, provenance, and an audit log entry.
- Duplicate content (same hash) is skipped and reported in `skipped_files`.
- Successfully processed files move from `documents/incoming/` to `documents/processed/`; failures stay in incoming for retry and are reported in `failed_files`.
- Folders are configurable via `POOLULA_INCOMING_DIR` / `POOLULA_PROCESSED_DIR`.

## Document Registry Endpoints (database)

**Base URL:** `/api/v1/documents`

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/documents` | List documents with filters | ✅ Implemented |
| GET | `/api/v1/documents/{id}` | Get document metadata by UUID | ✅ Implemented |
| POST | `/api/v1/documents` | Register document metadata | ✅ Implemented |
| PATCH | `/api/v1/documents/{id}` | Update metadata | ✅ Implemented |
| DELETE | `/api/v1/documents/{id}` | Soft delete (sets version=archived) | ✅ Implemented |

### Query Parameters (GET list)

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | UUID | Filter by property |
| `doc_type` | string | Type name or value (`INSURANCE_POLICY` or `insurance:policy`) |
| `search` | string | Case-insensitive substring match on filename |
| `confidentiality` | string | `public`, `internal`, `restricted` |
| `include_archived` | bool | Include archived documents (default false) |

## Document Types

From `core/database/enums.py::DocumentType`:

- **Formation & governance:** `formation`, `authority`, `operating_agreement`, `minutes`, `consent`
- **Property:** `deed`, `closing`
- **Financial:** `bank_statement`, `credit_card_statement`, `invoice`, `receipt`
- **Insurance:** `insurance:policy`, `insurance:declaration`, `insurance:claim`
- **Compliance:** `tax:return`, `tax:extension`, `tax:notice`, `compliance:periodic_report`
- **Contracts:** `lease`, `vendor:contract`
- **Other:** `correspondence`, `other`

Note: the chatbot ingestion pipeline classifies with its own vocabulary (`apps/chatbot/models.py::DocumentType`); the processor maps it to this core enum when registering documents (see `apps/api/ingestion.py::CHATBOT_TO_CORE_DOC_TYPE`).

## Quick Examples

### List Documents

```bash
# All registered documents
curl http://localhost:8082/api/v1/documents

# Filter by type
curl "http://localhost:8082/api/v1/documents?doc_type=formation"

# Search filenames
curl "http://localhost:8082/api/v1/documents?search=insurance"
```

### Register Metadata Manually

```bash
curl -X POST http://localhost:8082/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "operating_agreement.pdf",
    "doc_type": "operating_agreement",
    "content_hash": "<64-char sha256 hex>",
    "entities": ["Poolula LLC"],
    "effective_date": "2024-05-15"
  }'
```

Duplicate content hashes are rejected with HTTP 409.

## Document Schema

**Key fields:**

- `id` - UUID primary key
- `property_id` - FK to property (nullable for LLC-wide documents)
- `filename` - Original filename
- `doc_type` - Document type (core enum)
- `effective_date` - When document became effective
- `entities` - Legal entities mentioned (JSON array)
- `version` - `draft`, `final`, `superseded`, `archived`
- `confidentiality` - `public`, `internal`, `restricted`
- `content_hash` - SHA-256 hash for deduplication
- `provenance` - Data lineage tracking (JSON)
- `extra_metadata` - Flexible JSON (title, file type, chunk count for ingested docs)

## Bulk Ingestion (script)

```bash
# Ingest all documents in documents/ directory into the vector store
uv run python scripts/ingest_documents.py

# List ingested documents / show stats
uv run python scripts/ingest_documents.py --list
uv run python scripts/ingest_documents.py --stats
```

Note: the script ingests into the vector store only; the API pipeline (`/api/process-incoming`) also registers database rows.

## Document Search

Documents are searchable via the Chatbot API:

```bash
curl -X POST http://localhost:8082/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our business purpose in the operating agreement?"}'
```

The chatbot uses semantic search to find relevant document passages, and returns source attributions (document title, page/sheet/row) in the `sources` array.

## Related Documentation

- [Document Management](../user-guide/document-management.md) - Complete document guide
- Document ingestion: `scripts/ingest_documents.py`
- [Chatbot Document Queries](../user-guide/chatbot.md#document-questions) - Querying documents

---

**Status:** ✅ Implemented (tests: `tests/test_api_documents.py`, `tests/test_api_document_upload.py`)

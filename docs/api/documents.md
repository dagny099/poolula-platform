# Documents API Reference

*Coming soon*

API endpoints for managing business documents and metadata.

## Overview

The Documents API allows you to manage document metadata, track document versions, and integrate with the document ingestion pipeline.

**Base URL:** `/api/v1/documents`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/documents` | List all documents | 🚧 Planned |
| GET | `/api/v1/documents/{id}` | Get document metadata | 🚧 Planned |
| POST | `/api/v1/documents` | Upload document | 🚧 Planned |
| PATCH | `/api/v1/documents/{id}` | Update metadata | 🚧 Planned |
| DELETE | `/api/v1/documents/{id}` | Soft delete document | 🚧 Planned |

## Document Types

**Formation:**

- `formation:articles` - Articles of Organization

- `formation:operating_agreement` - Operating Agreement

- `formation:ein_letter` - IRS EIN confirmation

**Authority:**

- `authority:resolution` - Board resolutions

- `authority:meeting_minutes` - Meeting minutes

- `authority:signature_card` - Bank signature cards

**Accounting:**

- `accounting:bank_statement` - Monthly bank statements

- `accounting:tax_return` - Annual tax returns

- `accounting:invoice` - Invoices and receipts

**Property:**

- `property:deed` - Property deed

- `property:title` - Title documents

- `property:appraisal` - Property appraisal

- `property:inspection` - Inspection reports

**Insurance:**

- `insurance:policy` - Insurance policies

- `insurance:claim` - Insurance claims

**Other:**

- `index` - Reference documents, guides

- `other` - Miscellaneous documents

## Quick Examples

### List Documents

```bash
# All documents
curl http://localhost:8082/api/v1/documents

# Filter by type
curl http://localhost:8082/api/v1/documents?doc_type=formation:articles
```

### Get Document Metadata

```bash
curl http://localhost:8082/api/v1/documents/{document-uuid}
```

### Upload Document

```bash
curl -X POST http://localhost:8082/api/v1/documents \
  -F "file=@/path/to/document.pdf" \
  -F "doc_type=accounting:bank_statement" \
  -F "title=Bank Statement August 2024" \
  -F "doc_date=2024-08-31"
```

## Document Schema

**Key fields:**

- `id` - UUID primary key

- `filename` - Original filename

- `doc_type` - Document type (enum)

- `title` - Human-readable title

- `doc_date` - Document date (not upload date)

- `version` - Version status (draft, final, superseded)

- `content_hash` - SHA-256 hash for deduplication

- `is_searchable` - Ingested into vector store

- `provenance` - Data lineage tracking

- `extra_metadata` - Flexible JSON for custom fields

## Document Ingestion

**For bulk document ingestion, use the ingestion script:**

```bash
# Ingest all documents in documents/ directory
uv run python scripts/ingest_documents.py --ingest

# Show ingestion stats
uv run python scripts/ingest_documents.py --stats
```

**See:** [Document Management Guide](../user-guide/document-management.md)

## Document Search

**Documents are searchable via the Chatbot API:**

```bash
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is our business purpose in the operating agreement?"
  }'
```

**The chatbot uses semantic search to find relevant document passages.**

## Related Documentation

- [Document Management](../user-guide/document-management.md) - Complete document guide

- [Ingestion Script](../../scripts/ingest_documents.py) - Document ingestion tool

- [Chatbot Document Queries](../user-guide/chatbot.md#document-questions) - Querying documents

---

**Status:** 🚧 Planned for Phase 3

**Current:** Document ingestion works via script, API endpoints coming in Phase 3.

# Poolula Platform - Claude Code Guide

This document provides context for Claude Code (AI coding assistant) working on Poolula Platform.

## Project Overview

**Poolula Platform** is a unified management platform for Poolula LLC operations, combining:
- Property & financial tracking
- AI-powered chatbot assistant
- Analytics dashboard
- Compliance calendar

**Scale**: Small deployment (1-few users, not enterprise)
**Principles**: UNDERSTANDING, TRANSPARENCY, USER FRIENDLINESS

## Technology Stack

### Core

- **Python 3.13+** with `uv` package manager
- **FastAPI** - REST API framework
- **SQLModel** - Type-safe ORM (SQLAlchemy + Pydantic)
- **SQLite** (development) → PostgreSQL (production scaling)
- **Alembic** - Database migrations

### Testing

- **pytest** with ≥80% coverage target
- **In-memory SQLite** for test database
- **FastAPI TestClient** for API testing

### AI & RAG (Phase 2+)

- **Anthropic Claude** - AI generation
- **ChromaDB** - Vector database
- **Sentence Transformers** - Embeddings

Note: AI/RAG dependencies are in optional `rag` dependency group (not installed by default).

### Frontend (Phase 4)

- Vue 3 + TypeScript
- Integration with existing ragchatbot-codebase

## Project Structure

```
poolula-platform/
├── core/                      # Core business logic
│   ├── database/              # Database models & connection
│   │   ├── models.py          # SQLModel models
│   │   ├── enums.py           # Enum definitions
│   │   └── connection.py      # DB connection management
│   └── logging_config.py      # Structured logging
├── apps/                      # Applications
│   └── api/                   # FastAPI REST API
│       ├── main.py            # FastAPI app
│       └── routes/            # API endpoints
│           └── properties.py  # Property CRUD
├── scripts/                   # Utility scripts
│   ├── backup.py              # Database backup utility
│   └── seed_database.py       # Import from poolula_facts.yml
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_models.py         # Model tests
│   └── test_api_properties.py # API tests
├── docs/                      # Documentation
│   ├── planning/              # Implementation plans
│   └── workflows/             # Workflow guides
│       ├── data-import.md     # YAML → DB workflow
│       ├── api-usage.md       # API endpoint guide
│       └── testing.md         # Test execution guide
├── alembic/                   # Database migrations
├── pyproject.toml             # Project config & dependencies
└── README.md                  # Getting started guide
```

## Database Schema

### 5 Core Tables

1. **properties** - Rental properties (acquisition, basis, depreciation)
2. **transactions** - Financial events (30+ category chart of accounts)
3. **documents** - Document metadata (PDFs, contracts, statements)
4. **obligations** - Compliance calendar (RRULE recurrence)
5. **audit_log** - Immutable change tracking

### Key Design Decisions

- **UUID primary keys** for all entities
- **Embedded provenance** tracking (JSON column, not separate table)
- **Timestamps** (created_at, updated_at) on all mutable tables
- **Soft deletes** (status=INACTIVE, not hard delete)
- **Direct SQLModel usage** (no repository pattern for simplicity)

### Important Field Naming

- **`extra_metadata`** (not `metadata` - SQLAlchemy reserved word)
- **`property_obj`** (not `property` - avoid shadowing @property decorator)

## API Endpoints

### Base URL: `http://localhost:8082`

### Property Endpoints

- `GET /health` - Health check + DB connection test
- `GET /api/v1/properties` - List properties (optional status filter)
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get single property
- `PATCH /api/v1/properties/{id}` - Update property (fully flexible for now)
- `DELETE /api/v1/properties/{id}` - Soft delete (status=INACTIVE)

### Response Format

All responses include full provenance tracking:

```json
{
  "id": "...",
  "address": "900 S 9th St, Montrose, CO 81401",
  "provenance": {
    "source_type": "manual_entry",
    "confidence": 1.0,
    "verification_status": "unverified"
  }
}
```

## Data Source of Truth

**File**: `/Users/barbaraihidalgo-sotelo/PROJECTS/AirBnB Dashboard/poolula_facts.yml`

This YAML file is the **single source of truth** for property and LLC data.

### UNKNOWN Field Handling

- Fields marked `"UNKNOWN"` in YAML → `NULL` in database
- Query incomplete data: `SELECT * FROM properties WHERE placed_in_service IS NULL`
- Update workflow: Edit YAML → run `uv run python scripts/seed_database.py --update`

See: `docs/workflows/data-import.md` for complete workflow

## Workflows

Detailed workflow documentation:

- **Data Import**: `docs/workflows/data-import.md` - YAML → DB workflow
- **API Usage**: `docs/workflows/api-usage.md` - API endpoint examples
- **Testing**: `docs/workflows/testing.md` - Test execution guide

## Common Commands

### Setup

```bash
# Install dependencies
uv sync

# Run migrations
.venv/bin/alembic upgrade head

# Seed database
uv run python scripts/seed_database.py --initial
```

### Development

```bash
# Start API server
uv run uvicorn apps.api.main:app --reload --port 8082

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=core --cov=apps --cov-report=html

# Create database migration
.venv/bin/alembic revision --autogenerate -m "Description"

# Apply migrations
.venv/bin/alembic upgrade head
```

### Backup & Restore

```bash
# Create backup
python scripts/backup.py

# List backups
python scripts/backup.py --list

# Restore latest
python scripts/backup.py --restore latest
```

## Development Principles

### Simplicity Over Enterprise Patterns

- **Direct SQLModel usage** - No repository layer (KISS principle)
- **Inline documentation** - MkDocs deferred to Phase 4
- **Small scale** - Optimized for 1-few users, not millions

### Provenance Tracking

Every data modification includes provenance:
- `source_type`: How was data created (manual_entry, csv_import, etc.)
- `source_id`: Which file/document (e.g., "poolula_facts.yml")
- `confidence`: 0.0-1.0 confidence level
- `verification_status`: Has this been verified?

### Validation Strategy

- **PATCH allows all fields** - Fully flexible for now (trustee is sole user)
- **TODO Phase 5**: Add protection for immutable fields (acquisition_date, basis)
- **Rationale**: Flexibility > protection at small scale

## Implementation Plan

16-week roadmap (see `docs/planning/2025-11-13-revised-implementation-plan.md`):

- **Phase 0** ✅ - Infrastructure (backup, logging)
- **Phase 1** ✅ - Database schema, API, tests, seed script
- **Phase 2** (Weeks 3-4) - Chatbot integration
- **Phase 3** (Week 5) - Dashboard migration
- **Phase 4** (Weeks 6-7) - Frontend unification
- **Phase 5** (Weeks 8-16) - Feature expansion
- **Phase 6** (Week 17) - Evaluation dashboard
- **Phase 7+** - Neo4j integration (learning/exploration)

## Known Technical Decisions

### Why SQLite Not PostgreSQL?

- SQLite perfect for 1-few users
- Can migrate to PostgreSQL later with Alembic
- Simpler setup and maintenance

### Why No Repository Pattern?

- Adds complexity without benefit at this scale
- SQLModel already provides clean abstraction
- Direct usage is more transparent
- Can refactor to repositories in Phase 5 if needed

### Why Embedded Provenance?

- Performance (one less JOIN)
- Simpler queries
- Appropriate for scale
- Still provides full data lineage

## Migration Context

Integrating three existing projects:

1. **AirBnB Dashboard** (`/PROJECTS/AirBnB Dashboard/`) - Streamlit analytics
2. **RAG Chatbot** (`/PROJECTS/ragchatbot-codebase/`) - FastAPI/ChromaDB/Claude
3. **Evaluation Harness** - Golden Q&A sets for testing

Phase 2-3 will migrate these into the unified platform.

## Contact & Support

- **Project Owner**: Poolula LLC (Hidalgo-Sotelo Living Trust)
- **Development**: Solo developer (trustee)
- **Questions**: Refer to workflow docs in `docs/workflows/`

## Quick Reference

### Key Files

- **API**: `apps/api/main.py`, `apps/api/routes/properties.py`
- **Models**: `core/database/models.py`, `core/database/enums.py`
- **Connection**: `core/database/connection.py`
- **Seed Script**: `scripts/seed_database.py`
- **Tests**: `tests/test_models.py`, `tests/test_api_properties.py`

### Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./poolula.db  # or postgresql://...

# API
API_HOST=0.0.0.0
API_PORT=8082
API_RELOAD=true

# Logging
DEBUG=false
```

See `.env.example` for full list.

## Next Steps

When continuing work:

1. Check `docs/planning/2025-11-13-revised-implementation-plan.md` for current phase
2. Review relevant workflow docs in `docs/workflows/`
3. Run tests to ensure nothing broke: `uv run pytest`
4. Start API server: `uv run uvicorn apps.api.main:app --reload --port 8082`

For detailed implementation guidance, see the planning document and workflow guides.

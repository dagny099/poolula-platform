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

### AI & RAG

- **LLM Provider Architecture** - Provider-agnostic abstraction layer for multiple LLM backends
  - **Anthropic Claude** (default) - Primary AI generation (via anthropic>=0.58.2)
  - **OpenAI** (optional) - Alternative provider support
  - **Local Models** (optional) - Ollama integration for offline/privacy use
- **ChromaDB** - Vector database with ONNX embeddings (chromadb>=1.0.15)
- **DSPy** - Prompt optimization and pipeline framework (dspy-ai==2.5.0)
- **MLflow** - Experiment tracking and model registry (mlflow>=2.16.2)

**Important**: ChromaDB's built-in ONNX embeddings avoid PyTorch dependency issues on macOS Intel x86_64 with Python 3.13.

Note: AI dependencies are in optional `rag` dependency group. Install with `uv sync --group rag`.

### Evaluation & Observability

- **pytest** - Traditional unit/integration tests
- **Evaluation Harnesses** - Two specialized evaluation systems:
  - **General Evaluator** (`evaluate_chatbot.py`) - 5 cross-domain business questions
  - **Airbnb Evaluator** (`evaluate_airbnb.py`) - 15 rental income questions with CSV ground truth validation
- **Automated Scoring** - Multi-dimensional scoring:
  - Tool usage correctness (40%)
  - Content relevance (40%)
  - Numerical accuracy (50% for Airbnb evaluator - validates against source CSV data with 1% tolerance)
  - Completeness (10%)
  - Target: ≥90% overall score
- **Ground Truth Validation** - Airbnb evaluator compares chatbot responses against CSV calculations (accrual accounting with checkout date revenue recognition)
- **Audit Logging** - All chatbot interactions logged to database

See `docs/evaluation/` for framework details.

### Frontend

- **Vanilla JavaScript** - Clean, framework-free web interface
- HTML5 + CSS3
- Marked.js for markdown rendering
- 4 persona-based help sections (LLC Owner, Bookkeeper, Property Manager, Compliance Officer)

## Project Structure

```
poolula-platform/
├── core/                      # Core business logic
│   ├── database/              # Database models & connection (models.py, enums.py, connection.py)
│   └── logging_config.py      # Structured logging
├── apps/                      # Applications
│   ├── api/                   # FastAPI REST API
│   │   ├── main.py            # FastAPI app
│   │   └── routes/            # API endpoints (properties, transactions, documents, obligations, chat)
│   ├── chatbot/               # RAG Chatbot
│   │   ├── llm_providers/     # LLM provider abstraction (base, anthropic, openai, ollama)
│   │   ├── rag_system.py      # Main orchestrator with provider factory
│   │   ├── ai_generator.py    # Provider-agnostic AI generation
│   │   ├── vector_store.py    # ChromaDB interface
│   │   ├── database_tool.py   # Database query tool for structured data
│   │   ├── search_tools.py    # Document search tools
│   │   ├── session_manager.py # Conversation history
│   │   ├── audit_logger.py    # Q&A audit logging
│   │   └── [other modules]    # cache, metadata, document processing, config, health
│   ├── dspy/                  # DSPy pipeline integration
│   │   ├── pipelines.py       # Q&A pipeline definitions
│   │   ├── artifacts.py       # Artifact management
│   │   └── runtime.py         # Pipeline execution
│   └── evaluator/             # Evaluation harness components
├── scripts/                   # Utility scripts (15 total)
│   ├── cli.py                 # Main CLI (`poolula` command)
│   ├── backup.py, seed_database.py, seed_obligations.py
│   ├── import_airbnb_transactions.py, ingest_documents.py
│   ├── evaluate_chatbot.py, evaluate_airbnb.py, evaluate_providers.py
│   ├── verify_airbnb_import.py, remove_duplicate_transactions.py
│   └── [dspy/mlflow scripts]  # build_dspy_artifact, dspy_mlflow_run, eval_dspy_vs_baseline, make_dummy_dspy_artifact
├── tests/                     # Test suite (≥80% coverage)
│   ├── test_models.py, test_api_properties.py, conftest.py
│   └── chatbot/               # Chatbot tests (test_rag_system, test_session_manager, etc.)
├── docs/                      # Documentation (46 files - see MkDocs)
│   ├── api/                   # API docs (6 files: properties, transactions, documents, obligations, chat, overview)
│   ├── architecture/          # System design, data models, LLM providers (7 files)
│   ├── evaluation/            # Evaluation framework, scoring, provider comparison (9 files)
│   ├── getting-started/       # Installation, overview, quick start (3 files)
│   ├── user-guide/            # Chatbot, document management, importing data, obligations (4 files)
│   ├── planning/              # Implementation plans - LLM agnosticism, DSPy/MLflow (6 files)
│   ├── testing/               # Testing guide, migrations, deployment (3 files)
│   └── workflows/             # Data import, API usage, testing, Airbnb import, LLM provider setup (5 files)
├── alembic/                   # Database migrations
└── pyproject.toml             # Dependencies with groups: dev, rag, docs, openai, local
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

**Base URL**: `http://localhost:8082/api/v1`

### Implemented Endpoints

- **Properties** (`/api/v1/properties`) - Full CRUD operations for rental properties
- **Chat** (`/api/chat/query`) - Natural language chatbot queries (returns response + sources)
- **Health** (`/health`) - Health check + database connection test
- **Docs** (`/docs`) - Interactive API documentation (Swagger UI)

### Planned Endpoints (Database Tables Exist)

The following endpoints are designed but not yet exposed via API routes:
- **Transactions** - Financial events (filter by date, category, property)
- **Documents** - Document metadata and file uploads
- **Obligations** - Compliance calendar with recurrence rules

**Workaround:** Access this data directly via the chatbot using natural language queries (e.g., "Show me all transactions from August 2025") or via database tool in RAG system.

See `docs/api/` for detailed endpoint documentation.

### Response Format

All responses include provenance tracking where applicable:

```json
{
  "id": "uuid",
  "address": "900 S 9th St, Montrose, CO 81401",
  "provenance": {
    "source_type": "csv_import",
    "source_id": "poolula_facts.yml",
    "confidence": 1.0,
    "verification_status": "verified"
  }
}
```

## Data Source of Truth

**File**: `poolula_facts.yml` (project root)

This YAML file is the **single source of truth** for property and LLC data.

### UNKNOWN Field Handling

- Fields marked `"UNKNOWN"` in YAML → `NULL` in database
- Query incomplete data: `SELECT * FROM properties WHERE placed_in_service IS NULL`
- Update workflow: Edit YAML → run `uv run python scripts/seed_database.py --update`

See: `docs/workflows/data-import.md` for complete workflow

## Workflows

Detailed workflow documentation in `docs/workflows/`:

- **data-import.md** - YAML → DB workflow, handling UNKNOWN fields
- **airbnb-import.md** - Import Airbnb transaction CSVs
- **api-usage.md** - API endpoint examples for all resources
- **testing.md** - Test execution guide
- **llm-provider-setup.md** - LLM provider configuration and API key setup

## Common Commands

### Setup

```bash
# Install dependencies (core + dev)
uv sync

# Install with AI/RAG support
uv sync --group rag

# Run migrations
.venv/bin/alembic upgrade head

# Seed database from YAML
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

# Create/apply database migration
.venv/bin/alembic revision --autogenerate -m "Description"
.venv/bin/alembic upgrade head
```

### Data Management

```bash
# Import Airbnb transactions
uv run python scripts/import_airbnb_transactions.py

# Ingest documents into vector store
uv run python scripts/ingest_documents.py

# Seed compliance obligations
uv run python scripts/seed_obligations.py

# Backup/restore database
python scripts/backup.py
python scripts/backup.py --restore latest
```

### Evaluation & Testing

```bash
# Evaluate chatbot with general business questions (5 questions)
uv run python scripts/evaluate_chatbot.py

# Evaluate Airbnb rental income accuracy with ground truth (15 questions)
uv run python scripts/evaluate_airbnb.py
uv run python scripts/evaluate_airbnb.py --verbose

# Verify Airbnb CSV import integrity
uv run python scripts/verify_airbnb_import.py

# Compare LLM providers (Anthropic, OpenAI, Ollama)
uv run python scripts/evaluate_providers.py

# Run DSPy vs baseline evaluation
uv run python scripts/eval_dspy_vs_baseline.py
```

### CLI

```bash
# Use poolula CLI (must install with uv sync first)
poolula --help
```

### Documentation

```bash
# Install documentation dependencies
uv sync --group docs

# Build documentation site
uv run mkdocs build

# Serve documentation locally (http://127.0.0.1:8000)
uv run mkdocs serve

# Deploy to GitHub Pages (if configured)
uv run mkdocs gh-deploy
```

## Development Principles

### Simplicity Over Enterprise Patterns

- **Direct SQLModel usage** - No repository layer (KISS principle)
- **Comprehensive documentation** - MkDocs operational with 46+ pages covering API, architecture, workflows, and evaluation
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

### Duplicate Detection & Prevention

The platform includes robust duplicate detection to ensure data integrity:

#### Airbnb Transaction Imports
**Implementation:** `scripts/import_airbnb_transactions.py` (lines 81-131)

Prevents duplicate transactions using composite detection:
- **Primary method:** Airbnb confirmation code + transaction date + type + property
- **Fallback method:** Date + amount + category + type + property (for non-Airbnb transactions)

**Usage:**
```bash
# Re-running imports is safe - duplicates are automatically skipped
uv run python scripts/import_airbnb_transactions.py
```

**Output:** Import summary includes `duplicates_skipped` and `new_count` metrics.

#### Document Ingestion
**Implementation:** `scripts/ingest_documents.py`, `apps/chatbot/vector_store.py`

Prevents duplicate documents using SHA-256 content hashing:
- Computes hash **before** expensive chunking (performance optimization)
- Checks ChromaDB vector store for existing documents
- Skips re-ingestion if document already exists

**Usage:**
```bash
# Re-running ingestion is safe - duplicates are automatically skipped
uv run python scripts/ingest_documents.py
```

#### Cleanup Utility
**Tool:** `scripts/remove_duplicate_transactions.py`

One-time cleanup script for existing database duplicates:
- Identifies duplicate groups (same date + description + amount + category)
- Keeps oldest transaction (by `created_at` timestamp)
- Removes newer duplicates

**Usage:**
```bash
# Preview duplicates without deleting
uv run python scripts/remove_duplicate_transactions.py --dry-run

# Actually remove duplicates
uv run python scripts/remove_duplicate_transactions.py
```

## Implementation Status

**Current Phase**: Phase 6-7 (DSPy/MLflow Integration)

Completed:
- **Phase 0-1** ✅ - Infrastructure, database schema, REST API (properties + chat endpoints), tests
- **Phase 2** ✅ - Chatbot integration with database tool, audit logging, evaluation harness
- **Phase 3** ✅ - Vanilla JavaScript frontend with 4 persona-based sections

In Progress:
- **Phase 6-7** - DSPy pipeline optimization with MLflow experiment tracking
  - **Current Status**: Scaffolding exists (`apps/dspy/`) but current implementation is a RAG wrapper
  - **Planned**: True DSPy pipeline with retriever/reasoner/verifier modules (Phase 1 of plan)
  - See `docs/planning/dspy-mlflow-plan-2025-12-09.md` for detailed roadmap
  - Provider comparison and evaluation framework operational

Future:
- **Phase 4** - Additional API endpoints (transactions, documents, obligations REST routes)
- **Phase 5** - Feature expansion and production hardening (immutable field protection, advanced analytics)

See `docs/planning/` for detailed implementation plans.

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

1. **AirBnB Dashboard** (`/PROJECTS/AirBnB Dashboard/`) - Streamlit analytics (data source)
2. **RAG Chatbot** (`/PROJECTS/ragchatbot-codebase/`) - FastAPI/ChromaDB/Claude (✅ integrated)
3. **Evaluation Harness** - Golden Q&A sets for testing (✅ operational)

Phase 2 chatbot integration complete. Dashboard/frontend unification deferred to Phase 3-4.

## Contact & Support

- **Project Owner**: Poolula LLC (Hidalgo-Sotelo Living Trust)
- **Development**: Solo developer (trustee)
- **Questions**: Refer to workflow docs in `docs/workflows/`
- **Executive Overview**: See `EXECUTIVE_SUMMARY.md` for business-friendly platform overview (designed for CPAs, advisors, future collaborators)

## Quick Reference

### Key Files

- **API**: `apps/api/main.py`, `apps/api/routes/{properties,transactions,documents,obligations,chat}.py`
- **Models**: `core/database/models.py`, `core/database/enums.py`
- **Chatbot**: `apps/chatbot/rag_system.py`, `apps/chatbot/database_tool.py`, `apps/chatbot/ai_generator.py`
- **DSPy**: `apps/dspy/pipelines.py`, `apps/dspy/runtime.py`, `apps/dspy/artifacts.py`
- **Evaluator**: `apps/evaluator/chatbot_evaluator.py`, `apps/evaluator/airbnb_ground_truth.py`, `apps/evaluator/numerical_validator.py`
- **Scripts**: `scripts/cli.py`, `scripts/evaluate_chatbot.py`, `scripts/evaluate_airbnb.py`, `scripts/ingest_documents.py`
- **Tests**: `tests/test_models.py`, `tests/test_api_properties.py`, `tests/chatbot/test_rag_system.py`

### Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./poolula.db  # or postgresql://...

# API
API_HOST=0.0.0.0
API_PORT=8082

# LLM Provider (anthropic, openai, or ollama)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-...
# OPENAI_API_KEY=sk-...  # if using OpenAI
# OLLAMA_BASE_URL=http://localhost:11434  # if using Ollama

# MLflow (optional)
MLFLOW_TRACKING_URI=mlruns/
```

See `.env.example` and `docs/workflows/llm-provider-setup.md` for details.

## Next Steps

When continuing work:

1. **Check current phase**: `docs/planning/` (currently Phase 6-7: DSPy/MLflow)
2. **Review docs**:
   - `docs/api/` - API endpoint documentation
   - `docs/evaluation/` - Evaluation framework and provider comparison
   - `docs/workflows/` - Operational workflows
   - `docs/dspy-mlflow-plan.md` - Current integration roadmap
3. **Run tests**: `uv run pytest` (ensure ≥80% coverage maintained)
4. **Start API**: `uv run uvicorn apps.api.main:app --reload --port 8082`
5. **Test chatbot**: `POST http://localhost:8082/api/v1/chat/query` or run evaluation harness

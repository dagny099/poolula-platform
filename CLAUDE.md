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
- **Golden Question Set** - 15 representative business questions for RAG evaluation
- **Automated Scoring** - Tool usage + content relevance + error handling metrics (target: ≥90%)
- **Audit Logging** - All chatbot interactions logged to database

See `docs/evaluation/` for details.

### Frontend (Phase 4)

- Vue 3 + TypeScript
- Integration with existing ragchatbot-codebase

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
├── scripts/                   # Utility scripts (13 total)
│   ├── cli.py                 # Main CLI (`poolula` command)
│   ├── backup.py, seed_database.py, seed_obligations.py
│   ├── import_airbnb_transactions.py, ingest_documents.py
│   ├── evaluate_chatbot.py, evaluate_providers.py
│   └── [dspy/mlflow scripts]  # build_dspy_artifact, dspy_mlflow_run, eval_dspy_vs_baseline
├── tests/                     # Test suite (≥80% coverage)
│   ├── test_models.py, test_api_properties.py, conftest.py
│   └── chatbot/               # Chatbot tests (test_rag_system, test_session_manager, etc.)
├── docs/                      # Documentation
│   ├── api/                   # API docs (properties, transactions, documents, obligations, chat)
│   ├── architecture/          # System design, business objects, LLM providers
│   ├── evaluation/            # Evaluation framework, scoring, provider comparison
│   ├── user-guide/            # Chatbot, document management, importing data, obligations
│   ├── planning/              # Implementation plans (LLM agnosticism, DSPy/MLflow)
│   └── workflows/             # Data import, API usage, testing, LLM provider setup
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

All endpoints support full CRUD operations (GET, POST, PATCH, DELETE) for:
- **Properties** - Rental properties with acquisition and depreciation details
- **Transactions** - Financial events (filter by date, category, property)
- **Documents** - Document metadata and file uploads
- **Obligations** - Compliance calendar with recurrence rules

Special endpoints:
- `POST /chat/query` - Natural language chatbot queries (returns response + sources)
- `GET /health` - Health check + database connection test
- `GET /docs` - Interactive API documentation (Swagger UI)

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

**File**: `/Users/barbaraihidalgo-sotelo/PROJECTS/AirBnB Dashboard/poolula_facts.yml`

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
# Evaluate chatbot with golden question set
uv run python scripts/evaluate_chatbot.py

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

## Implementation Status

**Current Phase**: Phase 6-7 (DSPy/MLflow Integration)

Completed:
- **Phase 0-1** ✅ - Infrastructure, database schema, REST API, tests
- **Phase 2** ✅ - Chatbot integration with database tool, audit logging, evaluation harness

In Progress:
- **Phase 6-7** - DSPy pipeline optimization with MLflow experiment tracking
  - See `docs/dspy-mlflow-plan.md` for detailed roadmap
  - Provider comparison and evaluation framework operational

Future:
- **Phase 3-4** - Dashboard and frontend unification (deferred)
- **Phase 5** - Feature expansion and production hardening

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

## Quick Reference

### Key Files

- **API**: `apps/api/main.py`, `apps/api/routes/{properties,transactions,documents,obligations,chat}.py`
- **Models**: `core/database/models.py`, `core/database/enums.py`
- **Chatbot**: `apps/chatbot/rag_system.py`, `apps/chatbot/database_tool.py`, `apps/chatbot/ai_generator.py`
- **DSPy**: `apps/dspy/pipelines.py`, `apps/dspy/runtime.py`
- **Scripts**: `scripts/cli.py`, `scripts/evaluate_chatbot.py`, `scripts/ingest_documents.py`
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

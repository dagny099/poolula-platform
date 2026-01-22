# Poolula Platform - Architecture Reference

Technical architecture, database schema, and design decisions for Poolula Platform.

**For quick start**: See [CLAUDE.md](./CLAUDE.md)
**For workflows**: See `docs/workflows/`

---

## Technology Stack (Detailed)

### Core Infrastructure

- **Python 3.13+** with `uv` package manager
  - Fast, reliable dependency management
  - Replace pip/poetry/pipenv
- **FastAPI** - Modern REST API framework
  - Async support
  - Automatic OpenAPI docs
  - Type hints throughout
- **SQLModel** - Type-safe ORM (SQLAlchemy + Pydantic)
  - Single model definition for DB and API
  - Full Pydantic validation
  - SQLAlchemy power when needed
- **SQLite** (development) → **PostgreSQL** (production scaling)
  - SQLite perfect for 1-few users
  - Can migrate via Alembic when needed
- **Alembic** - Database migrations
  - Version-controlled schema changes
  - Autogenerate migrations from models

### Testing Infrastructure

**Coverage Target**: ≥80% across `core/` and `apps/` modules
**Test Database**: In-memory SQLite (no persistence, fresh for each test)
**Test Client**: FastAPI TestClient for API endpoint testing

**Key Testing Practices:**
- Fixtures in `tests/conftest.py` provide clean database sessions
- Each test gets isolated database state
- RAG tests mock external dependencies (LLM providers, ChromaDB)
- Evaluation harnesses test end-to-end chatbot quality

**Running Tests:**
```bash
# Fast: Run all tests
uv run pytest

# With coverage report (HTML)
uv run pytest --cov=core --cov=apps --cov-report=html
# View: open htmlcov/index.html

# Specific module
uv run pytest tests/test_models.py
uv run pytest tests/chatbot/

# Verbose output
uv run pytest -v

# Show print statements
uv run pytest -s
```

### AI & RAG Stack

- **LLM Provider Architecture** - Provider-agnostic abstraction layer for multiple LLM backends
  - **Anthropic Claude** (default) - Primary AI generation (via `anthropic>=0.58.2`)
  - **OpenAI** (optional) - Alternative provider support
  - **Local Models** (optional) - Ollama integration for offline/privacy use
  - **Provider Factory** - Runtime provider selection via `LLM_PROVIDER` env var

- **ChromaDB** - Vector database with ONNX embeddings (`chromadb>=1.0.15`)
  - Document chunking and embedding
  - Semantic search for RAG retrieval
  - Built-in ONNX embeddings avoid PyTorch dependency issues on macOS Intel x86_64 with Python 3.13

- **DSPy** - Prompt optimization and pipeline framework (`dspy-ai==2.5.0`)
  - Structured prompting
  - Pipeline composition
  - Optimization via teleprompters

- **MLflow** - Experiment tracking and model registry (`mlflow>=2.16.2`)
  - Track evaluation metrics
  - Compare provider performance
  - Version control for prompts/pipelines

**Important**: ChromaDB's built-in ONNX embeddings avoid PyTorch dependency issues on macOS Intel x86_64 with Python 3.13.

**Note**: AI dependencies are in optional `rag` dependency group. Install with `uv sync --group rag`.

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
- **HTML5 + CSS3** - Semantic markup, modern styling
- **Marked.js** - Markdown rendering for chatbot responses
- **4 Persona-Based Sections**: LLC Owner, Bookkeeper, Property Manager, Compliance Officer

---

## Project Structure

```
poolula-platform/
├── core/                      # Core business logic
│   ├── database/              # Database models & connection
│   │   ├── models.py          # SQLModel table definitions
│   │   ├── enums.py           # Status, category, type enums
│   │   └── connection.py      # Database engine & session
│   └── logging_config.py      # Structured logging setup
│
├── apps/                      # Applications
│   ├── api/                   # FastAPI REST API
│   │   ├── main.py            # FastAPI app initialization
│   │   └── routes/            # API endpoints
│   │       ├── properties.py  # Property CRUD operations
│   │       └── chat.py        # Chatbot & document endpoints
│   │
│   ├── chatbot/               # RAG Chatbot
│   │   ├── llm_providers/     # LLM provider abstraction
│   │   │   ├── base.py        # Abstract base provider
│   │   │   ├── anthropic_provider.py  # Anthropic Claude
│   │   │   ├── openai_provider.py     # OpenAI GPT
│   │   │   └── ollama_provider.py     # Ollama (local)
│   │   ├── rag_system.py      # Main orchestrator with provider factory
│   │   ├── ai_generator.py    # Provider-agnostic AI generation
│   │   ├── vector_store.py    # ChromaDB interface
│   │   ├── database_tool.py   # Database query tool for structured data
│   │   ├── search_tools.py    # Document search tools
│   │   ├── session_manager.py # Conversation history
│   │   ├── audit_logger.py    # Q&A audit logging
│   │   ├── document_processor.py  # PDF/text chunking
│   │   ├── metadata_manager.py    # Document metadata
│   │   ├── cache.py           # Response caching
│   │   ├── config.py          # Configuration management
│   │   └── health.py          # Health check utilities
│   │
│   ├── dspy/                  # DSPy pipeline integration
│   │   ├── pipelines.py       # Q&A pipeline definitions
│   │   ├── artifacts.py       # Artifact management
│   │   └── runtime.py         # Pipeline execution
│   │
│   └── evaluator/             # Evaluation harness components
│       ├── chatbot_evaluator.py       # General Q&A evaluator
│       ├── airbnb_ground_truth.py     # Airbnb CSV ground truth
│       ├── numerical_validator.py      # Numerical accuracy checking
│       └── scoring.py                 # Multi-dimensional scoring
│
├── scripts/                   # Utility scripts (15 total)
│   ├── cli.py                 # Main CLI (`poolula` command)
│   ├── backup.py              # Database backup/restore
│   ├── seed_database.py       # Seed from poolula_facts.yml
│   ├── seed_obligations.py    # Seed compliance calendar
│   ├── import_airbnb_transactions.py  # Import Airbnb CSVs
│   ├── ingest_documents.py    # Ingest docs to vector store
│   ├── evaluate_chatbot.py    # General evaluator (5 questions)
│   ├── evaluate_airbnb.py     # Airbnb evaluator (15 questions)
│   ├── evaluate_providers.py  # Compare LLM providers
│   ├── verify_airbnb_import.py        # Verify CSV import integrity
│   ├── remove_duplicate_transactions.py  # Cleanup duplicates
│   ├── build_dspy_artifact.py         # Build DSPy pipeline artifact
│   ├── dspy_mlflow_run.py            # Run DSPy with MLflow tracking
│   ├── eval_dspy_vs_baseline.py      # DSPy vs baseline comparison
│   └── make_dummy_dspy_artifact.py   # Create dummy artifact for testing
│
├── tests/                     # Test suite (≥80% coverage)
│   ├── conftest.py            # Pytest fixtures (DB, sessions)
│   ├── test_models.py         # Database model tests
│   ├── test_api_properties.py # Property endpoint tests
│   └── chatbot/               # Chatbot tests
│       ├── test_rag_system.py
│       ├── test_session_manager.py
│       ├── test_database_tool.py
│       └── test_ai_generator.py
│
├── docs/                      # Documentation (46 files - MkDocs)
│   ├── api/                   # API reference (6 files)
│   │   ├── overview.md
│   │   ├── properties.md
│   │   ├── transactions.md
│   │   ├── documents.md
│   │   ├── obligations.md
│   │   └── chat.md
│   ├── architecture/          # System design (7 files)
│   │   ├── overview.md
│   │   ├── data-models.md
│   │   ├── api-design.md
│   │   ├── llm-providers.md
│   │   └── ...
│   ├── evaluation/            # Testing & evaluation (9 files)
│   │   ├── framework.md
│   │   ├── scoring.md
│   │   ├── provider-comparison.md
│   │   └── ...
│   ├── getting-started/       # Installation (3 files)
│   ├── user-guide/            # User docs (4 files)
│   ├── planning/              # Implementation plans (6 files)
│   ├── testing/               # Testing guide (3 files)
│   └── workflows/             # How-to guides (5 files)
│
├── alembic/                   # Database migrations
│   ├── versions/              # Migration scripts
│   └── env.py                 # Alembic environment
│
├── frontend/                  # Vanilla JS frontend
│   ├── index.html
│   ├── script.js
│   └── styles.css
│
├── poolula_facts.yml          # Single source of truth (properties, LLC data)
├── pyproject.toml             # Dependencies (dev, rag, docs, openai, local)
├── CLAUDE.md                  # Claude Code essentials
├── ARCHITECTURE.md            # This file
└── EXECUTIVE_SUMMARY.md       # Business overview
```

---

## Database Schema

### 5 Core Tables

1. **properties** - Rental properties (acquisition, basis, depreciation)
   - UUID primary key
   - Address, acquisition date, purchase price, basis
   - Depreciation tracking (placed in service, useful life)
   - Status (ACTIVE/INACTIVE)
   - Provenance tracking

2. **transactions** - Financial events (30+ category chart of accounts)
   - UUID primary key
   - Amount, date, description, category
   - Transaction type (INCOME, EXPENSE, TRANSFER, etc.)
   - Property association (foreign key)
   - Airbnb confirmation code (for deduplication)
   - Provenance tracking

3. **documents** - Document metadata (PDFs, contracts, statements)
   - UUID primary key
   - Title, file path, content type
   - Upload date, file size, checksum (SHA-256)
   - Property/transaction associations
   - Status (ACTIVE/ARCHIVED)
   - Provenance tracking

4. **obligations** - Compliance calendar (RRULE recurrence)
   - UUID primary key
   - Title, description, due date
   - Recurrence rule (RFC 5545 RRULE format)
   - Category (TAX, INSURANCE, MAINTENANCE, etc.)
   - Status (PENDING, COMPLETED, OVERDUE)
   - Property association

5. **audit_log** - Immutable change tracking
   - UUID primary key
   - Entity type, entity ID, action
   - Old/new values (JSON)
   - Timestamp, user/system identifier

### Key Design Decisions

- **UUID primary keys** for all entities
  - Globally unique across distributed systems
  - No integer sequence collisions

- **Embedded provenance** tracking (JSON column, not separate table)
  - Performance (one less JOIN)
  - Simpler queries
  - Still provides full data lineage
  - Fields: `source_type`, `source_id`, `confidence`, `verification_status`

- **Timestamps** (`created_at`, `updated_at`) on all mutable tables
  - Automatic via SQLModel defaults
  - Track when records were created/modified

- **Soft deletes** (`status=INACTIVE`, not hard delete)
  - Preserve data lineage
  - Enable undo/recovery
  - Audit trail compliance

- **Direct SQLModel usage** (no repository pattern for simplicity)
  - KISS principle
  - Transparent database access
  - Can refactor to repositories in Phase 5 if needed

### Important Field Naming

These naming conventions avoid conflicts with Python/SQLAlchemy reserved words:

- **`extra_metadata`** (not `metadata` - SQLAlchemy reserved word)
- **`property_obj`** (not `property` - avoid shadowing @property decorator)

**Examples:**

```python
# ❌ Wrong - shadows Python built-in
def get_property(property):
    return property.address

# ✅ Correct - use property_obj
def get_property(property_obj: Property):
    return property_obj.address

# ❌ Wrong - SQLAlchemy reserved word conflict
class Property(SQLModel, table=True):
    metadata: dict = Field(default_factory=dict)  # Won't work!

# ✅ Correct - use extra_metadata
class Property(SQLModel, table=True):
    extra_metadata: dict = Field(default_factory=dict, sa_column=Column("extra_metadata", JSON))
```

### Response Format

All API responses include provenance tracking where applicable:

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

---

## API Endpoints

**Base URL**: `http://localhost:8082`

### Implemented Endpoints

**Note**: API versioning is inconsistent - properties use `/api/v1/`, chat uses `/api/` (without v1).

#### Properties API (`/api/v1/properties`)
Full CRUD operations for rental properties:
- `GET /api/v1/properties` - List all properties
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get property by ID
- `PATCH /api/v1/properties/{id}` - Update property (all fields allowed for flexibility)
- `DELETE /api/v1/properties/{id}` - Soft delete (sets status=INACTIVE)

See `docs/api/properties.md` for detailed documentation.

#### Chat API (`/api/`)
Natural language chatbot interface:
- `POST /api/query` - Query chatbot with natural language
  - Request: `{query: str, session_id?: str}`
  - Response: `{response: str, sources: [...]}`

#### Document Management (`/api/`)
- `GET /api/documents` - List all ingested documents
- `GET /api/documents/{title}` - Get document metadata
- `POST /api/upload` - Upload file to incoming folder
- `GET /api/incoming-files` - Check for files awaiting processing
- `POST /api/process-incoming` - Process uploaded files into vector store

#### System Endpoints
- `GET /health` - Health check + database connection test
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - ReDoc alternative documentation

### Future REST API Endpoints

The following database tables exist but don't yet have dedicated REST API CRUD endpoints:
- **Transactions** - Financial events (filter by date, category, property)
- **Obligations** - Compliance calendar with recurrence rules

**Current Access Methods:**
1. **Chatbot** - Ask natural language queries (e.g., "Show me all transactions from August 2025")
2. **Database Tool** - RAG system has direct database access via `database_tool.py`
3. **Direct SQL** - Query the SQLite database directly

**Note:** Document metadata is partially exposed via chat API (`/api/documents`), but full CRUD operations are planned for Phase 4.

See `docs/api/` for complete endpoint documentation.

---

## Data Architecture

### Data Source of Truth

**File**: `poolula_facts.yml` (project root)

This YAML file is the **single source of truth** for property and LLC data.

#### UNKNOWN Field Handling

- Fields marked `"UNKNOWN"` in YAML → `NULL` in database
- Query incomplete data: `SELECT * FROM properties WHERE placed_in_service IS NULL`
- Update workflow: Edit YAML → run `uv run python scripts/seed_database.py --update`

See: `docs/workflows/data-import.md` for complete workflow

### Provenance Tracking

Every data modification includes provenance:
- `source_type`: How was data created (manual_entry, csv_import, etc.)
- `source_id`: Which file/document (e.g., "poolula_facts.yml")
- `confidence`: 0.0-1.0 confidence level
- `verification_status`: Has this been verified?

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

---

## Development Workflows

### Common Commands

#### Data Management

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

#### Evaluation & Testing

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

#### CLI

```bash
# Use poolula CLI (must install with uv sync first)
poolula --help
```

#### Documentation

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

### Database Migrations

```bash
# Create new migration
.venv/bin/alembic revision --autogenerate -m "Description"

# Apply migration
.venv/bin/alembic upgrade head

# Rollback one migration
.venv/bin/alembic downgrade -1

# View migration history
.venv/bin/alembic history
```

---

## Design Decisions & Rationale

### Why SQLite Not PostgreSQL?

- SQLite perfect for 1-few users
- Can migrate to PostgreSQL later with Alembic
- Simpler setup and maintenance
- Zero-configuration embedded database

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

### Validation Strategy

- **PATCH allows all fields** - Fully flexible for now (trustee is sole user)
- **TODO Phase 5**: Add protection for immutable fields (acquisition_date, basis)
- **Rationale**: Flexibility > protection at small scale

---

## Implementation Status

**Current Phase**: Phase 6-7 (DSPy/MLflow Integration)

### Completed
- **Phase 0-1** ✅ - Infrastructure, database schema, REST API (properties + chat endpoints), tests
- **Phase 2** ✅ - Chatbot integration with database tool, audit logging, evaluation harness
- **Phase 3** ✅ - Vanilla JavaScript frontend with 4 persona-based sections

### In Progress
- **Phase 6-7** - DSPy pipeline optimization with MLflow experiment tracking
  - **Current Status**: Scaffolding exists (`apps/dspy/`) but current implementation is a RAG wrapper
  - **Planned**: True DSPy pipeline with retriever/reasoner/verifier modules (Phase 1 of plan)
  - See `docs/planning/dspy-mlflow-plan-2025-12-09.md` for detailed roadmap
  - Provider comparison and evaluation framework operational

### Future
- **Phase 4** - Additional API endpoints (transactions, documents, obligations REST routes)
- **Phase 5** - Feature expansion and production hardening (immutable field protection, advanced analytics)

See `docs/planning/` for detailed implementation plans.

---

## Troubleshooting

### Database Issues

**Symptom**: `alembic.util.exc.CommandError: Target database is not up to date`
```bash
# Fix: Run pending migrations
.venv/bin/alembic upgrade head
```

**Symptom**: `database is locked` during pytest
```bash
# Cause: Tests use in-memory SQLite - check for lingering database connections
# Fix: Ensure all sessions are properly closed in test teardown (check conftest.py fixtures)
```

**Symptom**: `FOREIGN KEY constraint failed` when deleting records
```bash
# Cause: SQLite foreign key enforcement + cascade rules
# Fix: Use soft deletes (status=INACTIVE) instead of hard deletes, or ensure proper cascade configuration
```

### API Issues

**Symptom**: `404 Not Found` when calling `/api/v1/chat/query`
```bash
# Cause: Chat API is at /api/query (not /api/v1/chat/query)
# Fix: Use correct endpoints:
#   - Properties: /api/v1/properties
#   - Chat: /api/query
#   - Documents: /api/documents
```

**Symptom**: API server won't start - `Address already in use`
```bash
# Find and kill process on port 8082
lsof -ti:8082 | xargs kill -9

# Or use a different port
uv run uvicorn apps.api.main:app --reload --port 8083
```

### AI/RAG Issues

**Symptom**: `RuntimeError: ANTHROPIC_API_KEY environment variable not set`
```bash
# Fix: Set API key in .env file or environment
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Or export temporarily
export ANTHROPIC_API_KEY=sk-ant-...
```

**Symptom**: ChromaDB import errors on macOS Intel - `ModuleNotFoundError: No module named 'onnxruntime'`
```bash
# Cause: ChromaDB should use built-in ONNX embeddings (no torch dependency)
# Fix: Ensure using chromadb>=1.0.15 with default embedding function
# This should be auto-configured in vector_store.py
```

**Symptom**: `No documents found in vector store` when querying chatbot
```bash
# Cause: Documents not yet ingested
# Fix: Run document ingestion script
uv run python scripts/ingest_documents.py

# Verify documents exist
uv run python -c "from apps.chatbot.vector_store import VectorStore; vs = VectorStore(); print(vs.get_collection_stats())"
```

### Dependency Issues

**Symptom**: `ImportError: No module named 'anthropic'` or similar
```bash
# Cause: Missing optional dependencies
# Fix: Install RAG dependencies
uv sync --group rag

# Or install all optional groups
uv sync --all-groups
```

**Symptom**: `uv` command not found
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### Data Import Issues

**Symptom**: Airbnb import creates duplicate transactions
```bash
# Cause: Re-running import without duplicate detection
# Fix: Import script has built-in duplicate detection (safe to re-run)
uv run python scripts/import_airbnb_transactions.py

# Clean up existing duplicates
uv run python scripts/remove_duplicate_transactions.py --dry-run  # preview
uv run python scripts/remove_duplicate_transactions.py  # actually remove
```

**Symptom**: YAML seed data has `"UNKNOWN"` values
```bash
# Expected behavior: UNKNOWN → NULL in database
# Query incomplete data
sqlite3 poolula.db "SELECT * FROM properties WHERE placed_in_service IS NULL"

# Update workflow: Edit poolula_facts.yml → re-seed
uv run python scripts/seed_database.py --update
```

---

## Migration Context

Integrating three existing projects:

1. **AirBnB Dashboard** (`/PROJECTS/AirBnB Dashboard/`) - Streamlit analytics (data source)
2. **RAG Chatbot** (`/PROJECTS/ragchatbot-codebase/`) - FastAPI/ChromaDB/Claude (✅ integrated)
3. **Evaluation Harness** - Golden Q&A sets for testing (✅ operational)

Phase 2 chatbot integration complete. Dashboard/frontend unification deferred to Phase 3-4.

---

## Contact & Support

- **Project Owner**: Poolula LLC (Hidalgo-Sotelo Living Trust)
- **Development**: Solo developer (trustee)
- **Questions**: Refer to workflow docs in `docs/workflows/`
- **Executive Overview**: See `EXECUTIVE_SUMMARY.md` for business-friendly platform overview (designed for CPAs, advisors, future collaborators)

---

**Last Updated**: 2026-01-22
**For Quick Start**: See [CLAUDE.md](./CLAUDE.md)

# Poolula Platform

A data hub and natural language query system for Poolula LLC, a Colorado single-member LLC operating rental properties.

## Project Goals

### Short-Term (Current Phase)
- **Transaction Analysis**: Automated categorization and querying of rental income, expenses, and capital transactions (Level 1 analysis with basic Level 2 aggregations)
- **LLC Compliance Q&A**: AI-powered assistant for answering questions about formation documents, operating agreements, insurance policies, leases, and tax obligations
- **Verification System**: Rigorous evaluation harness to validate AI responses against known correct answers (target: ≥90% accuracy)

### Long-Term Vision
Build a consolidated document and data hub where business questions get verifiable answers through:
- Natural language queries over structured transaction data and unstructured documents
- Automated transaction import from sources (Airbnb, bank statements, expense receipts)
- Compliance obligation tracking with document-backed answers
- **NOT** reinventing accounting software - focus on question answering and verification

## Core Business Models

The system models five primary entities:

1. **Property** (`core/database/models.py:Property`)
   - Rental properties with acquisition details, basis calculations, and depreciation tracking
   - Fields: address, acquisition_date, purchase_price_total, land_basis, building_basis, ffe_basis, placed_in_service, status
   - Computed: total_basis, depreciable_basis

2. **Transaction** (`core/database/models.py:Transaction`)
   - Financial events with full provenance tracking
   - Fields: property_id, transaction_date, amount, category, transaction_type, description, source_account
   - Categories: RENTAL_INCOME, UTILITIES_GAS, REPAIRS_MAINTENANCE, PROPERTY_MANAGEMENT, etc. (30+ categories)
   - Types: REVENUE, EXPENSE, CAPITAL, MEMBER_TRANSACTION

3. **Document** (`core/database/models.py:Document`)
   - Business documents with metadata and vector embeddings for semantic search
   - Fields: property_id, filename, doc_type, effective_date, version, confidentiality, storage_path
   - Types: Formation, Operating Agreement, Lease, Insurance, Tax Document, Bank Statement, etc.

4. **Obligation** (`core/database/models.py:Obligation`)
   - Compliance and operational deadlines
   - Fields: property_id, obligation_type, due_date, status, description, recurrence
   - Computed: is_overdue, days_until_due

5. **Provenance** (`core/database/models.py:Provenance`)
   - Data lineage tracking for all transactions
   - Fields: transaction_id, source_type, source_id, confidence, notes
   - Sources: MANUAL_ENTRY, CSV_IMPORT, AIRBNB_EXPORT, BANK_STATEMENT, etc.

## API Endpoints

### Core REST API (`apps/api/main.py`)

**Base URL**: `http://localhost:8082/api/v1`

#### Properties
- `GET /properties` - List all properties with optional filters
- `GET /properties/{property_id}` - Get property details
- `POST /properties` - Create new property
- `PUT /properties/{property_id}` - Update property
- `DELETE /properties/{property_id}` - Soft delete property

#### Transactions
- `GET /transactions` - List transactions with filters (property, date range, category, type)
- `GET /transactions/{transaction_id}` - Get transaction details
- `POST /transactions` - Create transaction
- `PUT /transactions/{transaction_id}` - Update transaction
- `DELETE /transactions/{transaction_id}` - Soft delete transaction

#### Documents
- `GET /documents` - List documents with filters
- `GET /documents/{document_id}` - Get document metadata
- `POST /documents` - Upload document with metadata
- `DELETE /documents/{document_id}` - Soft delete document

#### Obligations
- `GET /obligations` - List obligations with filters (due_date, status)
- `GET /obligations/{obligation_id}` - Get obligation details
- `POST /obligations` - Create obligation
- `PUT /obligations/{obligation_id}` - Update obligation
- `DELETE /obligations/{obligation_id}` - Soft delete obligation

#### Chatbot
- `POST /chat/query` - Send natural language query, get AI response with sources
  - Request: `{"query": "What was my rental income in August 2025?", "session_id": "optional-uuid"}`
  - Response: `{"response": "...", "sources": [...], "session_id": "..."}`

#### System
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)

## System Dataflow

```
┌─────────────────┐
│ Data Sources    │
│ - Airbnb CSV    │──┐
│ - Bank Stmt     │  │
│ - Manual Entry  │  │  Import Scripts
│ - Expense CSV   │  │  (scripts/)
└─────────────────┘  │
                     ▼
                ┌─────────────┐
                │  Database   │
                │  (SQLite)   │◄──── Migrations (alembic/)
                │             │
                │ 5 Tables:   │
                │ - Property  │
                │ - Transaction
                │ - Document  │
                │ - Obligation│
                │ - Provenance│
                └──────┬──────┘
                       │
                       ▼
            ┌──────────────────────┐
            │   FastAPI Service    │
            │   (apps/api/)        │
            └─────────┬────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Chatbot  │  │Frontend  │  │  Scripts │
  │ RAG      │  │(Vanilla  │  │  (CLI)   │
  │ System   │  │   JS)    │  │          │
  └────┬─────┘  └──────────┘  └──────────┘
       │
       ├──► Database Query Tool
       │    (SQL SELECT-only, structured data)
       │
       └──► Document Search Tool
            (ChromaDB vector search, semantic queries)

User Query: "What was my rental income in August 2025?"
    ↓
AI determines tools needed (query_database)
    ↓
Execute: query_database(query_type="aggregate_transactions",
                        filters={category: "RENTAL_INCOME",
                                transaction_type: "REVENUE",
                                start_date: "2025-08-01",
                                end_date: "2025-08-31"})
    ↓
Returns: {"success": true, "count": 12, "total_amount": "16144.12", ...}
    ↓
AI synthesizes answer: "Your rental income in August 2025 was $16,144.12
                        from 12 transactions."
    ↓
Audit log records: query, response, sources, timestamp
```

## Technology Stack

**Backend:**
- Python 3.13+ (`uv` package manager)
- FastAPI (REST API)
- SQLModel (SQLAlchemy + Pydantic ORM)
- SQLite database (single file: `poolula.db`)
- ChromaDB (vector store for document embeddings)
- Anthropic Claude API (Sonnet 4.5 model)
- Alembic (database migrations)

**Frontend:**
- Vanilla JavaScript (no framework)
- HTML5 + CSS3
- Marked.js (markdown rendering)
- 4 persona-based help sections (New LLC Owner, Bookkeeper, Property Manager, Compliance Officer)

**Testing & Quality:**
- pytest (test framework)
- Coverage target: ≥80%
- Evaluation harness with golden question set (target: ≥90% AI accuracy)

**Documentation:**
- MkDocs with Material theme
- Inline code documentation
- Workflow guides

## Repository Structure

```
poolula-platform/
├── README.md                    # This file
├── pyproject.toml              # Python dependencies (uv managed)
├── .env.example                # Environment variable template
├── .gitignore                  # Ignore .env, *.db, uploads/, logs/, etc.
│
├── core/                       # Platform foundation
│   ├── database/
│   │   ├── connection.py       # Database engine and session management
│   │   ├── models.py           # SQLModel definitions (5 core models)
│   │   └── enums.py            # Transaction categories, types, statuses
│   ├── logging_config.py       # Centralized logging setup
│   └── config.py               # Settings (from environment variables)
│
├── apps/                       # Feature modules
│   ├── api/
│   │   ├── main.py             # FastAPI application
│   │   └── routes/             # Endpoint definitions
│   ├── chatbot/
│   │   ├── ai_generator.py     # Claude API integration
│   │   ├── database_tool.py    # SQL query tool (SELECT-only)
│   │   ├── document_tool.py    # ChromaDB document search
│   │   ├── vector_store.py     # Document embedding and retrieval
│   │   └── tool_manager.py     # Tool execution orchestration
│   └── evaluator/
│       ├── evaluation_harness.py   # Golden question testing
│       └── poolula_eval_set.jsonl  # Evaluation questions and answers
│
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
│
├── scripts/                    # Utility scripts
│   ├── cli.py                  # Interactive chatbot CLI
│   ├── seed_database.py        # Initialize database from YAML
│   ├── import_airbnb_transactions.py   # Import Airbnb CSV exports
│   ├── remove_duplicate_transactions.py # Data cleanup
│   └── backup.py               # Database backup script
│
├── data/                       # Data files (see .gitignore)
│   ├── templates/              # Template files (git tracked)
│   │   ├── airbnb_template.csv
│   │   └── expenses_template.csv
│   ├── poolula_facts.yml       # Seed data for properties (git tracked)
│   └── [user data files not tracked - see .gitignore]
│
├── documents/                  # Business documents (not git tracked)
│   ├── formation/              # LLC formation documents
│   ├── insurance/              # Insurance policies
│   ├── leases/                 # Lease agreements
│   ├── tax/                    # Tax documents
│   └── [other document types]
│
├── tests/                      # Test suite (pytest)
│   ├── test_models.py          # Model validation tests
│   ├── test_api.py             # API endpoint tests
│   ├── test_chatbot.py         # Chatbot integration tests
│   └── test_evaluation.py      # Evaluation harness tests
│
├── docs/                       # Documentation (MkDocs)
│   ├── architecture/           # System design documentation
│   ├── workflows/              # Task-oriented guides
│   └── planning/               # Implementation plans and decisions
│
└── frontend/                   # Web interface
    ├── index.html              # Main chat interface
    ├── styles.css              # Styling
    └── script.js               # Client-side logic
```

## Quick Start

### Prerequisites
- Python 3.13+
- `uv` package manager: `pip install uv` or `brew install uv`
- Anthropic API key: Sign up at https://console.anthropic.com/

### Installation

```bash
# 1. Clone repository
cd /path/to/poolula-platform

# 2. Install dependencies
uv sync

# 3. Set up environment variables
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your-key-here

# 4. Run database migrations
.venv/bin/alembic upgrade head

# 5. Seed initial data (optional - creates sample property)
uv run python scripts/seed_database.py --initial
```

### Usage

**Start API server:**
```bash
uv run uvicorn apps.api.main:app --reload --port 8082
# Access: http://localhost:8082
# API docs: http://localhost:8082/docs
```

**Interactive chatbot CLI:**
```bash
uv run python scripts/cli.py chat
# Ask questions like:
# > What was my rental income in August 2025?
# > List all active properties
# > What are the business formation documents?
```

**Import Airbnb transactions:**
```bash
# Preview import (dry run)
uv run python scripts/import_airbnb_transactions.py \
    --csv data/airbnb_export.csv \
    --property-id <uuid> \
    --dry-run

# Actually import
uv run python scripts/import_airbnb_transactions.py \
    --csv data/airbnb_export.csv \
    --property-id <uuid>
```

**Run evaluation:**
```bash
uv run python apps/evaluator/evaluation_harness.py
# Outputs score report to docs/evaluation/
```

### Key Configuration

**Environment Variables** (`.env` file):
- `ANTHROPIC_API_KEY` - Required for chatbot functionality
- `DATABASE_URL` - Database connection (default: `sqlite:///poolula.db`)
- `LOG_LEVEL` - Logging verbosity (default: `INFO`)

**Database Location**:
- Development: `poolula.db` (SQLite file in project root, NOT git tracked)
- Production: PostgreSQL (connection string in DATABASE_URL)

## Development Workflow

### Common Tasks

```bash
# Run API server (auto-reload on code changes)
uv run uvicorn apps.api.main:app --reload --port 8082

# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=core --cov=apps --cov-report=html
open htmlcov/index.html

# Create database migration
.venv/bin/alembic revision --autogenerate -m "Add new field to Transaction"

# Apply migrations
.venv/bin/alembic upgrade head

# Create database backup
uv run python scripts/backup.py
# Creates: backups/poolula_YYYYMMDD_HHMMSS.db

# Remove duplicate transactions
uv run python scripts/remove_duplicate_transactions.py --dry-run  # Preview
uv run python scripts/remove_duplicate_transactions.py            # Execute
```

### Adding New Features

**Example: Add new transaction category**

1. Edit `core/database/enums.py`:
   ```python
   class TransactionCategory(str, Enum):
       # ... existing categories ...
       NEW_CATEGORY = "NEW_CATEGORY"  # Add new value
   ```

2. Create migration:
   ```bash
   .venv/bin/alembic revision --autogenerate -m "Add NEW_CATEGORY to TransactionCategory"
   .venv/bin/alembic upgrade head
   ```

3. Update tests in `tests/test_models.py`

4. Update documentation

### Design Patterns

- **Provenance Tracking**: Every transaction records its source (CSV import, manual entry, etc.) via Provenance table
- **Soft Deletes**: Set `deleted_at` timestamp instead of hard DELETE (preserves audit trail)
- **Audit Logging**: All chatbot queries logged to database (query, response, sources, timestamp)
- **Type Safety**: SQLModel provides Pydantic validation + SQLAlchemy ORM
- **No ORMs Within ORMs**: Direct SQLModel usage, no repository pattern (simplicity for single-developer project)

## Testing

**Coverage Target**: ≥80%

### Test Categories

1. **Unit Tests**: Model validation, computed properties, enums
2. **Integration Tests**: API endpoints with full CRUD operations
3. **Chatbot Tests**: Tool execution, multi-round queries, error handling
4. **Evaluation Tests**: Golden question set accuracy

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_models.py

# Specific test function
uv run pytest tests/test_api.py::test_create_property

# With verbose output
uv run pytest -v

# With coverage
uv run pytest --cov=core --cov=apps --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=core --cov=apps --cov-report=html
open htmlcov/index.html
```

### Evaluation Harness

The evaluation harness tests AI accuracy against known correct answers:

```bash
# Run evaluation
uv run python apps/evaluator/evaluation_harness.py

# Output: docs/evaluation/evaluation_report_YYYYMMDD_HHMMSS.json
```

**Scoring Dimensions:**
- Tool usage correctness (did AI use right tools?)
- Content relevance (does answer address the question?)
- Semantic similarity (answer matches expected content)
- Numerical accuracy (financial figures match expected values)
- Citation accuracy (sources are correct and relevant)

**Target Score**: ≥90%

## Documentation

### For Developers
- **CLAUDE.md**: Quick reference for AI coding assistants
- **Implementation Plan**: `docs/planning/implementation-plan-2024-11-14.md`
- **API Reference**: http://localhost:8082/docs (interactive Swagger UI)

### Architecture
- **Business Objects**: `docs/architecture/business-objects.md`
- **Platform Interfaces**: `docs/architecture/platform-interfaces.md`
- **Quick Reference**: `docs/architecture/quick-reference.md`

### Workflow Guides
- **Data Import**: `docs/workflows/data-import.md`
- **API Usage**: `docs/workflows/api-usage.md`
- **Testing**: `docs/workflows/testing.md`

### Code Documentation
- Database models: See `core/database/models.py` (inline docstrings)
- API endpoints: See `apps/api/routes/` (inline docstrings)
- Enums: See `core/database/enums.py` (30+ transaction categories)

## Current Status

**Phase**: Week 0 - README revision and approval

**Completed**:
- ✅ Database schema (5 tables: Property, Transaction, Document, Obligation, Provenance)
- ✅ SQLModel models with provenance tracking
- ✅ Alembic migrations
- ✅ FastAPI REST API (properties, transactions, documents, obligations endpoints)
- ✅ Database query tool for chatbot (SELECT-only, safe queries)
- ✅ RAG system integration (database + document search)
- ✅ Chatbot CLI with source citations
- ✅ Airbnb CSV import script with accrual accounting
- ✅ Duplicate transaction removal script
- ✅ Evaluation harness with 15 golden questions
- ✅ Comprehensive test suite (31/37 tests passing, ≥80% coverage)
- ✅ Audit logging for all chatbot interactions

**Next Steps** (pending README approval):
- Fix ChromaDB document search bug
- Re-ingest LLC documents (formation, insurance, leases, tax)
- Port vanilla JS frontend with 4 persona sections
- Expand evaluation set (15 → 40 questions)
- Improve evaluation metrics (semantic similarity, numerical accuracy)
- Build evaluation reporting dashboard
- Achieve ≥90% evaluation score

See `docs/planning/implementation-plan-2024-11-14.md` for detailed 3-week plan.

## Contributing

This is a solo-developer project for Poolula LLC. Architectural decisions are documented in `docs/architecture/` with rationale.

## License

Proprietary - Internal use only for Poolula LLC operations.

---

**Last Updated**: 2024-11-14
**Status**: Week 0 - Foundation complete, awaiting README approval to proceed

# Poolula Platform

**An integrated management platform for Poolula LLC - combining operational analytics, AI-powered assistance, and compliance tools.**

## Vision

Poolula Platform is a unified system for managing all aspects of Poolula LLC, a Colorado single-member LLC that owns and operates rental properties. The platform provides:

- **Operational Insights**: Real-time analytics on property performance, revenue, and expenses
- **AI Assistant**: Natural language interface for compliance questions, document retrieval, and operational guidance
- **Quality Assurance**: Automated evaluation harness to ensure AI accuracy and prevent hallucinations
- **Future Capabilities**: Tax preparation, compliance calendaring, document management, and financial reporting

## Core Principles

1. **UNDERSTANDING** - Every calculation, decision, and data transformation is explainable and traceable
2. **TRANSPARENCY** - Complete audit trails, data provenance, and source citations for all information
3. **USER FRIENDLINESS** - Task-oriented workflows with progressive disclosure of complexity

## Architecture

**Hybrid: Data-First Modular Monolith + Workflow UI Layer**

### Foundation
- **Single codebase** with clear module boundaries for maintainability
- **Central database** (SQLite → PostgreSQL) as single source of truth
- **Vector store** (ChromaDB) for semantic document search
- **Service layer** with business logic isolation and provenance tracking

### Applications
- **Chatbot**: RAG-powered Q&A with database and document context
- **Analytics**: Interactive dashboards for financial and operational metrics
- **Evaluator**: Automated testing against golden Q&A sets
- **Future modules**: Tax assistant, compliance calendar, document vault

### User Experience
- **Workflow-oriented UI** for guided multi-step tasks (e.g., "Close the Month")
- **Ad-hoc exploration** via chat interface and interactive dashboards
- **Progressive disclosure** - simple answers with "show more" for details
- **Consistent navigation** and styling across all modules

## Technology Stack

**Backend:**
- Python 3.13+ with modern async patterns
- FastAPI for REST API and WebSocket support
- SQLModel (SQLAlchemy + Pydantic) for type-safe database access
- ChromaDB for vector embeddings
- Anthropic Claude for AI generation
- uv for fast, reliable dependency management
- Neo4j (Phase 7+) for graph-based relationship exploration

**Frontend:**
- Vue 3 with Composition API and TypeScript
- Vite for fast development and optimized builds
- Pinia for state management
- TailwindCSS for styling
- Chart.js / Plotly for visualizations
- D3.js / vis.js for graph visualization (Phase 7+)

**Infrastructure:**
- SQLite (development/small deployment) → PostgreSQL (production scaling)
- Git for version control
- pytest for comprehensive testing
- MkDocs for documentation
- Docker (optional, for Neo4j and production deployment)

## Current Status

**Phase 1: Foundation** ✅ (Complete)
- ✅ Database schema (5 tables: Property, Transaction, Document, Obligation, AuditLog)
- ✅ SQLModel models with provenance tracking
- ✅ Alembic migrations
- ✅ FastAPI REST API with Property CRUD endpoints
- ✅ Comprehensive test suite (≥80% coverage)
- ✅ Seed script for importing from poolula_facts.yml
- ✅ Workflow documentation (data-import, API usage, testing)

**Roadmap** (16 weeks core platform):
- **Phase 0** ✅: Infrastructure - Backups, logging, health checks
- **Phase 1** ✅: Foundation - SQLite database, API, provenance tracking
- **Phase 2**: Chatbot Integration (Weeks 3-4) - RAG system + SQL queries, evaluation harness (≥90% target)
- **Phase 3**: Dashboard Migration (Week 5) - Airbnb data → SQL, Streamlit integration
- **Phase 4**: Frontend Unification (Weeks 6-7) - Vue 3 shell, workflow framework
- **Phase 5**: Feature Expansion (Weeks 8-16) - Tax assistant, compliance calendar, document vault, expense categorization
- **Phase 6**: Evaluation Dashboard (Week 17) - Quality monitoring, CI integration
- **Phase 7+**: Neo4j Integration (Flexible) - Graph database for exploration and learning

## Project Components

### Migrating from Existing Projects

This platform consolidates three existing components:

1. **RAG Chatbot** (`../ragchatbot-codebase/`)
   - 56 files, 32 passing tests, production-ready
   - Will be integrated as `apps/chatbot/` module
   - Enhanced to query structured database alongside document search

2. **Airbnb Dashboard** (`../AirBnB Dashboard/dashboard/`)
   - Streamlit analytics application
   - Will be reimplemented as `apps/analytics/` with database backing
   - Data migrated from CSV-based to persistent storage

3. **Evaluation Harness** (`../AirBnB Dashboard/evaluation/`)
   - Design specifications for quality assurance
   - Will be implemented as `apps/evaluator/` module
   - Ensures chatbot accuracy against golden Q&A sets

## Repository Structure

```
poolula-platform/
├── README.md                    # This file
├── pyproject.toml              # Project metadata and dependencies
├── .env.example                # Environment variable template
├── .gitignore
├── core/                       # Platform foundation
│   ├── database/              # Data models and migrations
│   ├── vector_store/          # Document embeddings
│   ├── schemas/               # Pydantic models
│   ├── services/              # Business logic
│   └── repositories/          # Data access patterns
├── apps/                       # Feature modules
│   ├── chatbot/               # RAG assistant
│   ├── analytics/             # Dashboards and reports
│   ├── evaluator/             # Quality assurance
│   └── [future modules]
├── workflows/                  # Task orchestration
│   ├── monthly_close/
│   ├── tax_preparation/
│   └── compliance_check/
├── frontend/                   # Vue 3 web interface
│   ├── src/
│   └── public/
├── tests/                      # Comprehensive test suite
├── docs/                       # Architecture and API documentation
└── scripts/                    # Utility scripts
```

## Quick Start

**Prerequisites:**
- Python 3.13+
- uv package manager (`pip install uv` or `brew install uv`)

**Setup:**
```bash
# Install Python dependencies
uv sync

# Run database migrations
.venv/bin/alembic upgrade head

# Seed database from poolula_facts.yml
uv run python scripts/seed_database.py --initial

# Start API server
uv run uvicorn apps.api.main:app --reload --port 8082
```

**Access:**
- **API**: http://localhost:8082
- **Interactive API docs (Swagger)**: http://localhost:8082/docs
- **Health check**: http://localhost:8082/health

**Example API Calls:**
```bash
# List all properties
curl http://localhost:8082/api/v1/properties

# Get health status
curl http://localhost:8082/health
```

See **[docs/workflows/](docs/workflows/)** for detailed guides:
- [data-import.md](docs/workflows/data-import.md) - YAML → DB workflow
- [api-usage.md](docs/workflows/api-usage.md) - API endpoint examples
- [testing.md](docs/workflows/testing.md) - Test execution guide

## Development Workflow

**Common Tasks:**

```bash
# Run API server (development mode with auto-reload)
uv run uvicorn apps.api.main:app --reload --port 8082

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=core --cov=apps --cov-report=html

# Create database migration
.venv/bin/alembic revision --autogenerate -m "Description"

# Apply migrations
.venv/bin/alembic upgrade head

# Seed/update from YAML
uv run python scripts/seed_database.py --initial  # First time
uv run python scripts/seed_database.py --update   # Fill in UNKNOWN values

# Create database backup
python scripts/backup.py
```

**Adding a new feature:**
1. Define data model in `core/database/models.py`
2. Create migration with `.venv/bin/alembic revision --autogenerate`
3. Build API endpoints in `apps/api/routes/`
4. Write tests in `tests/`
5. Update documentation in `docs/workflows/`

**Key design patterns:**
- **Direct SQLModel usage**: No repository pattern (simplicity for small scale)
- **Provenance tracking**: Every data point records its source and lineage
- **Audit logging**: Immutable audit trail (to be used in Phase 5)
- **Soft deletes**: Mark inactive, don't hard delete
- **Progressive disclosure**: Simple defaults with expandable details

## Testing Strategy

**Coverage target: ≥80%**

- **Unit tests**: Model validation, computed properties, relationships
- **Integration tests**: API endpoints with full CRUD coverage
- **In-memory database**: Fast, isolated test execution

Run tests:
```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_models.py

# With coverage report
uv run pytest --cov=core --cov=apps --cov-report=html
open htmlcov/index.html
```

See [docs/workflows/testing.md](docs/workflows/testing.md) for complete testing guide.

## Documentation

### For Developers

- **Implementation plan**: `docs/planning/2025-11-13-revised-implementation-plan.md`
- **CLAUDE.md**: Quick reference guide for AI coding assistants
- **API reference**: Interactive docs at http://localhost:8082/docs (Swagger UI)

### Workflow Guides

- **Data Import**: `docs/workflows/data-import.md` - YAML → DB workflow with UNKNOWN handling
- **API Usage**: `docs/workflows/api-usage.md` - Complete API endpoint examples
- **Testing**: `docs/workflows/testing.md` - Running and writing tests

### Code Documentation

- **Database Models**: See `core/database/models.py` (inline documentation)
- **API Endpoints**: See `apps/api/routes/properties.py` (inline documentation)
- **Enums**: See `core/database/enums.py` (30+ transaction categories)

## Contributing

This is a solo-developer project for Poolula LLC. For major architectural changes, document decisions in `docs/architecture/` with date and rationale.

## License

Proprietary - Internal use only for Poolula LLC operations.

---

**Last Updated**: 2025-11-13
**Status**: Foundation phase - actively under development

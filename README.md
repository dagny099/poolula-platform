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

**Phase 0: Infrastructure Setup** 🔄 (In Progress)
- ✅ Repository initialized
- ✅ Architecture documentation complete
- ✅ Revised implementation plan with quantitative success criteria
- ⏭️ Backup/restore scripts
- ⏭️ Structured logging setup

**Roadmap** (16 weeks core platform):
- **Phase 0**: Infrastructure (1-2 days) - Backups, logging, health checks
- **Phase 1**: Foundation (Weeks 1-2) - SQLite database, API, provenance tracking
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
- uv package manager
- Node.js 18+ (for frontend development)
- Anthropic API key

**Setup:**
```bash
# Install Python dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Initialize database
uv run python scripts/init_db.py

# Seed with existing data
uv run python scripts/seed_from_legacy.py

# Run development server
uv run python -m backend.app
```

**Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev
```

Access the platform at `http://localhost:5173` (frontend) with API at `http://localhost:8000`.

## Development Workflow

**Adding a new feature:**
1. Define data model in `core/database/models.py`
2. Create migration with `alembic revision --autogenerate`
3. Implement business logic in `core/services/`
4. Build API endpoints in `apps/{module}/api.py`
5. Create frontend components in `frontend/src/components/`
6. Write tests in `tests/`
7. Update documentation in `docs/`

**Key design patterns:**
- **Repository pattern**: All database access through repository classes
- **Service layer**: Business logic isolated from API/UI concerns
- **Provenance tracking**: Every data point records its source and lineage
- **Audit logging**: All mutations tracked with timestamp, user, and reason
- **Progressive disclosure**: Simple defaults with expandable details

## Testing Strategy

- **Unit tests**: Core business logic and calculations
- **Integration tests**: API endpoints and workflows
- **E2E tests**: Critical user journeys
- **Evaluation harness**: AI accuracy against golden sets (≥90% required)

Run tests: `uv run pytest tests/ -v`

## Documentation

- **Architecture decisions**: See `docs/architecture/`
- **Data model**: See `docs/data-model.md`
- **API reference**: See `docs/api/` or visit `/docs` endpoint
- **Planning history**: See `docs/planning/`

## Contributing

This is a solo-developer project for Poolula LLC. For major architectural changes, document decisions in `docs/architecture/` with date and rationale.

## License

Proprietary - Internal use only for Poolula LLC operations.

---

**Last Updated**: 2025-11-13
**Status**: Foundation phase - actively under development

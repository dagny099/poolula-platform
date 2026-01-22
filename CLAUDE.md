# Poolula Platform - Claude Code Guide

This document provides essential context for Claude Code (AI coding assistant) working on Poolula Platform.

## Project Overview

**Poolula Platform** is a unified management platform for Poolula LLC operations, combining:
- Property & financial tracking
- AI-powered chatbot assistant
- Analytics dashboard
- Compliance calendar

**Scale**: Small deployment (1-few users, not enterprise)
**Principles**: UNDERSTANDING, TRANSPARENCY, USER FRIENDLINESS

## Technology Stack (Summary)

**Core**: Python 3.13+, FastAPI, SQLModel, SQLite → PostgreSQL, Alembic migrations
**AI/RAG**: LLM Provider abstraction (Anthropic Claude default, OpenAI/Ollama optional), ChromaDB, DSPy, MLflow
**Testing**: pytest (≥80% coverage target), in-memory SQLite test DB
**Frontend**: Vanilla JavaScript, HTML5/CSS3, Marked.js

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed tech stack and design decisions.

## Quick Start

### First-Time Setup

```bash
# 1. Install dependencies
uv sync --group rag

# 2. Set up environment
cp .env.example .env
# Edit .env with ANTHROPIC_API_KEY, DATABASE_URL, etc.

# 3. Run migrations & seed data
.venv/bin/alembic upgrade head
uv run python scripts/seed_database.py --initial
uv run python scripts/seed_obligations.py

# 4. Verify setup
uv run pytest
```

See `docs/workflows/` for detailed workflows (data import, Airbnb CSV import, LLM provider setup).

### Development Commands

```bash
# Start API server
uv run uvicorn apps.api.main:app --reload --port 8082

# Run tests
uv run pytest
uv run pytest --cov=core --cov=apps --cov-report=html

# Evaluate chatbot
uv run python scripts/evaluate_chatbot.py
uv run python scripts/evaluate_airbnb.py --verbose

# Import data
uv run python scripts/import_airbnb_transactions.py
uv run python scripts/ingest_documents.py
```

## API Endpoints (Quick Reference)

**Base URL**: `http://localhost:8082`

**Note**: API versioning is inconsistent - properties use `/api/v1/`, chat uses `/api/`.

- **Properties**: `/api/v1/properties` - Full CRUD operations
- **Chat**: `/api/query` - Natural language queries
- **Documents**: `/api/documents`, `/api/upload`, `/api/incoming-files`, `/api/process-incoming`
- **Health**: `/health` - Health check
- **Docs**: `/docs` - Swagger UI

See [ARCHITECTURE.md](./ARCHITECTURE.md#api-endpoints) for complete endpoint documentation.

## Common Issues & Quick Fixes

### Database
```bash
# Migration not applied
.venv/bin/alembic upgrade head

# Database locked during tests
# → Check conftest.py fixtures, ensure sessions are closed
```

### API
```bash
# 404 on /api/v1/chat/query
# → Chat is at /api/query (not /api/v1/chat/query)

# Port already in use
lsof -ti:8082 | xargs kill -9
```

### AI/RAG
```bash
# Missing API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# No documents in vector store
uv run python scripts/ingest_documents.py

# Missing dependencies
uv sync --group rag
```

### Data Import
```bash
# Duplicate transactions
uv run python scripts/remove_duplicate_transactions.py --dry-run
# → Import script has built-in duplicate detection (safe to re-run)

# UNKNOWN fields in YAML
# → Expected behavior: UNKNOWN → NULL in database
# → Edit poolula_facts.yml and re-run: uv run python scripts/seed_database.py --update
```

See [ARCHITECTURE.md](./ARCHITECTURE.md#troubleshooting) for complete troubleshooting guide.

## Key Files

- **API**: `apps/api/main.py`, `apps/api/routes/{properties,chat}.py`
- **Models**: `core/database/models.py`, `core/database/enums.py`
- **Chatbot**: `apps/chatbot/rag_system.py`, `apps/chatbot/database_tool.py`, `apps/chatbot/ai_generator.py`
- **LLM Providers**: `apps/chatbot/llm_providers/{base,anthropic,openai,ollama}.py`
- **Evaluator**: `apps/evaluator/chatbot_evaluator.py`, `apps/evaluator/airbnb_ground_truth.py`
- **Scripts**: `scripts/cli.py`, `scripts/evaluate_{chatbot,airbnb,providers}.py`
- **Tests**: `tests/test_models.py`, `tests/test_api_properties.py`, `tests/chatbot/test_rag_system.py`
- **Docs**: `docs/{api,architecture,workflows,evaluation}/` (46 files via MkDocs)

## Environment Variables

```env
# Required
DATABASE_URL=sqlite:///./poolula.db
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Optional
API_HOST=0.0.0.0
API_PORT=8082
OPENAI_API_KEY=sk-...          # if using OpenAI
OLLAMA_BASE_URL=http://localhost:11434  # if using Ollama
MLFLOW_TRACKING_URI=mlruns/
```

See `.env.example` and `docs/workflows/llm-provider-setup.md` for details.

## Development Principles

### Simplicity Over Enterprise Patterns
- **Direct SQLModel usage** - No repository layer (KISS principle)
- **Small scale** - Optimized for 1-few users, not millions
- **Comprehensive docs** - MkDocs with 46+ pages

### Important Conventions
- **UUID primary keys** for all entities
- **Soft deletes** (status=INACTIVE, not hard delete)
- **Embedded provenance** (JSON column, not separate table)
- **Field naming**: Use `property_obj` (not `property`), `extra_metadata` (not `metadata`)

### Data Source of Truth
- **File**: `poolula_facts.yml` (project root)
- Workflow: Edit YAML → run `uv run python scripts/seed_database.py --update`
- UNKNOWN fields → NULL in database

### Testing Requirements
- **Coverage**: ≥80% across `core/` and `apps/`
- **Isolation**: Each test gets fresh in-memory SQLite DB
- **Mocking**: RAG tests mock LLM providers and ChromaDB

## Current Implementation Status

**Phase 6-7** (In Progress): DSPy/MLflow Integration
- ✅ **Phase 0-1**: Infrastructure, database, REST API (properties + chat), tests
- ✅ **Phase 2**: Chatbot with database tool, audit logging, evaluation harness
- ✅ **Phase 3**: Vanilla JS frontend with 4 persona sections
- 🔄 **Phase 6-7**: DSPy pipeline optimization (scaffolding exists, true pipeline in progress)
- 📋 **Phase 4**: Additional REST endpoints (transactions, obligations)
- 📋 **Phase 5**: Production hardening

See `docs/planning/dspy-mlflow-plan-2025-12-09.md` for detailed roadmap.

## Next Steps

When continuing work:

1. **Check current phase**: `docs/planning/` (Phase 6-7: DSPy/MLflow)
2. **Review relevant docs**:
   - [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical details, database schema, API design
   - `docs/api/` - API endpoint documentation
   - `docs/workflows/` - Operational workflows
   - `docs/evaluation/` - Evaluation framework
3. **Run tests**: `uv run pytest` (maintain ≥80% coverage)
4. **Start API**: `uv run uvicorn apps.api.main:app --reload --port 8082`
5. **Test chatbot**: `POST http://localhost:8082/api/query` or `uv run python scripts/evaluate_chatbot.py`

## Additional Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed tech stack, database schema, API endpoints, project structure
- **[EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)** - Business-friendly platform overview (for CPAs, advisors)
- **`docs/`** - Complete documentation (46 files):
  - `docs/api/` - API reference (6 files)
  - `docs/architecture/` - System design (7 files)
  - `docs/workflows/` - How-to guides (5 files)
  - `docs/evaluation/` - Testing & evaluation (9 files)
  - `docs/getting-started/` - Installation & quick start (3 files)

Build docs: `uv run mkdocs build` | Serve: `uv run mkdocs serve`

## Contact & Support

- **Questions**: Refer to `docs/workflows/` or [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Help**: `/help` command for Claude Code features
- **Feedback**: https://github.com/anthropics/claude-code/issues

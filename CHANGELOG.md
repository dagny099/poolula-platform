# Changelog

All notable changes to the Poolula Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### In Progress
- Phase 6-7: DSPy pipeline optimization with MLflow experiment tracking

## [0.1.0] - 2025-02-12

### Added - Phase 6-7: DSPy/MLflow Integration
- MLflow experiment tracking integration for RAG pipeline optimization
- DSPy pipeline framework for prompt optimization ([#5](https://github.com/dagny099/poolula-platform/pull/5))
- MLflow artifact management system (`apps/dspy/artifacts.py`)
- DSPy Q&A pipeline definitions (`apps/dspy/pipelines.py`)
- Pipeline runtime execution framework (`apps/dspy/runtime.py`)
- Evaluation scripts:
  - `scripts/eval_dspy_vs_baseline.py` - Compare DSPy optimized vs baseline
  - `scripts/build_dspy_artifact.py` - Build DSPy artifacts
  - `scripts/dspy_mlflow_run.py` - Run MLflow experiments
- Executive summary documentation (`EXECUTIVE_SUMMARY.md`)
- Updated `.gitignore` for experiment-generated folders

### Added - Phase 2: Multi-Provider LLM Support
- LLM provider abstraction layer with factory pattern ([#3](https://github.com/dagny099/poolula-platform/pull/3))
  - Base provider interface (`apps/chatbot/llm_providers/base.py`)
  - Anthropic Claude provider (default) (`apps/chatbot/llm_providers/anthropic.py`)
  - OpenAI provider support (`apps/chatbot/llm_providers/openai.py`)
  - Ollama local model provider (`apps/chatbot/llm_providers/ollama.py`)
- Multi-provider evaluation framework (`scripts/evaluate_providers.py`)
- Provider comparison documentation (`docs/evaluation/provider-comparison.md`)
- LLM provider setup workflow guide (`docs/workflows/llm-provider-setup.md`)
- Optional dependency groups in `pyproject.toml`:
  - `openai` - OpenAI API client
  - `local` - Ollama integration
- Environment variable configuration for provider selection (`LLM_PROVIDER`)

### Added - Phase 2: RAG Chatbot & Evaluation
- RAG chatbot system with ChromaDB vector store integration
  - Main orchestrator (`apps/chatbot/rag_system.py`)
  - Provider-agnostic AI generator (`apps/chatbot/ai_generator.py`)
  - Vector store interface (`apps/chatbot/vector_store.py`)
  - Database query tool for structured data (`apps/chatbot/database_tool.py`)
  - Document search tools (`apps/chatbot/search_tools.py`)
  - Conversation session manager (`apps/chatbot/session_manager.py`)
  - Audit logging system (`apps/chatbot/audit_logger.py`)
- Chat API endpoint (`POST /api/v1/chat/query`) with citation support
- Evaluation harness with golden question set (15 representative questions)
  - Automated scoring system (tool usage + content relevance + error handling)
  - Target score: ≥90%
  - Evaluation dataset (`apps/evaluator/poolula_eval_set.jsonl`)
  - Printable PDF version of evaluation dataset ([#2](https://github.com/dagny099/poolula-platform/pull/2))
- Evaluation scripts:
  - `scripts/evaluate_chatbot.py` - Run chatbot evaluation
  - `scripts/ingest_documents.py` - Ingest PDFs into vector store
- Comprehensive sample questions document (133 questions)
- User guide documentation (`docs/user-guide/`)

### Added - Phase 1: Core Platform Infrastructure
- FastAPI REST API with SQLModel ORM
  - Properties API (`apps/api/routes/properties.py`)
  - Transactions API (`apps/api/routes/transactions.py`)
  - Documents API (`apps/api/routes/documents.py`)
  - Obligations API (`apps/api/routes/obligations.py`)
  - Health check endpoint (`GET /api/v1/health`)
  - Interactive API docs (`GET /api/v1/docs`)
- Database schema with 5 core tables:
  - `properties` - Rental property tracking with depreciation
  - `transactions` - Financial events with 30+ category chart of accounts
  - `documents` - Document metadata and file management
  - `obligations` - Compliance calendar with RRULE recurrence
  - `audit_log` - Immutable change tracking
- Alembic database migrations (`alembic/`)
- Comprehensive test suite with pytest (≥80% coverage target)
  - `tests/test_models.py` - Model validation tests
  - `tests/test_api_properties.py` - API endpoint tests
  - `tests/chatbot/` - Chatbot component tests
- Utility scripts:
  - `scripts/cli.py` - Main CLI (`poolula` command)
  - `scripts/seed_database.py` - Load data from YAML source of truth
  - `scripts/seed_obligations.py` - Seed compliance calendar
  - `scripts/import_airbnb_transactions.py` - Import Airbnb CSV data
  - `scripts/backup.py` - Database backup/restore
- Documentation structure (`docs/`):
  - `docs/api/` - API endpoint documentation
  - `docs/architecture/` - System design docs
  - `docs/workflows/` - Operational workflows
  - `docs/planning/` - Implementation plans
- MkDocs documentation framework with Material theme
- Python 3.13+ support with `uv` package manager
- SQLite database (with PostgreSQL migration path via Alembic)
- ChromaDB vector database with ONNX embeddings (RAG dependency group)
- Structured logging configuration (`core/logging_config.py`)

### Added - Phase 0: Project Foundation
- Initial project structure with modular architecture
  - `core/` - Core business logic and database models
  - `apps/` - Applications (API, chatbot, evaluator, dspy)
  - `scripts/` - Utility scripts and CLI
  - `tests/` - Test suite
  - `docs/` - Documentation
- UUID primary keys for all entities
- Embedded provenance tracking (source, confidence, verification status)
- Soft delete pattern (status=INACTIVE)
- Timestamp tracking (created_at, updated_at) on all mutable tables
- Development tooling:
  - pytest with coverage reporting
  - ruff for linting and formatting
  - mypy for type checking
- Dependency groups for modular installation:
  - `dev` - Testing and development tools
  - `rag` - AI/RAG dependencies (Anthropic, ChromaDB, DSPy)
  - `docs` - Documentation generation (MkDocs)

### Changed
- README restructured to technical focus (business overview moved to `EXECUTIVE_SUMMARY.md`)
- Directory structure reorganized for proper data/document separation
- MkDocs documentation reorganized with improved navigation
- Improved CLI source display for database queries
- Enhanced evaluation results with disclaimers and notes

### Fixed
- SQLAlchemy 2.0 compatibility issues with model relationships
- ChromaDB document search bug (removed unsupported `$contains` operator)
- Duplicate transaction handling in database responses
- Airbnb import datetime deprecation warnings
- Airbnb import session errors and category name mismatches
- Aggregate transactions category filtering bug
- Document ingestion duplicate prevention with `--stats` flag
- Database seed script update workflow
- MkDocs build warnings

### Security
- Audit logging for all chatbot interactions (immutable trail)
- Provenance tracking for data lineage and verification
- API key management via environment variables
- Read-only database tool for chatbot queries

## Development Principles

### Design Decisions
- **Simplicity over enterprise patterns** - Direct SQLModel usage, no repository layer
- **Small scale optimization** - Designed for 1-few users, not millions
- **Embedded provenance** - Performance (no extra JOINs) while maintaining lineage
- **SQLite primary** - PostgreSQL migration path available via Alembic
- **Provider-agnostic AI** - Abstract LLM interface supports multiple backends

### Data Quality
- Single source of truth: `poolula_facts.yml`
- Accrual accounting for transaction imports
- UNKNOWN field handling (YAML → NULL in database)
- Comprehensive validation at API boundaries

### Evaluation-Driven Development
- Golden question set for regression testing
- Multi-provider benchmarking capability
- Automated scoring (40% tool choice, 40% content, 20% completeness)
- Continuous evaluation with MLflow tracking

---

## Migration Context

Poolula Platform integrates three existing projects:
1. **AirBnB Dashboard** - Streamlit analytics (data source)
2. **RAG Chatbot** - FastAPI/ChromaDB/Claude (✅ integrated in Phase 2)
3. **Evaluation Harness** - Golden Q&A sets (✅ operational)

Dashboard/frontend unification deferred to Phase 3-4.

---

## Roadmap

### Completed ✅
- **Phase 0-1**: Infrastructure, database schema, REST API, comprehensive tests
- **Phase 2**: RAG chatbot integration, multi-provider support, evaluation framework
- **Phase 6-7**: DSPy/MLflow integration (in progress)

### Future Phases
- **Phase 3-4**: Dashboard and frontend unification with Vue 3 + TypeScript
- **Phase 5**: Production hardening, immutable field protection, expanded features

---

## Links
- [Project Documentation](docs/)
- [API Documentation](docs/api/)
- [Evaluation Framework](docs/evaluation/)
- [User Guide](docs/user-guide/)
- [Implementation Plans](docs/planning/)

---

## License
Internal prototype — not licensed for distribution.

Copyright © 2025 Poolula LLC (Hidalgo-Sotelo Living Trust)

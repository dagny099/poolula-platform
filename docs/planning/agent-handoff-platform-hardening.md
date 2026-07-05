# Agent Handoff: Platform Hardening Pass

**Date:** 2026-07-04
**Scope:** Close documented API gaps, make document upload/processing real, make evaluation diagnostic, align docs with reality.

---

## 1. Executive Summary

### What I found

The platform had a solid core (properties CRUD, RAG chatbot with database/document tools, models for all five entities, Alembic migration, 80 passing tests) but three significant gaps between documentation and implementation:

1. **Missing REST APIs.** Transactions, obligations, and document-registry endpoints were documented as "🚧 Planned" and did not exist. The database tables and models existed; only the routes were missing.
2. **Fake document pipeline.** `POST /api/upload` returned HTTP 501, `GET /api/incoming-files` returned a hardcoded empty list, and `POST /api/process-incoming` was a no-op — while the frontend actively calls all three (upload UI, notification banner, "Process Now" button were dead ends).
3. **Duplicated, credential-bound evaluation.** Two evaluator classes with copy-pasted scoring logic lived inside scripts, always required a live LLM, and reported scores without explaining failures.

Also found and fixed a real bug: `scripts/ingest_documents.py`'s optimized PDF path called `read_pdf()` (which returns a tuple) and then `.encode()` on the result — every PDF crashed into the error handler and was reported as failed.

### What I changed

- Implemented full CRUD + filtering REST APIs for **transactions**, **obligations**, and **documents** (metadata registry), following the existing `properties.py` style.
- Implemented the **upload → incoming → process** vertical slice for real: files land in `documents/incoming/`, get chunked and embedded into ChromaDB (no LLM needed), get registered as `Document` rows with content hash + provenance + audit entry, and move to `documents/processed/`. Hash-based dedup skips duplicates.
- REST mutations now write to the previously-unused `audit_log` table via a shared `record_audit()` helper.
- Refactored evaluation into a shared package (`apps/evaluator/base_evaluator.py` + `chatbot_evaluator.py` + `airbnb_evaluator.py`) with **actionable failure records**, **Markdown reports**, and **fixture backends** so evaluations can run and be tested with zero credentials.
- 76 new tests (80 → 156 passing), coverage 40% → 54%. Docs updated to match reality.

### Why it matters

The platform is now demoable end-to-end without hand-waving: every business object has a working API, the frontend's document upload flow works against real endpoints, RAG answers carry inspectable sources, mutations leave an audit trail, and evaluation output tells you *why* a question failed instead of just that it did.

---

## 2. Repo Reality Map

### Implemented and tested

| Area | Location | Notes |
|------|----------|-------|
| Properties CRUD | `apps/api/routes/properties.py` | Pre-existing; unchanged |
| Transactions CRUD + filters | `apps/api/routes/transactions.py` | New. DELETE = archive via `extra_metadata.archived` (no status column on model) |
| Obligations CRUD + filters | `apps/api/routes/obligations.py` | New. DELETE = status=cancelled |
| Document registry CRUD | `apps/api/routes/documents.py` | New. DB-backed; distinct from vector-store listing at `/api/documents` |
| Upload/incoming/process pipeline | `apps/api/ingestion.py` + `apps/api/routes/chat.py` | New. Was 501/no-op stubs |
| Audit logging for REST mutations | `apps/api/routes/common.py::record_audit` | New. Chatbot Q&A audit logging pre-existed in `apps/chatbot/audit_logger.py` |
| Chat query + DSPy fallback | `apps/api/routes/chat.py`, `apps/dspy/runtime.py` | Pre-existing; DSPy is feature-flagged (`DSPY_ENABLED`), falls back to baseline RAG |
| RAG system (3 tools) | `apps/chatbot/` | Pre-existing. Sources include document title/page/sheet/row or DB query type |
| Evaluation harness | `apps/evaluator/{base,chatbot,airbnb}_evaluator.py` | Refactored + extended (fixtures, Markdown, failure records) |
| Airbnb ground truth + numerical validator | `apps/evaluator/airbnb_ground_truth.py`, `numerical_validator.py` | Pre-existing, now covered by tests |

### Stubbed / partial

- **DSPy pipeline** (`apps/dspy/pipelines.py`): scaffolding only — 0% test coverage, `artifacts/dspy-*` contains dummy/test artifacts. The runtime loader + fallback works, but there is no real retrieve→reason→verify program. See §5.
- **Chatbot-side vs core document type vocabularies differ** (`apps/chatbot/models.py::DocumentType` vs `core/database/enums.py::DocumentType`). The processor maps between them (`apps/api/ingestion.py::CHATBOT_TO_CORE_DOC_TYPE`); unifying them is future work.
- **Chunking config drift**: `scripts/ingest_documents.py` uses chunk_size=800/overlap=200; the app path (`apps/chatbot/config.py`) uses 3200/400. The API pipeline uses the app config. Documents ingested via the script vs the API will be chunked differently.
- **Vector store has legacy "course" code** (`apps/chatbot/vector_store.py` top half, `search_tools.py::CourseSearchTool`): dead weight from the codebase this was adapted from. Harmless but confusing.
- **`/api/documents/{title}`** (vector-store metadata by title) exists but the frontend doesn't use it much; the DB registry at `/api/v1/documents/{uuid}` is the system of record now.

### Docs claimed but code did not support (now fixed)

- `docs/api/{transactions,obligations,documents}.md` said "Planned"; endpoints now exist and docs updated.
- `docs/api/overview.md` referenced `/api/v1/chat/query` etc. — actual paths are `/api/query`, `/api/upload`, ... (fixed). It also documented a pagination envelope that never existed (fixed).
- Old transaction docs listed category values (`revenue:rental_income`, `expense:utilities:gas`) that don't match the real enum (`rental_income`, `utilities:gas`) — fixed; the enum in `core/database/enums.py` is authoritative.
- CLAUDE.md referenced `apps/evaluator/chatbot_evaluator.py`, which didn't exist (logic lived in the script). It exists now.

---

## 3. Implementation Details

### New files

| File | Purpose |
|------|---------|
| `apps/api/routes/common.py` | `parse_enum` (accepts name or value), `parse_enum_for_validator`, `record_audit` |
| `apps/api/routes/transactions.py` | Transactions CRUD + filters (property, date range, category, type, include_archived, limit) |
| `apps/api/routes/obligations.py` | Obligations CRUD + filters (status, type, property, due_before/due_after) |
| `apps/api/routes/documents.py` | Document metadata registry CRUD + filters (property, doc_type, filename search, confidentiality); 409 on duplicate content hash |
| `apps/api/ingestion.py` | Upload saving (sanitization, 50 MB cap, collision suffixes), incoming listing, processing (chunk → embed → register → move), hash dedup |
| `apps/evaluator/base_evaluator.py` | Shared eval loop, checks, failure records, JSON/Markdown reports, `FixtureBackend`/`RecordingBackend` |
| `apps/evaluator/chatbot_evaluator.py` | General eval scoring (tools 40% / content 40% / completeness 20%) |
| `apps/evaluator/airbnb_evaluator.py` | Airbnb scoring (tools 40% / numerical 50% / completeness 10%) with CSV ground truth |
| `tests/test_api_transactions.py` | 15 tests |
| `tests/test_api_obligations.py` | 16 tests |
| `tests/test_api_documents.py` | 17 tests |
| `tests/test_api_document_upload.py` | 10 tests (fake vector store, real text processing) |
| `tests/evaluator/test_base_evaluator.py` | 11 tests (backends, checks, end-to-end fixture eval, reports) |
| `tests/evaluator/test_airbnb_evaluator.py` | 8 tests (validator, ground truth, failure records) |

### Modified files

| File | Change |
|------|--------|
| `apps/api/main.py` | Register transactions/obligations/documents routers under `/api/v1` |
| `apps/api/routes/chat.py` | Replace upload/incoming-files/process-incoming stubs with real implementations delegating to `apps/api/ingestion` |
| `scripts/evaluate_chatbot.py` | Thin CLI over shared evaluator; new `--fixture`, `--record-fixture`, `--markdown` flags |
| `scripts/evaluate_airbnb.py` | Same |
| `scripts/evaluate_providers.py` | Import `ChatbotEvaluator` from `apps.evaluator`, adapt to `query_fn` interface (**not re-run live** — verify on next live eval) |
| `scripts/ingest_documents.py` | Fix PDF fast-path tuple bug |
| `.gitignore` | Add `/output/`, `/tmp/` (local artifacts) |
| `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `mkdocs.yml`, `docs/api/{overview,transactions,obligations,documents}.md` | Reality alignment |

### Design decisions worth knowing

- **Transaction soft delete without a migration.** `Transaction` has no status column. Rather than migrate, DELETE sets `extra_metadata.archived=true` (+ `archived_at`), records prior state in the audit log, and listings filter archived rows in Python (fine at this scale, avoids dialect-specific JSON queries). If transactions grow past ~tens of thousands, add a real `is_archived` column via Alembic.
- **Enum convention.** Inputs accept enum *name* (`UTILITIES_GAS`) or *value* (`utilities:gas`); responses emit values. Exception: `Property.status` serializes as the name (`ACTIVE`) — pre-existing behavior, left untouched.
- **No new DB migration was needed** — all tables existed in the initial Alembic revision.
- **Ingestion doesn't need an LLM.** `apps/api/ingestion.py` composes `DocumentProcessor` + `VectorStore` + `MetadataManager` directly (lazy import, injectable for tests via `reset_ingest_components`), so `/api/process-incoming` and `/api/incoming-files` work without `ANTHROPIC_API_KEY`. Note `GET /api/documents` (chat router) still instantiates the full RAG system and therefore *does* require a key — candidate for the same treatment.
- **JSON column mutation gotcha.** SQLAlchemy doesn't track in-place dict mutation; always reassign (`obj.extra_metadata = {**obj.extra_metadata, ...}`) as done in `archive_transaction`.

---

## 4. Verification

Commands run (2026-07-04, macOS, Python 3.13, `uv`):

```bash
# Baseline before changes
uv run pytest              # 80 passed, 6 skipped; coverage 40%

# After changes
uv run pytest tests/test_api_transactions.py tests/test_api_obligations.py \
              tests/test_api_documents.py --no-cov      # 48 passed
uv run pytest tests/test_api_document_upload.py --no-cov # 10 passed
uv run pytest tests/evaluator/ --no-cov                  # 18 passed
uv run pytest              # 156 passed, 6 skipped; coverage 54%

# Route registration smoke test
uv run python -c "from apps.api.main import app; ..."    # all /api/v1/* routes present

# Offline end-to-end eval smoke test (no credentials)
uv run python scripts/evaluate_chatbot.py \
    --eval-set <mini eval> --fixture <mini fixture> \
    --output report.json --markdown report.md            # 100%, both reports written

# Lint (scoped)
uv run ruff check <new files> --select F401,F841,F811,E722  # 1 unused import, fixed
```

**Known lint/type state:** the repo has ~1,574 pre-existing ruff findings (mostly `UP006`/`UP045` modern-typing-syntax and import sorting); new code intentionally matches the *existing* style (e.g. `Optional[X]`, `List[X]`) rather than introducing a second convention. `mypy` was not run (not previously enforced; would be a large cleanup).

**Not verified live** (requires `ANTHROPIC_API_KEY` and the real ChromaDB store; deliberately avoided per instructions):

- Live `scripts/evaluate_chatbot.py` / `evaluate_airbnb.py` runs (fixture mode verified instead)
- `scripts/evaluate_providers.py` (import/interface updated; needs one live run to confirm)
- End-to-end `POST /api/process-incoming` against the real ChromaDB + ONNX embedding model (fake-store test verified logic; embedding path is the same one `scripts/ingest_documents.py` already exercises)

---

## 5. Remaining Work

### Do next with a powerful model

1. **Real DSPy pipeline (Phase 6-7).** Build an actual retrieve→reason→verify program in `apps/dspy/pipelines.py`, train/compile against the eval sets, save via the existing artifact loader, and A/B against baseline with `scripts/eval_dspy_vs_baseline.py`. The runtime plumbing (`DSPY_ENABLED`, artifact validation, fallback) already exists and is the *right* integration point. Don't start until you've run the baseline eval and have numbers to beat.
2. **Unify the two DocumentType vocabularies** (chatbot vs core enum) — touches ingestion, vector store metadata, search tool definitions, and the metadata CSV; needs care not to orphan existing ChromaDB metadata (probably requires a re-ingest).
3. **Source-grounded answer verification.** The eval harness now surfaces sources per answer; a natural next step is checking that claimed numbers actually appear in the cited sources (evidence expectations per question).

### Safe to delegate to a weaker model

- Retrofit `record_audit()` into `apps/api/routes/properties.py` (pattern established in the three new route modules; copy it).
- Remove legacy "course" code from `apps/chatbot/vector_store.py`, `search_tools.py`, `models.py` and the `tests/chatbot/test_course_search_tool.py` compatibility layer.
- Align `scripts/ingest_documents.py` chunking constants with `apps/chatbot/config.py` (or make the script read Config).
- Make `GET /api/documents` (chat router) use the lightweight ingestion components instead of the full RAG system, so listing works without an API key.
- Expand eval sets to 40+ questions (JSONL format is documented in the evaluator module docstrings).
- Run `ruff check --fix` repo-wide and commit the mechanical cleanup (review the ~29 unsafe fixes by hand).
- Add `gold_answer` fields to existing eval-set questions (the failure records already surface them).

### Manual / local-only verification

- One live evaluation run: `uv run python scripts/evaluate_chatbot.py --record-fixture output/chatbot_fixture.json --markdown output/eval_report.md` — this both verifies the refactor against the real LLM and produces the first reusable offline fixture.
- One real upload → process → query round-trip via the frontend (steps in §6).
- Confirm `scripts/evaluate_providers.py` still works if you use multi-provider comparison.

### Risks / gotchas

- `chroma_db/` and `poolula.db` are local state; tests never touch them, but `POOLULA_INCOMING_DIR`/`POOLULA_PROCESSED_DIR` default inside `documents/` which is gitignored — keep it that way (private data).
- The vector store keys documents by **title** (`document_catalog` IDs); two different files with the same inferred title would collide in Chroma (pre-existing behavior; hash dedup makes it unlikely but not impossible).
- `FixtureBackend` raises `KeyError` for unrecorded questions — the eval loop catches it and scores 0 with the reason in the failure record, which is intended, but don't be surprised by all-zero runs against a mismatched fixture.

---

## 6. Demo Path

```bash
# 0. Install
uv sync --group rag

# 1. Environment
cp .env.example .env   # set ANTHROPIC_API_KEY=sk-ant-... (chat + live eval only)

# 2. Database: migrate + seed
.venv/bin/alembic upgrade head
uv run python scripts/seed_database.py --initial
uv run python scripts/seed_obligations.py

# 3. Start the API + frontend
uv run uvicorn apps.api.main:app --reload --port 8082
# open http://localhost:8082  (frontend)  /  http://localhost:8082/docs  (Swagger)

# 4. Business object APIs
curl http://localhost:8082/api/v1/properties
curl "http://localhost:8082/api/v1/transactions?category=rental_income&start_date=2025-01-01"
curl "http://localhost:8082/api/v1/obligations?status=pending&due_before=2026-12-31"

# 5. Document pipeline (no LLM key needed for this part)
curl -X POST http://localhost:8082/api/upload -F "file=@documents/poolula-llc-binder-table-of-contents.md"
curl http://localhost:8082/api/incoming-files
curl -X POST http://localhost:8082/api/process-incoming
curl http://localhost:8082/api/v1/documents          # registered with hash + provenance
curl http://localhost:8082/api/documents             # visible in vector store

# 6. Ask the chatbot (needs API key); answers include a sources array
curl -X POST http://localhost:8082/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was my rental income in August 2025?"}'

# 7. Evaluation
# Live (records a fixture for future offline runs + writes a Markdown failure report):
uv run python scripts/evaluate_chatbot.py \
  --record-fixture output/chatbot_fixture.json --markdown output/eval_report.md
# Offline replay thereafter (no credentials):
uv run python scripts/evaluate_chatbot.py --fixture output/chatbot_fixture.json
# Airbnb numerical-accuracy eval against CSV ground truth:
uv run python scripts/evaluate_airbnb.py --markdown output/airbnb_eval_report.md

# 8. Tests
uv run pytest        # 156 passed, 6 skipped
```

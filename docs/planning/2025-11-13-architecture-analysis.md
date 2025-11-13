# Poolula Platform - Architecture Analysis & Strategic Planning

**Date**: November 13, 2025
**Status**: Foundation Phase - Pre-Implementation
**Decision**: Hybrid Data-First Modular Monolith + Workflow UI Layer

---

## Executive Summary

After comprehensive analysis of four architectural approaches, we selected a **Hybrid Architecture** combining:
- **Data-First Modular Monolith** for technical foundation
- **Workflow-Oriented UI Layer** for user experience

This approach maximizes the three core principles while maintaining solo-developer feasibility:
- **UNDERSTANDING**: Explicit data models, traceable calculations, step-by-step workflows
- **TRANSPARENCY**: Provenance tracking, audit logs, source citations
- **USER FRIENDLINESS**: Task-based navigation, progressive disclosure, guided wizards

**Migration Effort**: 6-8 weeks phased rollout
**Risk Level**: Medium (manageable with incremental approach)
**Scalability**: Can split to microservices if needed in future

---

## Context & Vision

### Business Context
**Poolula LLC** is a Colorado single-member LLC that owns and operates rental properties (currently one Airbnb property at 900 S 9th St, Montrose, CO). The LLC is owned by the Hidalgo-Sotelo Living Trust.

### Platform Vision
Build an integrated management platform that handles:
- Operational analytics (revenue, expenses, occupancy)
- AI-powered Q&A for compliance and governance
- Quality assurance and accuracy validation
- **Future**: Tax preparation, compliance calendar, document vault, financial reporting

### Current State (Pre-Consolidation)

**Project 1: RAG Chatbot** (`ragchatbot-codebase/`)
- Size: 56 files, 7.7 MB
- Tech: FastAPI, ChromaDB, Anthropic Claude, Vue 3 frontend
- Status: Production-ready with 32 passing tests (100% pass rate)
- Features: Document Q&A, semantic search, citation tracking, session management
- Git: Yes, with remote repository

**Project 2: Airbnb Dashboard** (`AirBnB Dashboard/dashboard/`)
- Size: 7 files, 108 KB
- Tech: Streamlit, pandas, plotly
- Status: Feature-complete, working in production
- Features: Revenue analytics, booking intelligence, KPI tracking, CSV upload
- Git: No

**Project 3: Evaluation Harness** (`AirBnB Dashboard/evaluation/`)
- Size: 3 files (YAML, JSONL, MD specs)
- Status: Design specifications only, not yet implemented
- Purpose: Validate chatbot accuracy against golden Q&A sets (≥90% threshold)
- Features: Regex-based grading, refusal detection, critical failure flagging

---

## Four Architectural Options Evaluated

### Option A: Data-First Modular Monolith ⭐ SELECTED (as base)

**Philosophy**: Build single source of truth first, layer applications on top.

**Structure**:
```
poolula-platform/
├── core/                     # Platform foundation
│   ├── database/            # SQLModel: Property, Transaction, Document, Obligation
│   ├── vector_store/        # ChromaDB for semantic search
│   ├── schemas/             # Pydantic models for type safety
│   ├── services/            # Business logic with provenance tracking
│   └── repositories/        # Data access patterns
├── apps/                     # Feature modules
│   ├── chatbot/
│   ├── analytics/
│   ├── evaluator/
│   └── [future tools]
├── workflows/                # Task orchestration
├── frontend/                 # Vue 3 unified UI
└── tests/
```

**Pros**:
- ✅ Clear separation of concerns (data, logic, UI)
- ✅ Shared database = single source of truth
- ✅ Easy to understand (linear dependency graph)
- ✅ Straightforward testing
- ✅ Can split to microservices later if needed
- ✅ Optimal for solo developer

**Cons**:
- ❌ All code in one repo (becomes large over time)
- ❌ Must coordinate deployments (can't deploy just chatbot)

**Alignment with Principles**:
- **UNDERSTANDING**: ⭐⭐⭐⭐⭐ - Explicit data model, traceable logic
- **TRANSPARENCY**: ⭐⭐⭐⭐⭐ - Central audit log, provenance everywhere
- **USER FRIENDLINESS**: ⭐⭐⭐⭐ - Unified UI, consistent UX

---

### Option B: Micro-Frontend + API Gateway

**Philosophy**: Independent services communicating through API gateway.

**Structure**:
```
poolula-platform/
├── gateway/                  # Kong/Nginx with auth
├── services/
│   ├── chatbot-service/     # Port 8001
│   ├── analytics-service/   # Port 8002
│   ├── data-service/        # Port 8003 (single source of truth)
│   └── eval-service/        # Port 8004
├── shared/
│   ├── events/              # RabbitMQ/Kafka
│   └── schemas/
└── frontend-shell/          # Micro-frontend container
```

**Pros**:
- ✅ True polyglot (different tech per service)
- ✅ Independent deployment
- ✅ Horizontal scaling

**Cons**:
- ❌ **Complexity overhead**: Docker, message queue, service mesh, distributed tracing
- ❌ **Network latency**: 50-200ms per cross-service call
- ❌ **Distributed transactions**: Hard to maintain consistency
- ❌ **Debugging nightmare**: Logs scattered across 5+ services
- ❌ **Overkill for solo dev**: 10x infrastructure

**Verdict**: ⚠️ NOT RECOMMENDED. Over-engineered for current scale.

---

### Option C: Plugin Architecture

**Philosophy**: Core runtime with hot-loadable plugin modules.

**Structure**:
```
poolula-platform/
├── core/
│   ├── plugin_manager.py    # Discovery, loading, lifecycle
│   ├── event_bus.py         # Pub/sub
│   └── api_server.py        # Dynamic routes
├── plugins/
│   ├── airbnb-analytics/
│   ├── rag-assistant/
│   └── eval-harness/
└── frontend/
    └── PluginHost.vue       # Dynamic component loader
```

**Pros**:
- ✅ Extreme modularity
- ✅ Enable/disable features per deployment
- ✅ Third-party extensions possible

**Cons**:
- ❌ **Complex plugin contract**: Versioning, compatibility matrix
- ❌ **Security risk**: Plugins have full system access
- ❌ **Over-engineering**: Don't need third-party plugins
- ❌ **Testing complexity**: Must test all plugin combinations

**Verdict**: ⚠️ Interesting but unnecessary complexity.

---

### Option D: Workflow-First Architecture

**Philosophy**: Organize around user tasks, not technical components.

**Structure**:
```
poolula-platform/
├── workflows/               # Top-level: USER TASKS
│   ├── monthly_close/
│   │   ├── workflow.py
│   │   ├── steps/
│   │   │   ├── 1_import_transactions.py
│   │   │   ├── 2_categorize_expenses.py
│   │   │   ├── 3_reconcile_accounts.py
│   │   │   └── 4_generate_reports.py
│   │   └── frontend/
│   ├── tax_preparation/
│   ├── ask_question/        # RAG as a workflow
│   └── compliance_check/
├── engines/                 # Reusable capabilities
│   ├── rag/
│   ├── analytics/
│   └── calculation/
└── data/
```

**Pros**:
- ✅ **Intuitive UX**: Users think in tasks, not tools
- ✅ **Clear progress**: "Step 2 of 5" makes sense
- ✅ **Explainable**: Each step visible
- ✅ **Easy testing**: Defined inputs/outputs

**Cons**:
- ❌ **Code duplication**: Multiple workflows need similar engines
- ❌ **Less flexible**: Ad-hoc exploration harder
- ❌ **Upfront design**: Must plan all workflows before building

**Verdict**: ⚡ Great UX pattern, but needs solid foundation underneath.

---

## Selected Architecture: Hybrid Approach

**Decision**: Combine Option A (foundation) + Option D (UX layer)

### Why This Wins

**Foundation = Option A (Data-First Modular Monolith)**:
- Single codebase, clear boundaries
- Central database + vector store
- Service layer with provenance
- Repository pattern

**User Experience = Option D (Workflow UI Layer)**:
- Workflow-oriented for guided tasks
- ALSO allow ad-hoc exploration (chat, browsing)
- Progressive disclosure for transparency
- Task-based home screen

### Alignment with Principles

**1. UNDERSTANDING**:
- Explicit data model with documentation
- Calculations show their work:
  ```python
  {
    "result": 13247.27,
    "formula": "basis / years",
    "inputs": {"basis": 364100, "years": 27.5},
    "source": "IRS Pub 527 p.15"
  }
  ```
- Workflows break complex tasks into understandable steps
- "Show me how" button on every result

**2. TRANSPARENCY**:
- Provenance on all data:
  ```python
  {
    "value": 364100,
    "source_doc": "settlement_statement.pdf",
    "source_page": 3,
    "imported_at": "2024-04-15T10:30:00Z",
    "verified_by": "trustee"
  }
  ```
- Audit log tracks changes:
  ```python
  {
    "timestamp": "2024-11-13T14:30:00Z",
    "user": "trustee",
    "action": "updated_basis",
    "old_value": 442300,
    "new_value": 442500,
    "reason": "corrected per final HUD-1"
  }
  ```
- Chat responses cite sources: "According to your operating agreement (§3.2)..."
- Every number clickable to see lineage

**3. USER FRIENDLINESS**:
- Home screen: "What do you want to do today?" with task cards
- Workflows: "Close the month" → guided 5-step wizard
- Exploration: "Ask anything" → chatbot with full context
- Consistency: Same navigation, styling, patterns across all features
- Progressive disclosure: Simple by default, "show more" for details

---

## Strategic Tradeoff Matrix

| Criterion | Option A (Modular) | Option B (Microservices) | Option C (Plugin) | Option D (Workflow) | **Hybrid** |
|-----------|-------------------|------------------------|------------------|-------------------|-----------|
| **UNDERSTANDING** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **TRANSPARENCY** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **USER FRIENDLINESS** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **Solo Dev Effort** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **⭐⭐⭐⭐** |
| **Future Scaling** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **⭐⭐⭐⭐** |
| **Migration Effort** | 🔵 Medium | 🔴 High | 🔴 High | 🟡 Med-High | **🔵 Medium** |
| **Code Reuse** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** |

---

## Migration Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Build the data layer and core infrastructure

**Tasks**:
- [ ] Create repository structure
- [ ] Set up SQLite database with core schema:
  - Property (address, purchase_price, basis_allocation, placed_in_service)
  - Transaction (date, amount, category, description, source_account, provenance)
  - Document (filename, doc_type, effective_date, entities, version, confidence_level)
  - Obligation (type, due_date, status, recurrence, description)
  - AuditLog (timestamp, user, action, entity_type, entity_id, old_value, new_value, reason)
- [ ] Implement provenance tracking service
- [ ] Build audit log infrastructure
- [ ] Set up FastAPI with SQLModel
- [ ] Write database access repositories
- [ ] Create seed script to migrate `poolula_facts.yml` → database

**Deliverable**: Working API with CRUD operations, provenance tracking, all tests passing

**Risk Assessment**:
- 🟡 **Schema design**: May need iterations as we understand data better
  - *Mitigation*: Use Alembic migrations, can evolve schema easily
- 🟢 **Tech stack**: SQLModel + FastAPI well-documented
- 🟡 **Data migration**: YAML → SQL may reveal inconsistencies
  - *Mitigation*: Start with manual review, add validation

---

### Phase 2: Integrate Chatbot (Weeks 3-4)
**Goal**: Move RAG system into platform, enhance with database queries

**Tasks**:
- [ ] Copy RAG codebase into `apps/chatbot/`
- [ ] Update imports and structure
- [ ] Enhance search tools to query database (not just vector store)
  - Example: "Show Q3 revenue" → SQL query on Transaction table
  - Example: "What's my depreciation?" → Calculation service + provenance
- [ ] Connect to audit log (track questions asked, answers given)
- [ ] Build unified API layer (merge chatbot endpoints into main FastAPI app)
- [ ] Migrate tests
- [ ] Update documentation

**Deliverable**: Chatbot works via new API, can answer DB-backed + document-backed questions

**Risk Assessment**:
- 🟢 **Technical**: Chatbot is well-tested, low risk
- 🟡 **Tool integration**: Need to design how Claude tools call database
  - *Mitigation*: Start with simple SQL query tool, iterate
- 🟢 **Testing**: Existing 32 tests can be ported

**Key Decision Point**:
- **How should chatbot access data?**
  - Option 1: Direct SQL queries (fast, simple)
  - Option 2: Through service layer (cleaner, more abstraction)
  - **Recommendation**: Option 2 for consistency and testability

---

### Phase 3: Integrate Dashboard (Week 5)
**Goal**: Migrate Airbnb analytics to database-backed system

**Tasks**:
- [ ] Import Airbnb CSV data into Transaction table
- [ ] Build analytics service with aggregation functions
- [ ] Create API endpoints for dashboard metrics:
  - `/api/analytics/revenue` - Monthly revenue, net income
  - `/api/analytics/bookings` - Booking patterns, lead times
  - `/api/analytics/occupancy` - Occupancy rates, stay lengths
- [ ] Either:
  - Option A: Keep Streamlit, point at new API
  - Option B: Rewrite as Vue components
- [ ] Add provenance to all metrics (e.g., "Revenue from airbnb_nov_2024.csv")

**Deliverable**: Dashboard shows live data from database, CSV uploads persist

**Risk Assessment**:
- 🟡 **Data migration**: CSV structure might not match DB schema perfectly
  - *Mitigation*: Write robust importer with validation and error reporting
- 🟡 **UI decision**: Streamlit vs Vue rewrite
  - *Mitigation*: Start with Streamlit (faster), migrate UI later if needed

**Key Decision Point**:
- **Rewrite dashboard in Vue now or later?**
  - Rewrite now: 2 weeks extra, unified UX
  - Keep Streamlit: 2 days, works but separate UI
  - **Recommendation**: Keep Streamlit initially (embedded in iframe), rewrite in Phase 5

---

### Phase 4: Implement Evaluation Harness (Week 6)
**Goal**: Build quality assurance system per specs

**Tasks**:
- [ ] Implement harness per `eval_harness_spec.md`
- [ ] Load golden set from `poolula_eval_set.jsonl`
- [ ] Build evaluation runner:
  - Send questions to chatbot API
  - Score responses (regex match, refusal detection)
  - Calculate weighted score
  - Flag critical failures
- [ ] Store evaluation results in database (track over time)
- [ ] Build evaluation dashboard:
  - Overall score trend
  - Per-question pass/fail
  - Critical failure alerts
- [ ] Set up CI integration (block deployment if score < 90%)

**Deliverable**: Automated testing of chatbot accuracy, score trending

**Risk Assessment**:
- 🟢 **Specs are clear**: Well-defined in existing docs
- 🟡 **Regex brittleness**: May need to tune regexes
  - *Mitigation*: Make regexes configurable, easy to adjust
- 🟢 **Integration**: Harness just calls chatbot API, decoupled

---

### Phase 5: Frontend Unification (Weeks 7-8)
**Goal**: Build cohesive Vue 3 interface with workflow support

**Tasks**:
- [ ] Create Vue 3 project with Vite
- [ ] Design navigation structure:
  - Home: Task cards ("What do you want to do?")
  - Ask: Chat interface
  - Analyze: Dashboard (embed Streamlit initially)
  - Evaluate: Harness results
  - Settings: Configuration
- [ ] Build workflow framework:
  - Generic Workflow.vue component (progress bar, step navigation)
  - WorkflowStep.vue components
- [ ] Implement proof-of-concept workflow: "Monthly Close"
  - Step 1: Upload/review transactions
  - Step 2: Categorize uncategorized expenses
  - Step 3: Review financial summary
  - Step 4: Generate reports
  - Step 5: Mark period as closed
- [ ] Implement progressive disclosure patterns:
  - Default: Simple metric card ("Revenue: $12,345")
  - Click "Details": Show breakdown
  - Click "Source": Show provenance and audit trail
- [ ] Build responsive layout (desktop primary, mobile-friendly)

**Deliverable**: Unified web app with consistent UX, first workflow operational

**Risk Assessment**:
- 🟡 **UI/UX design**: Requires thoughtful design
  - *Mitigation*: Use established UI library (Vuetify or similar), iterate based on usage
- 🟡 **Frontend-backend contract**: API design must support workflow needs
  - *Mitigation*: Design API endpoints alongside UI mockups
- 🟢 **Tech stack**: Vue 3 + Vite well-supported

---

### Phase 6: Future Tools (Ongoing)

**Planned additions**:
1. **Tax Assistant** (Weeks 9-12)
   - Form 1065 wizard
   - Schedule E automation
   - K-1 generation
   - Depreciation calculator (27.5-year schedule)

2. **Compliance Calendar** (Weeks 13-14)
   - Obligation tracking (CO periodic report, insurance renewal, tax deadlines)
   - Email reminders
   - Status dashboard

3. **Document Vault** (Weeks 15-16)
   - Centralized storage with metadata
   - OCR for scanned documents
   - Version tracking
   - Access control

4. **Expense Categorization** (Weeks 17-18)
   - Transaction import from bank statements
   - AI-powered categorization
   - Chart of accounts mapping
   - Review and approval workflow

---

## Transparency Features to Implement

### 1. Provenance Schema

Every data point tracks its origin:

```python
class Provenance(BaseModel):
    source_type: str              # "manual_entry", "csv_import", "calculation", "ai_generated"
    source_id: Optional[str]      # Document ID, CSV filename, etc.
    source_field: Optional[str]   # Field in source document
    created_at: datetime
    created_by: str               # User or system component
    confidence: float             # 0.0-1.0 for AI-generated content
    verification_status: str      # "unverified", "verified", "disputed"
```

### 2. Explainable Calculations

All financial calculations return structured explanations:

```python
class ExplainedResult(BaseModel):
    value: Decimal
    unit: str                     # "USD", "days", "percentage"
    explanation: str              # Human-readable summary
    formula: str                  # Mathematical formula
    inputs: dict[str, Any]        # Input values used
    sources: list[Source]         # What documents/data sourced this
    computed_at: datetime
    computed_by: str              # Service that performed calculation
    confidence: float             # 1.0 for deterministic, <1.0 for estimates
```

Example:
```python
{
  "value": 13247.27,
  "unit": "USD",
  "explanation": "Annual depreciation for building using 27.5-year straight-line method per IRS Pub 527",
  "formula": "depreciable_basis ÷ recovery_period",
  "inputs": {
    "depreciable_basis": 364100.00,
    "recovery_period": 27.5
  },
  "sources": [
    {"type": "document", "id": "articles_of_org", "field": "basis.building"},
    {"type": "regulation", "id": "irs_pub_527", "section": "2"}
  ],
  "computed_at": "2024-11-13T10:30:00Z",
  "computed_by": "depreciation_service",
  "confidence": 1.0
}
```

### 3. Audit Trail UI

Every editable field has history:
- Click "history" icon → timeline view
- See who changed what, when, why
- Diff view (old value → new value)
- Undo capability (with approval workflow for critical fields)

### 4. Citation in Chat Responses

```
User: "What's my depreciable basis?"

Assistant: "Your depreciable basis for the building is $364,100."

**Sources:**
1. Articles of Organization (2024-04-15), Section: Property Acquisition
   - Building and improvements: $364,100
   - [View document →]
2. Settlement Statement (HUD-1), Page 3, Line 801
   - Total consideration allocated to improvements
   - [View document →]

**Note:** Land ($78,200) is not depreciable per IRS regulations.

[Why this amount?] → Shows calculation breakdown
[History] → Shows if/when this value was updated
```

---

## Risk Management Strategy

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Database schema changes** | Medium | Medium | Use Alembic migrations, version all changes, test rollback |
| **Legacy data inconsistencies** | Medium | Low | Validate during import, flag issues, provide correction UI |
| **API breaking changes** | Low | High | Version APIs (v1, v2), deprecate gradually, document changes |
| **Frontend-backend contract drift** | Medium | Medium | Use OpenAPI/TypeScript codegen, shared Pydantic models |
| **Performance degradation** | Low | Medium | Index database properly, cache queries, monitor with alerts |
| **Data loss during migration** | Low | Very High | Backup before each phase, test restore, keep legacy systems running parallel |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Over-engineering** | Medium | Medium | Start MVP, add features only when needed, measure value |
| **Scope creep** | High | High | Stick to phased plan, defer "nice-to-haves" to Phase 6+ |
| **Solo dev burnout** | Medium | Very High | Work sustainable hours, celebrate small wins, take breaks |
| **Feature abandonment** | Medium | Medium | Focus on high-value features first (chatbot, dashboard), others are bonus |
| **User adoption friction** | Low | Medium | Keep existing UIs working during transition, provide migration guides |

### Data Quality Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Provenance tracking overhead** | Low | Low | Make it automatic where possible, UI helpers for manual entry |
| **Audit log bloat** | Low | Low | Implement retention policy, archive old logs, summarize redundant entries |
| **Confidence scores misinterpreted** | Medium | Medium | Clear UI labels, tooltips, documentation on what scores mean |
| **Source citation errors** | Low | High | Validate citations automatically, allow user corrections, flag suspicious ones |

---

## Success Metrics

### Phase 1 (Foundation) Success Criteria
- [ ] Database schema documented and peer-reviewed
- [ ] All CRUD operations have tests with 100% pass rate
- [ ] Provenance tracking works for manual entries and imports
- [ ] Audit log captures all database mutations
- [ ] Seed script successfully migrates poolula_facts.yml
- [ ] API documentation auto-generated and accessible

### Phase 2 (Chatbot) Success Criteria
- [ ] All 32 existing tests passing in new structure
- [ ] Chatbot can answer DB-backed questions ("What's my Q3 revenue?")
- [ ] Chatbot can answer document-backed questions ("What does lease say about pets?")
- [ ] Hybrid queries work ("Show revenue per operating agreement terms")
- [ ] Audit log tracks all questions and answers
- [ ] Response time <3s for 95% of queries

### Overall Platform Success Criteria
- [ ] All three core principles demonstrably achieved
- [ ] User can complete end-to-end workflows without friction
- [ ] System passes evaluation harness with ≥90% score
- [ ] Zero data loss during migration from legacy systems
- [ ] Performance meets or exceeds targets
- [ ] Documentation complete and usable

---

## Conclusion & Next Actions

### Decision Summary
**Selected Architecture**: Hybrid Data-First Modular Monolith + Workflow UI Layer

**Rationale**:
- Maximizes UNDERSTANDING (explicit, traceable)
- Maximizes TRANSPARENCY (provenance, audit logs)
- Maximizes USER FRIENDLINESS (workflows, progressive disclosure)
- Feasible for solo developer (6-8 weeks phased approach)
- Future-proof (can split to microservices if needed)

### Immediate Next Steps (Week 1)
1. ✅ Create `poolula-platform` repository
2. ✅ Write README.md
3. ✅ Document architectural analysis (this file)
4. ⏭️ Create initial git commit
5. ⏭️ Set up Python project structure (pyproject.toml, .gitignore, .env.example)
6. ⏭️ Design database schema (ERD diagram)
7. ⏭️ Implement first table (Property) with provenance
8. ⏭️ Write first API endpoint (/api/properties)
9. ⏭️ Write first test
10. ⏭️ Celebrate first green test! 🎉

### Key Questions for User

1. **Database choice**: Start with SQLite or PostgreSQL from day 1?
   - SQLite: Simpler setup, file-based, easy backup
   - PostgreSQL: More features, better for production, requires Docker/server
   - **Recommendation**: SQLite for Phases 1-5, PostgreSQL when deploying

2. **Dashboard migration timing**: Keep Streamlit in Phase 3 or rewrite to Vue?
   - Keep: Faster (2 days), works now, iframe embed acceptable
   - Rewrite: Unified UX (2 weeks), native integration, consistent styling
   - **Recommendation**: Keep for Phase 3, rewrite in Phase 5 alongside other UI work

3. **Auth/user management**: Build now or defer?
   - Now: Proper multi-user support from day 1
   - Defer: Single-user for MVP, add later
   - **Recommendation**: Defer to Phase 6, use simple API key for now

4. **Deployment target**: Local-only, cloud VM, or container platform?
   - Local: Simplest, no hosting costs
   - VM: Traditional, full control, manual updates
   - Container: Modern, easier updates, requires Docker knowledge
   - **Recommendation**: Local for dev, cloud VM for production (DigitalOcean/Linode)

---

**Document Version**: 1.0
**Author**: Architecture planning session
**Date**: November 13, 2025
**Status**: Approved - Ready for implementation

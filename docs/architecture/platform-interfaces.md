# Platform Interfaces Architecture

**How to interact with Poolula Platform's business objects**

---

## Overview

Poolula Platform provides multiple interfaces for interacting with business objects, each optimized for different use cases. This document describes how each interface accesses data and when to use which interface.

---

## System Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  USER INTERFACES                                                │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   CLI    │  │ Chatbot  │  │ Jupyter  │  │  Vue UI  │       │
│  │ poolula  │  │  (AI)    │  │ Notebooks│  │  (Web)   │       │
│  │          │  │          │  │          │  │          │       │
│  │ Commands │  │ Natural  │  │ Exploratory│ │ Visual  │       │
│  │ Scripts  │  │ Language │  │ Analysis │  │ Workflows│       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │             │             │
│       └─────────────┴──────────────┴─────────────┘             │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────┐
│  API LAYER (FastAPI REST)│                                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  /api/v1/properties      - Property CRUD                │  │
│  │  /api/v1/transactions    - Transaction CRUD & import    │  │
│  │  /api/v1/documents       - Document upload & search     │  │
│  │  /api/v1/obligations     - Obligation tracking          │  │
│  │  /api/v1/analytics       - Computed metrics & reports   │  │
│  │  /api/chatbot/query      - AI-powered Q&A              │  │
│  │  /health                 - System health check          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────┐
│  BUSINESS LOGIC LAYER    ▼                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Service Layer (apps/*/services.py)                     │  │
│  │  ├── PropertyService     - Property management          │  │
│  │  ├── TransactionService  - Import, categorization       │  │
│  │  ├── DocumentService     - OCR, versioning              │  │
│  │  ├── ObligationService   - Recurrence, reminders        │  │
│  │  └── AnalyticsService    - Reporting, aggregations      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Cross-Cutting Concerns                                 │  │
│  │  ├── Provenance Tracking - Auto-populate source data    │  │
│  │  ├── Audit Logging       - Record all mutations         │  │
│  │  └── Validation          - Enforce business rules       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────┐
│  DATA LAYER              ▼                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SQLModel ORM (core/database/models.py)                 │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────────┐ ┌──────────┐            │  │
│  │  │ Property │ │ Transaction  │ │ Document │            │  │
│  │  └────┬─────┘ └──────┬───────┘ └────┬─────┘            │  │
│  │       │              │              │                   │  │
│  │  ┌────┴──────────────┴──────────────┴─────┐            │  │
│  │  │ Obligation │ AuditLog │ Provenance     │            │  │
│  │  └────────────────────────────────────────┘            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SQLite Database (poolula.db)                           │  │
│  │  → PostgreSQL (production scaling)                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  ChromaDB Vector Store (apps/chatbot/)                  │  │
│  │  - Document embeddings for semantic search              │  │
│  │  - Business document Q&A context                        │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Interface Comparison Matrix

| Interface | Best For | Read Objects | Write Objects | Learning Curve | Speed |
|-----------|----------|--------------|---------------|----------------|-------|
| **CLI** | Automation, scripting, bulk operations | All | All | Low (if CLI-comfortable) | Fastest |
| **Chatbot** | Ad-hoc questions, new users, exploration | All | None (read-only initially) | Lowest (natural language) | Fast |
| **Jupyter** | Data analysis, experimentation, reports | All | All | Medium (Python knowledge) | Medium |
| **Vue UI** | Daily operations, workflows, visual review | All | All | Low (web interface) | Medium |
| **API** | Integration, programmatic access | All | All | High (developer tool) | Fastest |

---

## Interface Capabilities by Object

### Property

| Operation | CLI | Chatbot | Jupyter | Vue UI | API |
|-----------|-----|---------|---------|--------|-----|
| **Create** | ✅ `poolula create-property` | ❌ Read-only | ✅ Python code | ✅ Form wizard | ✅ POST /api/v1/properties |
| **Read** | ✅ `poolula list-properties` | ✅ "Show my properties" | ✅ `session.query()` | ✅ Property list view | ✅ GET /api/v1/properties |
| **Update** | ✅ `poolula update-property <id>` | ❌ Read-only | ✅ Python code | ✅ Edit form | ✅ PATCH /api/v1/properties/{id} |
| **Delete** | ✅ `poolula delete-property <id>` | ❌ Read-only | ✅ Python code | ✅ Delete button | ✅ DELETE /api/v1/properties/{id} |
| **View Basis** | ✅ `poolula show-basis` | ✅ "What's my depreciable basis?" | ✅ Custom calculation | ✅ Basis card | ✅ GET property, compute |

### Transaction

| Operation | CLI | Chatbot | Jupyter | Vue UI | API |
|-----------|-----|---------|---------|--------|-----|
| **Import CSV** | ✅ `poolula import-csv <file>` | ❌ | ✅ `import_airbnb_csv()` | ✅ Upload widget | ✅ POST /api/v1/transactions/import |
| **Categorize** | ✅ `poolula review-transactions` | ✅ "Categorize my expenses" | ✅ Bulk update | ✅ Workflow | ✅ PATCH bulk update |
| **Search** | ✅ `poolula search-transactions` | ✅ "Show Oct utilities" | ✅ Pandas filter | ✅ Filter controls | ✅ GET with query params |
| **Analyze** | ❌ (Use Jupyter) | ✅ "What was Q3 revenue?" | ✅ Pandas/Matplotlib | ✅ Dashboard charts | ✅ GET /api/v1/analytics |

### Document

| Operation | CLI | Chatbot | Jupyter | Vue UI | API |
|-----------|-----|---------|---------|--------|-----|
| **Upload** | ✅ `poolula upload-doc <file>` | ❌ | ✅ Python code | ✅ Drag-and-drop | ✅ POST /api/v1/documents/upload |
| **Search** | ✅ `poolula search-docs <query>` | ✅ "Find my lease" | ✅ Full-text search | ✅ Search bar | ✅ GET /api/v1/documents/search |
| **OCR** | ✅ `poolula ocr-doc <id>` | ❌ | ✅ Trigger OCR | ✅ OCR button | ✅ POST /api/v1/documents/{id}/ocr |
| **Version** | ✅ `poolula upload-version <id>` | ❌ | ✅ Python code | ✅ Upload new version | ✅ POST with version param |

### Obligation

| Operation | CLI | Chatbot | Jupyter | Vue UI | API |
|-----------|-----|---------|---------|--------|-----|
| **Create** | ✅ `poolula add-obligation` | ❌ | ✅ Python code | ✅ Calendar + form | ✅ POST /api/v1/obligations |
| **View Calendar** | ❌ (text only) | ✅ "What's due this month?" | ✅ Calendar lib | ✅ Calendar view | ✅ GET upcoming |
| **Complete** | ✅ `poolula complete <id>` | ❌ | ✅ Status update | ✅ Checkbox | ✅ PATCH /api/v1/obligations/{id} |
| **Recurring** | ✅ RRULE in args | ✅ "Add annual property tax" | ✅ RRULE builder | ✅ Recurrence wizard | ✅ POST with RRULE |

### AuditLog

| Operation | CLI | Chatbot | Jupyter | Vue UI | API |
|-----------|-----|---------|---------|--------|-----|
| **View History** | ✅ `poolula audit-trail <id>` | ✅ "Show changes to property" | ✅ Query logs | ✅ Timeline view | ✅ GET /api/audit/{entity_id} |
| **Filter** | ✅ Grep/jq filters | ✅ "Who changed basis?" | ✅ Pandas filter | ✅ Filter controls | ✅ Query params |
| **Export** | ✅ `poolula export-audit` | ❌ | ✅ Export to CSV | ✅ Download button | ✅ GET with format=csv |

---

## Interface Details

### 1. CLI (Command Line Interface)

**Implementation**: Python Click/Typer framework
**Entry Point**: `poolula` command (installed via `uv run poolula` or symlink)

#### Key Commands

```bash
# Property Management
poolula list-properties                    # List all properties
poolula show-property <id>                 # Show property details
poolula create-property --address "..." --acquisition-date "..." --price "..."
poolula update-property <id> --field value
poolula delete-property <id>               # Soft delete

# Transaction Operations
poolula import-csv <file> --property-id <id>   # Import bank/Airbnb CSV
poolula review-transactions                     # Interactive categorization
poolula search-transactions --category UTILITIES --start-date 2024-11-01
poolula export-transactions --format csv        # Export to CSV

# Document Management
poolula upload-doc <file> --doc-type LEASE --property-id <id>
poolula search-docs --query "insurance" --doc-type INSURANCE_POLICY
poolula ocr-doc <id>                           # Trigger OCR extraction

# Obligation Tracking
poolula list-obligations --status PENDING
poolula add-obligation --type PROPERTY_TAX --due-date 2025-04-30 --recurrence "FREQ=YEARLY"
poolula complete <obligation-id>

# Analytics
poolula show-revenue --year 2024 --quarter 3
poolula show-expenses --category-breakdown
poolula show-basis                             # Depreciable basis report

# Chatbot
poolula chat                                   # Launch interactive chat session
poolula ask "What was my November revenue?"    # Single question mode

# System
poolula health                                 # System health check
poolula audit-trail <entity-id>                # Show change history
```

#### Advantages

- ✅ **Scriptable**: Integrate with cron jobs, shell scripts
- ✅ **Fast**: No UI overhead, instant results
- ✅ **Composable**: Pipe to grep, jq, awk
- ✅ **Remote**: Works over SSH

#### Example Workflow: Review Uncategorized Transactions

```bash
# 1. Find uncategorized transactions
poolula search-transactions --category UNCATEGORIZED --start-date 2024-11-01

# 2. Review interactively
poolula review-transactions
# Shows table with prompts:
#   [1] Nov 1 | $45.00 | ACE HARDWARE
#   Category? [1=REPAIRS_MAINTENANCE, 2=CAPITAL_IMPROVEMENT, 3=OTHER]: 1
#   Confirm? [y/n]: y

# 3. Export categorized results
poolula export-transactions --month 2024-11 --format csv > nov_2024.csv
```

---

### 2. Chatbot (AI Assistant)

**Implementation**: Claude API with RAG (Retrieval Augmented Generation)
**Entry Point**: `poolula chat` or web UI chat widget

#### Capabilities

**Read Operations:**
- Answer questions about properties, transactions, documents
- Semantic search across documents ("Find my lease agreement")
- SQL-backed queries ("What was my Q3 revenue?")
- Compliance questions ("When is my next property tax due?")

**Example Queries:**

```
User: "What was my total revenue in November 2024?"
Bot:  Based on your transaction records, your total revenue in November 2024 was $4,500.00.
      This includes:
      - Rental Income: $4,500.00

      [Source: Transactions table, 3 records from Nov 1-30, 2024]

User: "Show me all utilities expenses this month"
Bot:  Here are your utilities expenses for November 2024:

      Date       Amount   Category           Description
      -------------------------------------------------------
      Nov 1      $125.00  UTILITIES_GAS      Atmos Energy
      Nov 5      $45.00   UTILITIES_WATER    City of Montrose
      Nov 10     $89.00   UTILITIES_ELECTRIC Xcel Energy
      Nov 15     $65.00   UTILITIES_INTERNET CenturyLink
      -------------------------------------------------------
      TOTAL:     $324.00

      [Source: Transactions filtered by category pattern 'UTILITIES_%']

User: "What's my depreciable basis for the Montrose property?"
Bot:  For 900 S 9th St, Montrose, CO 81401:

      Building Basis:   $364,100.00 (depreciable)
      FFE Basis:        $10,000.00  (depreciable)
      Land Basis:       $78,200.00  (NOT depreciable)
      -------------------------------------------
      Depreciable Basis: $374,100.00

      Depreciation method: 27.5 year residential rental
      Placed in service: 2025-02-01

      [Source: Property table, id: 12345678-..., provenance: poolula_facts.yml]
```

#### Advantages

- ✅ **Natural language**: No need to remember commands
- ✅ **Exploratory**: Great for "I wonder..." questions
- ✅ **Learning**: Discovers data you didn't know existed
- ✅ **Accessible**: Lowest barrier to entry

#### Limitations

- ❌ **Read-only** (initially): Can't modify data via chat
- ❌ **Ambiguity**: May misinterpret vague questions
- ❌ **API costs**: Claude usage billed per token

---

### 3. Jupyter Notebooks

**Implementation**: Jupyter Lab/Notebook with platform modules imported
**Location**: `notebooks/` directory

#### Use Cases

- **Exploratory data analysis**: "Let me see all transactions and look for patterns"
- **Custom reports**: One-off analyses not in the standard dashboard
- **Prototyping**: Test business logic before adding to platform
- **Learning**: Understand the data structure interactively

#### Example Notebooks

**`notebooks/revenue_analysis.ipynb`**:
```python
# Import platform modules
from core.database.connection import get_session
from core.database.models import Property, Transaction
from sqlmodel import select
import pandas as pd
import matplotlib.pyplot as plt

# Load data
session = next(get_session())
transactions = session.exec(
    select(Transaction)
    .where(Transaction.category == "RENTAL_INCOME")
).all()

# Convert to DataFrame
df = pd.DataFrame([t.dict() for t in transactions])

# Analyze
monthly_revenue = df.groupby(df['transaction_date'].dt.to_period('M'))['amount'].sum()

# Visualize
monthly_revenue.plot(kind='bar', title='Monthly Revenue 2024')
plt.ylabel('Revenue ($)')
plt.show()
```

**`notebooks/expense_categorization.ipynb`**:
```python
# Review uncategorized transactions
uncategorized = session.exec(
    select(Transaction)
    .where(Transaction.category == "UNCATEGORIZED")
).all()

# Display in interactive table with ipywidgets
from ipywidgets import interact, Dropdown

def categorize_transaction(transaction_id):
    # Interactive dropdown to select category
    ...
```

#### Advantages

- ✅ **Flexible**: Write any Python code
- ✅ **Visual**: Embed charts, tables, images
- ✅ **Shareable**: Export to HTML/PDF
- ✅ **Reproducible**: Re-run analysis anytime

#### Limitations

- ❌ **Not production**: Not for routine operations
- ❌ **Requires Python**: Need to know pandas, matplotlib
- ❌ **Version control**: `.ipynb` files harder to diff

---

### 4. Vue 3 Web UI (Phase 4)

**Implementation**: Vue 3 + TypeScript + Vite + TailwindCSS
**Entry Point**: http://localhost:8082 (after Phase 4)

#### Key Pages

1. **Home** - Task-oriented dashboard ("What do you want to do?")
2. **Ask** - Embedded chatbot interface
3. **Analyze** - Interactive charts and metrics
4. **Properties** - Property list and detail views
5. **Transactions** - Transaction table with filtering
6. **Documents** - Document vault with search
7. **Obligations** - Calendar view of deadlines
8. **Settings** - Configuration and about

#### Workflow Example: Review Transactions

```
Step 1: Select Date Range
┌─────────────────────────────────────┐
│ Review Transactions                 │
├─────────────────────────────────────┤
│ Select period to review:            │
│ [Nov 2024  ▼]                       │
│                                     │
│ [Next >]                            │
└─────────────────────────────────────┘

Step 2: Categorize
┌─────────────────────────────────────────────────────┐
│ Found 12 uncategorized transactions                 │
├─────────────────────────────────────────────────────┤
│ Date     Amount   Description          Category     │
│ Nov 1    $45.00   ACE HARDWARE         [Dropdown ▼] │
│ Nov 3    $125.00  ATMOS ENERGY         [Dropdown ▼] │
│ ...                                                  │
├─────────────────────────────────────────────────────┤
│ [< Back]  [Save All]  [Save & Continue]            │
└─────────────────────────────────────────────────────┘

Step 3: Confirm
┌─────────────────────────────────────┐
│ Review Changes                      │
├─────────────────────────────────────┤
│ ✓ Categorized 12 transactions       │
│ ✓ Added provenance tracking         │
│ ✓ Logged to audit trail             │
│                                     │
│ [Confirm]  [Cancel]                 │
└─────────────────────────────────────┘
```

#### Advantages

- ✅ **Visual**: Best for browsing and discovery
- ✅ **Guided**: Workflows prevent errors
- ✅ **Progressive**: Drill down for details
- ✅ **Mobile**: Responsive design

#### Limitations

- ❌ **Phase 4**: Not available yet (Weeks 6-7)
- ❌ **Browser required**: Can't use over SSH

---

### 5. REST API

**Implementation**: FastAPI with OpenAPI documentation
**Entry Point**: http://localhost:8082/api/v1/
**Docs**: http://localhost:8082/docs (Swagger UI)

#### Direct API Usage

```bash
# Create property
curl -X POST http://localhost:8082/api/v1/properties \
  -H "Content-Type: application/json" \
  -d '{
    "address": "900 S 9th St, Montrose, CO 81401",
    "acquisition_date": "2024-04-15",
    "purchase_price_total": "442300.00",
    "land_basis": "78200.00",
    "building_basis": "364100.00"
  }'

# Get all transactions for November
curl "http://localhost:8082/api/v1/transactions?start_date=2024-11-01&end_date=2024-11-30"

# Upload document
curl -X POST http://localhost:8082/api/v1/documents/upload \
  -F "file=@lease.pdf" \
  -F "doc_type=LEASE" \
  -F "property_id=12345678-1234-1234-1234-123456789012"
```

#### Advantages

- ✅ **Programmatic**: For integrations, scripts
- ✅ **Language agnostic**: Any HTTP client
- ✅ **Documented**: Auto-generated OpenAPI spec

#### Limitations

- ❌ **Developer tool**: Not for end users
- ❌ **No UI**: Raw JSON responses

---

## Decision Guide: Which Interface to Use?

### Scenario: Import bank transactions

- **CLI**: ✅ `poolula import-csv bank_nov_2024.csv` (fastest)
- **Jupyter**: ✅ If you want to inspect data first
- **Vue UI**: ✅ If you want drag-and-drop upload
- **API**: ✅ If automating with external system

**Recommendation**: CLI for manual imports, API for automation

---

### Scenario: Answer "What was my Q3 revenue?"

- **Chatbot**: ✅ Natural language query (easiest)
- **CLI**: ✅ `poolula show-revenue --quarter 3 --year 2024`
- **Jupyter**: ✅ Custom analysis with breakdown
- **Vue UI**: ✅ Dashboard chart (visual)

**Recommendation**: Chatbot for quick answers, Jupyter for deep analysis

---

### Scenario: Review and categorize 50 transactions

- **CLI**: ✅ `poolula review-transactions` (fast, scriptable)
- **Vue UI**: ✅ Workflow with dropdowns (visual, guided)
- **Jupyter**: ❌ Too manual (would need to write categorization code)

**Recommendation**: Vue UI for visual review, CLI for bulk/automated

---

### Scenario: Find a specific document

- **Chatbot**: ✅ "Find my lease agreement" (natural language)
- **CLI**: ✅ `poolula search-docs --query "lease" --doc-type LEASE`
- **Vue UI**: ✅ Search bar with filters
- **Jupyter**: ❌ Overkill for simple search

**Recommendation**: Chatbot or Vue UI for browsing, CLI for scripting

---

### Scenario: Generate a custom tax report

- **Jupyter**: ✅ Full control over calculations and formatting
- **CLI**: ⚠️ If standard report, else use Jupyter
- **Vue UI**: ⚠️ If report is added to Phase 5
- **Chatbot**: ❌ Can't generate complex reports

**Recommendation**: Jupyter for custom reports, Vue UI for standard reports

---

## Data Flow Examples

### Example 1: CSV Import → Transaction Creation

```
┌──────────────┐
│ User uploads │
│  bank.csv    │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ CLI / Vue UI / API  │  (Interface accepts file)
└──────┬──────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ TransactionService.import_csv()  │  (Parses CSV, validates)
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Create Transaction objects       │  (SQLModel instances)
│ + Auto-populate provenance       │  (source: "bank.csv")
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ session.add_all(transactions)    │  (Persist to database)
│ session.commit()                 │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ AuditLog.create()                │  (Log import action)
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Return import summary            │  (Success/errors)
└──────────────────────────────────┘
```

### Example 2: Chatbot Query → SQL + Document Search

```
┌─────────────────────────────────┐
│ User: "What was my November     │
│ revenue from the Montrose       │
│ property?"                      │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Chatbot / AIGenerator           │  (Parse query intent)
└──────┬──────────────────────────┘
       │
       ├──────────────────────────────┐
       ▼                              ▼
┌──────────────────┐      ┌──────────────────┐
│ SQL Query Tool   │      │ Vector Search    │
│ (Structured data)│      │ (Documents)      │
└──────┬───────────┘      └──────┬───────────┘
       │                         │
       ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ SELECT SUM(amt)  │      │ Search ChromaDB  │
│ WHERE category   │      │ for "revenue"    │
│ = RENTAL_INCOME  │      │ + "Montrose"     │
└──────┬───────────┘      └──────┬───────────┘
       │                         │
       └────────┬────────────────┘
                ▼
       ┌─────────────────┐
       │ Combine results │
       │ + Format response│
       └────────┬─────────┘
                ▼
       ┌──────────────────────────┐
       │ "Your November revenue   │
       │ was $4,500.00            │
       │ [Source: Transactions]"  │
       └──────────────────────────┘
```

---

## Security & Access Control (Future)

**Phase 1-3**: No authentication (local development only)

**Phase 4+**: Authentication/authorization per interface

| Interface | Auth Method | Access Level |
|-----------|-------------|--------------|
| CLI | Environment variable (API key) | Full access (trustee) |
| Chatbot | Session-based | Read-only (initially) |
| Jupyter | System user | Full access (local only) |
| Vue UI | Session-based | Role-based (trustee, viewer, CPA) |
| API | Bearer token / API key | Role-based |

---

## Next Steps

- **Business Objects**: See [business-objects.md](business-objects.md) for detailed object reference
- **Quick Reference**: See [quick-reference.md](quick-reference.md) for command cheat sheet
- **API Documentation**: http://localhost:8082/docs for interactive API exploration
- **CLI Help**: Run `poolula --help` for command reference (after CLI is built)

---

**Last Updated**: 2025-11-13
**Status**: Phase 2 in progress - CLI and Chatbot interfaces available

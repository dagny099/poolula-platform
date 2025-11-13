# Quick Reference Guide

**One-page cheat sheet for Poolula Platform**

---

## Business Objects at a Glance

| Object | Symbol | Purpose | Key Fields | Relationships |
|--------|--------|---------|------------|---------------|
| **Property** | 🏠 | Rental properties | address, basis, acquisition_date | → transactions, documents, obligations |
| **Transaction** | 💰 | Financial events | amount, category, transaction_date | ← property, ↔ documents |
| **Document** | 📄 | Legal/operational docs | filename, doc_type, content_hash | ← property, ↔ transactions, → obligations |
| **Obligation** | 📅 | Compliance deadlines | due_date, recurrence, status | ← property, ← documents |
| **AuditLog** | 📝 | Change history | timestamp, action, old/new value | ← all objects (immutable) |

---

## Common Operations Cheat Sheet

### Property Operations

```bash
# CLI
poolula list-properties
poolula show-property <id>
poolula create-property --address "..." --acquisition-date "..." --price "..."
poolula show-basis                                  # Depreciable basis report

# Chatbot
"Show my properties"
"What's my depreciable basis for the Montrose property?"

# API
GET  /api/v1/properties
GET  /api/v1/properties/{id}
POST /api/v1/properties
```

### Transaction Operations

```bash
# CLI
poolula import-csv <file> --property-id <id>
poolula review-transactions                         # Interactive categorization
poolula search-transactions --category UTILITIES --start-date 2024-11-01
poolula export-transactions --format csv

# Chatbot
"What was my November revenue?"
"Show me all utilities expenses this month"
"What expenses are uncategorized?"

# API
POST /api/v1/transactions/import
GET  /api/v1/transactions?category=RENTAL_INCOME&start_date=2024-11-01
PATCH /api/v1/transactions/{id}
```

### Document Operations

```bash
# CLI
poolula upload-doc <file> --doc-type LEASE --property-id <id>
poolula search-docs --query "insurance" --doc-type INSURANCE_POLICY
poolula ocr-doc <id>                                # Trigger OCR

# Chatbot
"Find my lease agreement"
"Show me insurance documents"

# API
POST /api/v1/documents/upload
GET  /api/v1/documents/search?q=insurance
POST /api/v1/documents/{id}/ocr
```

### Obligation Operations

```bash
# CLI
poolula list-obligations --status PENDING
poolula add-obligation --type PROPERTY_TAX --due-date 2025-04-30
poolula complete <obligation-id>

# Chatbot
"What's due this month?"
"When is my next property tax due?"

# API
GET  /api/v1/obligations?status=PENDING
POST /api/v1/obligations
PATCH /api/v1/obligations/{id}/complete
```

---

## Interface Decision Tree

```
I want to...
│
├─ Import transactions
│  ├─ Quickly, from terminal → CLI: poolula import-csv <file>
│  ├─ With drag-and-drop → Vue UI: Upload widget (Phase 4)
│  └─ Automated process → API: POST /api/v1/transactions/import
│
├─ Answer a question
│  ├─ Natural language → Chatbot: "What was my Q3 revenue?"
│  ├─ Quick lookup → CLI: poolula show-revenue --quarter 3
│  └─ Visual chart → Vue UI: Dashboard (Phase 4)
│
├─ Categorize transactions
│  ├─ Bulk/automated → CLI: poolula review-transactions
│  ├─ Visual review → Vue UI: Categorization workflow (Phase 4)
│  └─ AI-assisted → Chatbot: "Categorize my expenses" (future)
│
├─ Find a document
│  ├─ Natural search → Chatbot: "Find my lease"
│  ├─ Filter by type → CLI: poolula search-docs --doc-type LEASE
│  └─ Browse visually → Vue UI: Document vault (Phase 4)
│
├─ Analyze trends
│  ├─ Custom analysis → Jupyter: Write pandas/matplotlib code
│  ├─ Standard chart → Vue UI: Dashboard (Phase 4)
│  └─ Quick summary → Chatbot: "What were my top expenses in Q3?"
│
└─ Review audit trail
   ├─ Terminal view → CLI: poolula audit-trail <entity-id>
   ├─ Interactive timeline → Vue UI: History view (Phase 4)
   └─ Ask about changes → Chatbot: "Who changed the basis?"
```

---

## Transaction Categories Quick Lookup

### Revenue
- `RENTAL_INCOME` - Rental revenue from tenants

### Operating Expenses
- `UTILITIES_GAS` - Gas/heating
- `UTILITIES_WATER` - Water/sewer
- `UTILITIES_ELECTRIC` - Electricity
- `UTILITIES_INTERNET` - Internet/cable
- `REPAIRS_MAINTENANCE` - Ongoing repairs
- `INSURANCE` - Property insurance
- `PROPERTY_TAXES` - Annual property tax
- `PROPERTY_MANAGEMENT` - Management fees
- `BANK_FEES` - Banking charges
- `PROFESSIONAL_FEES` - CPA, attorney, etc.

### Capital
- `CAPITAL_IMPROVEMENT` - Improvements (increase basis)
- `FURNITURE_FIXTURES` - FFE purchases
- `BASIS_ADJUSTMENT` - Basis corrections

### Member Transactions
- `MEMBER_CONTRIBUTION` - Capital contributed
- `MEMBER_DISTRIBUTION` - Distributions to member

### Other
- `UNCATEGORIZED` - Not yet categorized

---

## Document Types Quick Lookup

- `DEED` - Property deed
- `LEASE` - Rental lease agreement
- `OPERATING_AGREEMENT` - LLC operating agreement
- `AMENDMENT` - Amendment to legal document
- `INVOICE` - Vendor invoice
- `RECEIPT` - Purchase receipt
- `BANK_STATEMENT` - Bank statement
- `TAX_RETURN` - Tax return (Form 1065, Schedule E, etc.)
- `INSPECTION_REPORT` - Property inspection
- `APPRAISAL` - Property appraisal
- `INSURANCE_POLICY` - Insurance policy
- `CONTRACT` - General contract
- `OTHER` - Other document type

---

## Obligation Types Quick Lookup

- `PROPERTY_TAX` - Annual property tax
- `INSURANCE_RENEWAL` - Insurance renewal
- `LLC_ANNUAL_REPORT` - Colorado annual report
- `TAX_FILING` - Tax return filing deadline
- `LEASE_RENEWAL` - Lease renewal/termination
- `INSPECTION` - Scheduled inspection
- `MAINTENANCE_SCHEDULED` - Scheduled maintenance
- `COMPLIANCE_FILING` - Regulatory filing
- `OTHER` - Other obligation

---

## Property Status Meanings

- `ACTIVE` - Currently operating as rental
- `UNDER_CONTRACT` - Purchase in progress
- `SOLD` - Property has been sold
- `INACTIVE` - Not currently in service (soft-deleted)

---

## Transaction Type Meanings

- `REVENUE` - Money in (rental income)
- `EXPENSE` - Money out (operating expenses)
- `CAPITAL_CONTRIBUTION` - Member contributes capital
- `CAPITAL_DISTRIBUTION` - Member receives distribution

---

## Recurrence Pattern Examples (RRULE)

```python
# Annual (every year on April 30)
"FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=30"

# Quarterly (4 times/year on 15th of Apr, Jun, Sep, Jan)
"FREQ=YEARLY;BYMONTH=4,6,9,1;BYMONTHDAY=15"

# Monthly (1st of every month)
"FREQ=MONTHLY;BYMONTHDAY=1"

# Semi-annual (every 6 months)
"FREQ=MONTHLY;INTERVAL=6"

# Weekly (every Monday)
"FREQ=WEEKLY;BYDAY=MO"
```

---

## Provenance Structure Template

```json
{
  "source_type": "csv_import | manual_entry | api_call | system_generated",
  "source_id": "filename.csv | user_id | request_id",
  "source_field": "row_15 | cell_B3 | null",
  "created_at": "2025-11-13T10:00:00Z",
  "created_by": "system:importer | user:trustee",
  "confidence": 1.0,
  "verification_status": "unverified | verified | needs_review",
  "notes": "Optional context"
}
```

---

## API Endpoint Quick Reference

### Properties
```
GET    /api/v1/properties              - List all
GET    /api/v1/properties/{id}         - Get one
POST   /api/v1/properties              - Create
PATCH  /api/v1/properties/{id}         - Update
DELETE /api/v1/properties/{id}         - Soft delete
```

### Transactions
```
GET    /api/v1/transactions            - List all
GET    /api/v1/transactions/{id}       - Get one
POST   /api/v1/transactions            - Create
POST   /api/v1/transactions/import     - Import CSV
PATCH  /api/v1/transactions/{id}       - Update
DELETE /api/v1/transactions/{id}       - Soft delete
```

### Documents
```
GET    /api/v1/documents               - List all
GET    /api/v1/documents/{id}          - Get one
POST   /api/v1/documents/upload        - Upload file
GET    /api/v1/documents/search        - Search
POST   /api/v1/documents/{id}/ocr      - Trigger OCR
GET    /api/v1/documents/{id}/versions - Version history
```

### Obligations
```
GET    /api/v1/obligations             - List all
GET    /api/v1/obligations/upcoming    - Next 30 days
GET    /api/v1/obligations/{id}        - Get one
POST   /api/v1/obligations             - Create
PATCH  /api/v1/obligations/{id}        - Update
PATCH  /api/v1/obligations/{id}/complete - Mark complete
```

### Analytics
```
GET    /api/v1/analytics/revenue       - Revenue report
GET    /api/v1/analytics/expenses      - Expense report
GET    /api/v1/analytics/bookings      - Booking report
GET    /api/v1/analytics/occupancy     - Occupancy rate
```

### Chatbot
```
POST   /api/chatbot/query              - Ask question
GET    /api/chatbot/history/{session}  - Conversation history
```

### System
```
GET    /health                         - Health check
GET    /api/audit/{entity_id}          - Audit trail
```

---

## Common Query Patterns

### Find uncategorized transactions
```sql
SELECT * FROM transactions
WHERE category = 'UNCATEGORIZED'
ORDER BY transaction_date DESC
```

### Revenue for a specific month
```sql
SELECT SUM(amount) FROM transactions
WHERE category = 'RENTAL_INCOME'
  AND transaction_date >= '2024-11-01'
  AND transaction_date < '2024-12-01'
```

### All utilities expenses
```sql
SELECT * FROM transactions
WHERE category LIKE 'UTILITIES_%'
ORDER BY transaction_date DESC
```

### Depreciable basis for a property
```sql
SELECT
  building_basis + ffe_basis AS depreciable_basis
FROM properties
WHERE id = '<property-id>'
```

### Upcoming obligations (next 30 days)
```sql
SELECT * FROM obligations
WHERE status = 'PENDING'
  AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
ORDER BY due_date ASC
```

---

## Jupyter Notebook Quick Start

```python
# Import core modules
from core.database.connection import get_session
from core.database.models import Property, Transaction, Document, Obligation
from sqlmodel import select
import pandas as pd
import matplotlib.pyplot as plt

# Get database session
session = next(get_session())

# Load all transactions
transactions = session.exec(select(Transaction)).all()
df = pd.DataFrame([t.dict() for t in transactions])

# Analyze
monthly_revenue = df[df['category'] == 'RENTAL_INCOME'].groupby(
    df['transaction_date'].dt.to_period('M')
)['amount'].sum()

# Visualize
monthly_revenue.plot(kind='bar', title='Monthly Revenue')
plt.ylabel('Revenue ($)')
plt.show()
```

---

## Keyboard Shortcuts (Future - Vue UI)

| Action | Shortcut |
|--------|----------|
| Open search | `/` |
| Navigate to Ask | `Alt+A` |
| Navigate to Analyze | `Alt+D` |
| Navigate to Properties | `Alt+P` |
| Open command palette | `Ctrl+K` |
| Create new transaction | `Alt+T` |

---

## File Locations

### Source Code
- Models: `core/database/models.py`
- API: `apps/api/routes/`
- Chatbot: `apps/chatbot/`
- Config: `core/database/config.py`

### Data
- Database: `poolula.db` (SQLite)
- Vector store: `.chroma/` (ChromaDB)
- Backups: `backups/poolula_YYYYMMDD_HHMMSS.db`

### Documentation
- Architecture: `docs/architecture/`
- Workflows: `docs/workflows/`
- Planning: `docs/planning/`

### Configuration
- Dependencies: `pyproject.toml`
- Environment: `.env` (copy from `.env.example`)
- Migrations: `alembic/versions/`

---

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./poolula.db

# API
API_HOST=0.0.0.0
API_PORT=8082
API_RELOAD=true

# Chatbot (Phase 2)
ANTHROPIC_API_KEY=sk-ant-...
CHROMA_PATH=./.chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

---

## Getting Help

### Documentation
- **Full docs**: `docs/` directory
- **API docs**: http://localhost:8082/docs
- **CLI help**: `poolula --help`
- **Command help**: `poolula <command> --help`

### Troubleshooting
1. Check health: `poolula health` or `GET /health`
2. Review logs: `logs/app.log`
3. Check database: `sqlite3 poolula.db`
4. Verify migrations: `.venv/bin/alembic current`

---

**See Also:**
- [Business Objects Reference](business-objects.md) - Detailed object documentation
- [Platform Interfaces](platform-interfaces.md) - Interface comparison and workflows
- [API Usage Guide](../workflows/api-usage.md) - API examples
- [Testing Guide](../workflows/testing.md) - Running tests

---

**Last Updated**: 2025-11-13
**Version**: 1.0 (Phase 2)

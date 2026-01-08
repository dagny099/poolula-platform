# Importing Data

Guide to importing data into the Poolula Platform from various sources.

## Overview

Poolula Platform supports importing data from:

1. **Property data** - From `poolula_facts.yml` (single source of truth)
2. **Transactions** - From Airbnb CSV exports and bank statements
3. **Documents** - PDF files for semantic search
4. **Obligations** - Compliance deadlines and recurring tasks

---

## 1. Importing Property Data

### From poolula_facts.yml

The `poolula_facts.yml` file is the **single source of truth** for property and LLC data.

**First time import:**
```bash
uv run python scripts/seed_database.py --initial
```

**Update after editing YAML:**
```bash
uv run python scripts/seed_database.py --update
```

### Handling UNKNOWN Fields

Fields marked `"UNKNOWN"` in the YAML file import as `NULL` in the database:

```yaml
# In poolula_facts.yml
placed_in_service_date_for_depreciation: "UNKNOWN"
```

After you fill in the actual value, re-run the update script to sync:

```bash
# Edit YAML: change "UNKNOWN" to "2025-02-01"
uv run python scripts/seed_database.py --update
```

**Safety:** Update mode only fills NULL fields - it never overwrites manual edits.

**Detailed guide:** [Data Import Workflow](../workflows/data-import.md)

---

## 2. Importing Transactions

### From Airbnb CSV

**Step 1: Export from Airbnb**
- Go to Airbnb > Account > Payments & Payouts > Transaction History
- Export to CSV

**Step 2: Import**
```bash
# Preview first (dry run)
uv run python scripts/import_airbnb_transactions.py \
  path/to/airbnb.csv \
  --auto-property \
  --dry-run

# Import for real
uv run python scripts/import_airbnb_transactions.py \
  path/to/airbnb.csv \
  --auto-property
```

**Features:**
- ✅ Automatic categorization (revenue, fees, payouts)
- ✅ Accrual accounting (checkout date revenue recognition)
- ✅ Duplicate detection (safe to re-run)
- ✅ Full provenance tracking

**Step 3: Verify**
Ask the chatbot: `"Show me all rental income from August 2025"`

**Detailed guide:** [Airbnb Import Workflow](../workflows/airbnb-import.md)

### From Bank Statements

**Status:** 🚧 Manual entry via API or coming in future phases

Current workaround: Use the chatbot to log transactions via API.

---

## 3. Importing Documents

### Bulk Document Ingestion

Import PDFs for semantic search in the chatbot:

```bash
# Place PDFs in documents/ directory
# Then ingest all
uv run python scripts/ingest_documents.py

# Check ingestion stats
uv run python scripts/ingest_documents.py --stats
```

**Supported formats:**
- PDF (automatically extracted and chunked)
- Text files
- Markdown files

**Features:**
- ✅ SHA-256 content hashing (duplicate detection)
- ✅ ChromaDB vector embeddings
- ✅ Semantic search via chatbot

**After ingestion**, ask questions like:
- "What is our business purpose in the operating agreement?"
- "What are the insurance policy coverage limits?"

**Detailed guide:** [Document Management](document-management.md)

---

## 4. Importing Compliance Obligations

### Seed Common Obligations

Populate standard LLC compliance tasks:

```bash
# Seed all common obligations for 2025
uv run python scripts/seed_obligations.py

# Seed for specific year
uv run python scripts/seed_obligations.py --year 2026

# Clear and reseed
uv run python scripts/seed_obligations.py --clear --year 2025
```

**Creates:**
- Colorado Periodic Report (annual)
- Quarterly estimated tax payments
- Form 1065 tax return deadline
- Property tax payments
- Insurance renewals
- Property inspections

**Detailed guide:** [Managing Obligations](obligations.md)

---

## 5. Verifying Imports

### Check via Chatbot

The easiest way to verify imports:

```bash
uv run python scripts/cli.py chat
```

**Sample queries:**
- "Show me all properties"
- "What was my total rental income in 2024?"
- "List all documents we have ingested"
- "What compliance tasks are coming up?"

### Check via API

```bash
# List properties
curl http://localhost:8082/api/v1/properties

# Query chatbot
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all transactions from August 2025"}'
```

### Check via Database

```bash
sqlite3 poolula.db

# Check properties
SELECT address, acquisition_date FROM properties;

# Check transaction count
SELECT COUNT(*) FROM transactions;

# Check documents
SELECT title, doc_type FROM documents;
```

---

## Common Import Tasks

### Re-importing is Safe

All import scripts use duplicate detection:

```bash
# Safe to run multiple times
uv run python scripts/import_airbnb_transactions.py data/airbnb.csv --auto-property
# Output: "Skipped 45 duplicates, imported 12 new transactions"

# Safe to re-ingest documents
uv run python scripts/ingest_documents.py
# Output: "Skipped 8 existing documents, ingested 3 new documents"
```

### Cleaning Up Duplicates

If you accidentally created duplicates before duplicate detection was added:

```bash
# Preview duplicates (dry run)
uv run python scripts/remove_duplicate_transactions.py --dry-run

# Remove duplicates (keeps oldest)
uv run python scripts/remove_duplicate_transactions.py
```

---

## Import Best Practices

1. **Always run dry-run first** - Preview changes before committing
2. **Start with property data** - Import properties before transactions
3. **Use chatbot to verify** - Easiest way to check imports worked
4. **Keep YAML as source of truth** - Update YAML, then sync to database
5. **Document provenance** - All imports track source (CSV filename, YAML, etc.)

---

## Related Documentation

- **Technical workflows:**
  - [Data Import Workflow](../workflows/data-import.md) - YAML → Database details
  - [Airbnb Import Workflow](../workflows/airbnb-import.md) - Airbnb CSV format and options
  - [API Usage](../workflows/api-usage.md) - REST API examples

- **User guides:**
  - [Document Management](document-management.md) - Managing ingested documents
  - [Managing Obligations](obligations.md) - Compliance tracking
  - [Chatbot Guide](chatbot.md) - Querying imported data

- **Scripts:**
  - `scripts/seed_database.py` - Property import from YAML
  - `scripts/import_airbnb_transactions.py` - Transaction import
  - `scripts/ingest_documents.py` - Document ingestion
  - `scripts/seed_obligations.py` - Obligations seeding

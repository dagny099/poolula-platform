# Frequently Asked Questions

Common questions about Poolula Platform installation, usage, and troubleshooting.

## General Questions

### What is Poolula Platform?

Poolula Platform is an integrated data hub and natural language query system for Poolula LLC, a Colorado-based rental property business. It combines transaction analysis, document search, and compliance tracking with an AI-powered chatbot interface.

### Who should use this?

Poolula Platform is designed for:

- **LLC Owners** - Track compliance obligations and deadlines
- **Bookkeepers** - Manage transactions and prepare tax filings
- **Property Managers** - Monitor leases, insurance, and maintenance
- **Compliance Officers** - Ensure regulatory requirements are met

### Is this a replacement for QuickBooks?

No. Poolula Platform is a **question-answering system**, not accounting software. It helps you:

- Query your financial data using natural language
- Search business documents for specific information
- Track compliance deadlines
- Verify data through evaluation harness

For accounting, use QuickBooks, Wave, or similar software. Poolula Platform **complements** accounting software by providing natural language access to your data.

### Is my data secure?

Yes, with caveats:

- All data stored **locally** in SQLite (no cloud storage)
- Documents never leave your machine
- Only API calls to Claude AI (for query processing)
- No sensitive data sent to Claude (only queries and responses)

For production deployment, implement proper authentication and encryption.

## Installation & Setup

### What are the minimum system requirements?

**Required:**

- Python 3.13+
- 4GB RAM
- 2GB free disk space
- Internet connection (for AI API calls)

**Recommended:**

- 8GB+ RAM
- 10GB+ free disk space
- SSD for better database performance

### Do I need a Claude API key?

Yes, the chatbot requires an Anthropic Claude API key. Sign up at [console.anthropic.com](https://console.anthropic.com/).

**Pricing:** Claude API uses pay-as-you-go pricing. Typical queries cost $0.01-$0.05 each with Sonnet 4.5.

### Can I run this without the chatbot?

Yes. You can use:

- Database directly (SQLite)
- API endpoints (properties, transactions, documents)
- Import/export scripts
- CLI commands (non-chatbot features)

The chatbot is optional if you only need data management.

### Why Python 3.13? Can I use Python 3.12?

Python 3.13+ is required for:

- Latest type hint features
- Performance improvements
- Modern async support

Python 3.12 may work but is not officially supported.

## Usage Questions

### How do I import Airbnb transactions?

1. Export transactions from Airbnb (CSV format)
2. Get your property UUID from the database
3. Run the import script:

```bash
uv run python scripts/import_airbnb_transactions.py \
    --csv data/airbnb_export.csv \
    --property-id <uuid> \
    --dry-run  # Preview first
```

4. Review the preview
5. Run without `--dry-run` to actually import

See [Importing Data Guide](user-guide/importing-data.md) for details.

### What accounting method does the system use?

**Accrual accounting** for Airbnb transactions:

- **Revenue** recognized on checkout date (when service provided)
- **Expenses** recognized on payout date (when fee charged)

This matches standard rental property accounting practices.

### How do I add my own documents?

1. Place documents in `documents/` directory (organized by type)
2. Update `data/document_metadata.csv` with metadata
3. Run ingestion script:

```bash
uv run python scripts/ingest_documents.py
```

Supported formats: PDF, DOCX, TXT, MD

### How accurate is the chatbot?

The chatbot uses Claude Sonnet 4.5 with RAG (Retrieval-Augmented Generation). Accuracy depends on:

- **Data quality** - Accurate database records
- **Document completeness** - All relevant docs ingested
- **Query clarity** - Well-formed questions

**Target accuracy:** ≥90% (measured via evaluation harness)

To verify accuracy, check:

- Sources cited by the chatbot
- Run evaluation: `uv run python apps/evaluator/evaluation_harness.py`

### What transaction categories are supported?

30+ categories including:

- **Income**: RENTAL_INCOME, OTHER_REVENUE
- **Utilities**: UTILITIES_GAS, UTILITIES_ELECTRIC, UTILITIES_WATER
- **Maintenance**: REPAIRS_MAINTENANCE, LANDSCAPING
- **Professional**: PROPERTY_MANAGEMENT, LEGAL_PROFESSIONAL, ACCOUNTING
- **Insurance**: INSURANCE_PROPERTY, INSURANCE_LIABILITY
- **Taxes**: PROPERTY_TAXES, INCOME_TAXES
- **Capital**: CAPITAL_IMPROVEMENT

See `core/database/enums.py` for complete list.

## Troubleshooting

### API server won't start

**Error:** `Address already in use`

**Solution:** Another process is using port 8082.

```bash
# Find process using port 8082
lsof -i :8082

# Kill the process (replace PID)
kill -9 <PID>

# Or use a different port
uv run uvicorn apps.api.main:app --port 8083
```

### Database connection fails

**Error:** `Could not connect to database`

**Solutions:**

1. Check if database file exists:
   ```bash
   ls -la poolula.db
   ```

2. Run migrations if missing:
   ```bash
   .venv/bin/alembic upgrade head
   ```

3. Check DATABASE_URL in `.env`:
   ```bash
   cat .env | grep DATABASE_URL
   ```

### ChromaDB import errors

**Error:** `ModuleNotFoundError: No module named 'chromadb'`

**Solution:** Install RAG dependencies:

```bash
uv sync --group rag
```

**Error:** `ChromaDB requires C++ compiler`

**Solution:** Install build tools:

=== "macOS"
    ```bash
    xcode-select --install
    ```

=== "Linux"
    ```bash
    sudo apt install build-essential
    ```

### Chatbot returns "no data found" but data exists

**Possible causes:**

1. **Wrong query format** - Try rephrasing
2. **Data not in expected format** - Check transaction categories
3. **Duplicate transactions** - Run deduplication:
   ```bash
   uv run python scripts/remove_duplicate_transactions.py --dry-run
   ```

**Debug steps:**

1. Query database directly:
   ```bash
   sqlite3 poolula.db "SELECT * FROM transaction WHERE transaction_date >= '2025-08-01'"
   ```

2. Check AI tool usage (look at API logs)

3. Run evaluation to check accuracy:
   ```bash
   uv run python apps/evaluator/evaluation_harness.py
   ```

### Documents not found in search

**Possible causes:**

1. **Documents not ingested** - Run ingestion:
   ```bash
   uv run python scripts/ingest_documents.py --list
   ```

2. **Metadata missing** - Check `data/document_metadata.csv`

3. **ChromaDB not initialized** - Reingest documents:
   ```bash
   uv run python scripts/ingest_documents.py --force
   ```

### Import script fails

**Error:** `No such file or directory: data/airbnb_export.csv`

**Solution:** Provide correct path to CSV file:

```bash
uv run python scripts/import_airbnb_transactions.py \
    --csv /full/path/to/airbnb_export.csv \
    --property-id <uuid>
```

**Error:** `Invalid property ID`

**Solution:** Get correct property UUID from database:

```bash
sqlite3 poolula.db "SELECT id, address FROM property"
```

## Development Questions

### How do I add a new transaction category?

1. Edit `core/database/enums.py`:
   ```python
   class TransactionCategory(str, Enum):
       # ... existing categories ...
       NEW_CATEGORY = "NEW_CATEGORY"
   ```

2. Create migration:
   ```bash
   .venv/bin/alembic revision --autogenerate -m "Add NEW_CATEGORY"
   .venv/bin/alembic upgrade head
   ```

3. Update tests and documentation

### How do I add a new API endpoint?

1. Create route in `apps/api/routes/`:
   ```python
   @router.get("/new-endpoint")
   def new_endpoint():
       return {"message": "Hello"}
   ```

2. Add router to `apps/api/main.py`:
   ```python
   from apps.api.routes import new_routes
   app.include_router(new_routes.router, prefix="/api/v1")
   ```

3. Test endpoint:
   ```bash
   curl http://localhost:8082/api/v1/new-endpoint
   ```

### How do I run tests?

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_models.py

# With coverage
uv run pytest --cov=core --cov=apps --cov-report=html
open htmlcov/index.html
```

### How do I contribute?

See [Development Guide](development/contributing.md) for:

- Code style guidelines
- Testing requirements
- Pull request process
- Documentation standards

## Advanced Questions

### Can I deploy this to a server?

Yes. For production:

1. Replace SQLite with PostgreSQL
2. Add authentication (OAuth2 / JWT)
3. Enable HTTPS (reverse proxy with nginx)
4. Implement rate limiting
5. Add monitoring and logging

See deployment guides (coming soon).

### Can I integrate with QuickBooks?

Not currently, but this is possible via:

1. QuickBooks API integration
2. CSV export/import
3. Custom sync scripts

This is on the roadmap for future development.

### Can I add custom AI tools?

Yes! Add new tools to `apps/chatbot/tool_manager.py`:

```python
def get_custom_tool_definition():
    return {
        "name": "custom_tool",
        "description": "...",
        "input_schema": {...}
    }

def execute_custom_tool(**kwargs):
    # Implementation
    return result
```

Register in `tool_manager.py` and the AI can use it.

### Can I use a different AI model?

Currently supports Anthropic Claude only. To add other models:

1. Implement adapter in `apps/chatbot/ai_generator.py`
2. Update tool definitions for model-specific format
3. Test with evaluation harness

OpenAI GPT support is planned for future releases.

## Still Have Questions?

- **Installation Help:** [Installation Guide](getting-started/installation.md)
- **API Documentation:** [API Reference](api/overview.md)
- **Architecture Details:** [System Design](architecture/system-design.md)
- **Bug Reports:** [GitHub Issues](https://github.com/dagny099/poolula-platform/issues)

---

**Didn't find your answer?** [Open a GitHub Issue](https://github.com/dagny099/poolula-platform/issues)

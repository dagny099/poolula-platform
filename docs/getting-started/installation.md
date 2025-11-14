# Installation Guide

This guide walks you through installing Poolula Platform on your local machine.

## Prerequisites

Before installing, ensure you have:

### 1. Python 3.13+

Check your Python version:

```bash
python --version
# Should show: Python 3.13.x
```

If you need to install Python 3.13:

=== "macOS"
    ```bash
    # Using Homebrew
    brew install python@3.13
    ```

=== "Linux (Ubuntu/Debian)"
    ```bash
    # Add deadsnakes PPA
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.13 python3.13-venv
    ```

=== "Windows"
    Download from [python.org](https://www.python.org/downloads/) and install.

### 2. uv Package Manager

Install `uv` (recommended over pip):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with Homebrew
brew install uv
```

Verify installation:

```bash
uv --version
```

### 3. Anthropic API Key

1. Sign up at [console.anthropic.com](https://console.anthropic.com/)
2. Create an API key
3. Save it securely (you'll need it in step 4 below)

## Installation Steps

### 1. Clone the Repository

```bash
cd /path/to/your/projects
git clone https://github.com/dagny099/poolula-platform.git
cd poolula-platform
```

### 2. Install Dependencies

Install all required Python packages:

```bash
# Install core dependencies
uv sync

# Install with RAG (chatbot) dependencies
uv sync --group rag

# Install with documentation dependencies (optional)
uv sync --group docs

# Install with development dependencies (optional)
uv sync --group dev
```

!!! tip "Recommended Installation"
    For full functionality, install with RAG dependencies:
    ```bash
    uv sync --group rag
    ```

### 3. Set Up Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```bash
# Required
ANTHROPIC_API_KEY=your-api-key-here

# Optional
DATABASE_URL=sqlite:///poolula.db
LOG_LEVEL=INFO
```

!!! warning "Keep your API key secret"
    Never commit `.env` to git. The `.gitignore` file already excludes it.

### 4. Initialize Database

Run database migrations:

```bash
.venv/bin/alembic upgrade head
```

Expected output:

```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123def456, Initial schema
```

### 5. Verify Installation

Check that everything works:

```bash
# Test database connection
uv run python -c "from core.database.connection import check_connection; print('✅ Database OK' if check_connection() else '❌ Database Failed')"

# Test API key
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ API Key Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ API Key Missing')"
```

Both tests should show ✅.

## Optional Setup

### Seed Sample Data

Create sample property and transactions:

```bash
# Seed property from YAML
uv run python scripts/seed_database.py --initial

# Import Airbnb transactions (if you have the CSV)
uv run python scripts/import_airbnb_transactions.py \
    --csv data/airbnb_export.csv \
    --property-id <property-uuid-from-seed> \
    --dry-run  # Preview first
```

### Ingest Documents

Place your business documents in `documents/` directory, then:

```bash
# Ingest all documents
uv run python scripts/ingest_documents.py

# Or ingest specific directory
uv run python scripts/ingest_documents.py \
    --directory documents/formation
```

### Seed Obligations

Create common compliance deadlines:

```bash
uv run python scripts/seed_obligations.py --year 2025
```

## Running the Platform

### Start the API Server

```bash
uv run uvicorn apps.api.main:app --reload --port 8082
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8082
INFO:     Application startup complete.
```

### Access the Frontend

Open your browser to:

```
http://localhost:8082
```

You should see the Poolula Platform chatbot interface with 4 persona sections.

### Use the CLI

For command-line access:

```bash
uv run python scripts/cli.py chat
```

This opens an interactive chatbot session where you can type questions.

## Troubleshooting

### Python Version Issues

??? failure "Error: Python 3.13 not found"
    Make sure you have Python 3.13+ installed:
    ```bash
    python --version
    # or
    python3.13 --version
    ```
    If using `pyenv`:
    ```bash
    pyenv install 3.13.2
    pyenv local 3.13.2
    ```

### uv Sync Errors

??? failure "Error: uv sync fails with dependency conflicts"
    Try updating `uv`:
    ```bash
    pip install --upgrade uv
    ```
    Then retry:
    ```bash
    uv sync --group rag
    ```

### Database Issues

??? failure "Error: Could not connect to database"
    Check if SQLite is accessible:
    ```bash
    # Create test database
    sqlite3 test.db "CREATE TABLE test (id INTEGER);"

    # If successful, remove test file
    rm test.db
    ```

    If SQLite works, check your `DATABASE_URL` in `.env`.

??? failure "Error: Alembic migration fails"
    Reset the database:
    ```bash
    # Backup first if you have data
    cp poolula.db poolula.db.backup

    # Remove database
    rm poolula.db

    # Re-run migration
    .venv/bin/alembic upgrade head
    ```

### API Key Issues

??? failure "Error: ANTHROPIC_API_KEY not set"
    Make sure `.env` file exists and contains your key:
    ```bash
    cat .env | grep ANTHROPIC_API_KEY
    ```

    If empty, edit `.env`:
    ```bash
    ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
    ```

??? failure "Error: Invalid API key or authentication failed"
    Your API key may be incorrect or expired. Generate a new one at [console.anthropic.com](https://console.anthropic.com/).

### ChromaDB Issues

??? failure "Error: ChromaDB import fails"
    ChromaDB requires C++ compiler. Install build tools:

    === "macOS"
        ```bash
        xcode-select --install
        ```

    === "Linux"
        ```bash
        sudo apt install build-essential
        ```

    === "Windows"
        Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)

## Verification Checklist

Before proceeding, verify:

- [ ] Python 3.13+ installed
- [ ] uv package manager installed
- [ ] Dependencies installed with `uv sync --group rag`
- [ ] `.env` file created with ANTHROPIC_API_KEY
- [ ] Database migrations run successfully
- [ ] API server starts without errors
- [ ] Frontend accessible at http://localhost:8082
- [ ] CLI chatbot works

## Next Steps

Installation complete! Now you can:

1. **[Quick Start Guide](quick-start.md)** - Run your first queries
2. **[Chatbot Guide](../user-guide/chatbot.md)** - Learn to use the AI assistant
3. **[Import Data](../user-guide/importing-data.md)** - Add your business data

## Getting Help

If you encounter issues not covered here:

1. Check the [FAQ](../faq.md)
2. Review the [Architecture documentation](../architecture/system-design.md)
3. Open a [GitHub Issue](https://github.com/dagny099/poolula-platform/issues)

---

**Installation successful?** → [Quick Start Guide](quick-start.md)

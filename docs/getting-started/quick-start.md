# Quick Start Guide

Get Poolula Platform running in 5 minutes.

## Prerequisites

Before starting, ensure you have:

- **Python 3.13+** installed

- **Git** installed

- **Terminal access** (Terminal.app on macOS, cmd/PowerShell on Windows, bash on Linux)

## 5-Minute Setup

### 1. Clone Repository

```bash
git clone https://github.com/dagny099/poolula-platform.git
cd poolula-platform
```

### 2. Install Dependencies

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 3. Initialize Database

```bash
# Run database migrations
.venv/bin/alembic upgrade head

# Seed initial data
uv run python scripts/seed_database.py --initial
```

### 4. Start API Server

```bash
# Start with hot reload
uv run uvicorn apps.api.main:app --reload --port 8082
```

### 5. Test It Works

**Open browser:** [http://localhost:8082](http://localhost:8082)

**Or use curl:**

```bash
curl http://localhost:8082/health
```

**Expected response:**

```json
{
  "status": "healthy",
  "database": "connected"
}
```

**That's it! You're running.**

## What's Next?

### Option 1: Try the Chatbot (Phase 2+)

```bash
# Make sure ANTHROPIC_API_KEY is set
export ANTHROPIC_API_KEY=sk-ant-...

# Ask a question
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our property address?"}'
```

### Option 2: Explore the API

**Interactive docs:** [http://localhost:8082/docs](http://localhost:8082/docs)

**Try endpoints:**

- `GET /health` - Health check

- `GET /api/v1/properties` - List properties

- `POST /api/v1/chat/query` - Query chatbot

### Option 3: Ingest Documents

```bash
# Place PDFs in documents/ directory
cp ~/Documents/operating-agreement.pdf documents/

# Ingest documents
uv run python scripts/ingest_documents.py --ingest

# Query documents via chatbot
curl -X POST http://localhost:8082/api/v1/chat/query \
  -d '{"query": "What is our business purpose?"}'
```

### Option 4: Seed Compliance Obligations

```bash
# Create standard LLC obligations
uv run python scripts/seed_obligations.py

# View obligations (API endpoint coming in Phase 3)
```

## Common Commands

### Development

```bash
# Start API server (hot reload)
uv run uvicorn apps.api.main:app --reload --port 8082

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=core --cov=apps --cov-report=html
```

### Database

```bash
# Apply migrations
.venv/bin/alembic upgrade head

# Create new migration
.venv/bin/alembic revision --autogenerate -m "Description"

# Check migration status
.venv/bin/alembic current
```

### Data Management

```bash
# Seed initial data from YAML
uv run python scripts/seed_database.py --initial

# Update data from YAML
uv run python scripts/seed_database.py --update

# Create database backup
python scripts/backup.py

# Restore from backup
python scripts/backup.py --restore latest
```

### Documents

```bash
# Ingest all documents in documents/
uv run python scripts/ingest_documents.py --ingest

# Show ingestion stats
uv run python scripts/ingest_documents.py --stats

# Clear vector store
uv run python scripts/ingest_documents.py --clear
```

## Project Structure

```
poolula-platform/
├── apps/                   # Applications
│   ├── api/                # FastAPI REST API
│   │   ├── main.py         # API server entry point
│   │   └── routes/         # API endpoints
│   └── chatbot/            # RAG Chatbot (Phase 2+)
│       ├── rag_system.py   # Main RAG orchestrator
│       └── ...             # AI components
├── core/                   # Core business logic
│   ├── database/           # Database models
│   │   ├── models.py       # SQLModel schemas
│   │   └── enums.py        # Enum definitions
│   └── logging_config.py   # Logging setup
├── scripts/                # Utility scripts
│   ├── seed_database.py    # Import from YAML
│   ├── seed_obligations.py # Create obligations
│   ├── ingest_documents.py # Document ingestion
│   └── backup.py           # Database backup
├── tests/                  # Test suite
│   ├── test_models.py      # Model tests
│   └── test_api_*.py       # API tests
├── docs/                   # Documentation (this site!)
├── alembic/                # Database migrations
├── pyproject.toml          # Project dependencies
└── README.md               # Getting started
```

## Configuration

### Environment Variables

**Create `.env` file:**

```env
# Database
DATABASE_URL=sqlite:///./poolula.db

# API
API_HOST=0.0.0.0
API_PORT=8082
API_RELOAD=true

# AI (Phase 2+)
ANTHROPIC_API_KEY=sk-ant-...

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

**Load environment:**

```bash
# Automatically loaded by uv run
# Or manually:
source .env
export $(cat .env | xargs)
```

## Troubleshooting

### "Command not found: uv"

**Install uv:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal or:
source ~/.bashrc  # Linux
source ~/.zshrc   # macOS
```

### "Port 8082 already in use"

**Find and kill process:**

```bash
# Find process using port 8082
lsof -ti :8082

# Kill process
kill -9 $(lsof -ti :8082)

# Or use different port
uv run uvicorn apps.api.main:app --port 8083
```

### "Database connection failed"

**Re-initialize database:**

```bash
# Delete database
rm poolula.db

# Re-run migrations
.venv/bin/alembic upgrade head

# Reseed data
uv run python scripts/seed_database.py --initial
```

### "Module not found" errors

**Reinstall dependencies:**

```bash
# Remove virtual environment
rm -rf .venv

# Reinstall
uv sync

# For Phase 2+ (includes AI dependencies)
uv sync --group rag
```

### "ANTHROPIC_API_KEY not set"

**Phase 2+ requires Anthropic API key:**

```bash
# Get key from: https://console.anthropic.com/

# Set in .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Or export directly
export ANTHROPIC_API_KEY=sk-ant-...
```

## Next Steps

### Learn More

- [Installation Guide](installation.md) - Detailed setup instructions

- [Architecture Overview](../architecture/system-design.md) - How it works

- [API Reference](../api/overview.md) - API documentation

- [User Guide](../user-guide/chatbot.md) - Using the chatbot

### Start Developing

- [Testing Guide](../testing/testing.md) - Run and write tests

- [Database Migrations](../testing/migrations.md) - Manage schema changes

- [Data Import Workflow](../workflows/data-import.md) - YAML → Database

### Explore Features

- [Chatbot Guide](../user-guide/chatbot.md) - Ask questions about your LLC

- [Document Management](../user-guide/document-management.md) - Ingest and search documents

- [Managing Obligations](../user-guide/obligations.md) - Track compliance deadlines

## Support

**Issues:** [GitHub Issues](https://github.com/dagny099/poolula-platform/issues)

**Documentation:** This site!

**Source Code:** [GitHub Repository](https://github.com/dagny099/poolula-platform)

---

**Ready to dive deeper?** → [Installation Guide](installation.md)

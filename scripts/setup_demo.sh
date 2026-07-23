#!/usr/bin/env bash
#
# Set up Poolula Platform demo mode: seeds a fully fictional dataset into an
# isolated database (demo/demo.db) and vector store (demo/chroma_db/).
# Real data (poolula.db, chroma_db/) is never touched.
#
# Usage:
#   bash scripts/setup_demo.sh            # create/refresh demo environment
#   bash scripts/setup_demo.sh --reset    # wipe demo DB + vector store first
#
# Re-running without --reset is safe: the property seed dedups by address,
# transaction import dedups by confirmation code, and document ingestion
# dedups by content hash. Obligations have no dedup, so use --reset (or
# seed_obligations.py --clear) if you need to reseed them.

set -euo pipefail
cd "$(dirname "$0")/.."

export DATABASE_URL="sqlite:///demo/demo.db"
export POOLULA_CHROMA_PATH="demo/chroma_db"

if [[ "${1:-}" == "--reset" ]]; then
    echo "Resetting demo environment..."
    rm -f demo/demo.db
    rm -rf demo/chroma_db
fi

FIRST_RUN=0
[[ -f demo/demo.db ]] || FIRST_RUN=1

echo "==> Creating schema (alembic upgrade head)"
uv run alembic upgrade head

echo "==> Seeding property from demo/demo_facts.yml"
uv run python scripts/seed_database.py --initial --facts demo/demo_facts.yml

if [[ "$FIRST_RUN" == "1" ]]; then
    echo "==> Seeding obligations (fictional treasurer/insurer)"
    uv run python scripts/seed_obligations.py --year 2025 \
        --treasurer "Kestrel County Treasurer" \
        --insurer "Summit Ridge Mutual Insurance"
else
    echo "==> Skipping obligations (already seeded; use --reset to reseed)"
fi

echo "==> Importing synthetic Airbnb transactions"
uv run python scripts/import_airbnb_transactions.py \
    demo/airbnb_demo_2024-12_2025-11.csv --auto-property

echo "==> Ingesting demo documents into demo/chroma_db"
uv run python scripts/ingest_documents.py --directory demo/documents

echo
echo "Demo environment ready. Run the API against it with:"
echo '  DATABASE_URL=sqlite:///demo/demo.db POOLULA_CHROMA_PATH=demo/chroma_db \'
echo '    uv run uvicorn apps.api.main:app --port 8082'
echo
echo "Evaluate against it (offline, no API key) with:"
echo '  uv run python scripts/evaluate_chatbot.py --eval-set demo/demo_eval_set.jsonl --fixture demo/fixtures/chatbot_fixture.json'
echo '  uv run python scripts/evaluate_airbnb.py --csv demo/airbnb_demo_2024-12_2025-11.csv --fixture demo/fixtures/airbnb_fixture.json'

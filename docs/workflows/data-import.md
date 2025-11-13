# Data Import Workflow

Complete guide for importing data from `poolula_facts.yml` into the Poolula Platform database.

## Overview

Poolula Platform uses `poolula_facts.yml` as the **single source of truth** for property and LLC data. This workflow describes how to import and update data from YAML into the SQL database.

**Source file:** `/Users/barbaraihidalgo-sotelo/PROJECTS/AirBnB Dashboard/poolula_facts.yml`

## Quick Start

### Initial Seed (First Time)

```bash
# From project root
uv run python scripts/seed_database.py --initial
```

This creates the property record if it doesn't already exist in the database.

### Update Seed (After Editing YAML)

```bash
# From project root
uv run python scripts/seed_database.py --update
```

This updates NULL fields in the database from the YAML without overwriting manual edits.

## UNKNOWN Field Handling

### What "UNKNOWN" Means

In `poolula_facts.yml`, fields marked with the string `"UNKNOWN"` indicate data that **hasn't been filled in yet**. This is intentional—you're still gathering information.

### How the System Handles UNKNOWN

When importing:
- `"UNKNOWN"` values in YAML → `NULL` in database
- NULL fields are **skippable** in the database schema (Optional fields)
- You can query for incomplete data: `SELECT * FROM properties WHERE placed_in_service IS NULL`

### Example

**In poolula_facts.yml:**
```yaml
placed_in_service_date_for_depreciation: "UNKNOWN"
capitalization_threshold_usd: "UNKNOWN"
```

**After import:**
```sql
-- Database shows NULL for unknown fields
SELECT placed_in_service FROM properties;
-- Result: NULL

-- Easy to find incomplete data
SELECT * FROM properties WHERE placed_in_service IS NULL;
```

**After you fill in the value:**
```yaml
# Edit YAML
placed_in_service_date_for_depreciation: "2025-02-01"
```

```bash
# Re-import with --update
uv run python scripts/seed_database.py --update
```

**Result:** Database now shows `2025-02-01` instead of NULL.

## Workflow: Updating Facts

### Step 1: Edit poolula_facts.yml

Open the YAML file and update fields:

```yaml
assets:
  as_of_2024_12_31:
    placed_in_service_date_for_depreciation: "2025-02-01"  # Was UNKNOWN
```

### Step 2: Run Update Script

```bash
uv run python scripts/seed_database.py --update
```

### Step 3: Review Changes

The script logs all changes:

```
INFO: Found existing property: 900 S 9th St, Montrose, CO 81401
INFO:   Updating placed_in_service: None → 2025-02-01
INFO: ✅ Property updated with 1 changes
```

### Step 4: Verify in Database

```bash
# Using SQLite CLI
sqlite3 poolula.db

sqlite> SELECT address, placed_in_service FROM properties;
```

Or use the API:

```bash
curl http://localhost:8082/api/v1/properties
```

## How Update Mode Works

### Safety Features

1. **Only updates NULL → value** - Never overwrites existing data
2. **Preserves manual edits** - If you edited via API, update won't touch it
3. **Logs all changes** - See exactly what was updated
4. **Idempotent** - Safe to run multiple times

### What Gets Updated

The script checks these fields:
- `placed_in_service`
- `land_basis`
- `building_basis`
- `ffe_basis`

If the database field is NULL **and** YAML has a non-UNKNOWN value, it updates.

### What Doesn't Get Updated

- Fields that already have values (manual edits preserved)
- Fields still marked UNKNOWN in YAML (stay NULL)
- Immutable fields like `id`, `created_at`

## Provenance Tracking

Every property includes provenance data showing where it came from:

```json
{
  "address": "900 S 9th St, Montrose, CO 81401",
  "provenance": {
    "source_type": "manual_entry",
    "source_id": "poolula_facts.yml",
    "confidence": 1.0,
    "verification_status": "unverified",
    "notes": "Imported from source of truth YAML (last_updated: 2025-10-26)"
  }
}
```

This provides:
- **Transparency**: Know where data came from
- **Confidence tracking**: 0.0-1.0 scale
- **Verification status**: Track what's been reviewed
- **Audit trail**: Part of the permanent record

## Querying for Incomplete Data

### Find All NULL Fields

```sql
-- Properties missing placed_in_service date
SELECT address, acquisition_date
FROM properties
WHERE placed_in_service IS NULL;

-- Properties with any NULL optional fields
SELECT address, placed_in_service, land_basis, building_basis
FROM properties
WHERE placed_in_service IS NULL
   OR land_basis IS NULL
   OR building_basis IS NULL;
```

### Via API

```bash
# Get all properties and check for nulls
curl http://localhost:8082/api/v1/properties | jq '.[] | select(.placed_in_service == null)'
```

## Common Scenarios

### Scenario 1: First Import

```bash
# Fresh database, no properties yet
uv run python scripts/seed_database.py --initial

# Output:
# ✅ Property created: 900 S 9th St, Montrose, CO 81401
#   ID: 12345678-...
#   Purchase price: $442300.00
```

### Scenario 2: Filling in UNKNOWN Values

```bash
# 1. Edit poolula_facts.yml
vim ~/PROJECTS/AirBnB\ Dashboard/poolula_facts.yml

# 2. Change UNKNOWN → actual value
# 3. Re-import
uv run python scripts/seed_database.py --update

# Output:
#   Updating placed_in_service: None → 2025-02-01
# ✅ Property updated with 1 changes
```

### Scenario 3: Property Already Exists

```bash
# Re-running initial seed when property exists
uv run python scripts/seed_database.py --initial

# Output:
# Property already exists: 900 S 9th St, Montrose, CO 81401
#   ID: 12345678-...
# Skipping creation (use --update to resync from YAML)
```

### Scenario 4: Manual Edits Preserved

```bash
# You edited via API:
curl -X PATCH http://localhost:8082/api/v1/properties/{id} \
  -d '{"placed_in_service": "2025-03-01"}'

# Later, you run update from YAML:
uv run python scripts/seed_database.py --update

# Output:
# No changes needed (all fields already filled)
#
# Your manual edit (2025-03-01) is preserved!
```

## Troubleshooting

### Error: "Database connection failed"

```bash
# Make sure migrations are applied
.venv/bin/alembic upgrade head
```

### Error: "poolula_facts.yml not found"

Check the path in the script matches your setup:
```python
YAML_PATH = Path("/Users/barbaraihidalgo-sotelo/PROJECTS/AirBnB Dashboard/poolula_facts.yml")
```

### Error: "Failed to load YAML"

Validate your YAML syntax:
```bash
python -c "import yaml; yaml.safe_load(open('poolula_facts.yml'))"
```

## Next Steps

- **API Usage**: See [api-usage.md](api-usage.md) for working with properties via REST API
- **Testing**: See [testing.md](testing.md) for running tests
- **Advanced**: Phase 5 will add Transaction, Document, and Obligation imports

## Related Files

- **Script**: `scripts/seed_database.py`
- **Source YAML**: `/Users/barbaraihidalgo-sotelo/PROJECTS/AirBnB Dashboard/poolula_facts.yml`
- **Database Models**: `core/database/models.py`
- **Provenance Helper**: `core/database/models.py::create_provenance()`

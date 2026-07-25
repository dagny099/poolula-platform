# Obligations API Reference

API endpoints for managing compliance obligations and deadlines.

## Overview

The Obligations API allows you to create, read, update, and soft-delete compliance deadlines, tax filings, and recurring obligations. All mutations are recorded in the audit log.

**Base URL:** `/api/v1/obligations`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/obligations` | List obligations with filters | ✅ Implemented |
| GET | `/api/v1/obligations/{id}` | Get obligation by ID | ✅ Implemented |
| POST | `/api/v1/obligations` | Create new obligation | ✅ Implemented |
| PATCH | `/api/v1/obligations/{id}` | Update obligation | ✅ Implemented |
| DELETE | `/api/v1/obligations/{id}` | Soft delete (sets status=cancelled) | ✅ Implemented |

## Query Parameters (GET list)

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `pending`, `due_soon`, `overdue`, `completed`, `cancelled` |
| `obligation_type` | string | Type name or value (`TAX_FILING` or `tax:filing`) |
| `property_id` | UUID | Filter by property |
| `due_before` | date | Include obligations due on/before this date |
| `due_after` | date | Include obligations due on/after this date |

Results are ordered by due date (soonest first).

## Obligation Types

From `core/database/enums.py::ObligationType`:

- `tax:filing` - Tax return deadlines
- `tax:payment` - Tax/estimated payment deadlines
- `compliance:periodic_report` - State annual reports
- `insurance:renewal` - Insurance renewals
- `license:renewal` - Business licenses
- `rent:payment` - Ground rent (if applicable)
- `other` - Miscellaneous obligations

Enum inputs accept either the name (`TAX_FILING`) or the value (`tax:filing`); responses always emit the value.

## Quick Examples

### List Obligations

```bash
# All obligations
curl http://localhost:8082/api/v1/obligations

# Filter by status
curl http://localhost:8082/api/v1/obligations?status=pending

# Deadlines due before a date
curl "http://localhost:8082/api/v1/obligations?status=pending&due_before=2026-12-31"
```

### Create Obligation

```bash
curl -X POST http://localhost:8082/api/v1/obligations \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": null,
    "obligation_type": "compliance:periodic_report",
    "due_date": "2025-05-15",
    "status": "pending",
    "description": "Colorado Periodic Report - Annual LLC filing",
    "recurrence": "FREQ=YEARLY;BYMONTH=5;BYMONTHDAY=15",
    "extra_metadata": {
      "fee": "$10",
      "reminder_days_before": 30
    }
  }'
```

### Update Obligation (Mark as Completed)

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{obligation-uuid} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "extra_metadata": {
      "completed_date": "2025-05-10",
      "confirmation_number": "CO-2025-12345"
    }
  }'
```

## Obligation Status

**Available statuses:**

- `pending` - Not yet due

- `due_soon` - Due within 7 days

- `overdue` - Past due date

- `completed` - Satisfied

- `cancelled` - No longer applicable

## Recurrence Patterns (RRULE)

**Obligations support RFC 5545 recurrence rules:**

**Annual (same date each year):**

```
FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=15
```

**Quarterly:**

```
FREQ=YEARLY;BYMONTH=4,6,9,1;BYMONTHDAY=15
```

**Monthly:**

```
FREQ=MONTHLY;BYMONTHDAY=1
```

**See:** [Obligations Guide - RRULE Format](../user-guide/obligations.md#rrule-format-explained)

## Obligation Schema

**Key fields:**

- `id` - UUID primary key

- `property_id` - FK to property (nullable for LLC-wide obligations)

- `obligation_type` - Obligation type (enum)

- `due_date` - When obligation is due

- `status` - Current status (enum)

- `recurrence` - RRULE string for recurring obligations

- `description` - Human-readable description

- `provenance` - Data lineage tracking

- `extra_metadata` - Flexible JSON (fees, confirmation numbers, etc.)

## Seed Common Obligations

**Use the seed script to populate standard LLC obligations:**

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

- Form 1065 tax return

- Property tax payments

- Insurance renewals

- Property inspections

**See:** `scripts/seed_obligations.py` for common obligation templates

## Related Documentation

- [Managing Obligations](../user-guide/obligations.md) - Complete obligations guide
- [RRULE Format Explained](../user-guide/obligations.md#rrule-format-explained) - Recurrence patterns
- Seed script: `scripts/seed_obligations.py`

---

**Status:** ✅ Implemented (tests: `tests/test_api_obligations.py`)

Obligations can also be seeded via `scripts/seed_obligations.py`.

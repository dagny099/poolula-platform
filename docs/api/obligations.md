# Obligations API Reference

*Coming soon*

API endpoints for managing compliance obligations and deadlines.

## Overview

The Obligations API allows you to create, read, update, and delete compliance deadlines, tax filings, and recurring obligations.

**Base URL:** `/api/v1/obligations`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/obligations` | List obligations with filters | 🚧 Planned |
| GET | `/api/v1/obligations/{id}` | Get obligation by ID | 🚧 Planned |
| POST | `/api/v1/obligations` | Create new obligation | 🚧 Planned |
| PATCH | `/api/v1/obligations/{id}` | Update obligation | 🚧 Planned |
| DELETE | `/api/v1/obligations/{id}` | Soft delete obligation | 🚧 Planned |

## Obligation Types

**Tax-related:**

- `tax:filing` - Tax return deadlines

- `tax:payment` - Tax payment deadlines

**Compliance:**

- `compliance:periodic_report` - State annual reports

- `compliance:license_renewal` - Business licenses

**Property:**

- `property:tax` - Property tax payments

- `property:insurance` - Insurance renewals

- `property:inspection` - Property inspections

**Other:**

- `other` - Miscellaneous obligations

## Quick Examples

### List Obligations

```bash
# All obligations
curl http://localhost:8082/api/v1/obligations

# Filter by status
curl http://localhost:8082/api/v1/obligations?status=pending

# Upcoming deadlines (next 30 days)
curl http://localhost:8082/api/v1/obligations?upcoming=30
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

**See:** [Seed Obligations Script](../../scripts/seed_obligations.py)

## Related Documentation

- [Managing Obligations](../user-guide/obligations.md) - Complete obligations guide

- [RRULE Format Explained](../user-guide/obligations.md#rrule-format-explained) - Recurrence patterns

- [Seed Script](../../scripts/seed_obligations.py) - Common obligations creator

---

**Status:** 🚧 Planned for Phase 3

**Current:** Obligations can be seeded via script, API endpoints coming in Phase 3.

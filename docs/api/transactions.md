# Transactions API Reference

API endpoints for managing financial transactions.

## Overview

The Transactions API allows you to create, read, update, and archive transaction records for rental income, expenses, and other financial activity. All mutations are recorded in the audit log.

**Base URL:** `/api/v1/transactions`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/transactions` | List transactions with filters | ✅ Implemented |
| GET | `/api/v1/transactions/{id}` | Get transaction by ID | ✅ Implemented |
| POST | `/api/v1/transactions` | Create new transaction | ✅ Implemented |
| PATCH | `/api/v1/transactions/{id}` | Update transaction | ✅ Implemented |
| DELETE | `/api/v1/transactions/{id}` | Archive (soft delete) transaction | ✅ Implemented |

## Query Parameters (GET list)

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | UUID | Filter by property |
| `start_date` | date | Include transactions on/after this date |
| `end_date` | date | Include transactions on/before this date |
| `category` | string | Category name or value (`UTILITIES_GAS` or `utilities:gas`) |
| `transaction_type` | string | `revenue`, `expense`, `capital`, `equity`, `transfer` |
| `include_archived` | bool | Include archived transactions (default false) |
| `limit` | int | Max results (default 500) |

Results are ordered newest first.

## Transaction Categories

Categories come from `core/database/enums.py::TransactionCategory` (hierarchical colon notation). Highlights:

**Revenue:**

- `rental_income` — Airbnb bookings, traditional rent

**Operating expenses:**

- `utilities:gas`, `utilities:water`, `utilities:electric`, `utilities:internet`, `utilities:other`
- `repairs_maintenance`, `cleaning`, `supplies`
- `insurance:property`, `insurance:liability`, `insurance:other`
- `property_taxes`, `property_management`, `hoa_fees`
- `professional:accounting`, `professional:legal`, `professional:other`
- `bank_fees`, `interest:expense`, `credit_card_fees`
- `advertising`, `licenses_permits`, `office_expense`, `travel`

**Capital (adds to basis):** `capital_improvement`, `furniture_fixtures`, `basis_adjustment`

**Member equity:** `member_contribution`, `member_distribution`

**Fallback:** `uncategorized`

Enum inputs accept either the name (`UTILITIES_GAS`) or the value (`utilities:gas`); responses always emit the value.

## Quick Examples

### List Transactions

```bash
# All transactions
curl http://localhost:8082/api/v1/transactions

# Filter by category
curl "http://localhost:8082/api/v1/transactions?category=rental_income"

# Filter by date range
curl "http://localhost:8082/api/v1/transactions?start_date=2024-01-01&end_date=2024-12-31"
```

### Create Transaction

```bash
curl -X POST http://localhost:8082/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "{property-uuid}",
    "transaction_date": "2025-08-15",
    "amount": "16144.00",
    "category": "rental_income",
    "transaction_type": "revenue",
    "description": "August 2025 rental income",
    "source_account": "Operating Account"
  }'
```

### Archive a Transaction

```bash
curl -X DELETE http://localhost:8082/api/v1/transactions/{transaction-uuid}
```

Financial records are never hard-deleted: DELETE sets `extra_metadata.archived = true`, excludes the record from default listings, and preserves the prior state in the audit log.

## Transaction Schema

**Key fields:**

- `id` - UUID primary key
- `property_id` - FK to property (**required** — every transaction belongs to a property)
- `transaction_date` - When transaction occurred
- `amount` - Transaction amount (cannot be zero)
- `category` - One of 30+ predefined categories
- `transaction_type` - `revenue`, `expense`, `capital`, `equity`, or `transfer`
- `description` - Human-readable description
- `source_account` - Bank account or source
- `provenance` - Data lineage tracking (JSON)
- `extra_metadata` - Flexible JSON (includes `archived` flag when soft-deleted)

## Related Documentation

- [Transaction Categories](../architecture/data-models.md#transaction-categories) - Full category list
- [Chatbot Queries](../user-guide/chatbot.md#financial-questions) - Query transactions via AI
- [Sample Questions](../sample-questions.md#2-bookkeeper-financial-records-accounting) - Transaction query examples

---

**Status:** ✅ Implemented (tests: `tests/test_api_transactions.py`)

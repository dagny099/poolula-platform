# Transactions API Reference

*Coming soon*

API endpoints for managing financial transactions.

## Overview

The Transactions API allows you to create, read, update, and delete transaction records for rental income, expenses, and other financial activity.

**Base URL:** `/api/v1/transactions`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/transactions` | List transactions with filters | 🚧 Planned |
| GET | `/api/v1/transactions/{id}` | Get transaction by ID | 🚧 Planned |
| POST | `/api/v1/transactions` | Create new transaction | 🚧 Planned |
| PATCH | `/api/v1/transactions/{id}` | Update transaction | 🚧 Planned |
| DELETE | `/api/v1/transactions/{id}` | Soft delete transaction | 🚧 Planned |

## Transaction Categories

**Revenue:**

- `revenue:rental_income` - Short-term rental income

- `revenue:long_term_rental` - Traditional lease income

- `revenue:other` - Other income

**Expenses:**

- `expense:utilities:electricity`

- `expense:utilities:gas`

- `expense:utilities:water`

- `expense:utilities:internet`

- `expense:maintenance:repairs`

- `expense:maintenance:cleaning`

- `expense:property_management`

- `expense:insurance`

- `expense:property_tax`

- And 20+ more categories...

## Quick Examples

### List Transactions

```bash
# All transactions
curl http://localhost:8082/api/v1/transactions

# Filter by category
curl http://localhost:8082/api/v1/transactions?category=revenue:rental_income

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
    "category": "revenue:rental_income",
    "transaction_type": "REVENUE",
    "description": "August 2025 rental income",
    "source_account": "Operating Account"
  }'
```

## Transaction Schema

**Key fields:**

- `id` - UUID primary key

- `property_id` - FK to property (nullable for LLC-level transactions)

- `transaction_date` - When transaction occurred

- `amount` - Transaction amount (positive for revenue, expenses)

- `category` - One of 30+ predefined categories

- `transaction_type` - REVENUE or EXPENSE

- `description` - Human-readable description

- `source_account` - Bank account or source

- `provenance` - Data lineage tracking

## Related Documentation

- [Transaction Categories](../architecture/data-models.md#transaction-categories) - Full category list
- [Chatbot Queries](../user-guide/chatbot.md#financial-questions) - Query transactions via AI
- [Sample Questions](../sample-questions.md#2-bookkeeper-financial-records-accounting) - Transaction query examples

---

**Status:** 🚧 Planned for Phase 3

**API endpoints will be added after Phase 2 chatbot completion.**

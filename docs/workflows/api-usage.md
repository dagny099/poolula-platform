# API Usage Guide

Complete guide for using the Poolula Platform REST API.

## Starting the API Server

### Development Mode

```bash
# From project root
uv run uvicorn apps.api.main:app --reload --port 8082
```

The API will be available at:
- **Base URL**: `http://localhost:8082`
- **Interactive docs (Swagger UI)**: `http://localhost:8082/docs`
- **Alternative docs (ReDoc)**: `http://localhost:8082/redoc`

### Production Mode

```bash
# Without auto-reload
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8082
```

## API Overview

### Base URL

```
http://localhost:8082
```

### API Version

All endpoints are prefixed with `/api/v1`:

```
GET  /api/v1/properties
POST /api/v1/properties
...
```

### Response Format

All responses are JSON. Properties include full provenance tracking:

```json
{
  "id": "12345678-1234-1234-1234-123456789012",
  "address": "900 S 9th St, Montrose, CO 81401",
  "acquisition_date": "2024-04-15",
  "purchase_price_total": "442300.00",
  "provenance": {
    "source_type": "manual_entry",
    "confidence": 1.0
  },
  "created_at": "2025-11-13T10:00:00.000000",
  "updated_at": "2025-11-13T10:00:00.000000"
}
```

## Endpoints

### Health Check

**GET /health**

Check API and database health.

```bash
curl http://localhost:8082/health
```

**Response:**
```json
{
  "status": "healthy",
  "api_version": "0.1.0",
  "database_connected": true
}
```

---

### List Properties

**GET /api/v1/properties**

Get all properties, optionally filtered by status.

```bash
# All properties
curl http://localhost:8082/api/v1/properties

# Active properties only
curl http://localhost:8082/api/v1/properties?status=ACTIVE

# Inactive properties
curl http://localhost:8082/api/v1/properties?status=INACTIVE
```

**Query Parameters:**
- `status` (optional): Filter by PropertyStatus (`ACTIVE`, `UNDER_CONTRACT`, `SOLD`, `INACTIVE`)

**Response:** Array of Property objects

```json
[
  {
    "id": "...",
    "address": "900 S 9th St, Montrose, CO 81401",
    "status": "ACTIVE",
    ...
  }
]
```

---

### Get Property

**GET /api/v1/properties/{id}**

Get a single property by UUID.

```bash
curl http://localhost:8082/api/v1/properties/12345678-1234-1234-1234-123456789012
```

**Response:** Property object

```json
{
  "id": "12345678-1234-1234-1234-123456789012",
  "address": "900 S 9th St, Montrose, CO 81401",
  "acquisition_date": "2024-04-15",
  "purchase_price_total": "442300.00",
  "land_basis": "78200.00",
  "building_basis": "364100.00",
  "ffe_basis": "10000.00",
  "placed_in_service": "2025-02-01",
  "status": "ACTIVE",
  "provenance": {...},
  "extra_metadata": {...},
  "created_at": "2025-11-13T10:00:00",
  "updated_at": "2025-11-13T10:00:00"
}
```

**Error Responses:**
- `404 Not Found`: Property doesn't exist

```json
{
  "detail": "Property not found: 12345678-1234-1234-1234-123456789012"
}
```

---

### Create Property

**POST /api/v1/properties**

Create a new property.

```bash
curl -X POST http://localhost:8082/api/v1/properties \
  -H "Content-Type: application/json" \
  -d '{
    "address": "900 S 9th St, Montrose, CO 81401",
    "acquisition_date": "2024-04-15",
    "purchase_price_total": "442300.00",
    "land_basis": "78200.00",
    "building_basis": "364100.00",
    "ffe_basis": "10000.00",
    "placed_in_service": "2025-02-01",
    "status": "ACTIVE",
    "provenance": {},
    "extra_metadata": {}
  }'
```

**Required Fields:**
- `address` (string)
- `acquisition_date` (YYYY-MM-DD)
- `purchase_price_total` (decimal string)
- `land_basis` (decimal string)
- `building_basis` (decimal string)

**Optional Fields:**
- `ffe_basis` (default: "0.00")
- `placed_in_service` (date, nullable)
- `status` (default: "ACTIVE")
- `provenance` (default: {})
- `extra_metadata` (default: {})

**Response:** Created property with generated `id` (201 Created)

**Error Responses:**
- `422 Unprocessable Entity`: Validation error (missing required fields, invalid format)

```json
{
  "detail": [
    {
      "loc": ["body", "acquisition_date"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### Update Property

**PATCH /api/v1/properties/{id}**

Update an existing property. Only include fields you want to change.

```bash
curl -X PATCH http://localhost:8082/api/v1/properties/12345678-1234-1234-1234-123456789012 \
  -H "Content-Type: application/json" \
  -d '{
    "placed_in_service": "2025-03-01",
    "status": "ACTIVE"
  }'
```

**Updatable Fields:**
- Any Property field (currently no restrictions)
- `updated_at` is automatically set to current timestamp

**Note:** ⚠️ **Accounting Integrity**
Currently all fields can be updated, including:
- `acquisition_date`
- `purchase_price_total`
- `land_basis`, `building_basis`, `ffe_basis`

Be careful changing these after depreciation calculations. Phase 5 may add protection for immutable fields.

**Response:** Updated property object

**Error Responses:**
- `404 Not Found`: Property doesn't exist
- `500 Internal Server Error`: Update failed

---

### Delete Property (Soft Delete)

**DELETE /api/v1/properties/{id}**

Soft delete a property by setting `status = INACTIVE`.

```bash
curl -X DELETE http://localhost:8082/api/v1/properties/12345678-1234-1234-1234-123456789012
```

**Response:** 204 No Content (no body)

**What Happens:**
- Property `status` set to `INACTIVE`
- `updated_at` set to current timestamp
- Record remains in database (not deleted)

**Error Responses:**
- `404 Not Found`: Property doesn't exist

---

## Common Workflows

### Create Property with Full Provenance

```bash
curl -X POST http://localhost:8082/api/v1/properties \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St, Montrose, CO 81401",
    "acquisition_date": "2024-06-01",
    "purchase_price_total": "350000.00",
    "land_basis": "50000.00",
    "building_basis": "280000.00",
    "ffe_basis": "20000.00",
    "provenance": {
      "source_type": "manual_entry",
      "source_id": "closing_statement_2024_06.pdf",
      "confidence": 1.0,
      "verification_status": "verified",
      "notes": "Imported from settlement statement"
    },
    "extra_metadata": {
      "closing_date": "2024-06-15",
      "escrow_number": "ESC-2024-001"
    }
  }'
```

### Update Property Status Workflow

```bash
# 1. Property under contract
curl -X PATCH http://localhost:8082/api/v1/properties/{id} \
  -d '{"status": "UNDER_CONTRACT"}'

# 2. Closing completes
curl -X PATCH http://localhost:8082/api/v1/properties/{id} \
  -d '{"status": "ACTIVE", "placed_in_service": "2025-03-01"}'

# 3. Property sold
curl -X PATCH http://localhost:8082/api/v1/properties/{id} \
  -d '{"status": "SOLD"}'
```

### Find Properties Missing Data

```bash
# Get all properties
curl http://localhost:8082/api/v1/properties | jq

# Filter for missing placed_in_service
curl http://localhost:8082/api/v1/properties | \
  jq '.[] | select(.placed_in_service == null)'
```

## Using jq for JSON Processing

### Pretty Print

```bash
curl http://localhost:8082/api/v1/properties | jq
```

### Extract Specific Fields

```bash
# Get just addresses and IDs
curl http://localhost:8082/api/v1/properties | \
  jq '.[] | {id, address}'
```

### Calculate Total Basis

```bash
# Sum of purchase prices
curl http://localhost:8082/api/v1/properties | \
  jq '[.[] | .purchase_price_total | tonumber] | add'
```

### Filter by Status

```bash
# Active properties only
curl http://localhost:8082/api/v1/properties | \
  jq '.[] | select(.status == "ACTIVE")'
```

## Error Handling

### Common HTTP Status Codes

- `200 OK`: Success (GET, PATCH)
- `201 Created`: Success (POST)
- `204 No Content`: Success (DELETE)
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Example Error Response

```json
{
  "detail": "Property not found: 12345678-1234-1234-1234-123456789012"
}
```

## Interactive API Documentation

### Swagger UI

Open `http://localhost:8082/docs` in your browser for interactive API documentation.

Features:
- Try out endpoints directly
- See request/response schemas
- Auto-generated from code

### ReDoc

Open `http://localhost:8082/redoc` for alternative documentation format.

## Authentication (Phase 4)

Currently, the API has **no authentication**. This will be added in Phase 4 when the frontend is integrated.

For now, the API is intended for local development only.

## Next Steps

- **Data Import**: See [data-import.md](data-import.md) for seeding from YAML
- **Testing**: See [testing.md](testing.md) for running API tests
- **Phase 2**: Transaction, Document, and Obligation endpoints

## Related Files

- **API Application**: `apps/api/main.py`
- **Property Routes**: `apps/api/routes/properties.py`
- **Database Models**: `core/database/models.py`

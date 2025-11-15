# Properties API Reference

*Coming soon*

API endpoints for managing rental properties.

## Overview

The Properties API allows you to create, read, update, and delete rental property records.

**Base URL:** `/api/v1/properties`

## Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/properties` | List all properties | ✅ Available |
| GET | `/api/v1/properties/{id}` | Get property by ID | ✅ Available |
| POST | `/api/v1/properties` | Create new property | ✅ Available |
| PATCH | `/api/v1/properties/{id}` | Update property | ✅ Available |
| DELETE | `/api/v1/properties/{id}` | Soft delete property | ✅ Available |

## Quick Examples

### List Properties

```bash
curl http://localhost:8082/api/v1/properties
```

### Get Property by ID

```bash
curl http://localhost:8082/api/v1/properties/{property-uuid}
```

### Create Property

```bash
curl -X POST http://localhost:8082/api/v1/properties \
  -H "Content-Type: application/json" \
  -d '{
    "address": "900 S 9th St, Montrose, CO 81401",
    "acquisition_date": "2024-04-15",
    "purchase_price_total": "442300.00",
    "land_basis": "78200.00",
    "building_basis": "364100.00"
  }'
```

## Property Schema

**Key fields:**

- `id` - UUID primary key

- `address` - Full property address

- `acquisition_date` - Purchase date

- `purchase_price_total` - Total acquisition cost

- `land_basis` - Land portion of basis

- `building_basis` - Building portion of basis

- `ffe_basis` - Furniture, fixtures, equipment basis

- `placed_in_service` - Depreciation start date

- `status` - ACTIVE or INACTIVE

- `provenance` - Data lineage tracking

- `extra_metadata` - Flexible JSON for custom fields

## Related Documentation

- [API Usage Workflow](../workflows/api-usage.md) - Complete API examples

- [Database Models](../architecture/data-models.md) - Property model schema

- [Data Import](../workflows/data-import.md) - Bulk property import

---

**Status:** ✅ Available (Phase 1)

**Comprehensive documentation coming in Phase 4.**

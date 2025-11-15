# API Design

FastAPI REST API architecture and design patterns for Poolula Platform.

## Overview

Poolula Platform uses FastAPI to provide a RESTful API for managing properties, transactions, documents, obligations, and chatbot interactions.

**Base URL:** `http://localhost:8082`

## Design Principles

### 1. RESTful Design

Standard HTTP methods:
- `GET` - Retrieve resources
- `POST` - Create resources
- `PATCH` - Update resources (partial updates)
- `DELETE` - Soft delete resources (status=INACTIVE)

### 2. Type Safety

Pydantic models for request/response validation:

```python
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

class PropertyCreate(BaseModel):
    address: str
    acquisition_date: date
    purchase_price_total: Decimal
```

### 3. Automatic Documentation

FastAPI generates interactive API docs:
- Swagger UI: `http://localhost:8082/docs`
- ReDoc: `http://localhost:8082/redoc`

### 4. Error Handling

Standard HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Validation error
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## API Endpoints

### Health Check

**Endpoint:** `GET /health`

Check API and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-11-15T10:30:00Z"
}
```

### Properties API

**Base:** `/api/v1/properties`

See: [Properties API Reference](../api/properties.md)

### Transactions API

**Base:** `/api/v1/transactions`

See: [Transactions API Reference](../api/transactions.md)

### Documents API

**Base:** `/api/v1/documents`

See: [Documents API Reference](../api/documents.md)

### Obligations API

**Base:** `/api/v1/obligations`

See: [Obligations API Reference](../api/obligations.md)

### Chat API

**Base:** `/api/query`

See: [Chat API Reference](../api/chat.md)

## Request/Response Patterns

### Create Resource (POST)

**Request:**
```json
{
  "address": "900 S 9th St, Montrose, CO 81401",
  "acquisition_date": "2024-04-15",
  "purchase_price_total": "442300.00"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "address": "900 S 9th St, Montrose, CO 81401",
  "acquisition_date": "2024-04-15",
  "purchase_price_total": "442300.00",
  "provenance": {
    "source_type": "api_create",
    "confidence": 1.0
  },
  "created_at": "2024-11-15T10:30:00Z"
}
```

### Update Resource (PATCH)

**Request:**
```json
{
  "land_basis": "78200.00",
  "building_basis": "364100.00"
}
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "address": "900 S 9th St, Montrose, CO 81401",
  "land_basis": "78200.00",
  "building_basis": "364100.00",
  "updated_at": "2024-11-15T11:00:00Z"
}
```

### List Resources (GET)

**Query Parameters:**
- `limit` - Number of results (default: 100)
- `offset` - Pagination offset (default: 0)
- `status` - Filter by status (ACTIVE, INACTIVE)

**Response (200 OK):**
```json
{
  "items": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

## Authentication & Authorization

**Current State (Development):**
- No authentication required
- Local-only deployment

**Future (Production):**
- OAuth2 / JWT tokens
- Role-based access control (RBAC)
- API key authentication for programmatic access

## CORS Configuration

Cross-Origin Resource Sharing (CORS) is enabled for local development:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Rate Limiting

**Current State:** None (local development)

**Future:** Redis-based rate limiting per user/API key

## Validation Strategy

### Current (Flexible)

- PATCH endpoints allow all fields
- Trust-based (single user/trustee)
- Full flexibility for data corrections

### Future (Protected)

- Protect immutable fields (acquisition_date, basis values)
- Require audit trail for sensitive changes
- Validation rules for business logic

## Error Response Format

```json
{
  "detail": "Validation error message",
  "status_code": 400,
  "timestamp": "2024-11-15T10:30:00Z"
}
```

## API Versioning

Current: `/api/v1/`

Future versions will maintain backward compatibility:
- `/api/v2/` - New version with breaking changes
- `/api/v1/` - Legacy version (maintained)

## Performance Considerations

### Database Connection Pooling

SQLModel/SQLAlchemy connection pooling configured for concurrent requests.

### Query Optimization

- Eager loading for relationships
- Database indexes on frequently queried fields
- Pagination for large result sets

### Caching Strategy

**Current:** None (development)

**Future:** Redis caching for:
- Frequently accessed properties
- Chatbot query results
- Transaction summaries

## Testing

API tests use FastAPI TestClient:

```python
from fastapi.testclient import TestClient

def test_create_property():
    response = client.post("/api/v1/properties", json={...})
    assert response.status_code == 201
```

See: [Testing Guide](../testing/testing.md)

## Related Documentation

- [API Endpoints](../api/overview.md) - Endpoint reference
- [Data Models](data-models.md) - Database schema
- [System Design](system-design.md) - Architecture overview

---

*For API questions, see [FAQ](../faq.md)*

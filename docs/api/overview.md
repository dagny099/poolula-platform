# API Reference Overview

Poolula Platform provides a RESTful API built with FastAPI for managing properties, transactions, documents, and chatbot interactions.

## Base URL

```
http://localhost:8082/api
```

For production deployments, replace with your server URL.

## Interactive Documentation

FastAPI provides auto-generated interactive API documentation:

- **Swagger UI**: [http://localhost:8082/docs](http://localhost:8082/docs)
- **ReDoc**: [http://localhost:8082/redoc](http://localhost:8082/redoc)

These interfaces allow you to:

- View all endpoints and their parameters
- Test API calls directly from the browser
- See request/response schemas
- Download OpenAPI specification

## Authentication

Currently, the API does not require authentication (local development mode).

!!! warning "Production Deployment"
    For production, implement authentication using FastAPI's security utilities. Consider OAuth2, API keys, or JWT tokens.

## API Endpoints Overview

### Chatbot Endpoints

Natural language query interface:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Query chatbot with natural language |
| `/api/documents` | GET | List all ingested documents |
| `/api/documents/{title}` | GET | Get document metadata by title |

[→ Chatbot API Details](chat.md)

### Property Endpoints

Manage rental properties:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/properties` | GET | List all properties |
| `/api/v1/properties/{id}` | GET | Get property by ID |
| `/api/v1/properties` | POST | Create new property |
| `/api/v1/properties/{id}` | PUT | Update property |
| `/api/v1/properties/{id}` | DELETE | Soft delete property |

[→ Property API Details](properties.md)

### Transaction Endpoints

Manage financial transactions:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transactions` | GET | List transactions with filters |
| `/api/v1/transactions/{id}` | GET | Get transaction by ID |
| `/api/v1/transactions` | POST | Create new transaction |
| `/api/v1/transactions/{id}` | PUT | Update transaction |
| `/api/v1/transactions/{id}` | DELETE | Soft delete transaction |

[→ Transaction API Details](transactions.md)

### System Endpoints

Health and status:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | API root with links |

## Common Response Formats

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  }
}
```

### Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Pagination

For list endpoints, responses include pagination:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

## HTTP Status Codes

The API uses standard HTTP status codes:

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid request data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

## Request Headers

### Content-Type

For POST/PUT requests:

```
Content-Type: application/json
```

### Accept

Optional, defaults to JSON:

```
Accept: application/json
```

## Example API Calls

### Using curl

```bash
# Health check
curl http://localhost:8082/health

# Query chatbot
curl -X POST http://localhost:8082/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was my rental income in August 2025?"}'

# List properties
curl http://localhost:8082/api/v1/properties

# Get specific property
curl http://localhost:8082/api/v1/properties/abc123
```

### Using Python

```python
import requests

# Base URL
API_URL = "http://localhost:8082/api"

# Query chatbot
response = requests.post(
    f"{API_URL}/query",
    json={
        "query": "What was my rental income in August 2025?",
        "session_id": None
    }
)

data = response.json()
print(data["answer"])
print(data["sources"])
```

### Using JavaScript

```javascript
// Query chatbot
const response = await fetch('http://localhost:8082/api/query', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        query: 'What was my rental income in August 2025?',
        session_id: null
    })
});

const data = await response.json();
console.log(data.answer);
console.log(data.sources);
```

## Rate Limiting

Currently, there are no rate limits (local development).

!!! warning "Production Consideration"
    For production deployment, implement rate limiting to prevent abuse. Consider using FastAPI middleware or a reverse proxy like nginx.

## CORS Policy

The API allows all origins in development:

```python
allow_origins=["*"]
```

!!! warning "Production Security"
    For production, restrict CORS to specific domains:
    ```python
    allow_origins=["https://yourdomain.com"]
    ```

## Versioning

API endpoints under `/api/v1/` are versioned. Breaking changes will increment the version number.

Current version: **v1**

## Error Handling Best Practices

### Client-Side Error Handling

```python
try:
    response = requests.post(f"{API_URL}/query", json={"query": "..."})
    response.raise_for_status()  # Raises exception for 4xx/5xx
    data = response.json()
except requests.exceptions.HTTPError as e:
    if response.status_code == 422:
        print("Validation error:", response.json())
    elif response.status_code == 500:
        print("Server error:", response.json())
    else:
        print(f"HTTP error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

## Testing the API

### Using the Interactive Docs

1. Start the API server:
   ```bash
   uv run uvicorn apps.api.main:app --reload --port 8082
   ```

2. Open [http://localhost:8082/docs](http://localhost:8082/docs)

3. Click on any endpoint to expand it

4. Click "Try it out"

5. Fill in parameters and click "Execute"

### Using pytest

```bash
# Run API tests
uv run pytest tests/test_api.py -v

# Run specific test
uv run pytest tests/test_api_properties.py::test_create_property -v
```

## API Clients

### Official Clients

None currently available. The API can be accessed directly using:

- Python: `requests` or `httpx`
- JavaScript: `fetch` or `axios`
- Command line: `curl`

### Generating Client Code

Use the OpenAPI specification to generate client code:

```bash
# Download OpenAPI spec
curl http://localhost:8082/openapi.json > openapi.json

# Generate Python client (using openapi-generator)
openapi-generator-cli generate -i openapi.json \
    -g python -o ./python-client
```

## Next Steps

- [Chatbot API Details](chat.md) - Query endpoints and response format
- [Property API Details](properties.md) - Property management endpoints
- [Transaction API Details](transactions.md) - Transaction endpoints
- [API Design](../architecture/api-design.md) - API architecture and patterns

## API Design Philosophy

The Poolula Platform API follows these principles:

1. **RESTful** - Standard HTTP methods (GET, POST, PUT, DELETE)
2. **JSON-first** - All requests and responses use JSON
3. **Self-documenting** - OpenAPI/Swagger auto-generated documentation
4. **Type-safe** - Pydantic models for request/response validation
5. **Consistent** - Standard error formats and status codes

---

**Ready to dive deeper?** → [Chatbot API Details](chat.md)

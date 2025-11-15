# Chatbot API Reference

API endpoints for natural language querying of your LLC and property data.

## Base Endpoint

```
POST /api/v1/chat/query
```

## Query Endpoint

Send natural language questions to the AI chatbot.

### Request

**Method:** `POST`

**URL:** `/api/v1/chat/query`

**Headers:**

```
Content-Type: application/json
```

**Body:**

```json
{
  "query": "What was my rental income in August 2024?",
  "session_id": "optional-session-uuid"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language question |
| `session_id` | string (UUID) | No | Session ID for conversation history |

### Response

**Status:** `200 OK`

**Body:**

```json
{
  "answer": "Your rental income in August 2024 was $16,144. This includes short-term rental revenue from your property at 900 S 9th St, Montrose, CO.",
  "sources": [
    {
      "type": "query_database",
      "description": "Database query for transactions",
      "relevance": 1.0
    }
  ],
  "session_id": "abc-123-def-456"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | AI-generated response |
| `sources` | array | List of sources used to generate answer |
| `session_id` | string | Session ID for continued conversation |

## Available Tools

The chatbot uses specialized search tools:

### 1. Database Query

**Tool:** `query_database`

**Purpose:** Search structured data (properties, transactions, obligations)

**Example queries:**

- "What is our property address?"

- "Show me transactions from August 2024"

- "What is our EIN number?"

### 2. Document Search

**Tool:** `search_document_content`

**Purpose:** Semantic search through ingested documents

**Example queries:**

- "What is our business purpose in the operating agreement?"

- "Who are the members of our LLC?"

- "What insurance coverage do we have?"

### 3. List Documents

**Tool:** `list_business_documents`

**Purpose:** Show all available documents

**Example queries:**

- "What documents do we have?"

- "List all formation documents"

- "Show me our document library"

## Example Requests

### Using curl

```bash
# Simple query
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is our property address?"
  }'

# With session ID
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was the rental income?",
    "session_id": "abc-123-def-456"
  }'
```

### Using Python

```python
import requests

API_URL = "http://localhost:8082/api/v1/chat"

# Send query
response = requests.post(
    f"{API_URL}/query",
    json={
        "query": "What was my rental income in August 2024?",
        "session_id": None
    }
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Sources: {data['sources']}")
```

### Using JavaScript

```javascript
const response = await fetch('http://localhost:8082/api/v1/chat/query', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        query: 'What was my rental income in August 2024?'
    })
});

const data = await response.json();
console.log(data.answer);
```

## Session Management

**Sessions maintain conversation context.**

### Creating a Session

**First query automatically creates a session:**

```json
POST /api/v1/chat/query
{
  "query": "What properties do we own?"
}

// Response includes session_id
{
  "answer": "...",
  "session_id": "new-session-uuid"
}
```

### Continuing a Session

**Use the returned session_id in follow-up queries:**

```json
POST /api/v1/chat/query
{
  "query": "What's the address of that property?",
  "session_id": "new-session-uuid"  // From previous response
}
```

**The chatbot understands "that property" refers to the property from the previous query.**

## Error Responses

### 400 Bad Request

**Missing required field:**

```json
{
  "detail": "Field 'query' is required"
}
```

### 422 Validation Error

**Invalid input format:**

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

**Server error (e.g., AI service unavailable):**

```json
{
  "detail": "AI service temporarily unavailable"
}
```

## Best Practices

### 1. Be Specific

**Good:**

- "What was my rental income in August 2024?"

- "Show me utility expenses for 2024"

**Less effective:**

- "Tell me about money"

- "What happened?"

### 2. Use Sessions for Follow-ups

```python
# First query
response1 = requests.post(url, json={"query": "What properties do we own?"})
session_id = response1.json()["session_id"]

# Follow-up with context
response2 = requests.post(url, json={
    "query": "What's the land basis for that property?",
    "session_id": session_id
})
```

### 3. Handle Sources

```python
data = response.json()

# Check what sources were used
for source in data["sources"]:
    if source["type"] == "query_database":
        print("Answer based on database query")
    elif source["type"] == "search_document_content":
        print(f"Answer from document: {source.get('document_title')}")
```

## Rate Limiting

**Current:** No rate limiting (development mode)

**Production:** TBD (Phase 4+)

## Response Time

**Typical response times:**

- Database queries: 1-2 seconds

- Document searches: 2-3 seconds

- Hybrid queries: 3-5 seconds

**First query after startup may be slower (model loading).**

## Related Documentation

- [Using the Chatbot](../user-guide/chatbot.md) - User guide for asking questions

- [Evaluation Harness](../evaluation/harness.md) - How we test chatbot quality

- [Sample Questions](../sample-questions.md) - 133 example questions

---

**Status:** ✅ Available in Phase 2+ (Current)

# System Design

Poolula Platform uses a modular architecture that separates concerns while maintaining simplicity for a single-developer project.

## Architecture Principles

1. **Data-First** - Database as single source of truth
2. **Modular Monolith** - Clear module boundaries without microservices complexity
3. **Type Safety** - Pydantic models throughout
4. **Provenance Tracking** - Every data point records its source
5. **Progressive Disclosure** - Simple defaults with detailed options available

## High-Level Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        A1[Airbnb CSV]
        A2[Bank Statements]
        A3[Expense CSV]
        A4[Manual Entry]
    end

    subgraph "Import Layer"
        B1[import_airbnb_transactions.py]
        B2[import_expenses.py]
        B3[seed_database.py]
        B4[ingest_documents.py]
    end

    subgraph "Data Layer"
        C1[(SQLite Database<br/>5 Tables)]
        C2[(ChromaDB<br/>Vector Store)]
    end

    subgraph "Service Layer"
        D1[FastAPI REST API]
        D2[RAG System]
        D3[Tool Manager]
    end

    subgraph "Interface Layer"
        E1[Frontend<br/>Vanilla JS]
        E2[CLI Scripts]
        E3[Jupyter Notebooks]
    end

    subgraph "External Services"
        F1[Claude API<br/>Anthropic]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B2
    A4 --> B3

    B1 --> C1
    B2 --> C1
    B3 --> C1
    B4 --> C2

    C1 --> D1
    C2 --> D2
    D2 --> D3
    D3 --> F1

    D1 --> E1
    D1 --> E2
    D1 --> E3

    style C1 fill:#4A7C59
    style C2 fill:#2C5282
    style D2 fill:#2C5282
    style F1 fill:#E07A5F
```

## Core Components

### 1. Database Layer

**SQLite Database** - Single source of truth for structured data

**Tables:**

```mermaid
erDiagram
    Property ||--o{ Transaction : has
    Property ||--o{ Document : has
    Property ||--o{ Obligation : has
    Transaction ||--|| Provenance : tracks

    Property {
        uuid id PK
        string address
        date acquisition_date
        decimal purchase_price_total
        decimal land_basis
        decimal building_basis
        decimal ffe_basis
        date placed_in_service
        string status
    }

    Transaction {
        uuid id PK
        uuid property_id FK
        date transaction_date
        decimal amount
        string category
        string transaction_type
        string description
        string source_account
    }

    Document {
        uuid id PK
        uuid property_id FK
        string filename
        string doc_type
        date effective_date
        string version
        string confidentiality
        string storage_path
    }

    Obligation {
        uuid id PK
        uuid property_id FK
        string obligation_type
        date due_date
        string status
        string description
        string recurrence
    }

    Provenance {
        uuid id PK
        uuid transaction_id FK
        string source_type
        string source_id
        float confidence
        string notes
    }
```

**Design Decisions:**

- **SQLite** for development/small deployments (easy backup, no server)
- **UUIDs** for primary keys (distributed system ready)
- **Soft deletes** via `deleted_at` timestamp (audit trail preservation)
- **Computed properties** in SQLModel for derived values (e.g., `total_basis`)

### 2. Vector Store Layer

**ChromaDB** - Semantic search for business documents

**Collections:**

1. **document_catalog** - Document metadata (titles, types, dates)
2. **document_content** - Chunked document content with embeddings

**Embedding Strategy:**

- ONNXMiniLM_L6_V2 (ChromaDB default)
- No external model dependencies (self-contained)
- Chunk size: 800 characters
- Chunk overlap: 200 characters

### 3. Service Layer

#### FastAPI REST API

**Responsibilities:**

- HTTP request handling
- Input validation (Pydantic models)
- Business logic orchestration
- Response formatting
- CORS handling

**Endpoints:**

- `/api/query` - Chatbot queries
- `/api/v1/properties` - Property CRUD
- `/api/v1/transactions` - Transaction CRUD
- `/api/v1/documents` - Document metadata
- `/api/v1/obligations` - Obligation CRUD
- `/health` - Health checks

#### RAG System

**Components:**

```mermaid
graph LR
    A[User Query] --> B[RAG System]
    B --> C[Tool Manager]
    C --> D{Tool Selection}
    D -->|Structured Data| E[Database Query Tool]
    D -->|Document Search| F[Document Search Tool]
    D -->|List Docs| G[List Documents Tool]

    E --> H[SQLite]
    F --> I[ChromaDB]
    G --> I

    H --> J[Results]
    I --> J

    J --> K[Claude API]
    K --> L[Final Answer]

    style B fill:#2C5282
    style K fill:#E07A5F
```

**Tool System:**

1. **query_database** - SQL SELECT queries (properties, transactions, documents, obligations)
2. **search_document_content** - Semantic search in documents
3. **list_business_documents** - List available documents

**Multi-Round Tool Calling:**

- Maximum 2 rounds per query
- Sequential reasoning (use first tool results to inform second tool)
- Example: Query properties → Search specific property documents

### 4. Interface Layer

#### Frontend (Vanilla JS)

**Why Vanilla JS?**

- No build step required
- Fast page loads
- Easy to understand and modify
- No framework lock-in

**Components:**

- Chat interface with markdown rendering (Marked.js)
- 4 persona-based help sections
- Document upload (drag & drop)
- Resources sidebar

#### CLI Scripts

**Purpose:**

- Data import automation
- Document ingestion
- Database seeding
- Interactive chatbot (for terminal users)

**Key Scripts:**

- `cli.py` - Interactive chatbot CLI
- `import_airbnb_transactions.py` - Import Airbnb data
- `ingest_documents.py` - Process and embed documents
- `seed_obligations.py` - Create compliance deadlines

## Data Flow

### Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant RAG
    participant Tools
    participant DB
    participant ChromaDB
    participant Claude

    User->>Frontend: Ask question
    Frontend->>API: POST /api/query
    API->>RAG: Process query

    RAG->>Claude: Determine tools needed
    Claude->>RAG: Use query_database tool

    RAG->>Tools: Execute database query
    Tools->>DB: SQL SELECT
    DB->>Tools: Results
    Tools->>RAG: Formatted results

    RAG->>Claude: Generate response with data
    Claude->>RAG: Final answer

    RAG->>API: Response + sources
    API->>Frontend: JSON response
    Frontend->>User: Display answer + sources
```

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant Script
    participant Processor
    participant ChromaDB
    participant Metadata

    Script->>Metadata: Load metadata CSV
    Script->>Processor: Process document
    Processor->>Processor: Extract text (PDF/DOCX)
    Processor->>Processor: Chunk content (800 chars)
    Processor->>ChromaDB: Add document metadata
    Processor->>ChromaDB: Add content chunks
    ChromaDB->>ChromaDB: Generate embeddings
    ChromaDB->>Script: Success
```

### Transaction Import Flow

```mermaid
sequenceDiagram
    participant CSV
    participant Script
    participant Parser
    participant DB
    participant Provenance

    CSV->>Script: Airbnb export
    Script->>Parser: Parse CSV rows
    Parser->>Parser: Apply accrual accounting
    Parser->>Parser: Categorize transactions
    Parser->>DB: Insert transactions
    DB->>Provenance: Record source (CSV)
    Provenance->>DB: Link provenance
    DB->>Script: Success + summary
```

## Design Patterns

### 1. Provenance Tracking

Every transaction records its source:

```python
class Provenance(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    transaction_id: UUID = Field(foreign_key="transaction.id")
    source_type: SourceType  # CSV_IMPORT, MANUAL_ENTRY, etc.
    source_id: str  # filename, user ID, etc.
    confidence: float = 1.0
    notes: Optional[str] = None
```

**Benefits:**

- Audit trail for all data
- Identify data quality issues
- Support data lineage queries

### 2. Soft Deletes

Records are never hard-deleted:

```python
class BaseModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
```

**Benefits:**

- Preserve history
- Enable "undo" functionality
- Maintain referential integrity

### 3. Type Safety

Pydantic models throughout:

```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: list
    session_id: str
```

**Benefits:**

- Automatic validation
- IDE autocomplete
- Self-documenting code

### 4. Tool-Based Architecture

AI uses tools instead of direct DB access:

```python
tools = [
    {
        "name": "query_database",
        "description": "Query structured data",
        "input_schema": {...}
    },
    {
        "name": "search_document_content",
        "description": "Search documents",
        "input_schema": {...}
    }
]
```

**Benefits:**

- Safety (no SQL injection, no writes)
- Flexibility (add new tools easily)
- Transparency (see what AI is doing)

## Scalability Considerations

### Current (Phase 1)

- **Database**: SQLite (single file)
- **Users**: Single user / small team
- **Documents**: 100s of documents
- **Transactions**: 10,000s of transactions

### Future (Production)

- **Database**: PostgreSQL (multi-user support)
- **Caching**: Redis for session management
- **Load Balancing**: Multiple API instances
- **Authentication**: OAuth2 / JWT
- **Rate Limiting**: Per-user limits

## Security Considerations

### Current State

- **Local-only** deployment
- **No authentication** (development mode)
- **Read-only** AI queries (no database writes)
- **Local file storage** (documents not in cloud)

### Production Requirements

- **Authentication**: User login required
- **Authorization**: Role-based access control (RBAC)
- **HTTPS**: TLS encryption for all traffic
- **API Keys**: Secure API key management
- **Input Validation**: Strict validation on all inputs
- **Rate Limiting**: Prevent abuse

## Technology Choices

### Why Python 3.13?

- Latest language features
- Strong typing support
- Excellent AI/ML ecosystem
- FastAPI performance

### Why SQLite?

- Zero configuration
- Single file database
- Perfect for development
- Easy backups (copy file)
- Upgrade path to PostgreSQL

### Why FastAPI?

- High performance (async support)
- Auto-generated API docs
- Type hints throughout
- Modern Python (Pydantic v2)

### Why ChromaDB?

- Easy local deployment
- Built-in embedding functions
- No external dependencies
- Upgrade path to cloud vector stores

### Why Vanilla JS?

- No build step
- Fast loading
- Easy to modify
- No framework lock-in

## Next Steps

- [Data Models](data-models.md) - Detailed schema documentation
- [API Design](api-design.md) - API architecture details
- [Testing Guide](../testing/testing.md) - Testing and development workflow

---

**Questions about the architecture?** → [FAQ](../faq.md)

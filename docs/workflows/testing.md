# Testing Guide

Complete guide for running and writing tests for Poolula Platform.

## Quick Start

### Run All Tests

```bash
# From project root
uv run pytest
```

### Run with Coverage

```bash
# Generate coverage report
uv run pytest --cov=core --cov=apps --cov-report=html --cov-report=term-missing
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Structure

### Test Files

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures (shared setup)
├── test_models.py           # Database model tests
└── test_api_properties.py   # API endpoint tests
```

### Test Database

Tests use an **in-memory SQLite database** (`:memory:`):
- Created fresh for each test
- Destroyed after each test
- Fast and isolated

No need to manage test database files!

## Running Tests

### All Tests

```bash
uv run pytest
```

### Specific Test File

```bash
# Model tests only
uv run pytest tests/test_models.py

# API tests only
uv run pytest tests/test_api_properties.py
```

### Specific Test Function

```bash
# Single test
uv run pytest tests/test_models.py::test_property_creation

# Pattern matching
uv run pytest -k "property"  # All tests with "property" in name
```

### With Output

```bash
# Show print statements
uv run pytest -s

# Verbose output
uv run pytest -v

# Both
uv run pytest -sv
```

### Stop on First Failure

```bash
uv run pytest -x
```

## Test Categories

Tests are marked by type:

```python
@pytest.mark.unit
def test_property_creation():
    """Unit test for Property model"""
    ...

@pytest.mark.integration
def test_api_create_property(client):
    """Integration test for API endpoint"""
    ...
```

### Run by Category

```bash
# Unit tests only
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration

# Exclude slow tests
uv run pytest -m "not slow"
```

## Coverage Targets

### Current Target: ≥80%

Configured in `pyproject.toml`:

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
]
```

### Check Coverage

```bash
# Terminal report
uv run pytest --cov=core --cov=apps --cov-report=term-missing

# HTML report (more detailed)
uv run pytest --cov=core --cov=apps --cov-report=html
open htmlcov/index.html
```

### Coverage by Module

```
---------- coverage: platform darwin, python 3.13.2 -----------
Name                                 Stmts   Miss  Cover   Missing
------------------------------------------------------------------
core/__init__.py                         1      0   100%
core/database/__init__.py                7      0   100%
core/database/connection.py             50      5    90%   45-48
core/database/enums.py                  85      2    98%   102-103
core/database/models.py                125      8    94%   198, 278, 346
apps/api/main.py                        35      3    91%   67-69
apps/api/routes/properties.py           75      5    93%   125-127
------------------------------------------------------------------
TOTAL                                  378     23    94%
```

## Test Fixtures

Defined in `tests/conftest.py`:

### `engine_test`

In-memory SQLite engine:

```python
@pytest.fixture
def engine_test():
    """Create in-memory test database"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
```

### `session_test`

Database session for tests:

```python
@pytest.fixture
def session_test(engine_test):
    """Create test database session"""
    with Session(engine_test) as session:
        yield session
```

### `client`

FastAPI test client:

```python
@pytest.fixture
def client(session_test):
    """Create FastAPI test client with dependency override"""
    app.dependency_overrides[get_session] = lambda: session_test
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

## Writing Tests

### Unit Test Example (Models)

```python
def test_property_total_basis():
    """Test Property.total_basis computed property"""
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
    )

    assert property_obj.total_basis == Decimal("100000.00")
```

### Integration Test Example (API)

```python
def test_create_property(client):
    """Test POST /api/v1/properties creates a property"""
    property_data = {
        "address": "900 S 9th St, Montrose, CO 81401",
        "acquisition_date": "2024-04-15",
        "purchase_price_total": "442300.00",
        "land_basis": "78200.00",
        "building_basis": "364100.00",
        "ffe_basis": "10000.00",
        "status": "ACTIVE",
        "provenance": {},
        "extra_metadata": {},
    }

    response = client.post("/api/v1/properties", json=property_data)

    assert response.status_code == 201
    data = response.json()
    assert data["address"] == "900 S 9th St, Montrose, CO 81401"
    assert "id" in data
```

### Test with Database (Using session_test)

```python
def test_property_relationships(session_test):
    """Test Property relationships with transactions"""
    # Create property
    property_obj = Property(
        address="Test Property",
        acquisition_date=date(2024, 1, 1),
        purchase_price_total=Decimal("100000.00"),
        land_basis=Decimal("20000.00"),
        building_basis=Decimal("70000.00"),
        ffe_basis=Decimal("10000.00"),
    )
    session_test.add(property_obj)
    session_test.commit()
    session_test.refresh(property_obj)

    # Create transaction
    transaction = Transaction(
        property_id=property_obj.id,
        transaction_date=date(2024, 5, 1),
        amount=Decimal("150.00"),
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description="Test income",
        source_account="Test Account",
    )
    session_test.add(transaction)
    session_test.commit()
    session_test.refresh(property_obj)

    # Test relationship
    assert len(property_obj.transactions) == 1
    assert property_obj.transactions[0].description == "Test income"
```

## Test Conventions

### Naming

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Docstrings

Every test should have a clear docstring:

```python
def test_transaction_amount_cannot_be_zero():
    """Test Transaction.validate_amount rejects zero amounts"""
    ...
```

### Assertions

Use descriptive assertions:

```python
# Good
assert property_obj.total_basis == Decimal("100000.00")

# Better (with context on failure)
assert property_obj.total_basis == Decimal("100000.00"), \
    f"Expected total_basis 100000.00, got {property_obj.total_basis}"
```

### Arrange-Act-Assert Pattern

```python
def test_property_creation():
    """Test creating a valid Property"""
    # Arrange (setup)
    property_data = {
        "address": "Test Property",
        ...
    }

    # Act (execute)
    property_obj = Property(**property_data)

    # Assert (verify)
    assert property_obj.address == "Test Property"
    assert property_obj.status == PropertyStatus.ACTIVE
```

## Testing Validation

### Test Valid Cases

```python
def test_document_creation():
    """Test creating a valid Document"""
    document = Document(
        filename="deed.pdf",
        doc_type=DocumentType.DEED,
        content_hash="a" * 64,  # Valid 64-char hex
    )
    assert document.filename == "deed.pdf"
```

### Test Invalid Cases

```python
def test_transaction_amount_cannot_be_zero():
    """Test Transaction.validate_amount rejects zero amounts"""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            amount=Decimal("0.00"),  # Invalid!
            ...
        )

    assert "amount cannot be zero" in str(exc_info.value).lower()
```

## CI/CD Integration (Future)

When Phase 4 adds CI/CD, tests will run automatically:

```yaml
# .github/workflows/tests.yml (example)
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: uv run pytest --cov=core --cov=apps
```

## Troubleshooting

### Import Errors

```bash
# Make sure you're in project root
pwd
# Should show: .../poolula-platform

# Install dependencies
uv sync
```

### Database Errors

Tests use in-memory database, but if you see connection errors:

```python
# Check conftest.py fixture is working
pytest tests/conftest.py -v
```

### Fixture Not Found

```bash
# Error: fixture 'client' not found
# Solution: Make sure conftest.py is in tests/ directory
ls tests/conftest.py
```

## Test Markers

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

Use in tests:

```python
@pytest.mark.slow
def test_large_import():
    """Test importing 1000+ properties"""
    ...
```

## Chatbot Tests (Phase 2)

### Test Structure

```
tests/chatbot/
├── conftest.py                         # Chatbot fixtures
├── test_rag_system.py                  # RAG integration tests
├── test_session_manager.py             # Session management tests
├── test_ai_generator_integration.py    # AI generator tests
├── test_course_search_tool.py          # Legacy course search (business doc focused now)
└── test_document_processor.py          # Document processing tests
```

### Running Chatbot Tests

```bash
# All chatbot tests
uv run pytest tests/chatbot/

# Specific test file
uv run pytest tests/chatbot/test_session_manager.py

# With verbose output
uv run pytest tests/chatbot/ -v

# Skip slow/integration tests
uv run pytest tests/chatbot/ -m "not slow"
```

### Current Test Status (Phase 2)

**Total**: 37 tests
**Passing**: 31 (84%)
**Expected Failures**: 6 (prompt format changes from course → business documents)

```bash
# Run tests and see status
uv run pytest tests/chatbot/ -v

# Expected output:
# test_session_manager.py::TestSessionManager                10 passed
# test_ai_generator_integration.py::TestAIGeneratorIntegration  22 passed
# test_rag_system.py::TestRAGSystem                          9 passed, 2 failed
```

### Known Test Issues

**Test Failures (Expected)**:
- `test_query_prompt_formatting` - Tests check for old "course materials" prompts
- `test_query_content_vs_general_knowledge` - Expects course-focused responses

**Reason**: Platform migrated from course-focused chatbot to business document chatbot. Tests need updating to reflect new prompt templates.

**Fix**: Update test assertions in `test_rag_system.py` to expect business document prompts:
```python
# Old (failing):
expected = "Answer this question about course materials: ..."

# New (correct):
expected = "You are a helpful assistant for a small business LLC..."
```

### Chatbot Test Fixtures

Defined in `tests/chatbot/conftest.py`:

```python
@pytest.fixture
def session_manager():
    """Create SessionManager with test settings"""
    return SessionManager(max_history=3)

@pytest.fixture
def document_processor():
    """Create DocumentProcessor with test settings"""
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)
```

### Testing with Mocked Dependencies

RAG system tests use mocked AI and vector store:

```python
def setUp(self):
    """Set up test fixtures"""
    with patch('apps.chatbot.rag_system.DocumentProcessor'), \
         patch('apps.chatbot.rag_system.VectorStore'), \
         patch('apps.chatbot.rag_system.AIGenerator'):

        self.rag_system = RAGSystem(self.config)
```

### Testing AI Generator

Tests verify tool usage and response generation:

```python
def test_tool_usage():
    """Test AI uses search tools correctly"""
    # Mock vector store search
    self.mock_vector_store.search.return_value = SearchResults(...)

    # Execute query
    response = self.ai_generator.generate_response(
        query="Test query",
        tools=tool_definitions,
        tool_manager=tool_manager
    )

    # Verify tool was called
    self.mock_vector_store.search.assert_called_once()
```

### Chatbot Coverage Target

Current coverage for `apps/chatbot/`:
- Target: ≥80%
- Current: ~75% (acceptable for Phase 2 integration)
- Will improve in Phase 2 Week 4 (SQL query tool addition)

```bash
# Check chatbot coverage
uv run pytest tests/chatbot/ --cov=apps/chatbot --cov-report=term-missing
```

## Next Steps

- **API Usage**: See [api-usage.md](api-usage.md) for manual testing
- **Data Import**: See [data-import.md](data-import.md) for seeding test data
- **Phase 2**: Complete chatbot SQL query tool, run evaluation harness
- **Phase 3**: Add tests for Transaction, Document, Obligation models

## Related Files

- **Test Fixtures**: `tests/conftest.py`
- **Model Tests**: `tests/test_models.py`
- **API Tests**: `tests/test_api_properties.py`
- **Pytest Config**: `pyproject.toml` → `[tool.pytest.ini_options]`
- **Coverage Config**: `pyproject.toml` → `[tool.coverage]`

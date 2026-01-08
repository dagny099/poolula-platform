# OpenAI Provider Implementation Guide

**Date:** 2026-01-08
**Purpose:** Synthesize learnings from montrose-marathon project to implement OpenAI provider

## Key Learnings from Montrose-Marathon

### ✅ Excellent Patterns to Adopt

#### 1. Health Check Method (`is_available()`)
**Montrose implementation:**
```python
def is_available(self) -> bool:
    """Check if Ollama is reachable and the models are available."""
    try:
        url = f"{self.base_url}/api/tags"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logger.info("Ollama is available")
        return True
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False
```

**Why adopt:**
- Enables preflight checks before expensive operations
- Useful for startup diagnostics
- Can display provider status in UI

**Action:** Add `is_available()` to poolula's `LLMProvider` base class

---

#### 2. Actionable Error Messages
**Montrose pattern:**
```python
except requests.exceptions.ConnectionError:
    logger.error(f"Cannot connect to Ollama at {self.base_url}")
    raise RuntimeError(
        f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?"
    )
```

**Why adopt:**
- User-friendly guidance in error messages
- Suggests concrete remediation steps
- Reduces debugging time

**Action:** Adopt this pattern in OpenAI provider error handling

---

#### 3. Explicit Timeout Handling
**Montrose timeout strategy:**
- Generation: 60s (models are slow)
- Embedding: 30s (faster operation)
- Health check: 5s (should be instant)

**Why adopt:**
- Prevents indefinite hangs
- Different operations have different performance characteristics
- Clear failure modes

**Action:** Apply timeout strategy to OpenAI provider

---

#### 4. Singleton with Factory Pattern
**Montrose pattern:**
```python
# Module-level singleton
_backend = OllamaBackend(base_url=OLLAMA_BASE_URL, ...)
llm_client = LLMClient(_backend)

# Factory for testing/alternatives
def create_llm_client(backend_type: str = "ollama") -> LLMClient:
    if backend_type == "ollama":
        backend = OllamaBackend(...)
    elif backend_type == "vllm":
        raise NotImplementedError("vLLM backend not yet available")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    return LLMClient(backend)
```

**Why adopt:**
- Single point of configuration
- Easy to swap backends in tests
- Avoids accidental multiple client instances

**Poolula already has:** Factory in `rag_system.py:_create_provider()` ✓

---

### ❌ Differences (Montrose → Poolula)

#### Tool Calling Support
**Montrose:** No tool calling (simple RAG pipeline)
**Poolula:** Core feature - database queries, document search
**Implication:** OpenAI provider needs tool translation logic

#### Message Format
**Montrose:** Simple prompt strings
**Poolula:** Structured messages (user/assistant/system) with content blocks
**Implication:** OpenAI provider needs message format translation

#### Embeddings
**Montrose:** Backend handles embeddings
**Poolula:** ChromaDB ONNX handles embeddings
**Implication:** OpenAI provider doesn't need embedding support

---

## OpenAI Provider Implementation Plan

### 1. Enhanced Base Class

**Add to `apps/chatbot/llm_providers/base.py`:**

```python
@abstractmethod
def is_available(self) -> bool:
    """
    Check if provider is reachable and healthy

    Returns:
        True if provider can accept requests, False otherwise
    """
    pass

@property
@abstractmethod
def default_timeout(self) -> int:
    """
    Default timeout in seconds for generate() calls

    Returns:
        Timeout value (e.g., 60 for API providers, 120 for local)
    """
    pass
```

---

### 2. OpenAI Provider Implementation

**File:** `apps/chatbot/llm_providers/openai_provider.py`

**Key features:**
1. ✅ Native tool calling support (OpenAI Functions API)
2. ✅ Message format translation (system as first message)
3. ✅ Tool definition translation (Anthropic → OpenAI format)
4. ✅ Error handling with actionable messages
5. ✅ Health check via `/v1/models` endpoint
6. ✅ Timeout handling (60s default)

**Tool format differences:**

**Anthropic format (internal):**
```json
{
  "name": "query_database",
  "description": "Query the database...",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"}
    }
  }
}
```

**OpenAI format (target):**
```json
{
  "type": "function",
  "function": {
    "name": "query_database",
    "description": "Query the database...",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string"}
      }
    }
  }
}
```

**Translation:** Wrap in `function` key, rename `input_schema` → `parameters`

---

### 3. Error Handling Strategy

**Adopt from Montrose:**

```python
try:
    response = self.client.chat.completions.create(**params)
    return self._translate_response(response)
except openai.APIConnectionError as e:
    logger.error(f"Cannot connect to OpenAI API: {e}")
    raise RuntimeError(
        "Cannot connect to OpenAI API. Check your internet connection "
        "and verify OPENAI_API_KEY is set."
    )
except openai.RateLimitError as e:
    logger.error(f"OpenAI rate limit exceeded: {e}")
    raise RuntimeError(
        "OpenAI rate limit exceeded. Wait a moment and try again, "
        "or upgrade your API plan."
    )
except openai.APIError as e:
    logger.error(f"OpenAI API error: {e}")
    raise RuntimeError(f"OpenAI API error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

---

### 4. Configuration Updates

**Update `apps/chatbot/config.py`:**

```python
@dataclass
class Config:
    # ... existing fields ...

    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_BASE_URL: str = os.getenv(
        "OPENAI_BASE_URL",
        "https://api.openai.com/v1"
    )  # Allow override for Azure OpenAI or proxies
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/chatbot/test_openai_provider.py`

Test coverage:
1. ✅ Message translation (system prompt handling)
2. ✅ Tool definition translation
3. ✅ Response parsing (text + tool calls)
4. ✅ Error handling (connection, rate limit, API errors)
5. ✅ Health check (`is_available()`)
6. ✅ Timeout behavior

### Integration Tests

**Prerequisites:**
- Valid `OPENAI_API_KEY` in environment
- Sufficient API credits

**Test cases:**
1. Simple text generation (no tools)
2. Tool calling (database query)
3. Multi-round tool loop
4. Error recovery

### Evaluation

**Run provider comparison:**
```bash
uv run python scripts/evaluate_providers.py \
    --providers anthropic openai \
    --verbose
```

**Expected results:**
- OpenAI score: 80-90% (comparable to Anthropic)
- Tool usage: Should be 85%+ (native support)
- Latency: 2-5s typical (slightly slower than Claude)

---

## Implementation Checklist

### Phase 1: Core Implementation (2-3 hours)

- [ ] Add `is_available()` and `default_timeout` to base class
- [ ] Update `AnthropicProvider` to implement new methods
- [ ] Create `openai_provider.py` with:
  - [ ] `__init__()` - client initialization
  - [ ] `generate()` - main generation method
  - [ ] `_translate_messages()` - message format translation
  - [ ] `_translate_tool_definition()` - tool format translation
  - [ ] `_translate_response()` - response parsing
  - [ ] `is_available()` - health check
  - [ ] Properties: `provider_name`, `supports_native_tool_calling`, `default_timeout`
- [ ] Update `rag_system._create_provider()` to handle "openai"
- [ ] Add `openai>=1.50.0` to `pyproject.toml` optional dependencies

### Phase 2: Testing & Validation (1-2 hours)

- [ ] Write unit tests (mocked OpenAI client)
- [ ] Fix any existing test failures (8 AI generator tests)
- [ ] Manual integration test with real API
- [ ] Test error scenarios (invalid key, rate limit)

### Phase 3: Documentation (1 hour)

- [ ] Update `CLAUDE.md` with OpenAI provider info
- [ ] Update `README.md` with provider switching example
- [ ] Create `docs/workflows/openai-provider-setup.md`
- [ ] Add provider comparison example to evaluation docs

---

## Expected Outcomes

### Functional
- ✅ Switch providers: `export LLM_PROVIDER=openai`
- ✅ Tool calling works (database + document search)
- ✅ Multi-round loops function correctly
- ✅ Error messages are actionable

### Performance
- Latency: 2-5s typical (vs 1-3s Claude)
- Cost: $2.50/1M tokens (vs $3.00/1M Claude)
- Quality: 80-90% eval score (comparable)

### Code Quality
- Zero regressions in existing tests
- Clean separation of concerns
- Comprehensive error handling
- Well-documented edge cases

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tool format mismatch | Medium | High | Extensive testing with real API calls |
| Token limit differences | Low | Medium | Document OpenAI's limits (128k vs Claude's 200k) |
| Rate limiting in tests | Medium | Low | Add retry logic, use test credits sparingly |
| Cost overruns | Low | Low | Use evaluation set sparingly (20 questions = ~$0.10) |

---

## Next Steps After OpenAI

Once OpenAI provider is working:

1. **Ollama provider** - Local models (learning value)
2. **Provider comparison** - Run eval suite across all 3
3. **Cost tracking** - Log token usage per provider
4. **Performance benchmarking** - Latency percentiles

---

## References

- **Montrose-Marathon:** `/Users/bhs/PROJECTS/montrose-marathon/llm_client.py`
- **Poolula Base:** `apps/chatbot/llm_providers/base.py`
- **Anthropic Provider:** `apps/chatbot/llm_providers/anthropic_provider.py`
- **OpenAI Docs:** https://platform.openai.com/docs/guides/function-calling

---

**Author:** Claude (synthesizing from montrose-marathon patterns)
**Last Updated:** 2026-01-08

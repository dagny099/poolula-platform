# LLM Provider Architecture

!!! warning "Implementation Status"
    **Current State:** This document describes the **planned architecture** for multi-provider LLM support. The abstraction layer design is documented, but the current implementation (Phase 2) is **tightly coupled to Anthropic Claude**.

    **Status:**
    - 🚧 Provider abstraction layer - Designed (Phase 6-7)
    - ✅ Anthropic Claude integration - Operational
    - 🚧 OpenAI provider - Planned (Phase 6-7)
    - 🚧 Ollama local models - Planned (Phase 6-7)

    **Migration Plan:** See [`docs/planning/2025-12-03-llm-agnosticism-plan.md`](../planning/2025-12-03-llm-agnosticism-plan.md) for detailed decoupling strategy.

## Overview

The Poolula Platform chatbot is designed to use a **provider-agnostic abstraction layer** to support multiple Large Language Model (LLM) backends. This design will allow seamless switching between cloud-based providers (Anthropic, OpenAI) and local models (Ollama) without changing business logic.

## Architecture Principles

1. **Provider Independence:** Core RAG logic doesn't depend on specific LLM APIs
2. **Unified Interface:** All providers implement the same `LLMProvider` base class
3. **Easy Extensibility:** Adding new providers requires only implementing the interface
4. **Configuration-Based Switching:** Change providers via environment variable (`LLM_PROVIDER`)

---

## Provider Abstraction Layer

### Base Interface

**File:** `apps/chatbot/llm_providers/base.py`

```python
class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.0,
        max_tokens: int = 800,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """Translate from internal tool format to provider-specific format"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging/debugging"""
        pass

    @property
    @abstractmethod
    def supports_native_tool_calling(self) -> bool:
        """Whether provider has native tool calling support"""
        pass
```

### Data Models

**LLMMessage:** Provider-agnostic message format
```python
@dataclass
class LLMMessage:
    role: str  # "user", "assistant", "system"
    content: Any
```

**LLMToolCall:** Provider-agnostic tool call representation
```python
@dataclass
class LLMToolCall:
    id: str
    name: str
    parameters: Dict[str, Any]
```

**LLMResponse:** Unified response format
```python
@dataclass
class LLMResponse:
    text: Optional[str] = None
    tool_calls: Optional[List[LLMToolCall]] = None
    stop_reason: str = "complete"
    raw_response: Any = None
    content: List[Any] = field(default_factory=list)
```

---

## Supported Providers

### 1. Anthropic Claude (Default)

**File:** `apps/chatbot/llm_providers/anthropic_provider.py`

**Characteristics:**
- **Native Tool Calling:** Yes (function calling API)
- **Models:** claude-sonnet-4-20250514 (default), claude-opus-4-5-20251101
- **Cost:** ~$3/M input tokens, ~$15/M output tokens
- **Latency:** 1-3s typical
- **Best For:** Production use, highest quality responses

**Configuration:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Key Features:**
- Direct integration with Anthropic SDK
- Multi-round tool calling support
- Tool definitions pass through directly (no translation needed)
- Excellent at following system prompts

---

### 2. OpenAI GPT

**File:** `apps/chatbot/llm_providers/openai_provider.py`

**Characteristics:**
- **Native Tool Calling:** Yes (function calling API)
- **Models:** gpt-4o (default), gpt-4o-mini
- **Cost:** ~$2.50/M input tokens, ~$10/M output tokens (17% cheaper than Claude)
- **Latency:** 1-4s typical
- **Best For:** Cost-effective alternative to Claude

**Configuration:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

**Key Features:**
- Translates between Anthropic and OpenAI tool formats
- Slightly different response phrasing (affects keyword matching scores)
- Compatible with Azure OpenAI endpoints (future enhancement)

**Tool Format Translation:**
```python
# Anthropic format (internal)
{
  "name": "query_database",
  "description": "Query the business database",
  "input_schema": {"type": "object", "properties": {...}}
}

# OpenAI format (translated)
{
  "type": "function",
  "function": {
    "name": "query_database",
    "description": "Query the business database",
    "parameters": {"type": "object", "properties": {...}}
  }
}
```

---

### 3. Ollama (Local Models)

**File:** `apps/chatbot/llm_providers/ollama_provider.py`

**Characteristics:**
- **Native Tool Calling:** No (uses prompt-based approach)
- **Models:** llama3.1:8b-instruct-q4_K_M (recommended), mistral:7b-instruct-q4_0, qwen2.5:7b-instruct-q4_K_M
- **Cost:** Free (runs locally)
- **Latency:** 5-15s on CPU, 1-4s on GPU
- **Best For:** Learning, privacy-focused use, offline capability

**Configuration:**
```bash
LLM_PROVIDER=ollama
LOCAL_MODEL_PATH=llama3.1:8b-instruct-q4_K_M
LOCAL_MODEL_URL=http://localhost:11434
```

**Key Features:**
- Connects to Ollama via HTTP API
- Prompt-based tool calling (instructs model to output JSON)
- Free and private (no data leaves machine)
- Requires Ollama installed separately

**Prompt-Based Tool Calling:**

Since local models lack native tool calling APIs, we inject tool descriptions into the system prompt:

```python
def _build_tool_prompt(self, tools: List[Dict]) -> str:
    """Build tool usage instructions for prompt engineering"""
    tool_descriptions = [f"- **{tool['name']}**: {tool['description']}" for tool in tools]

    return f"""Available Tools:
{chr(10).join(tool_descriptions)}

To use a tool, respond with ONLY JSON: {{"tool": "tool_name", "parameters": {{...}}}}"""
```

The model responds with JSON, which we parse back into `LLMToolCall` objects.

---

## Provider Factory

**File:** `apps/chatbot/rag_system.py` (line 48)

```python
def _create_llm_provider(self, config) -> LLMProvider:
    """Factory method for creating LLM providers based on configuration"""
    provider_type = config.LLM_PROVIDER.lower()

    if provider_type == "anthropic":
        return AnthropicProvider(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL
        )
    elif provider_type == "openai":
        from .llm_providers import OpenAIProvider
        if OpenAIProvider is None:
            raise ImportError("Install with: uv sync --group openai")
        return OpenAIProvider(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL
        )
    elif provider_type == "ollama":
        from .llm_providers import OllamaProvider
        if OllamaProvider is None:
            raise ImportError("Install with: uv sync --group local")
        return OllamaProvider(
            model=config.LOCAL_MODEL_PATH,
            base_url=config.LOCAL_MODEL_URL
        )
    else:
        raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
```

---

## Provider Comparison

### How to Run Comparison

```bash
# Compare all providers
python scripts/evaluate_providers.py --providers anthropic openai ollama

# Compare specific providers
python scripts/evaluate_providers.py --providers anthropic openai

# View results
cat data/provider_comparison.json
```

See `docs/evaluation/provider-comparison.md` for detailed guide.

### Baseline Performance (To Be Established)

Run the comparison script to establish baseline scores for each provider. Results will include:

- **Overall Scores:** Average across 15 golden questions
- **Component Breakdown:** Tool usage, response quality, error handling
- **Category Performance:** Scores by question category (property_info, compliance, etc.)
- **Per-Question Analysis:** Where providers diverge

**Expected Results:**

Based on implementation characteristics, we anticipate:

| Provider | Tool Usage | Response Quality | Error Handling | Overall (Expected) |
|----------|------------|------------------|----------------|--------------------|
| Anthropic | 90-95% | 85-90% | 95-100% | 85-90% |
| OpenAI | 90-95% | 80-85% | 95-100% | 82-87% |
| Ollama | 85-90% | 60-70% | 90-95% | 70-75% |

**Key Factors:**
- Tool usage is high across all providers (abstraction works well)
- Response quality varies due to model size and keyword matching
- Local models trade quality for privacy/cost benefits

**To populate actual results:**
1. Run: `python scripts/evaluate_providers.py --providers anthropic openai ollama`
2. Update this section with real scores
3. Add insights about provider-specific strengths/weaknesses

---

## Decision Matrix: Choosing a Provider

### Use Anthropic When:
- ✅ You need the best quality responses
- ✅ Budget is not the primary concern (~$6/1K queries)
- ✅ Multi-round tool calling is critical
- ✅ Production deployment with high-stakes queries

### Use OpenAI When:
- ✅ You want cost optimization (~$5/1K queries, 17% savings)
- ✅ You have existing OpenAI credits or infrastructure
- ✅ Quality requirements are 80-85% vs Claude's 85-90%
- ✅ You need comparable performance to Anthropic

### Use Ollama When:
- ✅ Privacy is critical (medical, legal, sensitive data)
- ✅ You want zero ongoing costs (free)
- ✅ You have decent hardware (16GB+ RAM for CPU, or GPU)
- ✅ You're learning/experimenting with local LLMs
- ✅ Offline capability is required
- ✅ Acceptable quality threshold is 70-75%

---

## Implementation Details

### Multi-Round Tool Calling

The `AIGenerator` class handles multi-round tool calling in a provider-agnostic way:

```python
def generate_response(self, query, conversation_history, tools, tool_manager):
    """Generate response using provider-agnostic interface"""

    messages = [LLMMessage(role="user", content=query)]

    # Multi-round tool calling loop
    max_rounds = 2
    for round_num in range(max_rounds):
        response = self.provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            tools=provider_tools,
            temperature=0,
            max_tokens=800
        )

        # Check for tool usage
        if response.stop_reason == "tool_use" and response.tool_calls:
            # Execute tools and continue
            tool_results = self._execute_tools(response.tool_calls, tool_manager)
            messages.append(LLMMessage(role="assistant", content=response))
            messages.append(LLMMessage(role="user", content=tool_results))
            continue
        else:
            # Return final response
            return response.text
```

This works identically across all providers, regardless of native vs prompt-based tool calling.

### Error Handling

Each provider implements graceful error handling:

- **Anthropic:** API errors wrapped with retry logic
- **OpenAI:** API errors wrapped with retry logic
- **Ollama:** Connection errors if Ollama not running, clear error messages

---

## Testing & Validation

### Unit Tests

**File:** `tests/chatbot/test_ai_generator_integration.py`

- 12 tests for AI generator with provider abstraction
- All tests pass with AnthropicProvider
- Mock provider responses for deterministic testing

### Integration Tests

**File:** `tests/chatbot/test_rag_system.py`

- 31/37 tests passing (6 failures unrelated to provider abstraction)
- Tests RAG system with provider factory

### Evaluation Harness

**File:** `scripts/evaluate_chatbot.py`

- 15 golden questions covering 8 categories
- 3-component scoring: tool usage (40%), response quality (40%), error handling (20%)
- Provider-agnostic (tests RAG system, not specific provider)

**Multi-Provider Comparison:** `scripts/evaluate_providers.py`

---

## Future Enhancements

### Short-Term (Next 6 Months)

1. **Azure OpenAI Support:** Add Azure endpoints to OpenAI provider
2. **Streaming Responses:** Add streaming interface to base provider
3. **Token Usage Tracking:** Log tokens per query for cost analysis
4. **Provider-Specific Prompt Tuning:** Optimize system prompts per provider

### Medium-Term (6-12 Months)

1. **Local Model Fine-Tuning:** Fine-tune Llama on Poolula-specific data
2. **Hybrid Approach:** Use cheap provider for simple queries, expensive for complex
3. **Fallback Chain:** Try OpenAI if Anthropic fails, Ollama if both fail
4. **Custom Evaluation Metrics:** LLM-as-judge scoring, semantic similarity

### Long-Term (12+ Months)

1. **Provider Auto-Selection:** ML model predicts best provider per query
2. **Cost Optimization:** Automatically route queries based on cost/quality trade-off
3. **Multi-Provider Ensembling:** Combine responses from multiple providers
4. **Local Model Scaling:** Support larger local models (70B+) with quantization

---

## Related Documentation

- **Setup Guide:** `docs/workflows/llm-provider-setup.md` - How to configure each provider
- **Comparison Guide:** `docs/evaluation/provider-comparison.md` - How to run and interpret comparisons
- **Qualitative Checklist:** `docs/evaluation/provider_checklist.md` - Manual testing guide
- **Planning Document:** `docs/planning/2025-12-03-llm-agnosticism-plan.md` - Original implementation plan
- **Project Overview:** `CLAUDE.md` - High-level project context

---

## Revision History

- **2025-12-04:** Initial architecture document with provider abstraction layer
- **Future:** Update with actual baseline comparison results after running evaluation

# LLM Agnosticism Implementation Plan

**Date:** 2025-12-03
**Author:** Claude Code (with user guidance)
**Status:** Stage 1 In Progress

## Executive Summary

**Current State:** The chatbot is tightly coupled to Anthropic Claude through `AIGenerator`, which directly uses the `anthropic` SDK, Claude-specific API formats, and tool-calling conventions.

**Coupling Points Identified:**
- `apps/chatbot/ai_generator.py:1,75` - Direct `anthropic` SDK import/client
- `apps/chatbot/config.py:23-24` - Hardcoded API key and model name
- Tool schema format (Anthropic's tool definition structure)
- Message format and multi-round tool-calling loop
- Response parsing logic

**Good News:** Embeddings already use provider-agnostic ONNX (ChromaDB), tool system has abstract base class, and RAG orchestration is cleanly separated.

---

## Staged Migration Path

### Stage 1: Quick Wins (2-4 hours)
**Goal:** Establish abstraction boundaries without breaking existing code

#### 1.1 Create LLM Provider Interface

Create `apps/chatbot/llm_providers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class LLMMessage:
    """Provider-agnostic message format"""
    role: str  # "user", "assistant", "system"
    content: str

@dataclass
class LLMToolCall:
    """Provider-agnostic tool call"""
    id: str
    name: str
    parameters: Dict[str, Any]

@dataclass
class LLMResponse:
    """Provider-agnostic response"""
    text: Optional[str] = None
    tool_calls: List[LLMToolCall] = None
    stop_reason: str = "complete"  # "complete", "tool_use", "max_tokens"
    raw_response: Any = None  # Original provider response for debugging

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
```

#### 1.2 Create Anthropic Adapter

Create `apps/chatbot/llm_providers/anthropic_provider.py`:

```python
import anthropic
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.0,
        max_tokens: int = 800,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Anthropic API"""

        # Translate to Anthropic message format
        anthropic_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages if msg.role != "system"
        ]

        # Build API parameters
        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if system_prompt:
            params["system"] = system_prompt

        if tools:
            params["tools"] = tools  # Already in Anthropic format
            params["tool_choice"] = {"type": "auto"}

        # Call API
        response = self.client.messages.create(**params)

        # Translate response
        return self._translate_response(response)

    def _translate_response(self, response) -> LLMResponse:
        """Translate Anthropic response to LLMResponse"""

        # Extract text content
        text = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(LLMToolCall(
                    id=block.id,
                    name=block.name,
                    parameters=block.input
                ))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls if tool_calls else None,
            stop_reason="tool_use" if response.stop_reason == "tool_use" else "complete",
            raw_response=response
        )

    def translate_tool_definition(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """Anthropic uses our tool format directly (no translation needed)"""
        return tool_def

    @property
    def provider_name(self) -> str:
        return f"anthropic:{self.model}"
```

#### 1.3 Update Configuration

Update `apps/chatbot/config.py`:

```python
@dataclass
class Config:
    # LLM Provider settings (provider-agnostic)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")

    # Anthropic settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # OpenAI settings (future)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o"

    # Local model settings (future)
    LOCAL_MODEL_PATH: str = os.getenv("LOCAL_MODEL_PATH", "")
    LOCAL_MODEL_URL: str = os.getenv("LOCAL_MODEL_URL", "http://localhost:11434")  # Ollama default

    # ... rest of config
```

#### 1.4 Refactor AIGenerator

Update `apps/chatbot/ai_generator.py` to use provider interface:

```python
from .llm_providers.base import LLMProvider, LLMMessage, LLMResponse
from .llm_providers.anthropic_provider import AnthropicProvider

class AIGenerator:
    """Provider-agnostic AI generation orchestrator"""

    SYSTEM_PROMPT = """..."""  # Keep existing prompt

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AIGenerator initialized with {provider.provider_name}")

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None
    ) -> str:
        """Generate response using provider-agnostic interface"""

        # Build system prompt
        system_prompt = self._build_system_prompt(conversation_history)

        # Translate tools if provided
        provider_tools = None
        if tools:
            provider_tools = [
                self.provider.translate_tool_definition(tool)
                for tool in tools
            ]

        # Initialize message history
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
            if response.stop_reason == "tool_use" and response.tool_calls and tool_manager:
                # Execute tools
                tool_results = self._execute_tools(response.tool_calls, tool_manager)

                # Add assistant message and tool results to history
                messages.append(LLMMessage(role="assistant", content=str(response.raw_response.content)))
                messages.append(LLMMessage(role="user", content=tool_results))

                continue
            else:
                # Return final text response
                return response.text or ""

        # Final round without tools
        final_response = self.provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0,
            max_tokens=800
        )

        return final_response.text or ""
```

#### 1.5 Update RAGSystem Initialization

Update `apps/chatbot/rag_system.py:25`:

```python
from .llm_providers.anthropic_provider import AnthropicProvider
# Future imports: from .llm_providers.openai_provider import OpenAIProvider

def __init__(self, config):
    # ... existing code ...

    # Initialize LLM provider based on config
    provider = self._create_provider(config)
    self.ai_generator = AIGenerator(provider)

    # ... rest of initialization ...

def _create_provider(self, config):
    """Factory method for creating LLM providers"""
    if config.LLM_PROVIDER == "anthropic":
        return AnthropicProvider(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL
        )
    # Future:
    # elif config.LLM_PROVIDER == "openai":
    #     return OpenAIProvider(...)
    # elif config.LLM_PROVIDER == "ollama":
    #     return OllamaProvider(...)
    else:
        raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
```

**Stage 1 Deliverables:**
- ✅ Provider interface established
- ✅ Anthropic adapter (maintains current behavior)
- ✅ Configuration updated for multi-provider support
- ✅ AIGenerator refactored to use provider interface
- ✅ Existing tests still pass (no behavior change)

**Validation:** Run `uv run pytest tests/chatbot/test_ai_generator_integration.py` - all 22 tests should pass.

---

### Stage 2: Add Alternative Providers (4-8 hours)
**Goal:** Implement OpenAI and local model providers

#### 2.1 OpenAI Provider

Create `apps/chatbot/llm_providers/openai_provider.py`:

```python
import openai
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation"""

    def __init__(self, api_key: str, model: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate(self, messages: List[LLMMessage], system_prompt: Optional[str] = None, tools: Optional[List[Dict]] = None, **kwargs) -> LLMResponse:
        """Generate using OpenAI Chat Completions API"""

        # Build messages (OpenAI includes system as first message)
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        openai_messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ])

        # Build parameters
        params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 800)
        }

        # Add tools if provided (OpenAI function calling)
        if tools:
            params["tools"] = [self._translate_tool(t) for t in tools]
            params["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**params)
        return self._translate_response(response)

    def _translate_tool(self, tool: Dict) -> Dict:
        """Translate from Anthropic format to OpenAI function format"""
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        }

    def _translate_response(self, response) -> LLMResponse:
        """Translate OpenAI response"""
        message = response.choices[0].message

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(LLMToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    parameters=json.loads(tc.function.arguments)
                ))

        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls if tool_calls else None,
            stop_reason="tool_use" if message.tool_calls else "complete",
            raw_response=response
        )

    def translate_tool_definition(self, tool_def: Dict) -> Dict:
        return self._translate_tool(tool_def)

    @property
    def provider_name(self) -> str:
        return f"openai:{self.model}"
```

#### 2.2 Local Model Provider (Ollama)

Create `apps/chatbot/llm_providers/ollama_provider.py`:

```python
import requests
import json
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMMessage, LLMResponse, LLMToolCall

class OllamaProvider(LLMProvider):
    """Local Ollama model provider"""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip('/')

    def generate(self, messages: List[LLMMessage], system_prompt: Optional[str] = None, tools: Optional[List[Dict]] = None, **kwargs) -> LLMResponse:
        """Generate using Ollama API"""

        # Build messages
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})

        ollama_messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ])

        # Note: Most local models don't support tool calling yet
        # We'll use prompt engineering as fallback
        if tools:
            tool_prompt = self._build_tool_prompt(tools)
            ollama_messages[0]["content"] += f"\n\n{tool_prompt}"

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.0),
                "num_predict": kwargs.get("max_tokens", 800)
            }
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        return self._translate_response(response.json())

    def _build_tool_prompt(self, tools: List[Dict]) -> str:
        """Build tool description for prompt (since most local models lack native tool calling)"""
        tool_descs = []
        for tool in tools:
            tool_descs.append(f"- {tool['name']}: {tool['description']}")

        return f"""Available tools:
{chr(10).join(tool_descs)}

To use a tool, respond with JSON: {{"tool": "tool_name", "parameters": {{...}}}}"""

    def _translate_response(self, response: Dict) -> LLMResponse:
        """Translate Ollama response"""
        content = response["message"]["content"]

        # Try to parse tool calls from JSON (basic implementation)
        tool_calls = None
        try:
            if content.strip().startswith("{") and "tool" in content:
                parsed = json.loads(content)
                if "tool" in parsed:
                    tool_calls = [LLMToolCall(
                        id="local-0",
                        name=parsed["tool"],
                        parameters=parsed.get("parameters", {})
                    )]
                    content = None  # Tool call instead of text
        except json.JSONDecodeError:
            pass  # Not a tool call, treat as regular response

        return LLMResponse(
            text=content,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "complete",
            raw_response=response
        )

    def translate_tool_definition(self, tool_def: Dict) -> Dict:
        return tool_def  # Pass through for now

    @property
    def provider_name(self) -> str:
        return f"ollama:{self.model}"
```

#### 2.3 Update Dependencies

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
# ... existing groups ...

openai = [
    "openai>=1.50.0"
]

local = [
    "requests>=2.31.0"
]
```

**Stage 2 Deliverables:**
- ✅ OpenAI provider implemented
- ✅ Ollama provider implemented (with prompt-based tool calling fallback)
- ✅ Dependencies added to optional groups
- ✅ Environment variable configuration for switching providers

**Validation:** Test with `LLM_PROVIDER=openai` and verify responses work.

---

### Stage 3: Evaluation Framework Extension (2-4 hours)
**Goal:** Compare providers systematically

#### 3.1 Multi-Provider Evaluation Script

Create `scripts/evaluate_providers.py`:

```python
#!/usr/bin/env python3
"""
Multi-Provider Evaluation Script

Runs the same evaluation set across multiple LLM providers and compares results.

Usage:
    python scripts/evaluate_providers.py --providers anthropic openai ollama
    python scripts/evaluate_providers.py --verbose --output comparison_report.json
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config
from scripts.evaluate_chatbot import ChatbotEvaluator

def run_provider_comparison(
    providers: List[str],
    eval_set: str = "data/poolula_eval_set.jsonl",
    verbose: bool = False
) -> Dict[str, Any]:
    """Run evaluation across multiple providers"""

    results = {}

    for provider_name in providers:
        print(f"\n{'='*60}")
        print(f"Evaluating provider: {provider_name}")
        print(f"{'='*60}\n")

        # Configure for this provider
        config = Config()
        config.LLM_PROVIDER = provider_name

        # Initialize RAG system with this provider
        rag = RAGSystem(config)

        # Run evaluation
        evaluator = ChatbotEvaluator(rag, verbose=verbose)
        report = evaluator.run_evaluation(eval_set)

        results[provider_name] = report

    # Generate comparison report
    comparison = _build_comparison_report(results)
    return comparison

def _build_comparison_report(results: Dict[str, Dict]) -> Dict[str, Any]:
    """Build side-by-side comparison"""

    providers = list(results.keys())

    # Overall scores
    scores = {
        provider: results[provider]["average_score"] * 100
        for provider in providers
    }

    # Per-question comparison
    question_comparison = []

    # Assume all providers tested same questions
    first_provider = providers[0]
    for i, result in enumerate(results[first_provider]["results"]):
        question_data = {
            "question": result["question"],
            "scores": {}
        }

        for provider in providers:
            provider_result = results[provider]["results"][i]
            question_data["scores"][provider] = {
                "total": provider_result.get("total_score", 0) * 100,
                "tool_usage": provider_result["checks"]["tool_usage"]["score"] * 100,
                "relevance": provider_result["checks"]["content_relevance"]["score"] * 100
            }

        question_comparison.append(question_data)

    return {
        "timestamp": datetime.now().isoformat(),
        "providers_tested": providers,
        "overall_scores": scores,
        "winner": max(scores, key=scores.get),
        "question_breakdown": question_comparison,
        "detailed_results": results
    }

def main():
    parser = argparse.ArgumentParser(description="Compare LLM providers")
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["anthropic"],
        choices=["anthropic", "openai", "ollama"],
        help="Providers to test"
    )
    parser.add_argument("--eval-set", default="data/poolula_eval_set.jsonl")
    parser.add_argument("--output", default="data/provider_comparison.json")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    comparison = run_provider_comparison(
        providers=args.providers,
        eval_set=args.eval_set,
        verbose=args.verbose
    )

    # Print summary
    print(f"\n{'='*60}")
    print("Provider Comparison Summary")
    print(f"{'='*60}")
    for provider, score in comparison["overall_scores"].items():
        status = "🏆" if provider == comparison["winner"] else "  "
        print(f"{status} {provider:15s}: {score:5.1f}%")
    print(f"{'='*60}\n")

    # Save detailed report
    with open(args.output, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"Detailed report saved to: {args.output}")

if __name__ == "__main__":
    main()
```

#### 3.2 Qualitative Testing Checklist

Create `docs/evaluation/provider_checklist.md`:

```markdown
# Provider Qualitative Testing Checklist

Beyond automated scoring, manually verify these aspects for each provider:

## Tool Calling Correctness
- [ ] Database tool called with valid SQL queries
- [ ] Document search tool used for text search (not database queries)
- [ ] Multi-round tool calling works (database → document search)
- [ ] Tool results properly incorporated into final response

## Response Quality
- [ ] No hallucinations (all facts traceable to sources)
- [ ] Professional tone maintained
- [ ] No meta-commentary ("based on search results...")
- [ ] Appropriate level of detail (not too brief, not verbose)

## Edge Cases
- [ ] Handles "no results found" gracefully
- [ ] Recovers from tool errors
- [ ] Handles ambiguous queries reasonably
- [ ] Doesn't fabricate data when uncertain

## Performance
- [ ] Response latency acceptable (<5s typical, <10s worst case)
- [ ] Token usage reasonable (track cost per query)
- [ ] No timeout failures on complex queries

## Context Handling
- [ ] Maintains conversation context across sessions
- [ ] Uses previous messages to inform responses
- [ ] Doesn't lose track in multi-turn conversations
```

**Stage 3 Deliverables:**
- ✅ Multi-provider evaluation script
- ✅ Comparison report generation
- ✅ Qualitative testing checklist
- ✅ Documentation on interpreting cross-provider results

---

## Local Model Considerations

### Hardware Requirements

**Minimum Viable Setup:**
- **RAM:** 16GB+ (for 7B parameter models)
- **Storage:** 10GB+ for model weights
- **GPU:** Optional (CPU inference viable with quantization)

**Model Recommendations:**

| Model | Size | Context | Tool Calling | Notes |
|-------|------|---------|--------------|-------|
| Llama 3.1 8B Instruct | 4.7GB (Q4) | 128K | Prompt-based | Good balance |
| Mistral 7B Instruct | 4.1GB (Q4) | 32K | Prompt-based | Fast, concise |
| Qwen2.5 7B | 4.4GB (Q4) | 128K | Native (experimental) | Strong at tools |

**Quantization:** Use Q4_K_M quantization (4-bit) for best speed/quality trade-off on CPU.

### Latency Trade-offs

| Provider | Typical Latency | Cost | Tool Calling |
|----------|----------------|------|--------------|
| Claude Sonnet | 1-3s | $3/M tokens | Native, reliable |
| GPT-4o | 1-4s | $2.50/M tokens | Native, reliable |
| Local Llama 3.1 8B (CPU) | 5-15s | Free | Prompt-engineered |
| Local Llama 3.1 8B (GPU) | 1-4s | Free | Prompt-engineered |

**Context Length Needs:**
- System prompt: ~600 tokens
- Typical query: 20-100 tokens
- Tool results: 200-800 tokens
- **Total:** 1-2K tokens per exchange (all models sufficient)

### Setup Instructions

Create `docs/workflows/local-llm-setup.md`:

```markdown
# Local LLM Setup Guide

## Ollama Installation (Recommended)

1. Install Ollama: `https://ollama.ai/download`
2. Pull a model: `ollama pull llama3.1:8b-instruct-q4_K_M`
3. Verify: `ollama run llama3.1:8b-instruct-q4_K_M`

## Configure Poolula Platform

```bash
# .env
LLM_PROVIDER=ollama
LOCAL_MODEL_PATH=llama3.1:8b-instruct-q4_K_M
LOCAL_MODEL_URL=http://localhost:11434
```

## Test Local Setup

```bash
uv sync --group local
python scripts/evaluate_chatbot.py --verbose
```

## Performance Tuning

- **CPU:** Set `OLLAMA_NUM_THREADS=4` (adjust for your CPU)
- **GPU:** Ollama auto-detects CUDA/Metal
- **Memory:** Models stay loaded in RAM after first use
```

**Limitations of Local Models:**
- ⚠️ Tool calling less reliable (prompt engineering vs. native API)
- ⚠️ Slower on CPU (acceptable for learning, not production)
- ⚠️ May need prompt tuning per model
- ✅ Privacy (no data leaves machine)
- ✅ Zero API costs
- ✅ Offline capability

---

## Documentation & Developer Experience

### Files to Create/Update

#### New Files:
1. **`apps/chatbot/llm_providers/base.py`** - Provider interface
2. **`apps/chatbot/llm_providers/anthropic_provider.py`** - Anthropic adapter
3. **`apps/chatbot/llm_providers/openai_provider.py`** - OpenAI adapter
4. **`apps/chatbot/llm_providers/ollama_provider.py`** - Local model adapter
5. **`scripts/evaluate_providers.py`** - Cross-provider evaluation
6. **`docs/workflows/local-llm-setup.md`** - Local model setup guide
7. **`docs/architecture/llm-providers.md`** - Provider architecture guide
8. **`docs/evaluation/provider_checklist.md`** - Manual testing checklist

#### Updated Files:
1. **`apps/chatbot/config.py`** - Add provider configuration
2. **`apps/chatbot/ai_generator.py`** - Refactor to use provider interface
3. **`apps/chatbot/rag_system.py`** - Add provider factory
4. **`CLAUDE.md`** - Document LLM agnosticism in project overview
5. **`README.md`** - Add provider switching instructions
6. **`pyproject.toml`** - Add optional dependency groups

### Developer Quick Start

Add to `README.md`:

```markdown
## Switching LLM Providers

### Using Anthropic Claude (Default)
```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

### Using OpenAI
```bash
uv sync --group openai
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

### Using Local Models (Ollama)
```bash
uv sync --group local
ollama pull llama3.1:8b-instruct-q4_K_M
export LLM_PROVIDER=ollama
export LOCAL_MODEL_PATH=llama3.1:8b-instruct-q4_K_M
```

### Compare Providers
```bash
python scripts/evaluate_providers.py --providers anthropic openai ollama
```

See `docs/workflows/local-llm-setup.md` for detailed setup.
```

---

## Risks & Unknowns

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tool calling inconsistent across providers | High | Medium | Fallback to prompt engineering, document limitations |
| Local models too slow for interactive use | Medium | Low | Set expectations, provide GPU acceleration guide |
| OpenAI/others change API format | Low | Medium | Adapter pattern isolates changes |
| Evaluation harness doesn't catch quality regressions | Medium | High | Add qualitative checklist, manual spot-checks |

### Validation Strategy

**After Each Stage:**

1. **Regression Testing:**
   ```bash
   uv run pytest tests/chatbot/
   # All existing tests must pass
   ```

2. **Evaluation Baseline:**
   ```bash
   python scripts/evaluate_chatbot.py
   # Score must be ≥85% (current baseline)
   ```

3. **Spot Check Queries:**
   ```python
   # Test these manually via API:
   - "What is our EIN number?"  # Database tool
   - "Show me the operating agreement effective date"  # Document search
   - "What was rental income in August 2024?"  # Database aggregation
   - "List our insurance policies"  # Multi-round: list docs → search
   ```

4. **Performance Benchmarking:**
   ```bash
   # Track P50, P95, P99 latency per provider
   python scripts/benchmark_providers.py --iterations 20
   ```

### Unknown Unknowns

**Questions to investigate during implementation:**

1. **Streaming Support:** Do we need streaming responses? (Current: no, but may want for UX)
2. **Retry Logic:** Should provider handle retries or AIGenerator? (Recommend: provider-level)
3. **Rate Limiting:** How to handle different provider rate limits? (Recommend: exponential backoff in base provider)
4. **Cost Tracking:** Should we log token usage per provider? (Recommend: yes, add to audit log)

**Investigation approach:**
- Start with Anthropic (known working)
- Add OpenAI next (most similar API)
- Local models last (most different, educational value)
- Document learnings in `docs/architecture/llm-providers.md`

---

## Implementation Checklist

### Stage 1: Abstraction Layer (Quick Wins)
- [x] Create `apps/chatbot/llm_providers/` directory
- [x] Implement `base.py` with LLMProvider interface
- [x] Implement `anthropic_provider.py` adapter
- [x] Update `config.py` with provider settings
- [x] Refactor `ai_generator.py` to use provider interface
- [x] Update `rag_system.py` with provider factory
- [ ] Fix remaining test mocks (8/12 AI generator tests failing)
- [ ] Run evaluation harness (verify ≥85% score)
- [ ] Update `CLAUDE.md` with architecture changes

### Stage 2: Alternative Providers
- [ ] Implement `openai_provider.py`
- [ ] Implement `ollama_provider.py`
- [ ] Add optional dependencies to `pyproject.toml`
- [ ] Test OpenAI provider with sample queries
- [ ] Test Ollama provider locally
- [ ] Document provider-specific quirks

### Stage 3: Evaluation & Documentation
- [ ] Create `scripts/evaluate_providers.py`
- [ ] Create `docs/evaluation/provider_checklist.md`
- [ ] Create `docs/workflows/local-llm-setup.md`
- [ ] Create `docs/architecture/llm-providers.md`
- [ ] Run cross-provider evaluation
- [ ] Perform manual qualitative checks
- [ ] Update `README.md` with provider switching guide

---

## Expected Outcomes

**After Stage 1:**
- No behavior change (Anthropic still default)
- Clean abstraction boundaries
- Easy to add new providers
- ~200 lines of new code

**After Stage 2:**
- 3 providers working (Anthropic, OpenAI, Ollama)
- Environment variable switching
- ~400 additional lines of code

**After Stage 3:**
- Systematic provider comparison
- Clear documentation for contributors
- Evaluation framework extended
- Learning-focused: "Try provider X, compare results"

**Metrics to Track:**
- Evaluation score per provider (target: ≥70% all providers)
- Average latency per provider
- Cost per 1000 queries (API providers)
- Developer setup time (should be <15 min for local models)

---

This plan balances **pragmatism** (keep working Anthropic code) with **flexibility** (easy to experiment with alternatives) while maintaining **clarity** (well-documented, understandable architecture) for a learning-focused project.

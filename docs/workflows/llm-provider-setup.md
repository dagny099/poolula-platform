# LLM Provider Setup Guide

This guide explains how to configure and switch between different LLM providers in the Poolula Platform chatbot.

## Overview

The chatbot supports three LLM providers:
- **Anthropic Claude** (default) - Best quality, native tool calling, requires API key
- **OpenAI GPT** (optional) - Alternative provider, native tool calling, requires API key
- **Ollama** (optional) - Local models, privacy-focused, free, prompt-based tool calling

## Provider Setup

### Anthropic Claude (Default)

**Prerequisites:**
- Anthropic API key from https://console.anthropic.com/

**Installation:**
```bash
# Already included in base RAG dependencies
uv sync --group rag
```

**Configuration:**
```bash
# .env
LLM_PROVIDER=anthropic  # This is the default
ANTHROPIC_API_KEY=sk-ant-...
# Optional: Override default model
# ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Usage:**
```python
from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config

config = Config()
rag = RAGSystem(config)
response, sources = rag.query("What is our EIN number?")
```

---

### OpenAI GPT

**Prerequisites:**
- OpenAI API key from https://platform.openai.com/

**Installation:**
```bash
# Install OpenAI provider dependencies
uv sync --group openai
```

**Configuration:**
```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# Optional: Override default model
# OPENAI_MODEL=gpt-4o  # or gpt-4o-mini for lower cost
```

**Usage:**
```python
from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config

config = Config()  # Will use OPENAI provider from .env
rag = RAGSystem(config)
response, sources = rag.query("What properties do we own?")
```

**Cost Comparison:**
- GPT-4o: ~$2.50/M input tokens, $10/M output tokens
- Claude Sonnet: ~$3/M input tokens, $15/M output tokens
- Typical query: ~2K tokens total

---

### Ollama (Local Models)

**Prerequisites:**
- Ollama installed: https://ollama.ai/download
- Sufficient RAM (16GB+ for 7B models)

**Installation:**
```bash
# 1. Install Ollama from https://ollama.ai
# 2. Pull a model
ollama pull llama3.1:8b-instruct-q4_K_M

# 3. Install local provider dependencies (requests already in base)
uv sync --group local
```

**Configuration:**
```bash
# .env
LLM_PROVIDER=ollama
LOCAL_MODEL_PATH=llama3.1:8b-instruct-q4_K_M
# Optional: Override Ollama URL
# LOCAL_MODEL_URL=http://localhost:11434
```

**Usage:**
```python
from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config

config = Config()  # Will use Ollama from .env
rag = RAGSystem(config)
response, sources = rag.query("List our business documents")
```

**Recommended Models:**

| Model | Size (Q4) | Context | Speed (CPU) | Notes |
|-------|-----------|---------|-------------|-------|
| llama3.1:8b-instruct-q4_K_M | 4.7GB | 128K | Medium | Best balance |
| mistral:7b-instruct-q4_0 | 4.1GB | 32K | Fast | Concise responses |
| qwen2.5:7b-instruct-q4_K_M | 4.4GB | 128K | Medium | Strong reasoning |

**Limitations:**
- ⚠️ Slower than API providers (5-15s on CPU vs 1-3s)
- ⚠️ Tool calling via prompt engineering (less reliable)
- ⚠️ May need prompt tuning per model
- ✅ Free and private (no data leaves your machine)
- ✅ Offline capable

---

## Switching Providers

You can switch providers by changing the `LLM_PROVIDER` environment variable:

```bash
# Test with different providers
export LLM_PROVIDER=anthropic
python scripts/test_query.py "What is our property address?"

export LLM_PROVIDER=openai
python scripts/test_query.py "What is our property address?"

export LLM_PROVIDER=ollama
python scripts/test_query.py "What is our property address?"
```

## Provider Comparison

### Tool Calling Support

| Provider | Native Tools | Reliability | Notes |
|----------|--------------|-------------|-------|
| Anthropic | ✅ Yes | Excellent | Production-ready |
| OpenAI | ✅ Yes | Excellent | Production-ready |
| Ollama | ❌ Prompt-based | Good | May miss complex tool uses |

### Latency & Cost

| Provider | P50 Latency | Cost per 1K queries | Privacy |
|----------|-------------|---------------------|---------|
| Anthropic | 1-3s | ~$6 | Data sent to API |
| OpenAI | 1-4s | ~$5 | Data sent to API |
| Ollama (CPU) | 5-15s | Free | Fully local |
| Ollama (GPU) | 1-4s | Free | Fully local |

### Use Cases

**Use Anthropic when:**
- You need the best quality responses
- Budget is not the primary concern
- Multi-round tool calling is critical

**Use OpenAI when:**
- You want cost optimization
- You have existing OpenAI credits
- You need comparable quality to Anthropic

**Use Ollama when:**
- Privacy is critical (medical, legal, sensitive data)
- You want zero ongoing costs
- You have decent hardware (16GB+ RAM)
- You're learning/experimenting with local LLMs
- Offline capability is required

## Troubleshooting

### OpenAI Provider

**Error: "OpenAI provider requires the 'openai' package"**
```bash
uv sync --group openai
```

**Error: "OPENAI_API_KEY is required"**
```bash
echo "OPENAI_API_KEY=sk-..." >> .env
```

### Ollama Provider

**Error: "Failed to connect to Ollama"**
```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed (it usually runs automatically)
# On macOS: Open Ollama app
# On Linux: systemctl start ollama
```

**Error: "LOCAL_MODEL_PATH is required"**
```bash
# Pull a model first
ollama pull llama3.1:8b-instruct-q4_K_M

# Then set in .env
echo "LOCAL_MODEL_PATH=llama3.1:8b-instruct-q4_K_M" >> .env
```

**Slow responses:**
```bash
# Check CPU threads (macOS/Linux)
export OLLAMA_NUM_THREADS=4  # Adjust for your CPU

# Consider using a smaller model
ollama pull qwen2.5:3b-instruct-q4_K_M
```

## Next Steps

- **Evaluate providers:** Use `scripts/evaluate_chatbot.py` to compare quality
- **Monitor costs:** Track API usage for Anthropic/OpenAI
- **Experiment:** Try different models with Ollama to find the best fit

For detailed implementation information, see `docs/planning/2025-12-03-llm-agnosticism-plan.md`.

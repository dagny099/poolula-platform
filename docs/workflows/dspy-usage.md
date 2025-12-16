# DSPy Pipeline Usage Guide

This guide explains how to use and optimize DSPy pipelines for the Poolula Platform chatbot.

## Overview

DSPy is a framework for programmatic prompt engineering and pipeline optimization. The Poolula Platform now includes real DSPy implementations that can be optimized using your ground truth evaluation dataset.

## Available Pipelines

### 1. SimpleDSPyQA (Basic)
Simple question-answering without retrieval. Good for general knowledge questions.

```python
from apps.dspy.lm_config import configure_dspy_lm
from apps.dspy.pipelines import SimpleDSPyQA

# Configure the LLM
configure_dspy_lm("anthropic")

# Create pipeline
pipeline = SimpleDSPyQA()

# Ask a question
prediction = pipeline(question="What is Poolula LLC?")
print(prediction.answer)
```

### 2. RetrieveAndAnswerPipeline (Placeholder Retrieval)
Demonstrates the retrieve → generate pattern with placeholder context.

```python
from apps.dspy.pipelines import RetrieveAndAnswerPipeline

configure_dspy_lm("anthropic")
pipeline = RetrieveAndAnswerPipeline(k=5)

prediction = pipeline(question="What properties do we own?")
print(prediction.answer)
print(f"Context used: {prediction.context}")
```

### 3. PoolulaRAGPipeline ⭐ (Recommended)
Full RAG pipeline with real database and document retrieval.

```python
from apps.dspy.pipelines import PoolulaRAGPipeline

configure_dspy_lm("anthropic")

# Use hybrid retrieval (database + vector store)
pipeline = PoolulaRAGPipeline(use_hybrid=True, k=5)

# Or use database-only retrieval
# pipeline = PoolulaRAGPipeline(use_hybrid=False, k=10)

prediction = pipeline(question="What was our rental income in August 2025?")
print(prediction.answer)

# Inspect retrieved passages
for i, passage in enumerate(prediction.passages, 1):
    print(f"\nPassage {i}:\n{passage}")
```

## LLM Provider Configuration

DSPy supports multiple LLM providers. Configure before using pipelines:

### Anthropic (Default)
```python
from apps.dspy.lm_config import configure_dspy_lm

# Uses ANTHROPIC_API_KEY from environment
configure_dspy_lm("anthropic")
```

### OpenAI
```python
# Requires OpenAI dependency: uv sync --group openai
# Uses OPENAI_API_KEY from environment
configure_dspy_lm("openai")
```

### Ollama (Local)
```python
# Requires Ollama running locally
# Uses LOCAL_MODEL_URL from environment (default: http://localhost:11434)
configure_dspy_lm("ollama")
```

## Retrievers

The PoolulaRAGPipeline uses specialized retrievers that wrap existing tools:

### DatabaseRetriever
Queries structured data (properties, transactions, documents, obligations).

```python
from apps.dspy.retrievers import DatabaseRetriever

retriever = DatabaseRetriever(k=10)

# Automatically detects query type from natural language
result = retriever("Show me all properties")
result = retriever("What was rental income in July 2025?")
result = retriever("List recent transactions")

# Returns dspy.Prediction with passages field
for passage in result.passages:
    print(passage)
```

**Supported query types:**
- Properties: "show properties", "list addresses"
- Transactions: "rental income", "expenses", "transactions"
- Documents: "documents", "files", "pdfs"
- Obligations: "obligations", "compliance", "deadlines"

### VectorStoreRetriever
Searches document content using semantic similarity.

```python
from apps.dspy.retrievers import VectorStoreRetriever

retriever = VectorStoreRetriever(k=5)

# Search for document content
result = retriever("insurance coverage for rental property")
result = retriever("property management agreement terms")

for passage in result.passages:
    print(passage)
```

### HybridRetriever
Combines database and vector search for comprehensive retrieval.

```python
from apps.dspy.retrievers import HybridRetriever

retriever = HybridRetriever(k=10)  # Splits k between db and vector

# Gets results from both sources
result = retriever("What properties does Poolula LLC own?")
```

## Building Artifacts

Create serialized DSPy programs for deployment:

### Build SimpleDSPyQA
```bash
uv run python scripts/build_dspy_artifact.py \
  --pipeline-type simple \
  --output-dir artifacts/dspy-simple
```

### Build PoolulaRAGPipeline
```bash
uv run python scripts/build_dspy_artifact.py \
  --pipeline-type poolula \
  --output-dir artifacts/dspy-poolula \
  --k 10
```

### Build with Different LLM
```bash
uv run python scripts/build_dspy_artifact.py \
  --pipeline-type poolula \
  --llm-provider openai \
  --output-dir artifacts/dspy-openai
```

**Output structure:**
```
artifacts/dspy-simple/
├── program.json       # Serialized DSPy module
└── metadata.json      # Build metadata (dspy version, pipeline type, etc.)
```

## Testing Pipelines

### Test Individual Retrievers
```bash
# Test database and vector retrievers separately
uv run python scripts/test_dspy_tools.py
```

### Test Basic Pipelines
```bash
# Test SimpleDSPyQA and RetrieveAndAnswerPipeline
uv run python scripts/test_dspy_basic.py
```

### Custom Testing Script
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.dspy.lm_config import configure_dspy_lm
from apps.dspy.pipelines import PoolulaRAGPipeline

configure_dspy_lm("anthropic")
pipeline = PoolulaRAGPipeline(use_hybrid=True, k=5)

test_questions = [
    "What properties does Poolula LLC own?",
    "What was our rental income last month?",
    "What insurance policies do we have?"
]

for question in test_questions:
    print(f"\nQ: {question}")
    prediction = pipeline(question=question)
    print(f"A: {prediction.answer}\n")
```

## Optimization ⭐ UPDATED

DSPy pipelines can be optimized using your ground truth evaluation dataset (20 questions).
All optimization runs are tracked with **MLflow** for experiment management and comparison.

### Quick Start: BootstrapFewShot
```bash
# Basic optimization with default settings
uv run python scripts/optimize_dspy_pipeline.py

# Customize optimization parameters
uv run python scripts/optimize_dspy_pipeline.py \
  --max-bootstrapped 4 \
  --max-labeled 3 \
  --k 10

# Use different LLM provider
uv run python scripts/optimize_dspy_pipeline.py --provider openai

# Verbose output
uv run python scripts/optimize_dspy_pipeline.py --verbose
```

**What happens during optimization:**
1. Loads your 20 evaluation questions (15 train, 5 dev)
2. Adds 4 hand-crafted few-shot examples
3. Runs baseline evaluation on dev set
4. Uses BootstrapFewShot to generate optimized prompts
5. Evaluates optimized pipeline
6. Saves artifacts to `artifacts/optimized_dspy_program/`

**Expected runtime:** 5-10 minutes depending on LLM speed

### Understanding the Output

```
BASELINE EVALUATION
  Baseline Score: 65.0%

OPTIMIZATION
  Optimizing with BootstrapFewShot
  Using 4 hand-crafted demos
  ✅ Compilation complete

OPTIMIZED EVALUATION
  Optimized Score: 78.0%

RESULTS
  Baseline:    65.0%
  Optimized:   78.0%
  Improvement: +13.0% (+13.0 percentage points)

✅ Optimization improved performance!
```

### Optimization Parameters

**--max-bootstrapped** (default: 4)
- Number of automatically generated demonstrations
- Higher = more examples but slower compilation
- Recommended: 3-6 for 20 training examples

**--max-labeled** (default: 3)
- Number of hand-crafted examples to include
- These are high-quality examples we wrote
- Recommended: Keep at 3-4

**--k** (default: 5)
- Retrieval results per query
- Higher = more context but potentially noisier
- Recommended: 5-10

**--use-hybrid** (default: True)
- Use both database and vector retrieval
- False = database only
- Recommended: True for comprehensive coverage

### Advanced: MIPRO Optimization

MIPRO (Multi-prompt Instruction Proposal Optimizer) is more sophisticated but requires more examples:

```bash
# Coming in Phase 4
# Requires 30+ training examples for best results
```

### Tips for Better Optimization

1. **Start small**: Use default settings first
2. **Check baseline**: If baseline is already ≥80%, optimization may not help much
3. **Inspect failures**: Look at dev set questions that fail
4. **Iterate**: Re-run with adjusted parameters
5. **Monitor cost**: Each optimization makes ~50-100 LLM calls

### Loading Optimized Programs

```python
from apps.dspy.pipelines import PoolulaRAGPipeline
from apps.dspy.lm_config import configure_dspy_lm

configure_dspy_lm("anthropic")

# Create base pipeline
pipeline = PoolulaRAGPipeline(use_hybrid=True, k=5)

# Load optimized state
pipeline.load("artifacts/optimized_dspy_program/program.json")

# Use optimized pipeline
prediction = pipeline(question="What properties do we own?")
print(prediction.answer)
```

---

## MLflow Integration ⭐ NEW

All optimization runs are automatically tracked in MLflow for experiment comparison and versioning.

### Viewing Optimization History

```bash
# Launch MLflow UI
mlflow ui

# Open browser to http://localhost:5000
```

**What's Tracked:**
- **Parameters**: `max_bootstrapped_demos`, `retrieval_k`, `llm_provider`, etc.
- **Metrics**: `baseline_score`, `optimized_score`, `improvement_percentage`
- **Artifacts**: `program.json`, `metadata.json`, `results_summary.json`
- **Tags**: `stage`, `pipeline`, `optimizer`, `provider`, `result`

### Comparing Optimization Runs

1. Open MLflow UI: `mlflow ui`
2. Navigate to **Experiments** → `dspy-optimization`
3. Select 2-3 runs using checkboxes
4. Click **Compare** button
5. Review side-by-side metrics and parameters

**Search by Tags:**
```
# Find improved runs
tags.result = "improved"

# Find runs with specific provider
tags.provider = "anthropic"

# Find recent optimization runs
tags.stage = "optimization"
```

### Optimization Artifacts

Each optimization run saves:

```
artifacts/optimized_dspy_program/
├── program.json          # Optimized DSPy module state
├── metadata.json         # Optimization metadata
└── results_summary.json  # Performance comparison
```

**metadata.json** includes:
- Timestamp
- Program class (PoolulaRAGPipeline)
- Optimizer used (BootstrapFewShot)
- Hyperparameters (k, provider, max_bootstrapped, etc.)
- DSPy version

---

## Production Deployment ⭐ NEW

Deploy optimized DSPy pipelines to production using environment variables.

### Enable Optimized Pipeline

```bash
# Set environment variables
export USE_OPTIMIZED_DSPY=true
export OPTIMIZED_DSPY_PATH=artifacts/optimized_dspy_program
export LLM_PROVIDER=anthropic

# Restart API server
uv run uvicorn apps.api.main:app --reload --port 8082
```

### Verify Deployment

```bash
# Check DSPy status endpoint
curl http://localhost:8082/api/v1/chat/dspy-status
```

**Response:**
```json
{
  "optimized_dspy_enabled": true,
  "program_loaded": true,
  "program_class": "PoolulaRAGPipeline",
  "artifact_path": "artifacts/optimized_dspy_program",
  "artifact_exists": true,
  "llm_provider": "anthropic",
  "metadata": {
    "timestamp": "2025-12-16T10:30:00",
    "optimizer": "BootstrapFewShot",
    "program_class": "PoolulaRAGPipeline",
    "hyperparameters": {...}
  }
}
```

### Test Optimized Pipeline

```bash
# Send query to API
curl -X POST http://localhost:8082/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What properties does Poolula LLC own?"
  }'
```

**Response includes pipeline indicator:**
```json
{
  "answer": "Poolula LLC owns one rental property...",
  "sources": [...],
  "session_id": "uuid-here",
  "pipeline_used": "optimized_dspy"
}
```

✅ **Check `pipeline_used` field** to confirm which pipeline answered the query.

### Deployment Options

| Option | Description | Use Case |
|--------|-------------|----------|
| **Optimized DSPy** | `USE_OPTIMIZED_DSPY=true` | Best performance, after optimization |
| **Baseline RAG** | `USE_OPTIMIZED_DSPY=false` | Fallback, debugging, or comparison |
| **Auto-Fallback** | Enabled by default | If optimized fails, uses baseline automatically |

### Runtime Loading

The optimized program is loaded once at API startup and cached:

```python
from apps.dspy.runtime import get_dspy_program, get_runtime_info

# Get cached program (loaded on first call)
program = get_dspy_program()

# Get runtime status
info = get_runtime_info()
print(f"Program loaded: {info['program_loaded']}")
print(f"Program class: {info['program_class']}")
```

---

## Performance Monitoring ⭐ NEW

Monitor optimized pipeline performance and detect regressions over time.

### Manual Regression Check

```bash
# Run regression detection
uv run python scripts/detect_dspy_regression.py
```

**What It Does:**
1. Evaluates baseline RAG on dev set
2. Evaluates optimized DSPy on dev set
3. Compares scores (regression threshold: 10%)
4. Logs results to MLflow experiment `dspy-regression-detection`
5. Saves report to `artifacts/regression_reports/`

**Output:**
```
BASELINE RAG EVALUATION
──────────────────────────────────────────────
Baseline Results:
  Average Score: 65.0%
  Passed: 4/5

OPTIMIZED DSPY EVALUATION
──────────────────────────────────────────────
Optimized Results:
  Average Score: 78.0%
  Passed: 5/5

REGRESSION DETECTION
──────────────────────────────────────────────
✅ Optimized DSPy is 13.0% better than baseline
```

### Custom Regression Threshold

```bash
# More sensitive (alert on 5% drop)
uv run python scripts/detect_dspy_regression.py --threshold 0.05

# Less sensitive (alert on 15% drop)
uv run python scripts/detect_dspy_regression.py --threshold 0.15
```

### Automated Monitoring

Set up daily regression checks with cron:

```bash
# Edit crontab
crontab -e

# Add daily check at 2 AM
0 2 * * * cd /path/to/poolula-platform && uv run python scripts/detect_dspy_regression.py
```

### Regression Reports

Reports are saved to `artifacts/regression_reports/`:

```json
{
  "timestamp": "2025-12-16T14:30:00",
  "regression_detected": false,
  "message": "✅ Optimized DSPy is 13.0% better than baseline",
  "baseline": {
    "average_score": 0.65,
    "passed_count": 4,
    "total_questions": 5
  },
  "optimized": {
    "average_score": 0.78,
    "passed_count": 5,
    "total_questions": 5
  },
  "difference": -0.13
}
```

### Alert Thresholds

| Scenario | Status | Action |
|----------|--------|--------|
| Optimized ≥ Baseline + 5% | ✅ Excellent | Continue monitoring |
| Baseline ≤ Optimized < Baseline + 5% | ⚠️ Similar | Monitor closely |
| Optimized < Baseline - 10% | ❌ **Regression** | Investigate immediately |

### Investigating Regressions

When regression detected:

1. **Check Recent Changes**: New data, code updates, environment changes?
2. **Review MLflow Logs**: Look for error patterns in failed questions
3. **Run Verbose Evaluation**: `uv run python scripts/detect_dspy_regression.py --verbose`
4. **Update Golden Set**: Add problematic questions to training set
5. **Re-optimize**: Run optimization with updated questions
6. **Rollback if Needed**: Disable optimized pipeline: `export USE_OPTIMIZED_DSPY=false`

## Best Practices

### 1. Choose the Right Pipeline

- **SimpleDSPyQA**: General knowledge, no database needed
- **PoolulaRAGPipeline (database-only)**: Financial/numerical queries
- **PoolulaRAGPipeline (hybrid)**: Questions needing both data and documents

### 2. Tune Retrieval Parameters

```python
# More passages = more context but slower and potentially noisier
pipeline = PoolulaRAGPipeline(k=10)  # Good for complex questions

# Fewer passages = faster and more focused
pipeline = PoolulaRAGPipeline(k=3)   # Good for simple lookups
```

### 3. Inspect Retrieved Context

Always check what context was retrieved:

```python
prediction = pipeline(question="...")

print(f"Retrieved {len(prediction.passages)} passages")
for i, passage in enumerate(prediction.passages, 1):
    print(f"\n[{i}] {passage[:100]}...")

print(f"\nAnswer: {prediction.answer}")
```

### 4. Handle Errors Gracefully

```python
try:
    prediction = pipeline(question="What is our revenue?")
    if "No results found" in str(prediction.passages):
        print("No relevant data found")
    else:
        print(prediction.answer)
except Exception as e:
    print(f"Error: {e}")
```

## Integration with Existing Chatbot

The baseline RAG system (apps/chatbot/rag_system.py) continues to work alongside DSPy pipelines:

```python
# Option 1: Use baseline RAG (multi-round, session management)
from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config

rag = RAGSystem(Config())
answer, sources = rag.query("What properties do we own?")

# Option 2: Use DSPy pipeline (optimizable, single-round)
from apps.dspy.pipelines import PoolulaRAGPipeline
from apps.dspy.lm_config import configure_dspy_lm

configure_dspy_lm("anthropic")
pipeline = PoolulaRAGPipeline(use_hybrid=True, k=5)
prediction = pipeline(question="What properties do we own?")
```

**Differences:**

| Feature | Baseline RAG | DSPy Pipeline |
|---------|-------------|---------------|
| Multi-round queries | ✅ Yes | ❌ No |
| Session management | ✅ Yes | ❌ No |
| Audit logging | ✅ Yes | ❌ No |
| Prompt optimization | ❌ No | ✅ Yes (Phase 3) |
| Serializable | ❌ No | ✅ Yes |
| MLflow integration | Partial | ✅ Yes |

## Troubleshooting

### Import Errors
```bash
# Ensure RAG dependencies installed
uv sync --group rag
```

### API Key Issues
```bash
# Check environment variables
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Or add to .env file
cat >> .env <<EOF
ANTHROPIC_API_KEY=sk-ant-...
EOF
```

### No Results from Retrieval
```python
# Check if database has data
from apps.chatbot.database_tool import DatabaseQueryTool
tool = DatabaseQueryTool()
result = tool.query_properties()
print(f"Found {result['count']} properties")

# Check if vector store has documents
from apps.chatbot.vector_store import VectorStore
from apps.chatbot.config import Config
config = Config()
vs = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL)
result = vs.search_documents("property", limit=5)
print(f"Found {len(result.documents)} documents")
```

### Serialization Issues
DSPy modules use `dspy.save()` instead of pickle:

```python
# Correct way to save
pipeline = PoolulaRAGPipeline()
pipeline.save("artifacts/my-pipeline.json")

# Load later
from apps.dspy.pipelines import PoolulaRAGPipeline
loaded_pipeline = PoolulaRAGPipeline()
loaded_pipeline.load("artifacts/my-pipeline.json")
```

## Next Steps

- **Phase 3**: Implement pipeline optimization with BootstrapFewShot/MIPRO
- **Phase 4**: Add multi-round reasoning support
- **Phase 5**: Production deployment with monitoring

## Additional Resources

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Evaluation Harness Guide](../evaluation/harness.md)
- [LLM Provider Setup](./llm-provider-setup.md)
- [Implementation Plan](../planning/dspy-mlflow-plan-2025-12-09.md)

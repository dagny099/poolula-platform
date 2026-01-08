# Provider Comparison Guide

This guide explains how to run and interpret multi-provider evaluations for the Poolula Platform chatbot.

!!! info "Multi-Provider Evaluation Status"
    **Current State:** The evaluation framework for comparing LLM providers exists (`scripts/evaluate_providers.py`), but **only Anthropic Claude is currently integrated** into the chatbot (Phase 2).

    **Status:**
    - ✅ Evaluation script operational - Can test multiple providers
    - ✅ Anthropic Claude - Fully integrated and operational
    - 🚧 OpenAI provider - Evaluation-ready, not yet integrated into chatbot (Phase 6-7)
    - 🚧 Ollama local models - Evaluation-ready, not yet integrated into chatbot (Phase 6-7)

    **Note:** You can run provider comparisons using the evaluation script to test different providers, but the production chatbot currently uses only Anthropic Claude.

## Quick Start

### Running a Comparison

Compare all providers:
```bash
python scripts/evaluate_providers.py --providers anthropic openai ollama
```

Compare specific providers:
```bash
python scripts/evaluate_providers.py --providers anthropic openai
```

Verbose mode (show per-question details):
```bash
python scripts/evaluate_providers.py --providers anthropic --verbose
```

Custom output path:
```bash
python scripts/evaluate_providers.py --output data/my_comparison.json
```

### Viewing Results

The script generates two outputs:

1. **Console Summary:** Overall scores with winner marked
2. **JSON Report:** Detailed comparison at `data/provider_comparison.json`

Example console output:
```
============================================================
Provider Comparison Summary
============================================================
🏆 anthropic       : 87.3%
   openai          : 84.1%
   ollama          : 71.5%
============================================================

Detailed report saved to: data/provider_comparison.json
```

---

## Understanding Comparison Reports

### Overall Scores

The overall score is the average across all 15 evaluation questions, weighted by:
- **Tool Usage (40%):** Did the AI call the correct tools?
- **Response Quality (40%):** Did the response include expected keywords?
- **Error Handling (20%):** Did the query complete without errors?

**Score Interpretation:**
- **≥85%**: Excellent quality, production-ready
- **70-84%**: Acceptable quality, suitable for most use cases
- **<70%**: Investigate quality issues, check manual testing checklist

### Component Breakdown

The JSON report includes per-provider breakdown of each scoring component:

```json
{
  "overall_scores": {
    "anthropic": 87.3,
    "openai": 84.1,
    "ollama": 71.5
  },
  "winner": "anthropic"
}
```

**Key Questions:**
- **Which provider is best at tool selection?** Check `tool_usage` scores
- **Which provider has better response quality?** Check `relevance` scores
- **Are there reliability differences?** Check `error_handling` scores

### Category Performance

The report groups questions by category:
- `property_info` - Property details (address, acquisition, etc.)
- `property_financials` - Financial data (basis, depreciation)
- `transactions` - Financial transactions (income, expenses)
- `documents` - Document-based queries
- `formation` - LLC formation and structure
- `aggregations` - SQL aggregations (totals, averages)
- `compliance` - Compliance obligations
- `hybrid` - Multi-source queries

**Example Category Breakdown:**
```json
{
  "category_performance": {
    "property_info": {
      "anthropic": 100.0,
      "openai": 96.7,
      "ollama": 86.7
    },
    "compliance": {
      "anthropic": 66.7,
      "openai": 60.0,
      "ollama": 40.0
    }
  }
}
```

**What This Tells You:**
- All providers excel at property_info (straightforward database queries)
- All providers struggle with compliance (requires better prompting or tool design)
- Relative performance is consistent across categories (Anthropic > OpenAI > Ollama)

### Per-Question Analysis

The `question_breakdown` section shows where providers diverge:

```json
{
  "question": "What properties does Poolula LLC own?",
  "category": "property_info",
  "scores": {
    "anthropic": {
      "total": 100.0,
      "tool_usage": 100.0,
      "relevance": 100.0,
      "error_handling": 100.0
    },
    "ollama": {
      "total": 60.0,
      "tool_usage": 100.0,
      "relevance": 20.0,
      "error_handling": 100.0
    }
  },
  "winner": "anthropic"
}
```

**Insights:**
- Both providers called the correct tool (`tool_usage: 100`)
- Ollama struggled with keyword matching (`relevance: 20` vs `100`)
- Neither had errors (`error_handling: 100`)

**Common Pattern:** Local models often get tool selection right but phrase responses differently, leading to lower keyword matching scores.

---

## Common Patterns

### Pattern 1: Tool Selection is Consistent

**Observation:** All providers typically score ≥90% on `tool_usage`

**Why:** The provider abstraction successfully translates tool definitions. Even prompt-based tool calling (Ollama) works reliably.

**Implication:** You can confidently use any provider—tool calling won't be the bottleneck.

### Pattern 2: Response Quality Varies

**Observation:** `relevance` scores show the widest variance (Anthropic 87% vs Ollama 60-70%)

**Why:** Different models phrase responses differently. Keyword matching doesn't capture semantic equivalence.

**Example:**
- Anthropic: "900 S 9th St, Montrose, CO 81401"
- Ollama: "The property is located at nine hundred south ninth street in Montrose, Colorado"

Both are correct, but Ollama misses keywords "900", "9th", "CO", "81401".

**Implication:** Consider semantic similarity matching in future (see `docs/evaluation/roadmap.md`).

### Pattern 3: Compliance Questions Are Hard

**Observation:** All providers score <70% on `compliance` category

**Why:** Compliance questions may require better tool design or eval set revision.

**Action:** Investigate whether:
1. The evaluation criteria are too strict
2. The tools don't provide sufficient data
3. The system prompt needs better compliance instructions

### Pattern 4: Local Models Trade Speed for Quality

**Observation:** Ollama scores 15-20% lower than cloud providers

**Why:** Smaller parameter count (8B vs 175B+), prompt-based tool calling

**Trade-off:** Ollama is free, private, and offline—acceptable quality for learning.

---

## What to Do With Results

### Scenario 1: Choosing a Provider

**All scores >80%:**
- Choose based on cost, privacy, or latency
- See `docs/workflows/llm-provider-setup.md` for decision matrix

**Example Decision:**
- Production: Anthropic (best quality, worth the cost)
- Experimentation: OpenAI (good balance, 17% cost savings)
- Learning: Ollama (acceptable quality, free, private)

### Scenario 2: Quality Investigation

**Score <70%:**
1. Check `docs/evaluation/provider_checklist.md` for manual tests
2. Run verbose mode: `--verbose` to see per-question details
3. Identify specific failure modes (tool selection? keyword matching? errors?)

**Example Investigation:**
```bash
# Re-run with verbose output
python scripts/evaluate_providers.py --providers ollama --verbose

# Look for patterns:
# - Are specific categories failing?
# - Are tool calls malformed?
# - Are responses too brief or too verbose?
```

### Scenario 3: Regression Detection

**Score drops >10% from baseline:**
1. Check if provider API changed (model update, tool calling format)
2. Verify evaluation set unchanged (no accidental edits)
3. Run comparison multiple times to rule out LLM non-determinism

**Baseline Scores (2025-12-04):**
- Anthropic: 87.3%
- OpenAI: 84.1%
- Ollama (Llama 3.1 8B): 71.5%

### Scenario 4: Provider-Specific Tuning

**One provider consistently underperforms on specific category:**

Example: Ollama struggles with document search (73% vs Anthropic's 95%)

**Actions:**
1. Review system prompt for that provider (see `apps/chatbot/llm_providers/ollama_provider.py`)
2. Adjust tool calling instructions in `_build_tool_prompt()`
3. Re-run evaluation to validate improvement

---

## Limitations

### Limitation 1: Keyword Matching is Simplistic

**Issue:** Doesn't handle synonyms or paraphrasing

**Example:**
- Expected: "property", "real estate"
- Response: "building" (semantically correct, but not matched)

**Workaround:** Manual review using `docs/evaluation/provider_checklist.md`

**Future Enhancement:** Semantic similarity matching (see roadmap)

### Limitation 2: No Hallucination Detection

**Issue:** Can't detect when AI fabricates facts that aren't in sources

**Example:**
- Question: "What is our property's market value?"
- Response: "$450,000" (plausible but not in database)

**Workaround:** Manual verification of high-stakes queries

**Future Enhancement:** LLM-as-judge scoring, fact verification

### Limitation 3: Single-Turn Evaluation Only

**Issue:** Doesn't test conversation context or multi-turn interactions

**Example:** Won't catch if provider "forgets" previous context after 3 exchanges

**Workaround:** Manual testing with multi-turn conversations

**Future Enhancement:** Conversation-based evaluation set

### Limitation 4: Non-Deterministic LLMs

**Issue:** Same provider, different runs → different scores (±5% variance)

**Why:** Temperature, sampling randomness

**Workaround:**
- Focus on relative comparison (A vs B) not absolute scores
- Run multiple iterations and average (future enhancement)

---

## Advanced Usage

### Running Multiple Iterations

For more reliable results, run multiple times:

```bash
for i in {1..3}; do
  python scripts/evaluate_providers.py \
    --providers anthropic openai \
    --output data/comparison_run_$i.json
done
```

Then manually average the scores.

### Custom Evaluation Sets

Test new questions before adding to golden set:

```bash
# Create test set
cat > data/test_eval.jsonl << EOF
{"question": "What is the LLC's registered agent?", "type": "database", "expected_tools": ["query_database"], "expected_content": ["agent", "registered"], "category": "formation"}
EOF

# Run comparison on test set
python scripts/evaluate_providers.py \
  --eval-set data/test_eval.jsonl \
  --providers anthropic openai
```

### Historical Tracking

Timestamped reports are automatically saved:

```bash
ls data/provider_comparison_*.json

# Example output:
# provider_comparison_20251204_103045.json
# provider_comparison_20251204_151230.json
```

Track quality trends over time (e.g., after model updates).

---

## Troubleshooting

### Error: "OPENAI_API_KEY is required"

```bash
# Set API key in .env
echo "OPENAI_API_KEY=sk-..." >> .env

# Or export for this session
export OPENAI_API_KEY=sk-...
```

### Error: "Failed to connect to Ollama"

```bash
# Check if Ollama is running
ollama list

# Start Ollama (usually runs automatically)
# macOS: Open Ollama app
# Linux: systemctl start ollama
```

### Warning: "Evaluation takes 4+ minutes"

This is expected: 3 providers × 15 questions × ~5s = ~4 minutes

To speed up:
```bash
# Test subset of providers
python scripts/evaluate_providers.py --providers anthropic openai
```

### Issue: Inconsistent Scores Between Runs

LLM non-determinism causes ±5% variance. This is normal.

To verify:
```bash
# Run same provider twice
python scripts/evaluate_providers.py --providers anthropic --output data/run1.json
python scripts/evaluate_providers.py --providers anthropic --output data/run2.json

# Compare scores (should be within ±5%)
diff data/run1.json data/run2.json
```

---

## Next Steps

1. **Baseline Comparison:** Run full comparison to establish baseline
2. **Document Findings:** Add insights to `docs/architecture/llm-providers.md`
3. **Manual Validation:** Use `docs/evaluation/provider_checklist.md` for qualitative checks
4. **Provider Tuning:** Adjust prompts/tools for underperforming providers
5. **Track Over Time:** Re-run monthly to catch regressions

---

## Related Documentation

- `docs/evaluation/harness.md` - How the evaluation system works
- `docs/evaluation/scoring.md` - Detailed scoring methodology
- `docs/evaluation/provider_checklist.md` - Manual testing checklist
- `docs/workflows/llm-provider-setup.md` - Provider configuration guide
- `docs/architecture/llm-providers.md` - Provider architecture overview

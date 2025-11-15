# Improvement Roadmap

Planned enhancements to the evaluation system and chatbot quality assurance.

## Overview

This roadmap outlines future improvements to evaluation methodology, metrics, and tooling for the Poolula Platform chatbot.

## Short Term (Weeks 1-4)

### 1. Enhanced Keyword Matching

**Current:** Simple case-insensitive substring matching

**Planned:** Semantic similarity scoring

**Implementation:**

- Use sentence embeddings for keyword matching
- Allow synonyms ("property" matches "real estate")
- Score based on semantic distance (0.0-1.0)

**Benefits:**

- More accurate quality scores
- Reduced false negatives
- Better handling of paraphrasing

### 2. Retrieval Metrics

**Current:** No measurement of search result quality

**Planned:** Precision and recall metrics for document retrieval

**Metrics:**

```python
Precision = relevant_results / total_results
Recall = relevant_results / total_relevant
F1 Score = 2 × (precision × recall) / (precision + recall)
```

**Implementation:**

- Add `relevant_documents` field to evaluation questions
- Track which documents were actually retrieved
- Calculate precision/recall per question

**Benefits:**

- Verify search is finding correct documents
- Detect when irrelevant documents are returned
- Optimize embedding model selection

### 3. Response Latency Tracking

**Current:** No performance metrics

**Planned:** Track response time per question and category

**Metrics:**

- Query processing time
- Tool execution time
- Total response time
- Percentiles (p50, p90, p99)

**Implementation:**

```python
{
  "question": "What is our property address?",
  "response_time_ms": 1250,
  "breakdown": {
    "query_processing": 200,
    "database_query": 50,
    "llm_generation": 1000
  }
}
```

**Benefits:**

- Identify slow queries
- Optimize performance bottlenecks
- Set latency SLOs

## Medium Term (Months 2-3)

### 4. LLM-as-Judge Scoring

**Current:** Keyword matching for response quality

**Planned:** Use GPT-4 to evaluate responses

**Methodology:**

```python
Prompt to GPT-4:
"Evaluate this response on a scale of 0-100:

Question: {question}
Expected answer should include: {context}
Actual response: {response}

Score based on:
- Accuracy (40%)
- Completeness (30%)
- Clarity (20%)
- Relevance (10%)

Return JSON: {score: int, reasoning: str}"
```

**Benefits:**

- Nuanced quality assessment
- Understands paraphrasing and synonyms
- Can detect hallucinations
- Evaluates explanation quality

**Challenges:**

- Cost (API calls per question)
- Latency (slower than keyword matching)
- Consistency (LLM outputs vary)

**Mitigation:**

- Run LLM-as-judge weekly, not per-commit
- Use GPT-4-mini for cost savings
- Average multiple runs for consistency

### 5. User Feedback Integration

**Current:** No production feedback loop

**Planned:** Collect and analyze user feedback

**Implementation:**

- Add thumbs up/down to chatbot UI
- Optional comment field for poor responses
- Log feedback to database

**Metrics:**

```python
User Satisfaction = positive_feedback / total_feedback
Feedback Rate = total_feedback / total_queries
```

**Dashboard:**

- Show satisfaction by question category
- Track common complaint themes
- Correlate with evaluation scores

**Benefits:**

- Real-world quality signal
- Identify gaps in golden question set
- Prioritize improvements

### 6. Continuous Evaluation

**Current:** Manual evaluation runs

**Planned:** Automated nightly evaluation

**Implementation:**

```yaml
# .github/workflows/nightly-eval.yml
name: Nightly Evaluation

on:
  schedule:
    - cron: "0 2 * * *"  # 2 AM daily

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - name: Run evaluation
        run: python scripts/evaluate_chatbot.py

      - name: Store results
        run: |
          DATE=$(date +%Y%m%d)
          cp results.json results/eval_$DATE.json

      - name: Check regression
        run: python scripts/check_regression.py

      - name: Notify on failure
        if: failure()
        run: echo "Evaluation failed!" | mail -s "Eval Alert" team@poolula.com
```

**Benefits:**

- Catch regressions immediately
- Track performance trends
- Automated quality monitoring

## Long Term (Months 4-6)

### 7. A/B Testing Framework

**Goal:** Compare different configurations systematically

**Test Scenarios:**

- Prompt variations
- Tool configurations
- Embedding models
- Retrieval parameters

**Implementation:**

```python
class ABTestRunner:
    def run_test(self, config_a, config_b, questions):
        results_a = evaluate(config_a, questions)
        results_b = evaluate(config_b, questions)

        # Statistical significance test
        p_value = ttest(results_a, results_b)

        return {
            "config_a_score": mean(results_a),
            "config_b_score": mean(results_b),
            "winner": "A" if mean(results_a) > mean(results_b) else "B",
            "statistically_significant": p_value < 0.05
        }
```

**Benefits:**

- Data-driven configuration choices
- Avoid regression from "improvements"
- Systematic optimization

### 8. Golden Question Set Expansion

**Current:** 15 questions

**Target:** 50+ questions with balanced coverage

**Expansion Plan:**

| Category | Current | Target | New Questions |
|----------|---------|--------|---------------|
| property_info | 3 | 5 | +2 |
| property_financials | 3 | 6 | +3 |
| transactions | 3 | 8 | +5 |
| documents | 2 | 5 | +3 |
| formation | 1 | 3 | +2 |
| aggregations | 1 | 5 | +4 |
| compliance | 1 | 5 | +4 |
| hybrid | 1 | 8 | +7 |
| governance | 0 | 3 | +3 |
| tax | 0 | 5 | +5 |

**Sources:**

- User query logs (when available)
- Sample questions document (133 questions)
- Stakeholder interviews
- Edge cases discovered in testing

**Benefits:**

- Better coverage of use cases
- More robust quality signal
- Catch edge cases

### 9. Multi-Model Comparison

**Goal:** Compare different LLM backends

**Models to Test:**

- GPT-4 (current)
- GPT-4-mini (cost optimization)
- Claude 3.5 Sonnet (alternative)
- Claude 3 Haiku (speed optimization)

**Evaluation Matrix:**

| Model | Score | Latency | Cost/1K | Use Case |
|-------|-------|---------|---------|----------|
| GPT-4 | TBD | TBD | $0.03 | Production |
| GPT-4-mini | TBD | TBD | $0.015 | Cost-optimized |
| Claude Sonnet | TBD | TBD | $0.015 | Alternative |
| Claude Haiku | TBD | TBD | $0.0008 | Speed-optimized |

**Implementation:**

- Pluggable LLM backend
- Run evaluation against all models
- Compare quality vs cost vs speed trade-offs

### 10. Hallucination Detection

**Goal:** Identify when AI makes up information

**Approach:**

- Source attribution checking
- Fact verification against database
- Confidence scoring

**Implementation:**

```python
def detect_hallucination(response, sources):
    # Extract claims from response
    claims = extract_claims(response)

    for claim in claims:
        # Check if claim is supported by sources
        supported = verify_claim_in_sources(claim, sources)

        if not supported:
            return {
                "hallucination_detected": True,
                "unsupported_claim": claim
            }

    return {"hallucination_detected": False}
```

**Scoring:**

- Penalize responses with hallucinations
- Add to evaluation metrics

## Future Research

### Advanced Metrics

**Semantic similarity scoring:**

- Use embedding similarity instead of keyword matching
- BERT-score or similar metric

**Answer equivalence:**

- Recognize semantically equivalent answers
- "900 S 9th St" vs "900 South Ninth Street"

**Factual consistency:**

- Verify numerical values match database
- Cross-reference dates and amounts

### Evaluation UI

**Interactive dashboard:**

- Visual performance trends
- Drill-down by category
- Compare evaluation runs
- Annotate failed questions

**Screenshot mockup:**

```
┌─────────────────────────────────────────┐
│ Evaluation Dashboard                    │
├─────────────────────────────────────────┤
│ Overall Score: 87.3% ▲ +2.1%           │
│                                         │
│ [Chart: Score trend over time]          │
│                                         │
│ Category Breakdown:                     │
│ ▓▓▓▓▓▓▓▓▓▓ property_info    100%       │
│ ▓▓▓▓▓▓▓▓▓░ property_fin     93%        │
│ ▓▓▓▓▓▓░░░░ compliance       67% ⚠️      │
│                                         │
│ Failed Questions (2):                   │
│ • [compliance] LLC report deadline      │
│ • [transactions] Monthly breakdown      │
└─────────────────────────────────────────┘
```

## Implementation Priorities

### High Priority (Next Quarter)

1. ✅ Enhanced keyword matching (semantic similarity)
2. ✅ Retrieval metrics (precision/recall)
3. ✅ Response latency tracking

**Rationale:** Low-hanging fruit, high impact on quality insight.

### Medium Priority (Q2 2025)

1. ✅ LLM-as-judge scoring
2. ✅ User feedback integration
3. ✅ Continuous evaluation (CI/CD)

**Rationale:** Adds production-grade quality monitoring.

### Low Priority (Q3 2025+)

1. ⏳ A/B testing framework
2. ⏳ Multi-model comparison
3. ⏳ Hallucination detection

**Rationale:** Advanced features for optimization and research.

## Success Metrics

### Evaluation System Goals

By Q2 2025:

- ✅ Automated daily evaluation runs
- ✅ User feedback integrated
- ✅ Latency SLOs defined and tracked
- ✅ Retrieval quality metrics baseline established

By Q3 2025:

- ✅ LLM-as-judge scoring operational
- ✅ 50+ golden questions
- ✅ A/B testing framework ready
- ✅ Multi-model comparison completed

### Chatbot Quality Goals

By Q2 2025:

- Overall score ≥ 90%
- All categories ≥ 80%
- p95 latency < 3 seconds
- User satisfaction ≥ 85%

## Related Documentation

- [Evaluation Harness](harness.md) - Current system
- [Scoring Methodology](scoring.md) - How scoring works
- [Results & Baselines](results.md) - Current performance
- [Implementation Plan](../planning/2025-11-13-revised-implementation-plan.md) - Overall project roadmap

# Provider Qualitative Testing Checklist

Beyond automated scoring, this checklist helps you manually verify provider quality across dimensions that are difficult to automate.

## Purpose

The automated evaluation (`scripts/evaluate_providers.py`) tests:
- Tool calling correctness (40% weight)
- Keyword matching (40% weight)
- Error handling (20% weight)

**This checklist tests:**
- Hallucinations (AI making up facts)
- Response tone and professionalism
- Edge case handling
- Context management (multi-turn conversations)

---

## How to Use This Checklist

1. **Run automated evaluation first:** Get quantitative baseline
2. **Use this checklist for qualitative validation:** Catch issues automation misses
3. **Document findings:** Add notes to comparison report
4. **Prioritize high-stakes queries:** Focus on financial/legal questions

**Testing Frequency:**
- **Initial provider adoption:** Full checklist
- **After provider updates:** Spot check critical queries
- **Quarterly review:** Random sample of 5-10 queries

---

## Checklist Sections

### 1. Tool Calling Correctness

#### Test 1.1: Database Tool Usage

**Query:** "What is our property address?"

**Expected Behavior:**
- ✅ Calls `query_database` tool
- ✅ SQL query is well-formed
- ✅ Results incorporated into response

**Red Flags:**
- ❌ Uses document search instead of database
- ❌ Makes up address without calling tools
- ❌ SQL query has syntax errors

**Provider Results:**

| Provider | Tool Called | SQL Valid | Result Used | Pass/Fail |
|----------|-------------|-----------|-------------|-----------|
| Anthropic | query_database | ✅ | ✅ | ✅ |
| OpenAI | query_database | ✅ | ✅ | ✅ |
| Ollama | query_database | ✅ | ✅ | ✅ |

**Notes:**
_Add observations here_

---

#### Test 1.2: Document Search Usage

**Query:** "What is the business purpose of Poolula LLC?"

**Expected Behavior:**
- ✅ Calls `search_document_content` tool
- ✅ Search query is semantically relevant
- ✅ Quotes or paraphrases from documents

**Red Flags:**
- ❌ Uses database instead of document search
- ❌ Makes up business purpose
- ❌ Search query is malformed or irrelevant

**Provider Results:**

| Provider | Tool Called | Query Relevant | Quotes Docs | Pass/Fail |
|----------|-------------|----------------|-------------|-----------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add observations here_

---

#### Test 1.3: Multi-Round Tool Calling

**Query:** "Show me documents related to insurance, then tell me the coverage amount"

**Expected Behavior:**
- ✅ Round 1: Calls `list_business_documents` or `search_document_content`
- ✅ Round 2: Uses document results to extract coverage amount
- ✅ Final response synthesizes findings

**Red Flags:**
- ❌ Only uses one tool (misses multi-round opportunity)
- ❌ Doesn't use results from first tool in second round
- ❌ Hallucinates coverage amount

**Provider Results:**

| Provider | Tools Used | Multi-Round | Correct Amount | Pass/Fail |
|----------|------------|-------------|----------------|-----------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add observations here_

---

### 2. Response Quality

#### Test 2.1: No Hallucinations

**Query:** "What is the market value of our property?"

**Expected Behavior:**
- ✅ Recognizes data not available in sources
- ✅ States "I don't have market value data" or similar
- ✅ May offer alternative data (acquisition price, basis)

**Red Flags:**
- ❌ Makes up a market value figure
- ❌ Uses acquisition price without clarification
- ❌ Provides outdated valuation without disclaimer

**Provider Results:**

| Provider | Hallucinated? | Clarified Unavailable Data? | Pass/Fail |
|----------|---------------|----------------------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Actual Responses:**

**Anthropic:**
```
[Record response here]
```

**OpenAI:**
```
[Record response here]
```

**Ollama:**
```
[Record response here]
```

---

#### Test 2.2: Professional Tone

**Query:** "Tell me about our LLC"

**Expected Behavior:**
- ✅ Professional, businesslike tone
- ✅ Factual, no unnecessary embellishment
- ✅ No informal language or slang

**Red Flags:**
- ❌ Overly casual ("your cool LLC", "awesome property")
- ❌ Marketing speak ("best-in-class", "premier")
- ❌ Emotional language ("exciting", "unfortunate")

**Provider Results:**

| Provider | Professional? | Factual? | Appropriate | Pass/Fail |
|----------|---------------|----------|-------------|-----------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add tone observations here_

---

#### Test 2.3: No Meta-Commentary

**Query:** "What was rental income in August 2024?"

**Expected Behavior:**
- ✅ Direct answer: "Rental income in August 2024 was $X"
- ✅ May include context (source, calculation)

**Red Flags:**
- ❌ "Based on my search of the database..."
- ❌ "According to the tool results..."
- ❌ "Let me look that up for you..."

**Provider Results:**

| Provider | Direct Answer | No Meta-Commentary | Pass/Fail |
|----------|---------------|--------------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Notes:**
_Add observations here_

---

#### Test 2.4: Appropriate Detail Level

**Query:** "What is our EIN?"

**Expected Behavior:**
- ✅ Concise: "Your EIN is XX-XXXXXXX"
- ✅ May add brief context if relevant

**Red Flags:**
- ❌ Overly verbose (paragraph about what an EIN is)
- ❌ Too terse ("12345678" without label)

**Provider Results:**

| Provider | Concise? | Sufficient? | Appropriate | Pass/Fail |
|----------|----------|-------------|-------------|-----------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add observations here_

---

### 3. Edge Cases

#### Test 3.1: No Results Found

**Query:** "Show me transactions from 2020" (assuming no 2020 transactions)

**Expected Behavior:**
- ✅ "I don't see any transactions from 2020"
- ✅ May offer alternative ("earliest transaction is from 2022")
- ✅ Doesn't apologize excessively

**Red Flags:**
- ❌ Makes up transactions
- ❌ Returns error message unformatted
- ❌ Overly apologetic ("I'm so sorry I couldn't find...")

**Provider Results:**

| Provider | Graceful Handling | No Fabrication | Pass/Fail |
|----------|-------------------|----------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Notes:**
_Add observations here_

---

#### Test 3.2: Ambiguous Queries

**Query:** "Tell me about the property"

**Expected Behavior:**
- ✅ Clarifies if multiple properties exist
- ✅ Returns info about single property if only one
- ✅ Doesn't assume user intent

**Red Flags:**
- ❌ Returns info about wrong property
- ❌ Combines data from multiple properties without clarification
- ❌ Ignores ambiguity entirely

**Provider Results:**

| Provider | Clarified Ambiguity | Correct Handling | Pass/Fail |
|----------|---------------------|------------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Notes:**
_Add observations here_

---

#### Test 3.3: Out-of-Scope Queries

**Query:** "What is the weather in Montrose today?"

**Expected Behavior:**
- ✅ "I don't have access to weather data"
- ✅ Stays in scope (Poolula business data only)

**Red Flags:**
- ❌ Attempts to answer (hallucinates weather)
- ❌ Calls inappropriate tools (database, document search)

**Provider Results:**

| Provider | Stayed in Scope | Clear Boundary | Pass/Fail |
|----------|-----------------|----------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Notes:**
_Add observations here_

---

### 4. Performance

#### Test 4.1: Response Latency

**Query:** Run 10 varied queries, measure time

**Target:**
- Cloud providers (Anthropic, OpenAI): <5s typical, <10s worst case
- Local provider (Ollama): <15s typical, <30s worst case

**Provider Results:**

| Provider | Min (s) | Median (s) | Max (s) | Acceptable? |
|----------|---------|------------|---------|-------------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add latency observations here_

---

#### Test 4.2: Timeout Failures

**Query:** Run 20 queries, count timeouts

**Target:** <5% timeout rate

**Provider Results:**

| Provider | Total Queries | Timeouts | Rate | Pass/Fail |
|----------|---------------|----------|------|-----------|
| Anthropic | 20 | | | |
| OpenAI | 20 | | | |
| Ollama | 20 | | | |

**Notes:**
_Add timeout patterns here_

---

### 5. Context Handling (Multi-Turn Conversations)

#### Test 5.1: Follow-Up Questions

**Turn 1:** "What properties does Poolula LLC own?"
**Turn 2:** "When was it acquired?"

**Expected Behavior:**
- ✅ Interprets "it" as referring to the property from Turn 1
- ✅ Provides acquisition date without needing property name repeated

**Red Flags:**
- ❌ "What property are you referring to?" (lost context)
- ❌ Returns acquisition dates for all properties
- ❌ Errors out

**Provider Results:**

| Provider | Maintained Context | Correct Referent | Pass/Fail |
|----------|-------------------|------------------|-----------|
| Anthropic | | | |
| OpenAI | | | |
| Ollama | | | |

**Notes:**
_Add context handling observations here_

---

#### Test 5.2: Multi-Turn Tool Usage

**Turn 1:** "List our business documents"
**Turn 2:** "Show me the operating agreement"
**Turn 3:** "What's the effective date?"

**Expected Behavior:**
- ✅ Turn 1: Calls `list_business_documents`
- ✅ Turn 2: Calls `search_document_content` with "operating agreement"
- ✅ Turn 3: Extracts effective date from Turn 2 results

**Red Flags:**
- ❌ Repeats Turn 1 search in Turn 2
- ❌ Loses document context by Turn 3
- ❌ Fabricates effective date

**Provider Results:**

| Provider | Turn 1 OK | Turn 2 OK | Turn 3 OK | Pass/Fail |
|----------|-----------|-----------|-----------|-----------|
| Anthropic | | | | |
| OpenAI | | | | |
| Ollama | | | | |

**Notes:**
_Add multi-turn observations here_

---

## Summary & Recommendations

### Overall Assessment

| Provider | Tool Calling | Response Quality | Edge Cases | Performance | Context | Overall |
|----------|--------------|------------------|------------|-------------|---------|---------|
| Anthropic | | | | | | |
| OpenAI | | | | | | |
| Ollama | | | | | | |

**Rating Scale:**
- ✅ Excellent (no issues)
- ⚠️ Acceptable (minor issues)
- ❌ Poor (significant issues)

### Key Findings

**Strengths by Provider:**

**Anthropic:**
_List strengths here_

**OpenAI:**
_List strengths here_

**Ollama:**
_List strengths here_

**Weaknesses by Provider:**

**Anthropic:**
_List weaknesses here_

**OpenAI:**
_List weaknesses here_

**Ollama:**
_List weaknesses here_

### Recommendations

**For Production Use:**
_Which provider(s) are production-ready?_

**For Experimentation:**
_Which provider(s) are suitable for testing?_

**Areas for Improvement:**
1. _What needs fixing?_
2. _Which providers need prompt tuning?_
3. _What evaluation gaps exist?_

---

## Next Steps

1. **Document findings:** Add summary to `docs/architecture/llm-providers.md`
2. **Address issues:** Tune prompts, adjust tools, update system prompt
3. **Re-test:** Run checklist again after changes
4. **Track over time:** Re-run quarterly or after provider updates

---

## Related Documentation

- `docs/evaluation/provider-comparison.md` - How to run automated comparisons
- `docs/evaluation/harness.md` - Evaluation system design
- `docs/workflows/llm-provider-setup.md` - Provider configuration
- `docs/architecture/llm-providers.md` - Provider architecture

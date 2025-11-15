# Scoring Methodology

The evaluation harness uses a three-component scoring system to assess chatbot response quality.

## Overview

Each response receives a score from 0.0 to 1.0 (0% to 100%) based on three weighted components:

```
Final Score = (Tool Usage × 0.40) + (Response Quality × 0.40) + (Error Handling × 0.20)
```

### Component Weights

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Tool Usage | 40% | Correct tool selection is critical for accuracy |
| Response Quality | 40% | Answer must contain expected information |
| Error Handling | 20% | System must be reliable and not crash |

## Component 1: Tool Usage (40%)

### What It Measures

Whether the AI correctly selected the appropriate search tools for the question type.

### Scoring Logic

```python
def score_tool_usage(expected_tools: List[str], tools_used: List[str]) -> float:
    """
    Returns 1.0 if all expected tools were used, 0.0 otherwise
    """
    if not expected_tools:
        return 1.0  # No tools required

    # Check if all expected tools are present
    all_tools_used = all(tool in tools_used for tool in expected_tools)

    return 1.0 if all_tools_used else 0.0
```

### Tool Categories

**Available tools:**

1. **`query_database`**

   - For: Properties, transactions, obligations, documents metadata
   - When: Structured data queries
   - Example: "What was my rental income in August?"

2. **`search_document_content`**

   - For: Searching within ingested documents
   - When: Semantic search for specific information
   - Example: "What's our business purpose in the operating agreement?"

3. **`list_business_documents`**
   - For: Document discovery
   - When: User wants to see what documents exist
   - Example: "What documents do we have?"

### Examples

**Example 1: Correct Tool Selection**

```python
Question: "What is our property address?"
Expected: ["query_database"]
AI used: ["query_database"]
Tool score: 1.0 ✓
```

**Example 2: Missing Tool**

```python
Question: "What's in our operating agreement?"
Expected: ["search_document_content"]
AI used: []  # AI tried to answer without searching
Tool score: 0.0 ✗
```

**Example 3: Wrong Tool**

```python
Question: "List all our documents"
Expected: ["list_business_documents"]
AI used: ["query_database"]  # Wrong tool
Tool score: 0.0 ✗
```

**Example 4: Hybrid Query**

```python
Question: "What properties do we own and what documents mention them?"
Expected: ["query_database", "search_document_content"]
AI used: ["query_database", "search_document_content"]
Tool score: 1.0 ✓
```

### Why Tool Usage Matters

**Accuracy:** Using the right tool determines answer correctness.

- Database query for "rental income" → precise numbers
- Document search for "business purpose" → exact wording from docs

**Efficiency:** Correct tool selection minimizes response time.

- Don't search documents for structured data
- Don't query database for unstructured document content

**Capability demonstration:** Shows the AI understands tool purposes.

## Component 2: Response Quality (40%)

### What It Measures

Whether the response contains the expected information based on keyword matching.

### Scoring Logic

```python
def score_response_quality(expected_keywords: List[str], response: str) -> float:
    """
    Returns ratio of expected keywords found in response (case-insensitive)
    """
    if not expected_keywords:
        return 1.0  # No keywords required

    response_lower = response.lower()
    keywords_found = sum(
        1 for keyword in expected_keywords
        if keyword.lower() in response_lower
    )

    return keywords_found / len(expected_keywords)
```

### Keyword Selection Guidelines

**Good keywords:**

- Specific values: "442300", "83-4567890", "900"
- Key concepts: "depreciation", "basis", "rental income"
- Critical terms: "Montrose", "CO", "August"

**Avoid:**

- Common words: "the", "and", "is"
- Generic terms: "property", "LLC" (unless specifically testing for these)
- Ambiguous words that could appear in any response

### Examples

**Example 1: Perfect Match**

```python
Question: "What is our property address?"
Expected keywords: ["900", "9th", "Montrose", "CO"]
Response: "Your property is located at 900 S 9th St, Montrose, CO 81401"

Keywords found: 4/4
Quality score: 1.0 (100%)
```

**Example 2: Partial Match**

```python
Question: "What is our property's total basis?"
Expected keywords: ["basis", "depreciation", "442300", "land", "building"]
Response: "The total basis for your property is $442,300, which includes the land and building components."

Keywords found: 4/5 (missing "depreciation")
Quality score: 0.8 (80%)
```

**Example 3: Poor Match**

```python
Question: "What was my rental income in August 2024?"
Expected keywords: ["August", "2024", "rental", "income", "16144"]
Response: "I found some transaction data for you."

Keywords found: 0/5
Quality score: 0.0 (0%)
```

### Limitations of Keyword Matching

**Current approach:**

- Simple, fast, objective
- Works well for factual questions
- No false positives from irrelevant matches

**Limitations:**

- Doesn't understand synonyms ("property" vs "real estate")
- Doesn't verify logical correctness
- Can't assess explanation quality

**Future enhancement:** See [Roadmap](roadmap.md) for planned LLM-as-judge scoring.

## Component 3: Error Handling (20%)

### What It Measures

Whether the query completed successfully without crashes or error responses.

### Scoring Logic

```python
def score_error_handling(error: Optional[str]) -> float:
    """
    Returns 1.0 if no error, 0.0 if error occurred
    """
    return 0.0 if error else 1.0
```

### Error Types Detected

**System errors:**

- Database connection failures
- Tool execution exceptions
- API timeout errors
- Memory errors

**Response errors:**

- Empty responses
- Null values
- Error messages in response text
- Exception traces

### Examples

**Example 1: Success**

```python
Response: "Your property is located at 900 S 9th St..."
Error: None
Error score: 1.0 ✓
```

**Example 2: Database Error**

```python
Response: None
Error: "DatabaseError: Connection refused"
Error score: 0.0 ✗
```

**Example 3: Tool Error**

```python
Response: "I encountered an error while searching..."
Error: "ToolExecutionError: Document not found"
Error score: 0.0 ✗
```

### Why Error Handling Matters

**Reliability:** System must be robust for production use.

**User experience:** Crashes frustrate users and reduce trust.

**Production readiness:** Error handling is critical for deployed applications.

## Composite Scoring

### Calculation Example

**Question:** "What is our property's total depreciable basis?"

**Results:**

- Tool usage: 1.0 (used `query_database` as expected)
- Response quality: 0.8 (4/5 keywords found)
- Error handling: 1.0 (no errors)

**Final score:**

```
Score = (1.0 × 0.40) + (0.8 × 0.40) + (1.0 × 0.20)
      = 0.40 + 0.32 + 0.20
      = 0.92 (92%)
```

### Score Interpretation

| Score Range | Grade | Interpretation |
|-------------|-------|----------------|
| 90-100% | A | Excellent response |
| 80-89% | B | Good response, minor issues |
| 70-79% | C | Acceptable, needs improvement |
| 60-69% | D | Below acceptable, investigation needed |
| 0-59% | F | Poor response, significant issues |

### Aggregate Metrics

**Overall performance:**

```
Overall Score = (Sum of all question scores) / (Total questions)
```

**Category performance:**

```
Category Score = (Sum of category question scores) / (Questions in category)
```

## Comparison to Traditional Testing

### Unit Tests

**Traditional:**

```python
def test_get_property():
    response = api.get_property("property-id")
    assert response.address == "900 S 9th St"  # Exact match
```

**Evaluation harness:**

```python
# Question: "What is our property address?"
# Expected keywords: ["900", "9th", "Montrose"]
# Score: 0.0-1.0 based on keyword presence
# More flexible, accounts for variation
```

### Why This Approach?

**LLM outputs vary:** Same query can produce different valid responses.

**Multiple correct answers:** Various phrasings can be equally correct.

**Graceful degradation:** Partial answers get partial credit.

**Realistic assessment:** Reflects actual user experience.

## Limitations and Future Improvements

### Current Limitations

1. **Keyword matching is simplistic**

   - Doesn't understand synonyms
   - Can't verify logical consistency
   - Misses semantic equivalence

2. **Binary tool scoring**

   - No credit for using some correct tools
   - Doesn't account for extra tools (as long as expected ones are present)

3. **No retrieval quality metrics**
   - Doesn't verify sources are relevant
   - Can't detect hallucinations
   - No precision/recall for search results

### Planned Improvements

See [Improvement Roadmap](roadmap.md):

- **LLM-as-judge scoring** for nuanced evaluation
- **Retrieval metrics** (precision, recall, NDCG)
- **Latency tracking** per question
- **User feedback integration**
- **A/B testing framework**

## Related Documentation

- [Evaluation Harness](harness.md) - How to run evaluations
- [Question Design](questions.md) - Question selection criteria
- [Results & Baselines](results.md) - Current performance metrics

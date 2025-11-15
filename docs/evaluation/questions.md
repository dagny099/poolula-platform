# Question Design

The golden question set is carefully designed to test core chatbot capabilities across different query types and data sources.

## Question Selection Criteria

### 1. Representative Coverage

Questions cover the main use cases from four user personas:

- New LLC Owner (compliance, getting started)
- Bookkeeper (financial records, accounting)
- Property Manager (operations, maintenance)
- Tax Preparer (basis, depreciation, deductions)

### 2. Tool Diversity

Questions test different tool combinations:

- Database-only queries
- Document-only queries
- Hybrid queries (database + documents)
- List/discovery queries

### 3. Realistic Scenarios

All questions reflect actual business needs:

- Compliance deadlines
- Financial reporting
- Property information
- Document searches

## Golden Question Set

**Location:** `data/poolula_eval_set.jsonl`

**Total Questions:** 15

### Category Breakdown

| Category | Count | Description |
|----------|-------|-------------|
| `property_info` | 3 | Basic property information |
| `property_financials` | 3 | Property basis and depreciation |
| `transactions` | 3 | Transaction queries and filtering |
| `documents` | 2 | Document search and discovery |
| `formation` | 1 | LLC formation details |
| `aggregations` | 1 | Financial aggregations |
| `compliance` | 1 | Compliance requirements |
| `hybrid` | 1 | Multi-source queries |

## Question Examples

### Property Information

**Question:** "What is our property address?"

**Category:** `property_info`

**Expected Tools:**

- `query_database`

**Expected Keywords:**

- "900"
- "9th"
- "Montrose"
- "CO"

**Why this matters:** Tests basic database retrieval of property information.

---

### Property Financials

**Question:** "What is our property's total depreciable basis?"

**Category:** `property_financials`

**Expected Tools:**

- `query_database`

**Expected Keywords:**

- "basis"
- "depreciation"
- "442300"

**Why this matters:** Tests ability to query financial data and perform calculations.

---

### Transactions

**Question:** "What was my rental income in August 2024?"

**Category:** `transactions`

**Expected Tools:**

- `query_database`

**Expected Keywords:**

- "August"
- "2024"
- "rental"
- "income"

**Why this matters:** Tests date-based filtering and category queries.

---

### Documents

**Question:** "What documents are in our knowledge base?"

**Category:** `documents`

**Expected Tools:**

- `list_business_documents`

**Expected Keywords:**

- "documents"
- "Articles"
- "Operating Agreement"

**Why this matters:** Tests document discovery functionality.

---

### Hybrid Queries

**Question:** "What is the business purpose stated in our LLC formation documents?"

**Category:** `hybrid`

**Expected Tools:**

- `search_document_content`
- `query_database` (optional)

**Expected Keywords:**

- "business purpose"
- "rental"
- "property"

**Why this matters:** Tests ability to search documents for specific information.

## JSONL Format

Each question is a single-line JSON object:

```json
{
  "question": "What is our property address?",
  "category": "property_info",
  "expected_tools": ["query_database"],
  "expected_keywords": ["900", "9th", "Montrose", "CO"],
  "context": "Tests basic property information retrieval from database"
}
```

### Field Descriptions

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `question` | Yes | The user query | "What is our EIN?" |
| `category` | Yes | Question category | "formation" |
| `expected_tools` | Yes | Tools AI should use | ["query_database"] |
| `expected_keywords` | Yes | Keywords in response | ["83", "4567890"] |
| `context` | No | Why question matters | "Tests EIN retrieval" |

## Question Design Principles

### 1. Specificity

**Good:** "What was my rental income in August 2024?"

- Clear time period
- Specific category
- Measurable answer

**Bad:** "Tell me about my finances"

- Too vague
- Multiple valid answers
- Hard to score

### 2. Single Concept

**Good:** "What is our property's land basis?"

- One piece of information
- Clear expected answer
- Single tool needed

**Bad:** "What is our property's land basis, building basis, and total depreciation schedule?"

- Multiple concepts
- Complex answer
- Hard to score components

### 3. Realistic Language

Use natural phrasing that actual users would employ:

**Natural:** "What's our EIN number?"

**Unnatural:** "Query the database for the employer identification number field"

### 4. Testable Outcomes

Ensure questions have verifiable answers:

**Verifiable:** "What is our property address?"

- Expected: "900 S 9th St, Montrose, CO"
- Can check for keywords: "900", "9th", "Montrose"

**Not verifiable:** "Is our property in a good location?"

- Subjective answer
- No clear keywords
- Opinion-based

## Adding New Questions

### Step 1: Identify Gap

Review current coverage and identify missing scenarios:

```bash
# Count questions by category
cat data/poolula_eval_set.jsonl | jq -r '.category' | sort | uniq -c

# Look for underrepresented categories
```

### Step 2: Write Question

Follow the design principles above:

```json
{
  "question": "When is our annual LLC filing due in Colorado?",
  "category": "compliance",
  "expected_tools": ["search_document_content"],
  "expected_keywords": ["annual", "report", "Colorado", "periodic"],
  "context": "Tests ability to find compliance deadlines in documents"
}
```

### Step 3: Validate Answer

Test the question manually before adding:

```bash
# Start API server
uv run uvicorn apps.api.main:app --reload --port 8082

# Ask the question via frontend
# Verify response is correct
```

### Step 4: Add to Set

```bash
# Append to JSONL file
echo '{"question": "...", ...}' >> data/poolula_eval_set.jsonl

# Run evaluation to get baseline
python scripts/evaluate_chatbot.py
```

## Question Maintenance

### When to Update Questions

**Add questions when:**

- New features are added (new tools, data sources)
- Coverage gaps are identified
- User feedback reveals untested scenarios

**Update questions when:**

- Expected keywords change due to data updates
- Tool definitions change
- Question wording is unclear

**Remove questions when:**

- Feature is deprecated
- Question is no longer relevant
- Duplicate coverage exists

### Version Control

Track changes to the question set:

```bash
# Commit changes with context
git add data/poolula_eval_set.jsonl
git commit -m "Add 3 compliance deadline questions

- Test annual report deadline lookup
- Test business license renewal
- Test tax filing deadlines

Increases compliance category coverage from 1 to 4 questions."
```

## Full Question List

See the complete set in `data/poolula_eval_set.jsonl`:

```bash
# View all questions
cat data/poolula_eval_set.jsonl | jq -r '.question'

# View by category
cat data/poolula_eval_set.jsonl | jq -r 'select(.category=="property_info") | .question'
```

## Statistical Analysis

### Category Distribution

```bash
# Count by category
cat data/poolula_eval_set.jsonl | jq -r '.category' | sort | uniq -c | sort -rn

# Output:
#   3 property_financials
#   3 property_info
#   3 transactions
#   2 documents
#   1 formation
#   1 aggregations
#   1 compliance
#   1 hybrid
```

### Tool Usage Distribution

```bash
# Count expected tool usage
cat data/poolula_eval_set.jsonl | jq -r '.expected_tools[]' | sort | uniq -c

# Output:
#  12 query_database
#   3 search_document_content
#   1 list_business_documents
```

### Keyword Complexity

```bash
# Average keywords per question
cat data/poolula_eval_set.jsonl | jq -r '.expected_keywords | length' | \
  awk '{sum+=$1} END {print "Average:", sum/NR}'

# Output:
# Average: 4.2 keywords per question
```

## Related Documentation

- [Evaluation Harness](harness.md) - How evaluation works
- [Scoring Methodology](scoring.md) - How questions are scored
- [Sample Questions](../sample-questions.md) - 133 additional questions for reference

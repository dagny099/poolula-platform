# Poolula Platform - Implementation Plan
**Date:** November 14, 2024
**Status:** Approved - Ready for execution

---

## Project Vision

### Short-Term Goal (Current Sprint)
Build a verifiable Q&A system for Poolula LLC that:
- Answers transaction questions from Airbnb CSV data
- Answers LLC compliance questions from formation documents
- Provides verified, cited answers with strong evaluation harness (≥90% accuracy)
- Beautiful vanilla JavaScript frontend with persona-based help

### Long-Term Goal
Consolidated document/data hub for rental property business management:
- Natural language queries across all business data
- Automated categorization and insights
- Tax report generation (Schedule E, P&L, cash flow)
- Compliance tracking with deadline alerts
- Maintained through rigorous evaluation and verification

---

## Strategic Direction

### What We're Building
- ✅ **Transaction Analysis** (Level 1 + some Level 2)
  - Basic queries: "What was my revenue in August 2025?"
  - Aggregations: "Show expenses by category"
  - NOT building: Full accounting system, complex forecasting

- ✅ **LLC Compliance Q&A**
  - Document-based queries from formation docs
  - Business purpose, authority, depreciation schedules
  - Obligation tracking (deadlines, renewals)

- ✅ **Verification & Evaluation**
  - Strong evaluation harness with 40+ golden questions
  - Multi-dimensional scoring (semantic, numerical, citation accuracy)
  - Transparent reporting dashboard
  - Continuous improvement through evaluation

### What We're NOT Building
- ❌ Complex accounting software (use QuickBooks for that)
- ❌ Multi-property support (single property focus)
- ❌ Payment processing or tenant CRM
- ❌ Replacement for CPA or attorney

### Core Principle
**"Verifiable answers through rigorous evaluation, not just automation"**

---

## Implementation Timeline

## Week 0 (Day 0): README Revision & Approval

### Task: Rewrite README.md
**Before any implementation starts, rewrite README to be:**
- Clear, technical documentation (NO marketing language)
- Short-term goals: Transaction analysis + LLC compliance Q&A with verification
- Long-term goals: Consolidated document/data hub with natural language queries
- Core business models: Property, Transaction, Document, Obligation, Provenance
- Key API endpoints: chat/query, transactions, documents, properties, obligations
- Dataflow diagram: CSV import → DB storage → RAG queries → Verified answers
- Remove ALL references to ragchatbot-codebase

**Deliverable:** Clean, technical README for review

**→ WAIT FOR APPROVAL BEFORE PROCEEDING TO WEEK 1**

---

## Week 1: Foundation & Core Setup (Day 1-5)

### Day 1: Directory Restructure & Data Organization

**Tasks:**
1. Create new directory structure:
   ```
   poolula-platform/
   ├── data/
   │   ├── templates/              # ✅ IN GIT
   │   │   ├── airbnb_template.csv
   │   │   └── expenses_template.csv
   │   ├── imports/                # ❌ NOT IN GIT
   │   │   ├── airbnb/
   │   │   │   ├── 2024/
   │   │   │   └── 2025/
   │   │   ├── expenses/
   │   │   └── .gitkeep
   │   ├── documents/              # ❌ NOT IN GIT
   │   │   ├── formation/          # Articles, Operating Agreement
   │   │   ├── authority/          # Statement of Authority
   │   │   ├── property/           # Deed, title docs
   │   │   ├── insurance/          # Policy documents
   │   │   ├── banking/            # Account docs
   │   │   ├── tax/                # Tax returns, basis calculations
   │   │   └── .gitkeep
   │   └── processed/              # ❌ NOT IN GIT
   │       ├── documents_metadata.csv
   │       └── ingestion_log.json
   ```

2. Update .gitignore:
   ```
   /data/imports/**
   !/data/imports/.gitkeep
   /data/documents/**
   !/data/documents/**/.gitkeep
   /data/processed/**
   !/data/processed/.gitkeep
   chroma_db/
   *.db
   *.db-*
   ```

3. Move existing files to new structure
4. Create .gitkeep files in tracked empty directories

**Deliverables:**
- Clean directory structure
- Proper .gitignore (no sensitive data in git)
- Existing files migrated

---

### Day 2: Fix ChromaDB Bug

**Tasks:**
1. Locate ChromaDB where clause bug in `apps/chatbot/vector_store.py` (around line 196)
2. Fix: Replace `$contains` operator with correct ChromaDB operator
3. Test document search queries
4. Document the fix and what it solved

**Background:**
Current error: `Expected where operator to be one of $gt, $gte, $lt, $lte, $ne, $eq, $in, $nin, got $contains`

**Deliverables:**
- Fixed document search
- Test results showing search works
- Documentation of fix

---

### Day 3: Document Re-ingestion

**Tasks:**
1. Copy LLC documents from ragchatbot-codebase to `data/documents/`:
   - Articles of Organization → `data/documents/formation/`
   - Operating Agreement → `data/documents/formation/`
   - Statement of Authority → `data/documents/authority/`
   - Property deed/closing docs → `data/documents/property/`
   - Insurance policies → `data/documents/insurance/`
   - Banking/accounting docs → `data/documents/banking/`
   - Tax documents → `data/documents/tax/`

2. Create `data/processed/documents_metadata.csv` with proper classifications:
   ```csv
   filename,doc_type,effective_date,confidentiality
   articles_of_organization.pdf,formation,2024-01-15,CONFIDENTIAL
   operating_agreement.pdf,formation,2024-01-20,CONFIDENTIAL
   statement_of_authority.pdf,authority,2024-01-25,INTERNAL
   ...
   ```

3. Run document ingestion script (or create if needed)
4. Verify ingestion in ChromaDB
5. Test document queries

**Documentation Required:**
- List of all documents ingested (filename, type, location)
- Storage structure explanation
- How to query documents
- How to add new documents

**Deliverables:**
- All LLC compliance documents ingested into ChromaDB
- Clear documentation of what was ingested and where
- Tested document queries

---

### Day 4: Frontend Integration

**Tasks:**
1. Copy `frontend/` folder from ragchatbot-codebase:
   - `index.html`
   - `script.js`
   - `style.css`
   - `favicon.svg` (replace with Poolula logo if available)

2. Adapt 4 personas in `index.html` (lines 48-97):

   **Property Owner:**
   - "What was my rental income in August 2025?"
   - "How many reservations did I have in September 2025?"
   - "What's my LLC's business purpose?"

   **Accountant/Bookkeeper:**
   - "What's my depreciable basis for the property?"
   - "Show me all expense categories"
   - "When was the property placed in service?"

   **Property Manager:**
   - "Show me all Airbnb service fees paid in 2025"
   - "What are my cleaning fee totals?"
   - "List all reservation dates"

   **Tax Preparer:**
   - "Show deductible expenses by category"
   - "What depreciation schedule should I use?"
   - "Export transactions for tax filing"

3. Update `script.js` API endpoints:
   ```javascript
   // Change from:
   POST /api/query
   GET  /api/documents

   // To:
   POST /api/v1/chat/query
   GET  /api/v1/documents
   ```

4. Wire up FastAPI in `apps/api/main.py`:
   ```python
   # Serve static frontend files
   app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

   # Chat endpoint
   @app.post("/api/v1/chat/query")
   async def chat_query(query: ChatQuery):
       response, sources = rag_system.query(query.query, session_id=query.session_id)
       return {"answer": response, "sources": sources, "session_id": query.session_id}
   ```

5. Test basic chat functionality

**Deliverables:**
- Working web UI at http://localhost:8082
- All 4 personas with adapted questions
- Chat integration working

---

### Day 5: Sample Questions & Obligation Seeding

**Tasks:**
1. Create `docs/sample-questions.md` with 50+ questions organized by:
   - **Level 1 - Basic Transaction Queries (20 questions)**
     - "What was my total rental income in August 2025?"
     - "How many Airbnb reservations in July 2025?"
     - "Show me all transactions from September 2025"
     - "List all Airbnb service fees paid in Q3 2025"

   - **Level 2 - Aggregations (15 questions)**
     - "What's my total revenue by month for 2025?"
     - "Show me expenses grouped by category"
     - "What percentage of revenue goes to service fees?"
     - "How many nights were booked each month?"

   - **LLC Compliance (10 questions)**
     - "What is Poolula LLC's business purpose?"
     - "Who are the members of the LLC?"
     - "What's our depreciable basis breakdown?"
     - "When was the property placed in service?"

   - **Hybrid Queries (5 questions)**
     - "Did my August 2025 revenue match projections?"
     - "What repairs can I deduct based on the operating agreement?"

2. Create `scripts/seed_obligations.py`:
   ```python
   # Seed common obligations:
   obligations = [
       {
           "type": "COMPLIANCE",
           "description": "Colorado Periodic Report Filing",
           "due_date": "2025-06-30",  # April 1 - June 30 window
           "recurring": "annual",
           "notes": "File between April 1 and due date"
       },
       {
           "type": "TAX_FILING",
           "description": "Tax Extension Deadline",
           "due_date": "2025-04-15",
           "recurring": "annual"
       },
       {
           "type": "TAX_FILING",
           "description": "Tax Return Filing (with extension)",
           "due_date": "2025-10-15",
           "recurring": "annual"
       },
       {
           "type": "INSURANCE",
           "description": "Property Insurance Renewal",
           "due_date": "2025-05-01",
           "recurring": "annual"
       }
   ]
   ```

3. Create `docs/user-guides/managing-obligations.md`:
   - How to add new obligations
   - How to mark obligations complete
   - How to query upcoming deadlines
   - Example: "What's due this quarter?"

4. Test all personas with sample questions

**Deliverables:**
- 50+ sample questions document
- Obligation seeding script with 4 common obligations
- Written instructions for managing obligations
- Test results from all personas

---

## Week 1.5: MkDocs Pilot Setup (Day 6-7)

### Setup Essential Documentation First

**Goal:** Get MkDocs up and running with the MOST USEFUL pages for immediate use.

**Tasks:**

1. **Setup MkDocs structure:**
   ```bash
   pip install mkdocs mkdocs-material
   ```

2. **Create `mkdocs.yml`:**
   ```yaml
   site_name: Poolula Platform
   site_description: Financial Q&A system for rental property management with verified answers
   theme:
     name: material
     palette:
       - scheme: default
         primary: blue grey
         accent: blue
   nav:
     - Home: index.md
     - Getting Started:
       - Overview: getting-started/overview.md
       - Installation: getting-started/installation.md
     - User Guides:
       - Importing Airbnb Transactions: user-guides/importing-airbnb.md
       - Persona Examples: user-guides/persona-examples.md
       - Managing Obligations: user-guides/managing-obligations.md
     - Architecture:
       - Database Schema: architecture/database-schema.md
       - Data Flow: architecture/dataflow.md
   ```

3. **Create 6 essential pages:**

   **a) `docs/index.md` - Homepage**
   ```markdown
   # Poolula Platform

   Financial Q&A system for Poolula LLC with verified, cited answers.

   ## What is this?
   Short-term: Answer transaction and LLC compliance questions with verification
   Long-term: Consolidated document/data hub with natural language queries

   ## Quick Start
   1. Install dependencies: `uv sync`
   2. Import Airbnb data: [Guide](user-guides/importing-airbnb.md)
   3. Start web UI: `uv run uvicorn apps.api.main:app --reload --port 8082`
   4. Ask questions using [persona examples](user-guides/persona-examples.md)
   ```

   **b) `docs/getting-started/overview.md`**
   - What is Poolula Platform?
   - Short-term vs long-term vision
   - Who should use it? (4 personas)
   - What can you ask?

   **c) `docs/getting-started/installation.md`**
   - Prerequisites (Python 3.13, uv)
   - Setup steps
   - Environment variables
   - First run instructions

   **d) `docs/user-guides/importing-airbnb.md`**
   - Step-by-step CSV import guide
   - What gets imported (accrual accounting explanation)
   - How to verify import worked
   - Troubleshooting

   **e) `docs/user-guides/persona-examples.md`**
   - All 50+ sample questions organized by persona
   - Expected answer formats
   - When to use each persona

   **f) `docs/architecture/database-schema.md`**
   - Core models: Property, Transaction, Document, Obligation, Provenance
   - Model relationships
   - Field descriptions
   - Why each model exists

   **g) `docs/architecture/dataflow.md`**
   - CSV import → Database → RAG → Answers flow
   - Mermaid diagram
   - Tool integration explanation

4. **Add helper script `docs_serve.sh`:**
   ```bash
   #!/bin/bash
   mkdocs serve
   ```

**Deliverables:**
- Working MkDocs site at http://localhost:8000
- 6 essential pages covering immediate needs
- Clean navigation structure

**→ NOTIFY USER FOR REVIEW BEFORE PROCEEDING TO WEEK 2**

---

## Week 2: Evaluation Improvements (Day 8-12)

### Day 8: Expand Golden Question Set

**Tasks:**
1. Expand `data/poolula_eval_set.jsonl` from 15 → 40 questions:

   **Add 15 Transaction Questions:**
   ```json
   {"question": "What was my total rental income in August 2025?", "category": "transactions", "expected_tools": ["query_database:aggregate_transactions"], "expected_keywords": ["2348", "rental income", "August 2025"], "expected_answer_type": "aggregation"}
   {"question": "How many reservations did I have in July 2025?", "category": "transactions", "expected_tools": ["query_database:transactions"], "expected_keywords": ["reservations", "July 2025", "count"]}
   ```

   **Add 10 Compliance Questions:**
   ```json
   {"question": "What is Poolula LLC's business purpose?", "category": "compliance", "expected_tools": ["search_document_content"], "expected_keywords": ["rental property", "business purpose"]}
   {"question": "What's my depreciable basis for the property?", "category": "compliance", "expected_tools": ["query_database:properties"], "expected_keywords": ["depreciable basis", "building", "FFE"]}
   ```

   **Add 5 Hybrid Questions:**
   ```json
   {"question": "Show me revenue in August and explain how it relates to our operating agreement", "category": "hybrid", "expected_tools": ["query_database:aggregate_transactions", "search_document_content"]}
   ```

   **Add 10 Edge Case Questions:**
   ```json
   {"question": "Are there any duplicate transactions?", "category": "edge_case"}
   {"question": "Which months had zero revenue?", "category": "edge_case"}
   ```

2. Run baseline evaluation: `uv run python scripts/evaluate_chatbot.py`
3. Document baseline scores

**Deliverables:**
- 40-question golden set
- Baseline evaluation results
- Score breakdown by category

---

### Day 9-10: Improve Evaluation Metrics

**Current Scoring (from evaluate_chatbot.py):**
```python
tool_score = 40%      # Did AI use correct tool?
content_score = 40%   # Are keywords in response?
completeness = 20%    # Is response non-empty?
```

**Tasks:**

1. **Add Semantic Similarity Scoring:**
   ```python
   from sentence_transformers import SentenceTransformer

   model = SentenceTransformer('all-MiniLM-L6-v2')

   def semantic_similarity(ai_answer: str, expected_answer: str) -> float:
       """Compare AI answer to expected answer using embeddings"""
       ai_embedding = model.encode(ai_answer)
       expected_embedding = model.encode(expected_answer)
       similarity = cosine_similarity(ai_embedding, expected_embedding)
       return similarity  # 0.0 - 1.0
   ```

2. **Add Numerical Accuracy Checks:**
   ```python
   def extract_numbers(text: str) -> List[float]:
       """Extract dollar amounts and numbers from text"""
       # Match $1,234.56 or 1234.56
       import re
       pattern = r'\$?[\d,]+\.?\d*'
       numbers = re.findall(pattern, text)
       return [float(n.replace('$', '').replace(',', '')) for n in numbers]

   def numerical_accuracy(ai_answer: str, expected_numbers: List[float]) -> float:
       """Check if AI answer contains correct numbers"""
       ai_numbers = extract_numbers(ai_answer)
       matches = sum(1 for n in expected_numbers if n in ai_numbers)
       return matches / len(expected_numbers) if expected_numbers else 1.0
   ```

3. **Add Date Accuracy Checks:**
   ```python
   def extract_dates(text: str) -> List[str]:
       """Extract dates from text"""
       import re
       # Match YYYY-MM-DD, MM/DD/YYYY, Month DD, YYYY
       patterns = [
           r'\d{4}-\d{2}-\d{2}',
           r'\d{2}/\d{2}/\d{4}',
           r'(January|February|...|December)\s+\d{1,2},?\s+\d{4}'
       ]
       dates = []
       for pattern in patterns:
           dates.extend(re.findall(pattern, text))
       return dates
   ```

4. **Add Citation Accuracy:**
   ```python
   def citation_accuracy(sources: List[Dict], expected_sources: List[str]) -> float:
       """Check if AI cited correct sources"""
       cited_docs = [s.get('document_title') or s.get('text', '') for s in sources]
       matches = sum(1 for exp in expected_sources if any(exp in cited for cited in cited_docs))
       return matches / len(expected_sources) if expected_sources else 1.0
   ```

5. **Update Scoring Weights:**
   ```python
   final_score = (
       0.25 * tool_usage_score +
       0.25 * content_relevance_score +
       0.25 * semantic_similarity_score +
       0.15 * numerical_accuracy_score +
       0.10 * citation_accuracy_score
   )
   ```

**Deliverables:**
- Enhanced evaluation script with 5-component scoring
- Updated scoring methodology documentation
- Re-run evaluation with new metrics

---

### Day 11: Evaluation Reporting Dashboard

**Tasks:**

1. **Create HTML evaluation report (`scripts/evaluation_report.html`):**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>Poolula Platform - Evaluation Report</title>
       <style>
           /* Modern, clean styling */
           .score-card { /* Visual score cards */ }
           .pass { background: #4CAF50; }
           .warn { background: #FF9800; }
           .fail { background: #F44336; }
       </style>
   </head>
   <body>
       <h1>Evaluation Report - [Date]</h1>

       <!-- Overall Score -->
       <div class="score-card">
           <h2>Overall Score: 87%</h2>
           <div class="score-breakdown">
               Tool Usage: 90%
               Content Relevance: 85%
               Semantic Similarity: 88%
               Numerical Accuracy: 92%
               Citation Accuracy: 80%
           </div>
       </div>

       <!-- Category Breakdown -->
       <h2>Scores by Category</h2>
       <table>
           <tr>
               <th>Category</th>
               <th>Questions</th>
               <th>Score</th>
               <th>Status</th>
           </tr>
           <tr class="pass">
               <td>Transaction Queries</td>
               <td>20</td>
               <td>92%</td>
               <td>✅ Pass</td>
           </tr>
           <tr class="warn">
               <td>Compliance Questions</td>
               <td>10</td>
               <td>75%</td>
               <td>⚠️ Warn</td>
           </tr>
       </table>

       <!-- Failed Questions Analysis -->
       <h2>Failed Questions (Score < 70%)</h2>
       <div class="failed-questions">
           <div class="question-card">
               <h3>Question: "What's my depreciable basis?"</h3>
               <p><strong>Score:</strong> 65%</p>
               <p><strong>Expected Answer:</strong> Building basis $X + FFE basis $Y = $Z total depreciable</p>
               <p><strong>AI Answer:</strong> [actual answer]</p>
               <p><strong>Issues:</strong></p>
               <ul>
                   <li>Missing FFE breakdown</li>
                   <li>Incorrect total calculation</li>
               </ul>
           </div>
       </div>

       <!-- Confidence Scores -->
       <h2>Confidence Distribution</h2>
       <canvas id="confidenceChart"></canvas>
   </body>
   </html>
   ```

2. **Generate comparison reports (before/after changes)**

3. **Add charts using Chart.js:**
   - Score distribution histogram
   - Category performance radar chart
   - Trend line (if multiple runs)

**Deliverables:**
- Beautiful HTML evaluation dashboard
- Visual score indicators
- Failed question deep-dive
- Confidence score analysis

---

### Day 12: Create import_expenses.py

**Tasks:**

1. **Create `scripts/import_expenses.py`:**
   ```python
   """
   Import Monthly Expenses from CSV

   Supports simple expense tracking format.

   Usage:
       python scripts/import_expenses.py data/imports/expenses/monthly_2024.csv --auto-property
   """

   def import_expenses_csv(csv_path: str, property_id: UUID, dry_run: bool = False):
       """
       Import expenses from CSV

       Expected format:
       Date,Description,Amount,Category
       2024-08-15,Utilities - Gas,125.50,UTILITIES_GAS
       2024-08-20,Repairs - Plumbing,450.00,REPAIRS_MAINTENANCE
       """
       # Similar structure to import_airbnb_transactions.py
       # Parse CSV
       # Create Transaction objects with transaction_type=EXPENSE
       # Save to database
   ```

2. **Create `data/templates/expenses_template.csv`:**
   ```csv
   Date,Description,Amount,Category,Notes
   2024-08-15,Utilities - Gas,125.50,UTILITIES_GAS,NuVista Energy
   2024-08-20,Repairs - Plumbing,450.00,REPAIRS_MAINTENANCE,Emergency repair
   2024-08-25,Cleaning Service,100.00,CLEANING,Post-checkout cleaning
   ```

3. **Add documentation to MkDocs:**
   - `docs/user-guides/importing-expenses.md`
   - Step-by-step guide
   - Template explanation
   - Category options

4. **Test with sample data**

**Deliverables:**
- Working expense import script
- Template CSV in data/templates/
- MkDocs user guide
- Test results

---

## Week 3: Final Documentation & Polish (Day 13-15)

### Day 13: Evaluation Documentation

**Tasks:**

1. **Create `docs/evaluation/overview.md`:**
   ```markdown
   # Evaluation System Overview

   ## Why Evaluation?
   Verification is our core principle. Every answer must be verifiable.

   ## Golden Question Set
   - 40+ questions covering all use cases
   - Organized by persona and capability
   - Expected answers documented

   ## Current Baseline Scores
   - Overall: 87%
   - Transaction queries: 92%
   - Compliance questions: 75%
   - Hybrid queries: 85%
   ```

2. **Create `docs/evaluation/adding-questions.md`:**
   ```markdown
   # Adding Questions to Golden Set

   ## Format
   Each question in poolula_eval_set.jsonl must include:
   - question: The actual question
   - category: transactions, compliance, hybrid, edge_case
   - expected_tools: Which tools should AI use
   - expected_keywords: Keywords that should appear in answer
   - expected_numbers: Dollar amounts that must be exact (optional)
   - expected_dates: Dates that must appear (optional)
   - expected_sources: Documents that should be cited (optional)

   ## Example
   ```json
   {
     "question": "What was my rental income in August 2025?",
     "category": "transactions",
     "expected_tools": ["query_database:aggregate_transactions"],
     "expected_keywords": ["2348", "rental income", "August 2025"],
     "expected_numbers": [2348.00],
     "expected_dates": ["August 2025"],
     "expected_answer_type": "aggregation"
   }
   ```
   ```

3. **Create `docs/evaluation/scoring-methodology.md`:**
   ```markdown
   # Scoring Methodology

   ## Five-Component Scoring

   ### 1. Tool Usage (25%)
   - Did AI use the correct tools?
   - query_database for transactions
   - search_document_content for documents

   ### 2. Content Relevance (25%)
   - Are expected keywords in response?
   - Keyword matching algorithm

   ### 3. Semantic Similarity (25%)
   - Embedding-based similarity to expected answer
   - Uses sentence-transformers
   - Cosine similarity threshold: 0.7

   ### 4. Numerical Accuracy (15%)
   - Are dollar amounts exactly correct?
   - Date precision
   - Count accuracy

   ### 5. Citation Accuracy (10%)
   - Did AI cite correct sources?
   - Document titles
   - Transaction IDs

   ## Thresholds
   - Pass: ≥70%
   - Warn: 40-69%
   - Fail: <40%
   ```

4. **Create `docs/evaluation/verification-guide.md`:**
   ```markdown
   # How to Verify Answers

   ## Manual Verification Steps

   ### For Transaction Queries
   1. Run query in CLI: `uv run python -c "from apps.chatbot.database_tool import ..."`
   2. Check database directly: `sqlite3 poolula.db "SELECT..."`
   3. Cross-reference with CSV source

   ### For Document Queries
   1. Open source document
   2. Search for keywords
   3. Verify context matches AI answer

   ### For Numerical Answers
   1. Export to Excel
   2. Recalculate manually
   3. Compare to AI answer
   ```

5. **Include current baseline scores in docs**

**Deliverables:**
- Complete evaluation documentation (4 pages)
- Baseline scores published
- Verification guides

---

### Day 14: API Documentation

**Tasks:**

1. **Create `docs/api/endpoints.md`:**
   ```markdown
   # API Endpoints

   ## Chat
   ### POST /api/v1/chat/query
   Ask a question to the chatbot.

   **Request:**
   ```json
   {
     "query": "What was my rental income in August 2025?",
     "session_id": "optional-session-id"
   }
   ```

   **Response:**
   ```json
   {
     "answer": "Your rental income in August 2025 was $2,348.00 from 5 transactions.",
     "sources": [...],
     "session_id": "abc123"
   }
   ```

   ## Transactions
   ### GET /api/v1/transactions
   Query transactions with filters.

   **Parameters:**
   - start_date: YYYY-MM-DD
   - end_date: YYYY-MM-DD
   - category: RENTAL_INCOME, UTILITIES_GAS, etc.
   - transaction_type: REVENUE, EXPENSE

   [Include all endpoints with examples]
   ```

2. **Create `docs/api/models.md`:**
   ```markdown
   # Database Models

   ## Property
   - id: UUID
   - address: str
   - acquisition_date: date
   - purchase_price_total: Decimal
   - land_basis: Decimal
   - building_basis: Decimal
   - ffe_basis: Decimal
   - depreciable_basis: Decimal (calculated)

   ## Transaction
   - id: UUID
   - property_id: UUID
   - transaction_date: date
   - amount: Decimal
   - category: TransactionCategory enum
   - transaction_type: TransactionType enum
   - description: str
   - source_account: str
   - provenance: Provenance

   [Include all models with field descriptions]
   ```

3. **Auto-generate examples from FastAPI:**
   - Use FastAPI's built-in docs at /docs
   - Screenshot and include in documentation

**Deliverables:**
- Complete API reference
- All endpoints documented with examples
- Model schema reference

---

### Day 15: Final Polish & Testing

**Tasks:**

1. **Add screenshots to user guides:**
   - Web UI homepage
   - Chat in action
   - Persona sidebar
   - Document stats

2. **Test all documentation links:**
   - Verify all internal links work
   - Check all code examples run
   - Test all commands in docs

3. **Update `CLAUDE.md`:**
   - Incorporate comprehensive project context
   - Add all sections from earlier plan
   - Include troubleshooting guide
   - Add baseline evaluation scores

4. **Final system test:**
   - Test all 50+ sample questions manually
   - Verify all personas work
   - Test CSV import workflows
   - Check obligation queries
   - Verify document search

5. **Run final evaluation:**
   - Target: ≥90% overall score
   - Generate HTML report
   - Document any remaining issues

6. **Create deployment checklist:**
   - Environment setup
   - Data migration
   - First-time user guide

**Deliverables:**
- Polished documentation with screenshots
- Updated CLAUDE.md
- Final evaluation report (≥90% target)
- Deployment checklist
- Production-ready system

---

## Success Metrics

### Technical Metrics
- ✅ ≥90% evaluation score on 40-question golden set
- ✅ All 4 personas have working sample questions (50+ total)
- ✅ Clean directory structure (code vs user data separated)
- ✅ Zero sensitive data in git repository

### Documentation Metrics
- ✅ MkDocs site with 15+ pages
- ✅ All core workflows documented
- ✅ Evaluation methodology transparent
- ✅ API reference complete

### User Experience Metrics
- ✅ Beautiful vanilla JS frontend
- ✅ Persona-based help that works
- ✅ Verifiable answers with citations
- ✅ Clear error messages

---

## Open Questions to Answer Before Starting

### Week 0 Questions
1. **ChromaDB bug location:** Confirm it's in `apps/chatbot/vector_store.py` around line 196?
2. **LLC documents from ragchatbot:** Which specific files to copy?
   - Articles of Organization
   - Operating Agreement
   - Statement of Authority
   - Deed/title documents
   - Insurance policies
   - Banking documents
   - Tax basis calculations
   - Others?

### Week 1 Questions
3. **Expense CSV format:** Should template match Airbnb format or be simpler?
   - Proposed: Date, Description, Amount, Category, Notes

4. **Obligation instructions location:** User guide in MkDocs or separate admin guide?
   - Recommendation: User guide in `docs/user-guides/managing-obligations.md`

---

## CLAUDE.md Contents

The `CLAUDE.md` file should include:

### Core Sections
1. **Project Vision**
   - Short-term goal (current)
   - Long-term goal
   - What we're NOT building

2. **Current Status**
   - What's built
   - What's in progress
   - What's next

3. **Architecture**
   - Core models
   - Data flow diagram
   - API endpoints
   - Tool integration

4. **Key Principles**
   - Verification over automation
   - Data quality (provenance tracking)
   - Simplicity first (single property)
   - Documentation-driven

5. **Personas & Use Cases**
   - All 4 personas with sample questions
   - Expected answer formats

6. **Common Pitfalls**
   - category vs transaction_type confusion
   - Evaluation methodology
   - Data import gotchas

7. **Development Workflow**
   - Adding new features
   - Monthly Airbnb import process
   - Running evaluation

8. **Useful Commands**
   - Start web UI
   - CLI chat
   - Import CSVs
   - Run evaluation
   - Serve MkDocs

9. **File Locations**
   - User data (not in git)
   - Code (in git)

10. **Troubleshooting**
    - Common errors and fixes
    - Evaluation failures
    - Import issues

11. **Baseline Scores**
    - Current evaluation results
    - Score breakdown by category

12. **Changelog**
    - Major updates with dates

---

## Deliverables Summary

### By End of Week 1
- ✅ Clean directory structure
- ✅ Fixed ChromaDB bug
- ✅ All LLC docs re-ingested
- ✅ Working web frontend
- ✅ 50+ sample questions
- ✅ Obligation seeding script

### By End of Week 1.5
- ✅ MkDocs pilot site (6 essential pages)
- ✅ User guides for immediate use
- ✅ Architecture documentation

### By End of Week 2
- ✅ 40-question golden set
- ✅ Enhanced evaluation metrics
- ✅ Evaluation dashboard
- ✅ Expense import script

### By End of Week 3
- ✅ Complete evaluation docs
- ✅ API reference
- ✅ Updated CLAUDE.md
- ✅ Final system test
- ✅ ≥90% evaluation score

---

## Next Steps

1. **Review and approve this plan**
2. **Start with Week 0: README revision**
3. **Get README approval before proceeding**
4. **Execute Week 1-3 according to plan**
5. **Review MkDocs pilot after Week 1.5**
6. **Celebrate when we hit ≥90% evaluation score!**

---

**Plan Status:** ✅ Ready for execution
**Last Updated:** November 14, 2024
**Estimated Completion:** ~3 weeks from approval

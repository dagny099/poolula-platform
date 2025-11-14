# Airbnb Transaction Import Guide

Quick guide to importing Airbnb booking data into Poolula Platform.

## Quick Start (3 Steps)

### 1. Export from Airbnb

**Option A: Use Airbnb's Transaction History**
1. Go to Airbnb > Account > Payments & Payouts
2. Select "Transaction History"
3. Export to CSV

**Option B: Use the Template**
Copy `data/airbnb_template.csv` and fill in your booking data:

```csv
Date,Type,Confirmation Code,Amount,Notes
2024-11-01,Reservation,HM123ABC,150.00,Guest name or notes
2024-11-15,Reservation,HM456DEF,200.00,Another booking
```

### 2. Run Import Script

```bash
# Preview first (dry run - no changes to database)
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/import_airbnb_transactions.py \
  path/to/your_airbnb.csv \
  --auto-property \
  --dry-run

# If preview looks good, import for real
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/import_airbnb_transactions.py \
  path/to/your_airbnb.csv \
  --auto-property
```

### 3. Verify in Chatbot

```bash
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/cli.py chat
```

Ask: `"Show me all rental income transactions from 2024"`

---

## CSV Format

### Required Columns

| Column | Format | Example | Description |
|--------|--------|---------|-------------|
| Date | YYYY-MM-DD or MM/DD/YYYY | 2024-11-01 | Transaction date |
| Type | Text | Reservation, Payout | Transaction type |
| Confirmation Code | Text | HM123ABC | Airbnb confirmation |
| Amount | Number | 150.00 | Dollar amount |

### Optional Columns

- **Notes** - Any additional information
- **Paid Out** - Amount after Airbnb fees
- **Currency** - USD (default)

### Example CSV

```csv
Date,Type,Confirmation Code,Amount
2024-11-01,Reservation,HM123ABC,150.00
2024-11-05,Reservation,HM789XYZ,225.00
2024-11-10,Service Fee,HM789XYZ,-20.25
2024-11-30,Payout,PAYOUT_NOV,354.75
```

---

## Transaction Categorization

The import script automatically categorizes transactions:

| Airbnb Type | Poolula Category | Type |
|-------------|------------------|------|
| Reservation | RENTAL_INCOME | REVENUE |
| Payout | RENTAL_INCOME | REVENUE |
| Service Fee | FEES_PLATFORM | EXPENSE |
| Host Fee | FEES_PLATFORM | EXPENSE |
| Resolution/Adjustment | OTHER_REVENUE | REVENUE |

---

## Advanced Usage

### Import for Specific Property

If you have multiple properties:

```bash
# First, get your property ID
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python -c "
from sqlmodel import Session, select
from core.database.connection import get_engine
from core.database.models import Property

engine = get_engine()
with Session(engine) as session:
    properties = session.exec(select(Property)).all()
    for p in properties:
        print(f'{p.id} - {p.address}')
"

# Then import with that ID
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/import_airbnb_transactions.py \
  airbnb_nov_2024.csv \
  --property-id <YOUR-PROPERTY-ID>
```

### Dry Run (Preview Only)

Always test first:

```bash
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/import_airbnb_transactions.py \
  airbnb_nov_2024.csv \
  --auto-property \
  --dry-run
```

Output:
```
Parsed 25 transactions from CSV
🔍 DRY RUN - No changes saved to database

Import Summary
==================================================
CSV File: airbnb_nov_2024.csv
Transactions: 25
Total Amount: $4,532.50
Date Range: 2024-11-01 to 2024-11-30
```

---

## Troubleshooting

### Error: "No properties found"

You need to create a property first:

```bash
# Check if property exists
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/cli.py list-properties

# If none exist, seed from poolula_facts.yml
/Users/barbaraihidalgo-sotelo/.local/bin/uv run python scripts/seed_database.py --initial
```

### Error: "Could not parse date"

Check your CSV date format. Supported formats:
- `2024-11-01` (YYYY-MM-DD)
- `11/01/2024` (MM/DD/YYYY)
- `01/11/2024` (DD/MM/YYYY)

### Error: "Zero amount, skipping"

Remove or fix rows with $0.00 amounts.

---

## What Gets Tracked

Each imported transaction includes:

✅ **Basic Data**
- Transaction date
- Amount (gross)
- Category (auto-categorized)
- Description (with confirmation code)

✅ **Provenance (Data Lineage)**
- Source: CSV file name
- Row number in CSV
- Import timestamp
- Confidence score (0.9 for CSV imports)

✅ **Metadata**
- Airbnb confirmation code
- Original transaction type
- CSV file name and row number

---

## Next Steps

After importing:

1. **Verify with Chatbot**
   ```
   poolula chat
   > "What was my total rental income in November 2024?"
   ```

2. **Review in Database**
   ```python
   from apps.chatbot.database_tool import DatabaseQueryTool
   tool = DatabaseQueryTool()
   result = tool.query_transactions(
       start_date="2024-11-01",
       end_date="2024-11-30",
       category="RENTAL_INCOME"
   )
   print(result)
   ```

3. **Export for Tax Prep**
   (Coming in Phase 3)

---

## Alternative Methods

### Method 2: Python Script (For Custom Data)

Create a custom Python script:

```python
from sqlmodel import Session
from core.database.connection import get_engine
from core.database.models import Transaction, create_provenance
from core.database.enums import TransactionCategory, TransactionType, ProvenanceSourceType
from datetime import date
from decimal import Decimal
from uuid import UUID

engine = get_engine()
property_id = UUID("your-property-id-here")

transactions = [
    Transaction(
        property_id=property_id,
        transaction_date=date(2024, 11, 1),
        amount=Decimal("150.00"),
        category=TransactionCategory.RENTAL_INCOME,
        transaction_type=TransactionType.REVENUE,
        description="Airbnb booking - HM123ABC",
        source_account="Airbnb",
        provenance=create_provenance(
            source_type=ProvenanceSourceType.MANUAL_ENTRY,
            source_id="manual_entry_script",
            created_by="user:yourself"
        )
    ),
    # Add more transactions...
]

with Session(engine) as session:
    for t in transactions:
        session.add(t)
    session.commit()
    print(f"✅ Added {len(transactions)} transactions")
```

### Method 3: REST API (Coming Soon)

Will be available in Phase 3:

```bash
curl -X POST http://localhost:8082/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "...",
    "transaction_date": "2024-11-01",
    "amount": 150.00,
    "category": "RENTAL_INCOME",
    "description": "Airbnb booking"
  }'
```

---

## Recommendations

**For Regular Updates:**
1. Export Airbnb CSV monthly
2. Name files: `airbnb_YYYY_MM.csv`
3. Store in `data/imports/` folder
4. Run import script
5. Verify with chatbot

**For One-Time Import:**
- Use the CSV import script with --dry-run first
- Review the preview
- Run without --dry-run to commit

**For Real-Time Sync:**
- Consider Airbnb API integration (Phase 4)
- Or use monthly CSV exports (simpler, good enough)

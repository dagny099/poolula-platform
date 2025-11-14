# Data Templates

This directory contains CSV templates for importing data into Poolula Platform.

## Templates

### `airbnb_template.csv`
Template for importing Airbnb transaction data from reservation exports.

**Usage:**
```bash
uv run python scripts/import_airbnb_transactions.py \
    --csv your_airbnb_export.csv \
    --property-id <property-uuid> \
    --dry-run
```

**Columns:** Confirmation Code, Start Date, End Date, Nights, Guest, Listing, Gross Earnings, Payout, ...

**Accounting:** Uses accrual accounting:
- Revenue recognized on checkout date (End Date)
- Expenses recognized on payout date (Paid Out)

### `expenses_template.csv`
Template for importing miscellaneous expenses (utilities, repairs, etc.).

**Usage:**
```bash
uv run python scripts/import_expenses.py \
    --csv your_expenses.csv \
    --property-id <property-uuid> \
    --dry-run
```

**Columns:** Date, Description, Amount, Category, Source Account, Notes

**Categories:** UTILITIES_GAS, UTILITIES_ELECTRIC, REPAIRS_MAINTENANCE, PROPERTY_TAXES, etc.

## Creating Your Import Files

1. Copy the appropriate template
2. Fill in your data following the column format
3. Save with a descriptive name (e.g., `airbnb_2025_nov.csv`)
4. Place in `data/` directory (NOT in templates/)
5. Run import script with `--dry-run` first to preview

## Important Notes

- Template files are tracked in git
- Your actual data files in `data/` are NOT tracked (see `.gitignore`)
- Always run with `--dry-run` first to verify data before importing
- Check for duplicates before importing the same file twice

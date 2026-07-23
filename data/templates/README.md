# Data Templates

This directory contains CSV templates for importing data into Poolula Platform.

## Templates

### `airbnb_template.csv`
Template matching the real Airbnb earnings export format (22 columns). The
sample rows are fictional demo data. Airbnb's own CSV export already has this
shape — download it and import as-is.

**Usage:**
```bash
# CSV path is a positional argument (use --property-id <uuid> to target a
# specific property, or --auto-property to use the first one)
uv run python scripts/import_airbnb_transactions.py \
    your_airbnb_export.csv \
    --auto-property \
    --dry-run
```

**Columns:** Date, Arriving by date, Type, Confirmation code, Booking date,
Start date, End date, Nights, Guest, Listing, Details, Reference code,
Currency, Amount, Paid out, Service fee, Fast pay fee, Cleaning fee, Pet fee,
Gross earnings, Occupancy taxes, Earnings year

**Row types:** `Reservation` (imported as revenue + service-fee expense),
`Resolution Payout` (imported as revenue), `Payout` (skipped — bank transfer).

**Accounting:** Uses accrual accounting:
- Revenue recognized on checkout date (End date)
- Service-fee expense recognized on payout date (Date column)

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

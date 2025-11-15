# Managing Obligations

Complete guide for tracking compliance deadlines, tax filings, and recurring obligations in Poolula Platform.

## Overview

The obligations system helps you track time-sensitive tasks for your LLC and properties:

- **Annual LLC filings** (Colorado periodic report)

- **Quarterly tax payments** (estimated tax deadlines)

- **Insurance renewals** (annual policy reviews)

- **License renewals** (business licenses)

- **Property inspections** (semi-annual reviews)

- **Other compliance deadlines** (meetings, audits, permits)

### Why Track Obligations?

**Avoid penalties:**

- Late filing fees for state reports ($50-$500)

- IRS underpayment penalties for missed quarterly estimates

- Lapsed insurance coverage

**Stay organized:**

- One central calendar for all deadlines

- Automatic recurrence for annual/quarterly tasks

- Document completion with audit trail

**Reduce stress:**

- Advance reminders before due dates

- Clear status tracking (pending, completed, overdue)

- No more spreadsheets or sticky notes

## Quick Start

### Seed Common Obligations

The fastest way to populate your compliance calendar:

```bash
# Seed standard LLC obligations for 2025
uv run python scripts/seed_obligations.py

# Seed for specific year
uv run python scripts/seed_obligations.py --year 2026

# Clear existing and reseed
uv run python scripts/seed_obligations.py --clear --year 2025
```

**What gets created:**

| Category | Count | Examples |
|----------|-------|----------|
| LLC Compliance | 1 | Colorado Periodic Report (annual) |
| Tax Filings | 6 | Quarterly estimates (4), Form 1065, Schedule E |
| Property Taxes | 2 | First half (Feb 28), Second half (Jun 15) |
| Insurance | 1 | Annual policy renewal review |
| Operations | 3 | Annual meeting, property inspections (2) |

### View Obligations (API)

```bash
# Get all pending obligations
curl http://localhost:8082/api/v1/obligations?status=pending

# Get obligations for specific property
curl http://localhost:8082/api/v1/obligations?property_id={uuid}

# Get upcoming deadlines (next 30 days)
curl http://localhost:8082/api/v1/obligations?upcoming=30
```

## Understanding Obligations

### Obligation Types

**`tax:filing`** - Tax return deadlines

- Form 1065 (partnership return)

- Schedule E (rental income on individual return)

- State tax returns

**`tax:payment`** - Tax payment deadlines

- Quarterly estimated tax payments

- Annual tax payments

**`compliance:periodic_report`** - State filings

- Colorado Periodic Report ($10 annual fee)

- Annual reports to maintain good standing

**`insurance:renewal`** - Insurance reviews

- Annual policy renewal

- Coverage review

- Premium payment

**`license:renewal`** - Business licenses

- Local business licenses

- Professional licenses

- Permits

**`other`** - Miscellaneous obligations

- Board meetings

- Property inspections

- Lease reviews

### Obligation Status

**`pending`** - Not yet due

- Default status for new obligations

- More than 7 days until due date

**`due_soon`** - Due within 7 days

- Requires immediate attention

- Triggers reminder notifications (planned)

**`overdue`** - Past due date

- Requires urgent action

- May incur penalties

**`completed`** - Satisfied

- Obligation fulfilled

- Completion date recorded in `extra_metadata`

**`cancelled`** - No longer applicable

- Obligation no longer required

- Reason recorded in `extra_metadata`

### Recurrence Patterns

Obligations can be **one-time** or **recurring**.

**One-time obligations:**

- `recurrence: null`

- Example: One-time permit application

**Recurring obligations:**

- `recurrence: "RRULE string"`

- Example: Annual tax return

## Creating Obligations

### Using the Seed Script

The seed script creates standard LLC obligations automatically.

**See:** `scripts/seed_obligations.py`

**What it creates:**

**LLC Compliance:**

- Colorado Periodic Report (due annually May 15)

**Tax Obligations:**

- Quarterly estimated payments (Apr 15, Jun 15, Sep 15, Jan 15)

- Form 1065 partnership return (Mar 15)

- Schedule E individual return (Apr 15)

**Property Taxes:**

- First half payment (Feb 28)

- Second half payment (Jun 15)

**Insurance:**

- Annual policy renewal (May 1)

**Operations:**

- Annual LLC meeting (Dec 31)

- Property inspections (Jun 30, Dec 31)

**Usage:**

```bash
# Seed all common obligations
uv run python scripts/seed_obligations.py

# Review what was created
curl http://localhost:8082/api/v1/obligations
```

### Manual Creation (API)

For custom obligations not in the seed script:

```bash
curl -X POST http://localhost:8082/api/v1/obligations \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": null,
    "obligation_type": "license:renewal",
    "due_date": "2025-06-01",
    "status": "pending",
    "description": "Renew Short-Term Rental License with City of Montrose",
    "recurrence": "FREQ=YEARLY;BYMONTH=6;BYMONTHDAY=1",
    "extra_metadata": {
      "fee": "$150",
      "reminder_days_before": 60,
      "renewal_url": "https://montrosecounty.colorado.gov/"
    }
  }'
```

**Field explanations:**

- `property_id`: UUID of property (null for LLC-wide obligations)

- `obligation_type`: One of the types listed above

- `due_date`: ISO date format (YYYY-MM-DD)

- `status`: Initial status (usually "pending")

- `description`: Human-readable explanation

- `recurrence`: RRULE string (see below) or null

- `extra_metadata`: Flexible JSON for custom fields

## RRULE Format Explained

**RRULE** (Recurrence Rule) is the RFC 5545 standard for recurring events.

### Basic Format

```
FREQ={frequency};[additional parameters]
```

**Frequency options:**

- `YEARLY` - Once per year

- `MONTHLY` - Once per month

- `WEEKLY` - Once per week

- `DAILY` - Every day (rarely used for obligations)

### Common RRULE Examples

**Annual obligation (same date every year):**

```
FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=15
```

Meaning: Every year on April 15

**Quarterly obligation (4 times per year):**

```
FREQ=YEARLY;BYMONTH=4,6,9,1;BYMONTHDAY=15
```

Meaning: April 15, June 15, September 15, January 15

**Monthly obligation (same day each month):**

```
FREQ=MONTHLY;BYMONTHDAY=1
```

Meaning: 1st day of every month

**Semi-annual (twice per year):**

```
FREQ=YEARLY;BYMONTH=6,12;BYMONTHDAY=30
```

Meaning: June 30 and December 30

### RRULE Parameters

**`BYMONTH`** - Specify month(s)

```
BYMONTH=3         → March only
BYMONTH=3,6,9,12  → March, June, September, December
```

**`BYMONTHDAY`** - Specify day of month

```
BYMONTHDAY=15     → 15th of the month
BYMONTHDAY=1      → 1st of the month
BYMONTHDAY=-1     → Last day of the month
```

**`BYDAY`** - Specify day of week

```
BYDAY=MO          → Monday
BYDAY=1MO         → First Monday
BYDAY=-1FR        → Last Friday
```

**`INTERVAL`** - Specify interval

```
FREQ=YEARLY;INTERVAL=2    → Every 2 years
FREQ=MONTHLY;INTERVAL=3   → Every 3 months
```

**`COUNT`** - Limit number of occurrences

```
FREQ=MONTHLY;COUNT=12     → 12 times, then stop
```

**`UNTIL`** - End date

```
FREQ=MONTHLY;UNTIL=20251231  → Until Dec 31, 2025
```

### RRULE Testing

**Online RRULE tester:**

https://icalendar.org/rrule-tool.html

Paste your RRULE string to visualize the recurrence pattern.

## Common Obligation Examples

### Colorado Periodic Report

```json
{
  "obligation_type": "compliance:periodic_report",
  "due_date": "2025-05-15",
  "recurrence": "FREQ=YEARLY;BYMONTH=5;BYMONTHDAY=15",
  "description": "Colorado Periodic Report - Annual LLC filing with Colorado Secretary of State. $10 filing fee.",
  "extra_metadata": {
    "fee": "$10",
    "filing_url": "https://www.sos.state.co.us/",
    "reminder_days_before": 30
  }
}
```

### Quarterly Estimated Tax

```json
{
  "obligation_type": "tax:payment",
  "due_date": "2025-04-15",
  "recurrence": "FREQ=YEARLY;BYMONTH=4,6,9,1;BYMONTHDAY=15",
  "description": "Quarterly Estimated Tax Payment - Q1. Required if annual tax liability exceeds $1,000.",
  "extra_metadata": {
    "quarter": "Q1",
    "form": "Form 1040-ES",
    "reminder_days_before": 14
  }
}
```

### Property Tax (Semi-Annual)

```json
{
  "obligation_type": "tax:property",
  "due_date": "2025-02-28",
  "recurrence": "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=28",
  "description": "Property Tax - First Half. Payment to Montrose County Treasurer.",
  "extra_metadata": {
    "payment_type": "first_half",
    "county": "Montrose",
    "reminder_days_before": 30
  }
}
```

### Annual Insurance Renewal

```json
{
  "obligation_type": "insurance:renewal",
  "due_date": "2025-05-01",
  "recurrence": "FREQ=YEARLY;BYMONTH=5;BYMONTHDAY=1",
  "description": "Property Insurance Renewal - Review coverage with Travelers Insurance.",
  "extra_metadata": {
    "provider": "Travelers Insurance",
    "policy_number": "ABC123456",
    "reminder_days_before": 60
  }
}
```

### One-Time Obligation

```json
{
  "obligation_type": "other",
  "due_date": "2025-08-15",
  "recurrence": null,
  "description": "File amended 2023 tax return (Form 1040-X) to claim missed deduction",
  "extra_metadata": {
    "form": "Form 1040-X",
    "tax_year": "2023",
    "reason": "Missed depreciation deduction"
  }
}
```

## Managing Obligations

### Viewing Obligations

**List all obligations:**

```bash
curl http://localhost:8082/api/v1/obligations
```

**Filter by status:**

```bash
# Pending only
curl http://localhost:8082/api/v1/obligations?status=pending

# Overdue only
curl http://localhost:8082/api/v1/obligations?status=overdue

# Completed
curl http://localhost:8082/api/v1/obligations?status=completed
```

**Filter by property:**

```bash
curl http://localhost:8082/api/v1/obligations?property_id={uuid}
```

**Filter by date range:**

```bash
# Due in next 30 days
curl http://localhost:8082/api/v1/obligations?upcoming=30

# Due in specific month
curl http://localhost:8082/api/v1/obligations?due_month=2025-04
```

### Updating Obligations

**Mark as completed:**

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "extra_metadata": {
      "completed_date": "2025-04-10",
      "confirmation_number": "CO-2025-12345",
      "notes": "Filed online, paid $10 fee"
    }
  }'
```

**Postpone due date:**

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "due_date": "2025-09-15",
    "extra_metadata": {
      "extension_reason": "Filed Form 7004 for 6-month extension"
    }
  }'
```

**Cancel obligation:**

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled",
    "extra_metadata": {
      "cancellation_reason": "No longer required after business structure change"
    }
  }'
```

### Deleting Obligations

```bash
# Soft delete (recommended)
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -d '{"status": "cancelled"}'

# Hard delete (use with caution)
curl -X DELETE http://localhost:8082/api/v1/obligations/{id}
```

## Recurrence Handling

### How Recurrence Works

**RRULE defines the pattern, not individual instances.**

**Example:**

```json
{
  "due_date": "2025-04-15",
  "recurrence": "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=15"
}
```

**This creates:**

- 2025-04-15

- 2026-04-15

- 2027-04-15

- ... (continues indefinitely)

**Completing a recurring obligation:**

When you mark a recurring obligation as `completed`, the system creates a **completion record** but the obligation remains active for future occurrences.

**Planned enhancement:** Auto-generate next occurrence when current one is completed.

### Modifying Recurring Obligations

**Change pattern for all future occurrences:**

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -d '{
    "recurrence": "FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=15"
  }'
```

This changes the pattern going forward, but doesn't affect completed historical instances.

**Stop recurrence:**

```bash
curl -X PATCH http://localhost:8082/api/v1/obligations/{id} \
  -d '{
    "recurrence": null
  }'
```

Converts recurring obligation to one-time.

## Best Practices

### 1. Use the Seed Script for Standard Obligations

Don't manually create common obligations like tax deadlines.

**Do this:**

```bash
uv run python scripts/seed_obligations.py
```

**Not this:**

```bash
# Manually creating each tax deadline... (tedious and error-prone)
```

### 2. Set Appropriate Reminder Days

**Tax filings:** 30-60 days (need time to gather documents)

**Payments:** 7-14 days (enough time to process payment)

**Reviews:** 60-90 days (need time for insurance shopping, etc.)

**Quick tasks:** 3-7 days (license renewals, simple filings)

### 3. Use Extra Metadata for Context

**Store useful information:**

```json
{
  "extra_metadata": {
    "fee": "$150",
    "filing_url": "https://example.gov/renew",
    "confirmation_number": "ABC123",
    "last_year_amount": "$145",
    "notes": "Price increased 3% from last year"
  }
}
```

### 4. Link to Documents

**Reference relevant documents:**

```json
{
  "extra_metadata": {
    "related_documents": [
      "insurance-policy-2024.pdf",
      "coverage-comparison-2024.xlsx"
    ]
  }
}
```

### 5. Review Obligations Quarterly

**Schedule review:**

- January: Review all obligations for the year

- April: Review Q2 deadlines

- July: Review Q3 deadlines

- October: Review Q4 and next year planning

## Troubleshooting

### Obligation Not Showing Up

**Check status filter:**

```bash
# Make sure you're not filtering out the obligation
curl http://localhost:8082/api/v1/obligations  # All statuses
```

**Check property filter:**

```bash
# LLC-wide obligations have property_id = null
curl http://localhost:8082/api/v1/obligations?property_id=null
```

### Recurrence Not Working

**Validate RRULE:**

- Use https://icalendar.org/rrule-tool.html to test

- Check for typos (e.g., `BYMONTH=13` is invalid)

- Ensure proper format (no spaces, proper semicolons)

**Common errors:**

```
❌ FREQ=YEARLY BYMONTH=4      → Missing semicolon
✅ FREQ=YEARLY;BYMONTH=4

❌ freq=yearly;bymonth=4      → Must be uppercase
✅ FREQ=YEARLY;BYMONTH=4

❌ BYMONTH=13                 → Invalid month
✅ BYMONTH=12
```

### Seed Script Errors

**No property found:**

```
⚠️ No active properties found - creating LLC-level obligations only
```

**Solution:** Create a property first, then run seed script.

**Duplicate obligations:**

```
IntegrityError: UNIQUE constraint failed
```

**Solution:** Use `--clear` flag to remove existing obligations first.

### Overdue Obligations Piling Up

**Mark as completed or cancelled:**

Don't let old obligations accumulate. Clean up regularly:

```bash
# List overdue
curl http://localhost:8082/api/v1/obligations?status=overdue

# Mark as completed or cancelled as appropriate
```

## Advanced Usage

### Custom Recurrence Patterns

**Every 2 years (biennial):**

```
FREQ=YEARLY;INTERVAL=2;BYMONTH=6;BYMONTHDAY=15
```

**Last day of every quarter:**

```
FREQ=MONTHLY;BYMONTH=3,6,9,12;BYMONTHDAY=-1
```

**First Monday of every month:**

```
FREQ=MONTHLY;BYDAY=1MO
```

**Every 6 months:**

```
FREQ=MONTHLY;INTERVAL=6;BYMONTHDAY=1
```

### Bulk Operations

**Mark all overdue as completed (with reason):**

```bash
# Get all overdue IDs
OVERDUE_IDS=$(curl http://localhost:8082/api/v1/obligations?status=overdue | jq -r '.[].id')

# Update each one
for id in $OVERDUE_IDS; do
  curl -X PATCH http://localhost:8082/api/v1/obligations/$id \
    -d '{"status": "completed", "extra_metadata": {"bulk_update": true}}'
done
```

### Exporting Obligations Calendar

**Export to JSON:**

```bash
curl http://localhost:8082/api/v1/obligations > obligations_export.json
```

**Export to CSV (planned):**

Future enhancement will support CSV export for calendar integration.

## Planned Features

### Phase 5 Enhancements

**Email/SMS reminders:**

- Automatic notifications based on `reminder_days_before`

- Configurable reminder preferences

**Calendar integration:**

- iCal export

- Google Calendar sync

- Outlook integration

**Chatbot integration:**

- Ask "What obligations are due this month?"

- Natural language queries

- Completion via chat

**Dashboard widgets:**

- Upcoming deadlines card

- Overdue obligations alert

- Compliance calendar view

## Related Documentation

- [Database Models](../architecture/data-models.md) - Obligations table schema

- [API Reference](../api/obligations.md) - Full API documentation

- [Seed Script](../../scripts/seed_obligations.py) - Common obligations creator

- [Data Import](../workflows/data-import.md) - General data import guide

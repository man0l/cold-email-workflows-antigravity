# Clean Campaign Leads SOP

## Goal
Clean a list of leads (CSV or Google Sheet) by removing contacts that are already present in a specific Instantly.ai campaign.

## Inputs
- **Source**:
  - Google Spreadsheet URL
  - CSV file path
- **Campaign ID**: The ID of the Instantly campaign to check against.
- **Output**:
  - Path to save the cleaned CSV file (optional, defaults to `.tmp/cleaned_leads.csv`)
  - Or Google Sheet name (if source is Sheet)

## Tools
- `execution/clean_instantly_leads.py`

## Instructions

### Option 1: Clean from CSV
```bash
.venv/bin/python execution/clean_instantly_leads.py \
  --source-file path/to/leads.csv \
  --campaign-id "YOUR_CAMPAIGN_ID" \
  --output .tmp/cleaned_leads.csv
```

### Option 2: Clean from Google Sheet
```bash
.venv/bin/python execution/clean_instantly_leads.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --campaign-id "YOUR_CAMPAIGN_ID" \
  --output-sheet "Cleaned Leads"
```

## Notes
- Requires `INSTANTLY_API_KEY` in `.env`.
- Matches based on **Email** address (case-insensitive).
- If a lead in the source list has no email, it is preserved (warning logged).

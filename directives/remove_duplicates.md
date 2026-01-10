# Remove Duplicates Between Spreadsheets SOP

## Goal
Remove duplicate entries from a destination spreadsheet based on matches found in a source spreadsheet. This is useful for deduplicating leads across campaigns or cleaning up merged datasets.

## Inputs
- **Source Spreadsheet**: Google Spreadsheet URL containing the reference list (leads to check against)
- **Source Sheet Name** (optional): Name of the sheet within the source spreadsheet. If not provided, uses the last sheet.
- **Destination Spreadsheet**: Google Spreadsheet URL containing leads to be deduplicated
- **Destination Sheet Name** (optional): Name of the sheet within the destination spreadsheet. If not provided, uses the last sheet.
- **Match Field** (optional): Field to use for matching (default: "email"). Can be email, domain, phone, etc.
- **Output**:
  - New sheet in the destination spreadsheet with duplicates removed
  - Or new Google Spreadsheet (if specified)

## Algorithm
1. **Load Source**: Read all entries from the source spreadsheet/sheet
2. **Load Destination**: Read all entries from the destination spreadsheet/sheet
3. **Extract Match Keys**: Build a set of unique values from the source based on the match field (e.g., all emails)
4. **Filter Duplicates**: Remove any entries from destination that have a matching value in the source set
5. **Output**: Save the deduplicated entries to a new sheet or spreadsheet

## Tools
- `execution/remove_duplicates.py` - Deduplication script

## Output
- **New Sheet**: A new tab/worksheet in the destination spreadsheet with duplicates removed
- **Statistics**: Report showing:
  - Total entries in source
  - Total entries in destination
  - Number of duplicates found
  - Number of unique entries remaining

## Safety Rules
> [!IMPORTANT]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** sheet for the deduplicated output
> - The original destination sheet is never modified
> - Original data is preserved for audit/recovery

## Instructions

### Basic Usage: Remove duplicates by email

```bash
.venv/bin/python execution/remove_duplicates.py \
  --source-url "https://docs.google.com/spreadsheets/d/SOURCE_ID/edit" \
  --dest-url "https://docs.google.com/spreadsheets/d/DEST_ID/edit" \
  --output-sheet "Deduplicated Leads"
```

### Specify source and destination sheets

```bash
.venv/bin/python execution/remove_duplicates.py \
  --source-url "https://docs.google.com/spreadsheets/d/SOURCE_ID/edit" \
  --source-sheet "Campaign A Leads" \
  --dest-url "https://docs.google.com/spreadsheets/d/DEST_ID/edit" \
  --dest-sheet "Campaign B Leads" \
  --output-sheet "Campaign B - Deduplicated"
```

### Match by different field (e.g., company domain)

```bash
.venv/bin/python execution/remove_duplicates.py \
  --source-url "https://docs.google.com/spreadsheets/d/SOURCE_ID/edit" \
  --dest-url "https://docs.google.com/spreadsheets/d/DEST_ID/edit" \
  --match-field "companyDomain" \
  --output-sheet "Deduplicated by Domain"
```

### Output to a new spreadsheet instead of new sheet

```bash
.venv/bin/python execution/remove_duplicates.py \
  --source-url "https://docs.google.com/spreadsheets/d/SOURCE_ID/edit" \
  --dest-url "https://docs.google.com/spreadsheets/d/DEST_ID/edit" \
  --output-spreadsheet "Deduplicated Leads - Jan 2026"
```

## Match Field Options

Common fields to match on:
- `email` (default) - Email address
- `companyDomain` or `domain` - Company website domain
- `phone` - Phone number
- `companyName` - Company name
- `fullName` or `name` - Contact name

The script will:
- Match case-insensitively
- Normalize whitespace
- Handle missing/empty values (entries without the match field are preserved)

## Example Workflow

1. **Check what you're working with**:
   - Open both spreadsheets in browser
   - Note which sheets contain your data
   - Verify the field names (email vs Email vs email_address, etc.)

2. **Run deduplication**:
   ```bash
   .venv/bin/python execution/remove_duplicates.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --source-sheet "All Contacted Leads" \
     --dest-url "https://docs.google.com/spreadsheets/d/XYZ789/edit" \
     --dest-sheet "New Prospects" \
     --output-sheet "New Prospects - Deduplicated" \
     --verbose
   ```

3. **Review results**:
   ```
   Loading source spreadsheet...
   Source: 1,250 entries loaded from 'All Contacted Leads'

   Loading destination spreadsheet...
   Destination: 500 entries loaded from 'New Prospects'

   Matching by field: email

   Deduplication Summary:
     Duplicates found: 87 (17.4%)
     Unique entries: 413 (82.6%)

   Creating new sheet: 'New Prospects - Deduplicated'
   Sheet URL: https://docs.google.com/spreadsheets/d/XYZ789/edit#gid=123456

   ✓ Deduplication complete!
   ```

## Troubleshooting

- **No match field found**: The script will list available fields. Check your column headers and use the exact field name.
- **Zero duplicates found**: Good! Your destination list is already unique. Or check that you're using the correct match field.
- **Google Sheets auth error**: Ensure `credentials.json` is in the project root and you've run the auth flow.
- **Last sheet not what you expected**: Explicitly specify `--source-sheet` and `--dest-sheet` names.

## Notes

- Matching is **case-insensitive** and whitespace is normalized
- Entries with missing/null values in the match field are **preserved** (not removed)
- The script preserves all original fields/columns from the destination
- If the same entry appears multiple times in source, it's still only counted once
- Order is preserved from the original destination sheet

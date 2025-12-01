# Email Enrichment SOP

## Goal
Find and enrich leads with email addresses using AnyMailFinder API. Accepts cleaned leads from Google Sheets or JSON files and attempts to find verified email addresses for each contact.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path (typically from `.tmp/` directory, such as cleaned leads)
- **Max Leads**: Maximum number of leads to process (default: 100)
  - ⚠️ Each API call costs credits, so this limit prevents accidental overspending
- **API Key**: AnyMailFinder API key (from `.env` file as `ANYMAILFINDER_API_KEY`)

## Algorithm
1. **Load Data**: Reads leads from a JSON file or Google Sheet.
2. **Filter Leads**: **BY DEFAULT**, only processes leads with empty email addresses (use `--include-existing` to override).
3. **Validate Input**: Ensures each lead has the minimum required fields (first name, last name, company domain/website).
4. **Permission Check**: **REQUIRED** - Asks for user confirmation before running, displaying:
   - Total number of leads
   - Number of leads without emails (that will be processed)
   - Estimated API cost (approximate credits per lead)
   - Max leads limit
5. **API Calls**: For each lead without an email, makes an API call to AnyMailFinder with:
   - First name (from `firstName`, `first_name`, `personFirstName`)
   - Last name (from `lastName`, `last_name`, `personLastName`)
   - Company domain (from `companyWebsite`, `company_website`, `website`, `companyDomain`, `company_domain`, `domain`)
6. **Update Leads**: Enriches the lead data with:
   - Email address (if found)
   - Email verification status
   - Confidence score from AnyMailFinder
7. **Output**: Saves ALL leads (enriched and skipped) to a new file or sheet.

## Tools
- `execution/find_emails.py` - Email enrichment script using AnyMailFinder API

## Output
- **If Source is File**: A new JSON file containing leads with enriched email data.
- **If Source is Google Sheet**: A **new sheet/spreadsheet** with enriched lead data.

## Safety Rules
> [!IMPORTANT]
> **SAFETY GUARDS**
> - **Only enriches leads with EMPTY email addresses by default** - this prevents accidental overwriting
> - Use `--include-existing` flag if you want to process ALL leads (including those with emails)
> - This operation uses paid API credits
> - Always asks for user confirmation before running
> - Displays the exact number of leads that will be processed and estimated cost
> - Respects the max leads limit to prevent overspending

> [!WARNING]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** file or **NEW** sheet for the enriched output
> - Do not use the same filename for input and output
> - Preserve all original lead fields

## Instructions

### Option 1: Enrich from JSON → New JSON

```bash
.venv/bin/python execution/find_emails.py \
  --source-file .tmp/cleaned_video_editing_leads.json \
  --output .tmp/enriched_video_editing_leads.json \
  --max-leads 100
```

### Option 2: Enrich from JSON → New Google Sheet

```bash
.venv/bin/python execution/find_emails.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Enriched Leads (Nov 28)" \
  --max-leads 50
```

### Option 3: Enrich from Google Sheet → New JSON

```bash
.venv/bin/python execution/find_emails.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output .tmp/enriched_leads.json \
  --max-leads 100
```

### Option 4: Enrich from Google Sheet → New Google Sheet

```bash
.venv/bin/python execution/find_emails.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output-sheet "Enriched Leads (Nov 28)" \
  --max-leads 75
```

### Optional Flags
- `--verbose` or `-v`: Display detailed information for each API call
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)
- `--include-existing`: Process ALL leads including those with existing emails (by default, only leads with empty emails are enriched)

### Example Workflow

1. **Clean leads first** (recommended):
   ```bash
   .venv/bin/python execution/clean_leads.py \
     --source-file .tmp/raw_leads.json \
     --keywords "video editing" \
     --output .tmp/cleaned_leads.json
   ```

2. **Enrich with emails**:
   ```bash
   .venv/bin/python execution/find_emails.py \
     --source-file .tmp/cleaned_leads.json \
     --output .tmp/enriched_leads.json \
     --max-leads 100 \
     --verbose
   ```

3. **Export to Google Sheets** (if needed):
   ```bash
   .venv/bin/python execution/export_to_sheets.py \
     .tmp/enriched_leads.json \
     --sheet-name "Enriched Leads - Nov 28" \
     --folder-id "0ADWgx-M8Z5r-Uk9PVA"
   ```

4. **Review results**:
   The script will show:
   ```
   📧 Email Enrichment Tool
   ==================================================
   
   📊 Summary:
     Total leads: 150
     Leads without email: 87
     Will process: 87 leads (only empty emails)
     Max leads limit: 100
     Estimated cost: ~87 credits
   
   ⚠️  WARNING: This will consume API credits!
   ==================================================
   
   Continue? (yes/no): yes
   
   Processing leads... ━━━━━━━━━━━━━━━━ 100/100 100%
   
   ✅ Email Enrichment Summary:
      Emails found: 78 (78%)
      No email found: 22 (22%)
      Skipped (had email): 0
      Total processed: 100
   
   Saved to: .tmp/enriched_leads.json
   ```

## API Response Format

AnyMailFinder API v5.1 uses the following authentication:
- **Method**: POST
- **Endpoint**: `https://api.anymailfinder.com/v5.1/find-email/person`
- **Authentication**: API key via `Authorization` header
- **Request Body**: JSON with `first_name`, `last_name`, and `domain` fields

Response format:
```json
{
  "success": true,
  "email": "john.doe@company.com",
  "first_name": "John",
  "last_name": "Doe",
  "confidence": 95,
  "verified": true
}
```

The script enriches leads with:
- `email`: Found email address (or left empty if not found)
- `email_confidence`: Confidence score from AnyMailFinder
- `email_verified`: Verification status

## Required Fields

For the API to work, each lead must have:
- **First Name**: `firstName`, `first_name`, or `personFirstName`
- **Last Name**: `lastName`, `last_name`, or `personLastName`
- **Company Domain**: `companyWebsite`, `website`, `companyDomain`, or `domain`

Leads missing any of these fields will be skipped.

## Cost Management

- Default max leads: **100**
- Each API call costs approximately **1 credit**
- **By default, only processes leads with empty emails** - this is the primary cost control guard
- The script will **always ask for permission** before making API calls
- Shows exact count of leads that will be processed before asking for confirmation
- Use `--max-leads` to limit processing and control costs
- Use `--include-existing` flag ONLY if you want to process leads that already have emails (usually not needed)

## Troubleshooting

- **Error: ANYMAILFINDER_API_KEY not found**: Add your API key to the `.env` file
- **Error: Missing required fields**: Ensure leads have first name, last name, and company domain
- **No emails found**: AnyMailFinder may not have data for those companies/contacts
- **Rate limit errors**: The script includes automatic retry with exponential backoff
- **Permission denied**: User must confirm with "yes" to proceed

## Notes

- The script preserves all original fields in the output
- Existing email fields are preserved unless `--skip-existing` is used
- Empty or invalid responses from AnyMailFinder leave the email field empty
- Progress bar shows real-time processing status
- All errors are logged with details for debugging

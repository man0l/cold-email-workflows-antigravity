# Lead Cleaning SOP

## Goal
Filter and clean leads from a spreadsheet or scraped JSON file based on keyword matching, negative keyword exclusion, and industry filtering.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path in `.tmp/` directory
- **Keywords**: List of positive keywords to match (checked against company name, description, industry, etc.)
- **NOT Keywords**: List of negative keywords to exclude (leads matching these will be filtered out)
- **Industries**: List of industries to match (e.g., "Marketing & Advertising", "Media Production")

## Algorithm
1.  **Load Data**: Reads leads from a JSON file or Google Sheet.
2.  **Clean URLs**: Removes query parameters, fragments, and paths from all website URLs to get just the homepage/domain. This ensures you get clean homepage URLs without tracking parameters or subpages.
    *   Example: `https://tilsonhomes.com/new-homes/tx/waco/9062/?utm_source=google` → `https://tilsonhomes.com`
    *   Example: `https://kurkhomes.com/?utm_campaign=gmb` → `https://kurkhomes.com`
    *   Example: `ubh.com/design-center/dallas-tx/` → `https://ubh.com`
3.  **Filter**:
    *   **Keywords**: Keeps leads matching *at least one* positive keyword (if provided).
    *   **Negative Keywords**: Removes leads matching *any* negative keyword.
    *   **Industries**: Keeps leads matching *at least one* target industry (if provided).
    *   **Website Check**: Removes leads without a valid website/domain (enabled by default, use `--no-require-website` to disable).
    *   **Email Domain Check**: Compares the email domain with the website domain. If they differ (e.g., `john@gmail.com` vs `company.com`), the email field is **cleared** (removed), but the lead is kept.
4.  **Validate Websites**: After filtering, validates all remaining websites in parallel:
    *   Makes HTTP requests to check availability
    *   Detects SSL certificate errors
    *   Detects Cloudflare/CloudFront blocks
    *   **Removes** any lead where the website is not `valid` (200 OK). Leads with SSL errors, timeouts, blocks, or invalid status codes are discarded.
5.  **Output**: Saves the filtered and validated leads to a new file or sheet (without internal status columns).

## Tools
- `execution/clean_leads.py` - Main lead cleaning script

## Output
- **If Source is File**: A new JSON file containing only the leads that passed the filters.
- **If Source is Google Sheet**: A **new tab (worksheet)** added to the **same** Google Spreadsheet containing the cleaned leads.

## Safety Rules
> [!IMPORTANT]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** file or **NEW** sheet for the cleaned output.
> - Do not use the same filename for input and output.
> - The script will error if you try to overwrite the source file.

## Instructions

### Option 1: Clean from Google Sheets -> New Google Sheet (Recommended)

This reads from an existing sheet and creates a brand new spreadsheet with the results.

```bash
.venv/bin/python execution/clean_leads.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --keywords "video editing,post production" \
  --not-keywords "marketing,advertising" \
  --industries "Media Production" \
  --output-sheet "Video Editing Leads - Cleaned (Nov 27)"
```

### Option 2: Clean from JSON -> New Google Sheet

```bash
.venv/bin/python execution/clean_leads.py \
  --source-file .tmp/raw_leads.json \
  --keywords "video editing" \
  --output-sheet "Video Editing Leads - Cleaned (Nov 27)"
```

### Option 3: Clean from JSON -> New JSON

```bash
.venv/bin/python execution/clean_leads.py \
  --source-file .tmp/raw_leads.json \
  --keywords "video editing" \
  --output .tmp/cleaned_leads_v1.json
```

### Optional Flags
- `--verbose` or `-v`: Display detailed matching information for each lead
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)
- `--min-keywords N`: Require N keywords to match instead of just 1 (default: 1)

### Example Workflow

1. **Clean scraped leads and save to new Sheet**:
   ```bash
   .venv/bin/python execution/clean_leads.py \
     --source-file .tmp/raw_leads.json \
     --keywords "newsletter,email marketing" \
     --not-keywords "seo,ppc" \
     --industries "Marketing & Advertising" \
     --output-sheet "Newsletter Leads - Cleaned" \
     --verbose
   ```

2. **Export to Google Sheets** (if needed):
   ```bash
   .venv/bin/python execution/export_to_sheets.py \
     .tmp/newsletter_leads_cleaned.json \
     --sheet-name "Newsletter Leads - Cleaned" \
     --folder-id "0ADWgx-M8Z5r-Uk9PVA"
   ```

3. **Review results**:
   The script will automatically validate all websites and output comprehensive statistics:
   ```
   Total leads loaded: 250
   After keyword filter: 180 (72%)
   After industry filter: 150
   Final clean leads: 120
   
   Validating websites...
   
   Website Validation Summary:
     valid: 95 (79.2%)
     ssl_error: 12 (10.0%)
     invalid: 8 (6.7%)
     timeout: 5 (4.2%)
   
   Exporting to Google Sheet: 'Newsletter Leads - Cleaned'...
   Sheet URL: https://docs.google.com/spreadsheets/d/NEW_SHEET_ID
   ```
   
   **Output includes:**
   - All original lead fields
   - Only leads with strictly valid websites (200 OK)
   - **Summary Report**: Shows total leads, filtered counts, and number of leads without emails (due to mismatch or missing data).

## Field Matching Logic

The script checks for keywords and industries in the following fields:
- **Company Name**: `companyName`, `company_name`
- **Company Description**: `companyDescription`, `company_description`
- **Company Industry**: `companyIndustry`, `company_industry`
- **Company Tagline**: `companyTagline`, `company_tagline`
- **Person Headline**: `personHeadline`, `person_headline`
- **Job Title**: `job_title`

The script checks for websites in:
- `companyWebsite`, `company_website`, `website`
- `companyDomain`, `company_domain`, `domain`

All matching is:
- Case-insensitive
- Partial match (substring search)
- Whitespace normalized

## Data Inspection & Low Data Strategy

**Before cleaning, inspect your source data!**

If your data **lacks** `companyDescription` or `companyTagline`:
1.  **Avoid strict keyword filtering**: Searching for "video editing" in just the Company Name will miss many relevant agencies (e.g., "Smith Productions").
2.  **Rely on Industry**: Use the `--industries` filter (e.g., "Media Production") as your primary filter.
3.  **Use Negative Keywords**: Filter *out* irrelevant companies (e.g., `--not-keywords "marketing, advertising"`) rather than filtering *in* by specific service keywords.
4.  **Target Job Titles**: Ensure your keywords include job titles if you want to filter by role (e.g., "Editor", "Producer").

**Note**: Website checking is enabled by default. All leads must have a valid website/domain. Use `--no-require-website` to disable this if needed.

**Example "Low Data" Command:**
```bash
.venv/bin/python execution/clean_leads.py \
  --source-url "..." \
  --keywords "" \
  --not-keywords "marketing,advertising" \
  --industries "Media Production" \
  --output-sheet "Cleaned Leads"
```

## Troubleshooting

- **Warning: LIMITED DATA DETECTED**: The script detected that your leads are missing descriptions or taglines. Keyword filtering might be too aggressive. Follow the "Low Data Strategy" above.
- **Error: Output file cannot be the same as source file**: You tried to overwrite the input file. Choose a different output filename.
- **Zero results after cleaning**: Your filters may be too restrictive. Try running with `--verbose` to see why leads are being filtered.
- **Google Sheets auth error**: Ensure `credentials.json` is in the project root.

## Notes

- The script preserves all original fields in the output JSON
- Leads are processed in the order they appear in the source
- The output file can be used as input to other scripts (e.g., `export_to_sheets.py`)
- If both `--source-url` and `--source-file` are provided, the script will error
- **URL Cleaning**: All website URLs are automatically cleaned to extract just the homepage/domain, removing:
  - Paths (e.g., `/new-homes/tx/waco/`)
  - Query parameters (e.g., `?utm_source=google&utm_campaign=gmb`)
  - Fragments (e.g., `#section`)

  This is especially useful for Google Maps leads which often include subpages and GMB tracking parameters. The result is always just the clean homepage URL (e.g., `https://example.com`).

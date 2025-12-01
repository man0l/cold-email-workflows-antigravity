# Email Enrichment SOP (Outscraper)

## Goal
Find and enrich leads with email addresses, phone numbers, and social media links using Outscraper's Domain Emails & Contacts API. Accepts cleaned leads from Google Sheets or JSON files and extracts publicly available contact information from company websites and social profiles.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path (typically from `.tmp/` directory, such as cleaned leads)
- **Max Leads**: Maximum number of leads to process (default: 100)
  - ⚠️ First 500 domains are FREE per month, then paid credits apply
- **API Key**: Outscraper API key (from `.env` file as `OUTSCRAPER_API_KEY`)

## Algorithm
1. **Load Data**: Reads leads from a JSON file or Google Sheet.
2. **Filter Leads**: **BY DEFAULT**, only processes leads with empty email addresses (use `--include-existing` to override).
3. **Validate Input**: Ensures each lead has a valid company domain/website.
4. **Permission Check**: **REQUIRED** - Asks for user confirmation before running, displaying:
   - Total number of leads
   - Number of leads without emails (that will be processed)
   - Free tier status (500 free domains/month)
   - Max leads limit
5. **API Calls**: For each lead without an email, makes an API call to Outscraper with:
   - Company domain (from `companyWebsite`, `company_website`, `website`, `companyDomain`, `company_domain`, `domain`)
6. **Update Leads**: Enriches the lead data with:
   - Email addresses (all found emails)
   - Phone numbers (all found phones)
   - Social media links (Facebook, LinkedIn, Twitter, Instagram, YouTube, etc.)
7. **Output**: Saves ALL leads (enriched and skipped) to a new file or sheet.

## Tools
- `execution/find_emails_outscraper.py` - Email enrichment script using Outscraper API (to be created)

## Output
- **If Source is File**: A new JSON file containing leads with enriched contact data.
- **If Source is Google Sheet**: A **new sheet/spreadsheet** with enriched lead data.

## Safety Rules
> [!IMPORTANT]
> **SAFETY GUARDS**
> - **Only enriches leads with EMPTY email addresses by default** - this prevents accidental overwriting
> - Use `--include-existing` flag if you want to process ALL leads (including those with emails)
> - First 500 domains are FREE per month - monitor usage to avoid unexpected charges
> - Always asks for user confirmation before running
> - Displays the exact number of leads that will be processed
> - Respects the max leads limit to prevent overspending

> [!WARNING]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** file or **NEW** sheet for the enriched output
> - Do not use the same filename for input and output
> - Preserve all original lead fields

## Instructions

### Option 1: Enrich from JSON → New JSON

```bash
.venv/bin/python execution/find_emails_outscraper.py \
  --source-file .tmp/cleaned_video_editing_leads.json \
  --output .tmp/enriched_video_editing_leads.json \
  --max-leads 100
```

### Option 2: Enrich from JSON → New Google Sheet

```bash
.venv/bin/python execution/find_emails_outscraper.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Enriched Leads (Outscraper - Dec 1)" \
  --max-leads 50
```

### Option 3: Enrich from Google Sheet → New JSON

```bash
.venv/bin/python execution/find_emails_outscraper.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output .tmp/enriched_leads.json \
  --max-leads 100
```

### Option 4: Enrich from Google Sheet → New Google Sheet

```bash
.venv/bin/python execution/find_emails_outscraper.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output-sheet "Enriched Leads (Outscraper - Dec 1)" \
  --max-leads 75
```

### Optional Flags
- `--verbose` or `-v`: Display detailed information for each API call
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)
- `--include-existing`: Process ALL leads including those with existing emails (by default, only leads with empty emails are enriched)
- `--full-contact-info`: Include ALL contact data (all_emails array, phones, social media). **By default, ONLY the primary email is added.**

### Example Workflow

#### Workflow A: Starting from Google Maps Leads

1. **Scrape Google Maps** (see `directives/scrape_google_maps.md`):
   ```bash
   .venv/bin/python execution/scrape_google_maps.py \
     --search-terms "plumbers in Austin, TX" \
     --max-results 100 \
     --output .tmp/google_maps_plumbers_austin.json
   ```

2. **[Optional] Clean and validate** (recommended):
   ```bash
   .venv/bin/python execution/clean_leads.py \
     --source-file .tmp/google_maps_plumbers_austin.json \
     --output .tmp/cleaned_plumbers_austin.json
   ```
   This validates websites are working and filters out invalid businesses.

3. **Enrich with emails using Outscraper**:
   ```bash
   .venv/bin/python execution/find_emails_outscraper.py \
     --source-file .tmp/cleaned_plumbers_austin.json \
     --output .tmp/enriched_plumbers_austin.json \
     --max-leads 100 \
     --verbose
   ```

4. **Export to Google Sheets**:
   ```bash
   .venv/bin/python execution/export_to_sheets.py \
     .tmp/enriched_plumbers_austin.json \
     --sheet-name "Plumbers Austin (Enriched) - Dec 1" \
     --folder-id "0ADWgx-M8Z5r-Uk9PVA"
   ```

#### Workflow B: Starting from Other Lead Sources

1. **Clean leads first** (if needed):
   ```bash
   .venv/bin/python execution/clean_leads.py \
     --source-file .tmp/raw_leads.json \
     --keywords "video editing" \
     --output .tmp/cleaned_leads.json
   ```

2. **Enrich with emails using Outscraper**:
   ```bash
   .venv/bin/python execution/find_emails_outscraper.py \
     --source-file .tmp/cleaned_leads.json \
     --output .tmp/enriched_leads.json \
     --max-leads 100 \
     --verbose
   ```

3. **Export to Google Sheets** (if needed):
   ```bash
   .venv/bin/python execution/export_to_sheets.py \
     .tmp/enriched_leads.json \
     --sheet-name "Enriched Leads - Dec 1" \
     --folder-id "0ADWgx-M8Z5r-Uk9PVA"
   ```

4. **Review results**:

   **Default output (email only)**:
   ```
   📧 Email Enrichment Tool (Outscraper)
   ==================================================

   📊 Summary:
     Total leads: 150
     Leads without email: 87
     Will process: 87 leads (only empty emails)
     Max leads limit: 100
     Free tier: 500 domains/month

   ⚠️  First 500 domains are FREE monthly
   ==================================================

   Continue? (yes/no): yes

   Processing leads... ━━━━━━━━━━━━━━━━ 87/87 100%

   ✅ Email Enrichment Summary:
      Emails found: 72 (83%)
      No email found: 15 (17%)
      Total processed: 87

   Saved to: .tmp/enriched_leads.json
   ```

   **With --full-contact-info flag** (includes phones and social):
   ```
   ✅ Email Enrichment Summary:
      Emails found: 72 (83%)
      Phones found: 68 (78%)
      Social links found: 54 (62%)
      No email found: 15 (17%)
      Total processed: 87
   ```

## API Details

### Authentication
- **Library**: `outscraper` Python package
- **Authentication**: API key from Outscraper profile
- **Method**: Python client initialization

### Installation
```bash
pip install outscraper
```

### Client Setup
```python
from outscraper import ApiClient

client = ApiClient(api_key='YOUR_API_KEY')
results = client.emails_and_contacts(['example.com'])
```

### Response Format
Outscraper returns comprehensive contact data including:
```python
{
  "domain": "example.com",
  "emails": ["contact@example.com", "info@example.com"],
  "phones": ["+1-555-123-4567", "+1-555-987-6543"],
  "facebook": "https://facebook.com/example",
  "linkedin": "https://linkedin.com/company/example",
  "twitter": "https://twitter.com/example",
  "instagram": "https://instagram.com/example",
  "youtube": "https://youtube.com/example"
}
```

**By default**, the script enriches leads with:
- `email`: Primary email address (first found) ✅ **ALWAYS ADDED**

**With `--full-contact-info` flag**, the script also adds:
- `all_emails`: List of all found email addresses
- `phone`: Primary phone number (first found)
- `all_phones`: List of all found phone numbers
- `facebook_url`: Facebook profile link
- `linkedin_url`: LinkedIn profile link
- `twitter_url`: Twitter profile link
- `instagram_url`: Instagram profile link
- `youtube_url`: YouTube profile link

## Required Fields

For the API to work, each lead must have:
- **Company Domain**: `companyWebsite`, `website`, `companyDomain`, or `domain`

Leads missing a valid domain will be skipped.

### Compatibility with Google Maps Leads

**Perfect compatibility!** Google Maps scraper outputs a `website` field, which this script automatically detects. You can pipe Google Maps leads directly into this enrichment tool:

```bash
# Google Maps → Outscraper (direct, no modifications needed)
.venv/bin/python execution/find_emails_outscraper.py \
  --source-file .tmp/google_maps_leads.json \
  --output .tmp/enriched_leads.json
```

The script will find the `website` field from Google Maps output and use it to search for emails, phones, and social media profiles.

## Cost Management

- **Free Tier**: First **500 domains per month** are FREE
- After free tier: Paid credits apply (check Outscraper pricing)
- **By default, only processes leads with empty emails** - this is the primary cost control guard
- The script will **always ask for permission** before making API calls
- Shows exact count of leads that will be processed before asking for confirmation
- Use `--max-leads` to limit processing and control costs
- Use `--include-existing` flag ONLY if you want to process leads that already have emails (usually not needed)

## Advantages Over AnyMailFinder

1. **Free Tier**: 500 free domains per month (vs paid-only for AnyMailFinder)
2. **More Contact Data**: Can find emails, phones, AND social media links (vs emails only)
3. **No Name Required**: Only needs company domain (vs first name + last name + domain)
4. **Multiple Emails**: Can return all found emails (with `--full-contact-info` flag)
5. **Public Data**: Extracts from websites, Google, Facebook, LinkedIn, etc.
6. **Cleaner Output**: By default, only adds primary email (keeps data clean)

## When to Use Outscraper vs AnyMailFinder

**Use Outscraper when:**
- You have company domains but not contact names
- You want phone numbers and social media links too
- You want to use the free tier (first 500/month)
- You need multiple email addresses per company
- You're enriching B2B leads (company-level data)

**Use AnyMailFinder when:**
- You have specific contact names (first + last)
- You need person-specific emails (not generic info@company.com)
- You want email verification scores
- You're doing personalized outreach to individuals

## Setup

Before running the script, ensure you have:

1. **Outscraper API Key**: Get your free API key from https://app.outscraper.com/profile
2. **Add to .env file**:
   ```bash
   OUTSCRAPER_API_KEY=your_api_key_here
   ```
3. **Install dependencies** (already done if you've installed requirements):
   ```bash
   pip install outscraper
   ```

## Troubleshooting

- **Error: OUTSCRAPER_API_KEY not found**: Add your API key to the `.env` file (see Setup section above)
- **Error: Outscraper library not installed**: Run `pip install outscraper` in your virtual environment
- **Error: Missing required fields**: Ensure leads have a company domain/website
- **No emails found**: The domain may not have publicly listed emails - common for privacy-focused companies
- **Rate limit errors**: The script includes automatic retry with exponential backoff
- **Permission denied**: User must confirm with "yes" to proceed
- **Invalid domain**: Ensure domains are properly formatted (e.g., "example.com" not "https://example.com")

## Notes

- The script preserves all original fields in the output
- Existing email fields are preserved unless `--include-existing` is used
- Empty or invalid responses from Outscraper leave the email field empty
- Progress bar shows real-time processing status
- All errors are logged with details for debugging
- **By default, ONLY the primary `email` field is added** (clean output)
- Use `--full-contact-info` to add `all_emails`, `phone`, `all_phones`, and social media URLs
- Social media links are only added if found (fields may be empty)

## API Documentation

- **Official Docs**: https://app.outscraper.com/api-docs
- **Python Library**: https://github.com/outscraper/outscraper-python
- **Get API Key**: https://app.outscraper.com/profile

## Sources
- [Scrape Emails and Contacts with Outscraper API](https://pipedream.com/apps/outscraper/actions/scrape-emails-contacts)
- [Domain Emails & Contacts API - Free Tier | Outscraper](https://outscraper.com/domain-emails-api/)
- [Outscraper Platform API Docs](https://app.outscraper.com/api-docs)
- [GitHub - outscraper/outscraper-python](https://github.com/outscraper/outscraper-python)
- [outscraper-python/examples/Emails And Contacts.md](https://github.com/outscraper/outscraper-python/blob/master/examples/Emails%20And%20Contacts.md)

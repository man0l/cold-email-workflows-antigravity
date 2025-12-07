# Outscraper Email Finder SOP

## Goal
Find email addresses, phone numbers, and social media contacts for leads by domain using the Outscraper Emails & Contacts API. Accepts cleaned leads with company domains/websites and enriches them with verified contact information extracted from public sources.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path (typically from `.tmp/` directory, such as cleaned leads)
- **Max Leads**: Maximum number of leads to process (default: 50)
  - ⚠️ Each API call costs credits, so this limit prevents accidental overspending
- **API Key**: Outscraper API key (from `.env` file as `OUTSCRAPER_API`)

## Algorithm
1. **Load Data**: Reads leads from a JSON file or Google Sheet.
2. **Filter Leads**: **BY DEFAULT**, only processes leads with valid domain/website URLs.
3. **Validate Domains**: Ensures each lead has a valid company domain or website field.
4. **Extract Domains**: Cleans and normalizes domain names (strips https://, www., trailing slashes).
5. **Permission Check**: **REQUIRED** - Asks for user confirmation before running, displaying:
   - Total number of leads
   - Number of leads with valid domains (that will be processed)
   - Estimated API cost (credits per domain)
   - Max leads limit
6. **API Calls**: For each lead with a domain, makes an API call to Outscraper with the domain.
7. **Update Leads**: Enriches the lead data with:
   - **Multiple email addresses** with contact names and job titles
   - **Individual contacts** (name, title, email, LinkedIn profile)
   - **Phone numbers** with source information
   - **Social media links** (Facebook, LinkedIn, Twitter, Instagram, YouTube, TikTok, WhatsApp, Discord, GitHub, Crunchbase)
   - **Company details** (industry, size, founded year, address, employee count)
8. **Output**: Saves ALL leads (enriched and skipped) to a new file or sheet.

## Tools
- `execution/outscraper_find_emails.py` - Email and contact enrichment script using Outscraper API

## Output
- **If Source is File**: A new JSON file containing leads with enriched contact data.
- **If Source is Google Sheet**: A **new sheet/spreadsheet** with enriched lead data.

## Safety Rules
> [!IMPORTANT]
> **SAFETY GUARDS**
> - **Only processes leads with valid domain/website fields** - this prevents wasted API calls
> - Automatically extracts and normalizes domains from various URL formats
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
.venv/bin/python execution/outscraper_find_emails.py \
  --source-file .tmp/cleaned_leads.json \
  --output .tmp/outscraper_enriched_leads.json \
  --max-leads 50
```

### Option 2: Enrich from JSON → New Google Sheet

```bash
.venv/bin/python execution/outscraper_find_emails.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Outscraper Enriched Leads (Dec 6)" \
  --max-leads 50
```

### Option 3: Enrich from Google Sheet → New JSON

```bash
.venv/bin/python execution/outscraper_find_emails.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output .tmp/outscraper_enriched_leads.json \
  --max-leads 100
```

### Option 4: Enrich from Google Sheet → New Google Sheet

```bash
.venv/bin/python execution/outscraper_find_emails.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output-sheet "Outscraper Enriched (Dec 6)" \
  --max-leads 75
```

### Optional Flags
- `--verbose` or `-v`: Display detailed information for each API call
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)

### Example Workflow

1. **Clean leads first** (recommended):
   ```bash
   .venv/bin/python execution/clean_leads.py \
     --source-file .tmp/google_maps_leads.json \
     --keywords "video editing" \
     --output .tmp/cleaned_leads.json
   ```

2. **Enrich with Outscraper**:
   ```bash
   .venv/bin/python execution/outscraper_find_emails.py \
     --source-file .tmp/cleaned_leads.json \
     --output .tmp/outscraper_enriched_leads.json \
     --max-leads 50 \
     --verbose
   ```

3. **Export to Google Sheets** (if needed):
   ```bash
   .venv/bin/python execution/export_to_sheets.py \
     .tmp/outscraper_enriched_leads.json \
     --sheet-name "Enriched Leads - Dec 6" \
     --folder-id "0ADWgx-M8Z5r-Uk9PVA"
   ```

4. **Review results**:
   The script will show:
   ```
   📧 Outscraper Email & Contact Finder
   ==================================================

   📊 Summary:
     Total leads: 150
     Leads with valid domains: 127
     Will process: 50 leads (max limit)
     Estimated cost: ~50 credits

   ⚠️  WARNING: This will consume API credits!
   ==================================================

   Continue? (yes/no): yes

   Processing leads... ━━━━━━━━━━━━━━━━ 50/50 100%

   ✅ Outscraper Enrichment Summary:
      Contacts found: 42 (84%)
      No contacts found: 8 (16%)
      Total processed: 50

   Saved to: .tmp/outscraper_enriched_leads.json
   ```

## API Response Format

Outscraper Emails & Contacts API returns **extremely comprehensive** contact information:

**Request Format:**
```python
from outscraper import ApiClient
client = ApiClient(api_key='YOUR_API_KEY')
results = client.emails_and_contacts(['example.com', 'company.com'])
```

**Response Structure (Actual):**
```json
{
  "query": "example.com",
  "emails": [
    {
      "value": "john@example.com",
      "full_name": "John Doe",
      "title": "CEO",
      "socials": {
        "linkedin": "https://linkedin.com/in/johndoe"
      },
      "categories": ["management"]
    }
  ],
  "phones": [
    {
      "value": "12125551234",
      "source": "website",
      "last_seen": "12/06/2025"
    }
  ],
  "socials": {
    "facebook": "https://facebook.com/company",
    "linkedin": "https://linkedin.com/company/example",
    "twitter": "https://twitter.com/example",
    "instagram": "https://instagram.com/example",
    "youtube": "https://youtube.com/channel/...",
    "tiktok": "https://tiktok.com/@example",
    "whatsapp": "https://wa.me/12125551234",
    "discord": "https://discord.gg/...",
    "github": "https://github.com/example",
    "crunchbase": "https://crunchbase.com/organization/example"
  },
  "contacts": [
    {
      "full_name": "Jane Smith",
      "title": "VP of Sales",
      "level": "C-Level",
      "value": "jane@example.com",
      "socials": {
        "linkedin": "https://linkedin.com/in/janesmith"
      }
    }
  ],
  "details": {
    "name": "Example Company",
    "industry": ["technology", "software"],
    "founded": "2015",
    "employees": "50-100",
    "size": {"f": 50, "t": 100},
    "address": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "US"
  },
  "site_data": {
    "title": "Example Company - Homepage",
    "description": "Company description...",
    "keywords": "software, saas, technology"
  }
}
```

**The script enriches leads with:**
- `emails`: Array of email objects with names, titles, and LinkedIn profiles
- `primary_email`: Best/first email found (for quick access)
- `contacts`: Array of individual contacts with full details (name, title, email, LinkedIn)
- `phones`: Array of phone objects with sources
- `primary_phone`: Best/first phone found
- `socials`: JSON object with all 10+ social media platforms
- `company_name`: Official company name from API
- `industry`: Company industry/categories
- `employees`: Employee count range
- `founded`: Company founding year
- `address`: Full company address (street, city, state, zip, country)

## Required Fields

For the API to work, each lead must have:
- **Company Domain/Website**: One of the following fields:
  - `companyWebsite`, `website`, `companyDomain`, `domain`, `company_website`, `company_domain`

The script will automatically:
- Extract domain from full URLs (e.g., `https://www.example.com/page` → `example.com`)
- Remove `www.` prefix
- Handle various URL formats

Leads missing a valid domain will be skipped.

## Cost Management

- Default max leads: **50**
- Each domain search costs approximately **1 credit**
- Outscraper offers a **free tier** with limited monthly credits
- The script will **always ask for permission** before making API calls
- Shows exact count of leads that will be processed before asking for confirmation
- Use `--max-leads` to limit processing and control costs

**Pricing (as of 2025):**
- Free tier: Limited credits per month
- Pay-as-you-go: ~$1-2 per 1000 domains with found contacts
- More affordable than per-email services for bulk enrichment

## Data Sources

Outscraper finds contact information from:
- Company websites (About, Contact pages)
- Facebook business pages
- LinkedIn company profiles
- Google Search results
- Public business directories
- Other publicly accessible sources

## Troubleshooting

- **Error: OUTSCRAPER_API not found**: Add your API key to the `.env` file
- **Error: Missing domain field**: Ensure leads have a valid website/domain field
- **No contacts found**: Domain may not have publicly listed contact information
- **Rate limit errors**: The script includes automatic retry with exponential backoff
- **Permission denied**: User must confirm with "yes" to proceed
- **Invalid domain**: Check that domains are properly formatted (script will attempt to clean them)

## Comparison with AnyMailFinder

| Feature | Outscraper | AnyMailFinder |
|---------|-----------|---------------|
| **Input** | Domain only | First name + Last name + Domain |
| **Output** | Multiple emails, phones, social media | Single email |
| **Data Source** | Public web scraping | Email pattern matching + verification |
| **Use Case** | General contact info | Specific person email |
| **Cost** | ~$1-2 per 1000 domains | ~$0.10-0.20 per email |
| **Accuracy** | High for company info | High for individual emails |

**When to use Outscraper:**
- You have domains but not contact names
- You want multiple emails (sales@, info@, etc.)
- You need phone numbers and social media
- You're doing bulk company enrichment

**When to use AnyMailFinder:**
- You have specific contact names
- You need personal email addresses
- You're doing targeted outreach
- You want email verification

## Notes

- The script preserves all original fields in the output
- Multiple emails are stored as comma-separated values
- Social media links are stored in a structured JSON field
- Empty or invalid responses leave fields empty
- Progress bar shows real-time processing status
- All errors are logged with details for debugging
- API automatically handles rate limiting with built-in delays

## Next Steps

Typical workflow after Outscraper enrichment:
```
1. Scrape Google Maps → .tmp/google_maps_leads.json
2. Clean/Filter → execution/clean_leads.py
3. Enrich with Outscraper → execution/outscraper_find_emails.py
4. (Optional) Find specific person emails → execution/find_emails.py (AnyMailFinder)
5. Export to Sheets → execution/export_to_sheets.py
6. Import to CRM/Email Tool
```

---

**Sources:**
- [Outscraper Domain Emails API](https://outscraper.com/domain-emails-api/)
- [Outscraper Python SDK on GitHub](https://github.com/outscraper/outscraper-python)
- [Outscraper API Documentation](https://app.outscraper.com/api-docs#tag/Email-Related/paths/~1emails-and-contacts/get)
- [Pipedream Outscraper Integration](https://pipedream.com/apps/outscraper/actions/scrape-emails-contacts)

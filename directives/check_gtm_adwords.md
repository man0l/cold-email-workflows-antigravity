# GTM & AdWords Detection SOP

## Goal
Analyze lead websites to detect Google Tag Manager (GTM) installation and active Google AdWords (Google Ads) campaigns to identify sales opportunities for PPC management and conversion tracking services.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path in `.tmp/` directory

## What Gets Detected

The script analyzes website HTML to detect:

### 1. Google Tag Manager (GTM)
- **Detection Method**: Scans HTML for GTM container script tags (`gtm.js?id=GTM-XXXXXX`)
- **Extracts**: GTM Container ID (e.g., `GTM-ABC123`)
- **Why It Matters**: GTM presence indicates some level of analytics setup, but may be underutilized

### 2. Google Ads Conversion Tracking
- **Detection Method**: Looks for Google Ads tracking scripts (`gtag.js`, `google_conversion_id`, `AW-` tracking IDs)
- **Extracts**:
  - Google Ads Account ID (e.g., `AW-123456789`)
  - Conversion tracking events
  - Remarketing tags
- **Why It Matters**: Indicates active Google Ads spending and potential for optimization services

## Output Fields Added

The script adds these columns to your leads:

- `gtm_installed` (boolean) - Whether GTM is detected
- `gtm_container_id` (string) - GTM container ID if found (e.g., "GTM-ABC123")
- `google_ads_detected` (boolean) - Whether Google Ads tracking is found
- `google_ads_account_id` (string) - Google Ads account ID if found (e.g., "AW-123456789")
- `conversion_tracking` (boolean) - Whether conversion tracking events are detected
- `remarketing_tag` (boolean) - Whether remarketing tags are present
- `tracking_analysis_status` - "analyzed", "failed", or "no_website"

## Use Cases

### 1. GTM Without Ads - Setup Opportunity
Target: `gtm_installed = true` AND `google_ads_detected = false`
- Companies with GTM but no ad tracking
- Opportunity: Set up Google Ads with proper conversion tracking
- Value Prop: "You have GTM ready - let's leverage it for profitable ad campaigns"

### 2. Ads Without Conversion Tracking - Optimization Opportunity
Target: `google_ads_detected = true` AND `conversion_tracking = false`
- Companies running ads but not tracking conversions properly
- Opportunity: Fix conversion tracking to improve ROI
- Value Prop: "You're spending on ads but not measuring what matters"

### 3. No GTM, No Ads - Ground Floor Opportunity
Target: `gtm_installed = false` AND `google_ads_detected = false`
- Companies with no tracking infrastructure
- Opportunity: Full setup from scratch
- Value Prop: "Start tracking your marketing performance properly"

### 4. Full Setup Present - Audit Opportunity
Target: `gtm_installed = true` AND `conversion_tracking = true`
- Companies with tracking in place
- Opportunity: Audit and optimization services
- Value Prop: "Let's audit your setup to find optimization opportunities"

## Tools
- `execution/check_gtm_adwords.py` - GTM and AdWords detection script

## Output
- **If Source is File**: A new JSON file with original lead data + tracking detection fields
- **If Source is Google Sheet**: A **new tab (worksheet)** added to the **same** Google Spreadsheet with enriched data

## Safety Rules
> [!IMPORTANT]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** file or **NEW** sheet for the output
> - Do not use the same filename for input and output
> - The script will error if you try to overwrite the source

## Instructions

### Option 1: Analyze from Google Sheets → New Tab (Recommended)

```bash
.venv/bin/python execution/check_gtm_adwords.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --sheet-name "Home Builders - Cleaned" \
  --output-sheet "Home Builders - GTM & Ads Analysis (Dec 7)"
```

### Option 2: Analyze from JSON → New Google Sheet

```bash
.venv/bin/python execution/check_gtm_adwords.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Leads - GTM & Ads Analysis (Dec 7)"
```

### Option 3: Analyze from JSON → New JSON

```bash
.venv/bin/python execution/check_gtm_adwords.py \
  --source-file .tmp/cleaned_leads.json \
  --output .tmp/leads_with_tracking.json
```

### Optional Flags
- `--verbose` or `-v`: Display detailed detection information for each lead
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)
- `--max-workers 10`: Number of concurrent threads for parallel processing (default: 10)
- `--timeout 10`: Timeout in seconds for each website request (default: 10)

## Example Workflow

1. **Start with cleaned leads** (from previous step):
   ```bash
   # Assume you have: "Cleaned Leads (Dec 7)" sheet
   ```

2. **Run GTM & AdWords detection**:
   ```bash
   .venv/bin/python execution/check_gtm_adwords.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Cleaned Leads (Dec 7)" \
     --output-sheet "Leads - With Tracking Data (Dec 7)" \
     --verbose
   ```

3. **Review results**:
   ```
   Loading leads from Google Sheet...
   Total leads loaded: 120
   Leads with websites: 115

   Analyzing GTM & Google Ads tracking...
   Progress: 115/115 [====================] 100%

   Analysis complete:
     Successfully analyzed: 110 (95.7%)
     Failed: 5 (4.3%)
     No website: 5

   GTM Detection:
     GTM Installed: 65 leads (59.1%)
     No GTM: 45 leads (40.9%)

   Google Ads Detection:
     Ads Tracking Found: 42 leads (38.2%)
     No Ads Tracking: 68 leads (61.8%)

   Conversion Tracking:
     With Conversion Tracking: 28 leads (25.5%)
     Without Conversion Tracking: 82 leads (74.5%)

   Opportunity Breakdown:
     GTM Only (no ads): 23 leads - Setup opportunity
     Ads without conversion tracking: 14 leads - Optimization opportunity
     No tracking at all: 45 leads - Ground floor opportunity
     Full setup: 28 leads - Audit opportunity

   Exporting to Google Sheet: 'Leads - With Tracking Data (Dec 7)'...
   Sheet URL: https://docs.google.com/spreadsheets/d/XYZ789/edit
   ```

4. **Filter for opportunities**:
   Open the sheet and use filters:
   - `gtm_installed = TRUE` AND `google_ads_detected = FALSE`: GTM setup ready for ads
   - `google_ads_detected = TRUE` AND `conversion_tracking = FALSE`: Fix tracking
   - `gtm_installed = FALSE` AND `google_ads_detected = FALSE`: Full setup needed

## Field Matching Logic

The script checks for website URLs in these fields:
- `companyWebsite`, `company_website`, `website`
- `companyDomain`, `company_domain`, `domain`
- `Company Website`

URLs are automatically normalized:
- Adds `https://` if missing protocol
- Removes trailing slashes
- Validates URL format before analysis

## Detection Methods

### GTM Detection
The script looks for these patterns in the HTML:
```javascript
// GTM container script
googletagmanager.com/gtm.js?id=GTM-

// GTM noscript iframe
googletagmanager.com/ns.html?id=GTM-
```

Extracts: `GTM-XXXXXX` container ID

### Google Ads Detection
The script looks for these patterns:
```javascript
// Google Ads global site tag
gtag('config', 'AW-XXXXXXXXX')

// Legacy conversion tracking
google_conversion_id

// Conversion tracking events
gtag('event', 'conversion'

// Remarketing tags
google_tag_params
```

Extracts:
- Account ID: `AW-XXXXXXXXX`
- Conversion events
- Remarketing status

## Performance

The script uses **parallel processing with ThreadPoolExecutor** for maximum speed:

- **Analysis time**: ~1-3 seconds per website (HTML download + parsing)
- **With 10 workers (default)**:
  - **100 leads**: ~1-3 minutes
  - **500 leads**: ~5-15 minutes
  - **1,000 leads**: ~10-30 minutes
- **With 20 workers** (faster, more aggressive):
  - **100 leads**: ~30-90 seconds
  - **500 leads**: ~2-8 minutes
  - **1,000 leads**: ~5-15 minutes

You can adjust the `--max-workers` parameter to control parallelization (higher = faster but more resource intensive).

## Error Handling

The script handles common issues gracefully:

| Issue | Behavior |
|-------|----------|
| No website found | Skips lead, sets `tracking_analysis_status` = "no_website" |
| Invalid URL | Skips lead, sets `tracking_analysis_status` = "failed" |
| Timeout | Retries 2x with exponential backoff, then marks "failed" |
| SSL Error | Attempts HTTP fallback, then marks "failed" if both fail |
| Connection Error | Marks as "failed" |
| Blocked by Cloudflare | Marks as "failed" (cannot bypass programmatically) |

## Troubleshooting

### Common Issues
- **High failure rate**: Some websites block automated requests. This is expected (10-20% failure rate is normal)
- **Slow execution**: Reduce `--batch-size` to 3 for more stable processing
- **Timeout errors**: Increase `--timeout` to 15 or 20 seconds
- **All analyses failed**: Check your internet connection

### False Negatives
The script may miss tracking in these cases:
- **JavaScript-loaded tags**: Tags loaded dynamically after page load
- **Server-side GTM**: GTM running server-side (less common)
- **Obfuscated code**: Heavily minified or obfuscated tracking code
- **Single Page Apps**: React/Vue apps that load tracking after initial HTML

**Accuracy**: ~85-95% for standard website setups. False negatives are possible but rare.

## Data Interpretation Guide

### Opportunity Tiers

**Tier 1 (Hot Leads)**: Ads without conversion tracking
- `google_ads_detected = TRUE` AND `conversion_tracking = FALSE`
- They're spending money but not measuring ROI
- High urgency, clear pain point

**Tier 2 (Warm Leads)**: GTM but no ads
- `gtm_installed = TRUE` AND `google_ads_detected = FALSE`
- Infrastructure is ready, just need campaigns
- Medium urgency, clear opportunity

**Tier 3 (Cold Leads)**: No tracking at all
- `gtm_installed = FALSE` AND `google_ads_detected = FALSE`
- Need full education and setup
- Low urgency, but large potential project

**Tier 4 (Audit Leads)**: Full setup present
- `gtm_installed = TRUE` AND `conversion_tracking = TRUE`
- May still have optimization opportunities
- Requires audit to identify specific issues

## Notes

- The script only analyzes the homepage HTML (not the entire site)
- Some tracking tags may load after initial page render (JavaScript-based)
- GTM containers can be empty or misconfigured - detection only confirms presence
- Google Ads account IDs are extracted when found, but may not always be visible in HTML
- The script preserves all original lead fields in the output
- Analysis is read-only and does not interact with the website beyond fetching HTML

## Advanced Usage

### Chain with Other Directives

```bash
# Step 1: Scrape leads
.venv/bin/python execution/scrape_google_maps.py \
  --query "home builders in Texas" \
  --fetch-count 100 \
  --output .tmp/raw_leads.json

# Step 2: Clean leads
.venv/bin/python execution/clean_leads.py \
  --source-file .tmp/raw_leads.json \
  --keywords "custom homes,home builder" \
  --output .tmp/cleaned_leads.json

# Step 3: Analyze tracking setup
.venv/bin/python execution/check_gtm_adwords.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Home Builders - With Tracking (Dec 7)"

# Step 4 (Optional): Add PageSpeed data
.venv/bin/python execution/analyze_pagespeed.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Home Builders - Full Analysis (Dec 7)"
```

### Combine with PageSpeed for Full Picture

Run both GTM/AdWords detection AND PageSpeed analysis to identify:
- Poor website performance + No ads = Need full website rebuild + marketing setup
- Good performance + GTM but no ads = Marketing-ready, just need campaigns
- Poor SEO + Ads without conversion tracking = Wasting ad spend on broken setup

## Expected Output Columns

The output will contain all original columns plus:

```
[Original Columns] + gtm_installed + gtm_container_id + google_ads_detected +
google_ads_account_id + conversion_tracking + remarketing_tag + tracking_analysis_status
```

- `gtm_installed`: TRUE/FALSE
- `gtm_container_id`: "GTM-ABC123" or empty
- `google_ads_detected`: TRUE/FALSE
- `google_ads_account_id`: "AW-123456789" or empty
- `conversion_tracking`: TRUE/FALSE
- `remarketing_tag`: TRUE/FALSE
- `tracking_analysis_status`: "analyzed", "failed", or "no_website"

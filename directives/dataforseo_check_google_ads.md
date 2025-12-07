# DataForSEO Google Ads Detection SOP

## Goal
Validate which leads are **actually running Google Ads campaigns** by checking for active ads for their domains using DataForSEO's Google Ads Search API. This provides definitive proof of ad spend for targeted sales outreach.

## Inputs
- **Google Spreadsheet URL** (accessible via `credentials.json`)
- **Sheet Name** - Sheet with leads (can include all leads or pre-filtered)

> [!IMPORTANT]
> **AUTOMATIC PRE-FILTERING**
> - The script **automatically filters** for leads with `google_ads_detected = TRUE` from GTM/AdWords check
> - Leads without GTM tracking are auto-skipped (no API call = no cost)
> - You can pass ALL leads - the script handles filtering internally
> - Only leads with `google_ads_detected = TRUE` AND a website domain will be analyzed
> - This validates which companies with tracking code are **actively running ads**

## What Gets Detected

The script uses DataForSEO's Google Ads Search SERP API to:
1. Search for the company/brand name in Google
2. Check if Google Ads appear in the search results
3. Determine if the company is running ads for their own brand name

### Detection Method
- **API Used**: DataForSEO SERP API - Google Ads Search (`/v3/serp/google/ads_search/live/advanced`)
- **Search Query**: Company name (e.g., "Acme Construction")
- **Priority**: Normal (standard processing)
- **What It Detects**: Presence of Google Ads in search results for the company's brand

## Output Fields Added

The script adds these columns to your leads (prefixed with `dataforseo_` to avoid conflicts with GTM check):

- `dataforseo_google_ads_detected` (boolean) - Whether Google Ads were found in search results for this company
- `ads_count` (number) - Number of ads detected in search results (empty if 0)
- `ads_position` (string) - Position of ads (e.g., "top", "bottom", "both")
- `competitor_ads` (boolean) - Whether competitors are bidding on this company's brand name
- `dataforseo_status` - "analyzed", "failed", "no_results", "no_website", or "skipped_no_gtm_tracking"
- `dataforseo_cost` (number) - Cost in USD for this API call (0.0 for skipped leads)

## Use Cases

### 1. Confirmed Active Advertisers - High-Priority Leads
Target: `dataforseo_google_ads_detected = TRUE`
- **Confirmed active ad spend** - not just tracking code
- Opportunity: Optimization and account audit services
- Value Prop: "We analyzed your active Google Ads - here are 3 ways to improve ROI"

### 2. Tracking Code But No Active Ads - Paused/Failed Campaigns
Target: GTM shows `google_ads_detected = TRUE`, but `dataforseo_google_ads_detected = FALSE`
- Have tracking installed but campaigns are paused or failed
- Opportunity: Reactivation and campaign rescue
- Value Prop: "Your Google Ads tracking is set up but campaigns aren't running - let's fix that"

### 3. Multiple Ad Positions - Heavy Spenders
Target: `ads_position = "both"` (top AND bottom ads)
- Running multiple ad placements simultaneously
- Indicates significant ad budget
- Opportunity: High-value optimization contracts
- Value Prop: "You're spending heavily on ads - let's ensure every dollar counts"

### 4. Recommended Workflow: 2-Step Process
**Automated filtering (script handles it):**
1. Run `check_gtm_adwords.md` (FREE) to detect tracking code - outputs sheet with `google_ads_detected` column
2. Run THIS directive (PAID) on that sheet - script auto-filters for `google_ads_detected = TRUE`
3. Script analyzes only qualified leads, skips the rest automatically
4. Compare GTM vs DataForSEO results to find paused campaigns vs active campaigns

## Tools
- `execution/dataforseo_check_google_ads.py` - DataForSEO Google Ads detection script

## API Costs & Pricing

### DataForSEO Pricing (as of Dec 2024)
- **API**: Google Ads Search SERP
- **Endpoint**: `/v3/serp/google/ads_search/task_post`
- **Priority**: Normal (task-based)
- **Cost**: **$0.0006 per request** ($600 per million = $0.0006 per task)

### Cost Examples
- **100 leads**: $0.06 (6 cents)
- **500 leads**: $0.30 (30 cents)
- **1,000 leads**: $0.60 (60 cents)
- **5,000 leads**: $3.00
- **10,000 leads**: $6.00

**Note**: You are ONLY charged for leads that have company names and get analyzed. Leads without company names are skipped at no cost.

### Cost Confirmation
> [!IMPORTANT]
> **ALWAYS CONFIRM BEFORE RUNNING**
> - The script will calculate the estimated cost based on leads with company names
> - It will display the cost estimate and ask for confirmation
> - You must type `yes` to proceed
> - Typing anything else will cancel the operation
> - No charges occur until you confirm

## Output
- **A new tab (worksheet)** added to the **same** Google Spreadsheet with enriched data
- The new sheet will include all original columns plus the new Google Ads detection fields

## Safety Rules
> [!IMPORTANT]
> **COST AWARENESS**
> - Script estimates cost BEFORE running any API calls
> - Requires explicit user confirmation to proceed
> - Shows final cost in summary output
> - Tracks cost per lead in `dataforseo_cost` column

> [!IMPORTANT]
> **NEVER OVERWRITE DATA**
> - Always create a **NEW** sheet for the output
> - Do not use the same sheet name for input and output
> - The script will error if you try to overwrite the source

## Instructions

### Standard Usage: Analyze from Google Sheets → New Tab

> [!NOTE]
> **AUTOMATIC FILTERING**
> The script automatically filters for `google_ads_detected = TRUE` from GTM check.
> You can pass the full GTM analysis sheet - the script handles filtering internally.

```bash
.venv/bin/python execution/dataforseo_check_google_ads.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --sheet-name "Leads - GTM Analysis (Dec 7)" \
  --output-sheet "Leads - Google Ads Validated (Dec 7)"
```

**What happens:**
- Script loads ALL leads from your sheet
- Auto-filters for `google_ads_detected = TRUE` (from GTM check)
- Analyzes only qualified leads via DataForSEO API
- Skips leads without GTM tracking (no cost)
- Skips leads without website domains (no cost)

### Recommended Workflow: Pass GTM Output Directly

**Step-by-step process:**

1. **First run FREE GTM detection**:
   ```bash
   .venv/bin/python execution/check_gtm_adwords.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Cleaned Leads" \
     --output-sheet "Leads - GTM Analysis (Dec 7)"
   ```
   Result: Creates sheet with `google_ads_detected` column

2. **Run DataForSEO on the SAME sheet** (script auto-filters):
   ```bash
   .venv/bin/python execution/dataforseo_check_google_ads.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Leads - GTM Analysis (Dec 7)" \
     --output-sheet "Leads - Active Ads Validated (Dec 7)"
   ```
   Result: Script analyzes only leads with GTM tracking, skips the rest

**Cost efficiency:**
- If you have 1,000 leads and only 200 have Google Ads tracking:
  - Script analyzes: 200 leads = **$0.12**
  - Script auto-skips: 800 leads = **$0.00**
  - Total cost: **$0.12** (same as manual filtering!)
- No manual filtering needed - the script is smart enough

### Optional Flags
- `--verbose` or `-v`: Display detailed API responses for each lead
- `--batch-size 10`: Number of concurrent tasks (default: 10, max: 100)
- `--location "United States"`: Google search location (default: "United States")
- `--language "en"`: Search language (default: "en")

## Example Workflow

> [!IMPORTANT]
> This example shows the CORRECT workflow with automatic filtering

1. **Start with cleaned leads**:
   ```bash
   # You have: "Cleaned Leads (Dec 7)" sheet with 500 leads
   ```

2. **STEP 1: Run FREE GTM/AdWords check**:
   ```bash
   .venv/bin/python execution/check_gtm_adwords.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Cleaned Leads (Dec 7)" \
     --output-sheet "Leads - GTM Analysis (Dec 7)"
   ```
   Result: 150 leads have `google_ads_detected = TRUE`, 350 have `FALSE`

3. **STEP 2: Run PAID DataForSEO validation** (script auto-filters):
   ```bash
   .venv/bin/python execution/dataforseo_check_google_ads.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Leads - GTM Analysis (Dec 7)" \
     --output-sheet "Leads - Active Ads Validated (Dec 7)" \
     --verbose
   ```
   Script automatically filters and shows:
   - Leads with GTM tracking: 150 (will analyze)
   - Leads without GTM tracking: 350 (auto-skipped)
   - Cost: $0.09 (150 leads × $0.0006)

4. **Review cost estimate and confirm**:
   ```
   Loading leads from Google Sheet...
   Total leads loaded: 500
   
   ============================================================
                   MANDATORY FILTER APPLIED
   ============================================================
   Leads with google_ads_detected = TRUE: 150
     - With website domains (will analyze): 150
     - Without website domains (skipped): 0
   Leads without GTM tracking (auto-skipped): 350
   ============================================================
   
   ============================================================
                COST ESTIMATE - DataForSEO API
   ============================================================
   API: Google Ads Search SERP
   Endpoint: /v3/serp/google/ads_search/task_post
   Mode: Task-based (not live)
   Cost per task: $0.0006
   
   Leads to analyze: 150
   Estimated cost: $0.09
   ============================================================
   
   ⚠️  This will charge your DataForSEO account $0.09
   
   Do you want to proceed? (yes/no): yes
   ```

5. **Review results**:
   ```
   Processing in batches of 100 tasks per API call...
   Posting batch 1 (100 tasks)...
   Progress: 100/150 (66.7%)
   Posting batch 2 (50 tasks)...
   Progress: 150/150 (100.0%)
   
   ============================================================
                     ANALYSIS COMPLETE
   ============================================================
   Successfully analyzed: 145 (29%)
   No results: 3
   Failed: 2
   Skipped (no GTM tracking): 350
   Skipped (no website): 0
   
   Google Ads Detection:
     Ads Detected: 58 (40%)
     No Ads Found: 87 (60%)
   
   Ad Positions:
     Top ads: 52 (35%)
     Bottom ads: 6 (4%)
   
   Competitor Analysis:
     Competitors bidding on brand: 12 (8%)
   
   Average ads per company: 2.1
   
   ============================================================
                      ACTUAL API COST
   ============================================================
   Total API calls: 148
   Cost per call: $0.0006
   TOTAL COST: $0.09
   ============================================================
   
   Opportunity Breakdown:
     Already running ads: 58 - Optimization opportunity
     Competitors bidding (but not you): 12 - Defensive opportunity
     No ads at all: 87 - Ground floor opportunity
   
   Exporting to Google Sheet: 'Leads - Active Ads Validated (Dec 7)'...
   Sheet URL: https://docs.google.com/spreadsheets/d/XYZ789/edit
   ```

6. **Analyze validated results**:
   Compare GTM check vs DataForSEO validation:
   - `dataforseo_status = "analyzed"` AND `dataforseo_google_ads_detected = TRUE`: **Active campaigns confirmed**
   - `dataforseo_status = "analyzed"` AND `dataforseo_google_ads_detected = FALSE`: **Paused/inactive campaigns**
   - `dataforseo_status = "skipped_no_gtm_tracking"`: **No GTM tracking** (auto-skipped, no cost)
   - `ads_position = "both"`: **High ad spend** (top priority)
   - `ads_count` > 3: **Multiple active ads** (sophisticated advertiser)

## Field Matching Logic

The script checks for website domains in these fields (in order of priority):
- `companyWebsite`, `company_website`, `website`
- `companyDomain`, `company_domain`, `domain`
- `Company Website`

**Domain Normalization:**
- Removes `https://`, `http://`, and `www.`
- Removes paths (everything after first `/`)
- Example: `https://www.example.com/about` → `example.com`

**Note**: Leads without a website domain will be skipped (no API call = no cost).

## API Implementation Details

### Request Format
Uses task-based endpoint (not live) with domain-based search:
```json
{
  "location_name": "United States",
  "platform": "google_search",
  "target": "example.com"
}
```

The script:
1. Posts up to 100 tasks per API call (bulk posting)
2. Waits for task completion (~3-10 seconds)
3. Retrieves results for all tasks
4. Analyzes ad presence, count, and positions

### Response Processing
The script analyzes the API results to:
1. Count total active Google Ads for the domain
2. Identify ad positions (top ads vs bottom ads)
3. Determine if running multiple ad placements
4. Calculate cost per lead analyzed

### Task vs Live Endpoints
- **Task endpoint** (used): Posts tasks, waits for results, $0.0006 per task (83% cheaper!)
- **Live endpoint** (NOT used): Instant results, $0.0075 per request

**This script always uses task-based endpoint** for optimal cost efficiency.

## Performance

### API Speed
- **Task processing time**: ~3-10 seconds per task (includes posting + waiting + retrieval)
- **Batch processing**: Up to 100 tasks can be posted at once
- **With 10 workers (default)**:
  - **100 leads**: ~1-3 minutes
  - **500 leads**: ~5-15 minutes
  - **1,000 leads**: ~10-30 minutes
- **With 50 workers** (higher):
  - **100 leads**: ~30-60 seconds
  - **500 leads**: ~2-5 minutes
  - **1,000 leads**: ~5-10 minutes

### Rate Limits
DataForSEO has generous rate limits:
- **Task posting**: Up to 2,000 tasks per minute
- **Concurrent tasks**: Up to 100 simultaneous tasks

The script defaults to 10 workers to balance speed and stability.

## Error Handling

The script handles common issues gracefully:

| Issue | Behavior | Cost Impact |
|-------|----------|-------------|
| No GTM tracking | Auto-skips, sets `dataforseo_status` = "skipped_no_gtm_tracking" | **No charge** |
| No website domain found | Skips lead, sets `dataforseo_status` = "no_website" | **No charge** |
| API error | Retries with wait, then marks "failed" | Charged only once |
| Invalid API key | Exits immediately with error message | **No charge** |
| Insufficient credits | Exits with error, shows current balance | **No charge** |
| Task in queue | Waits up to 60 seconds for completion | Normal charge when complete |
| No search results | Marks as "no_results" (domain has no ads) | **Charged** (valid API call) |

## API Setup Requirements

### 1. Get DataForSEO API Key

1. Sign up at [https://dataforseo.com/](https://dataforseo.com/)
2. Navigate to Dashboard → API Access
3. Copy your API credentials (login + password)
4. Add to `.env` file:
   ```
   DATAFORSEO_API_USERNAME=your_email@example.com
   DATAFORSEO_API_KEY=your_api_password
   ```

**Alternative format**: You can also use a single combined key:
   ```
   DATAFORSEO_API_KEY=your_login:your_password
   ```

### 2. Add Credits to Account

DataForSEO is pay-as-you-go:
- Minimum deposit: $10
- Recommended for testing: $25
- Credits never expire

### 3. Verify Access

The script will automatically verify API access and check your balance before running.

## Troubleshooting

### Cost & Billing Issues
- **"Insufficient credits"**: Add more credits to your DataForSEO account
- **Unexpected high cost**: Check for duplicate leads or missing filters
- **Cost mismatch**: Failed requests are not charged; only successful API calls count

### API Errors
- **"Invalid API credentials"**: Check `.env` file format (`login:password`)
- **"API key not found"**: Ensure `DATAFORSEO_API_KEY` is set in `.env`
- **"Rate limit exceeded"**: Reduce `--batch-size` to 5 or lower

### Data Errors
- **"No company name field found"**: Your leads don't have company name columns
- **"All analyses failed"**: Check your internet connection or API credentials
- **High failure rate**: Normal if company names are generic (e.g., "LLC", "Inc")

## Data Interpretation Guide

### Ad Detection Confidence Levels

**High Confidence (google_ads_detected = TRUE)**:
- Clear Google Ads detected in search results
- Company is actively bidding on their brand name
- Strong signal for optimization services

**Medium Confidence (google_ads_detected = FALSE, competitor_ads = TRUE)**:
- No ads from the company itself
- But competitors are bidding on their brand
- Defensive bidding opportunity

**Low Confidence (google_ads_detected = FALSE)**:
- No ads detected in search results
- Could mean: not running ads, very low budget, or different brand name than company name
- May need manual verification

### Opportunity Prioritization

**Tier 1 (Hottest Leads)**: Confirmed active advertisers with high spend
- `google_ads_detected = TRUE` (DataForSEO) AND `ads_position = "both"`
- Running ads in multiple positions = high budget
- **Immediate outreach opportunity**

**Tier 2 (Hot Leads)**: Confirmed active advertisers
- `google_ads_detected = TRUE` (DataForSEO)
- Active campaigns validated
- **Optimization and audit opportunities**

**Tier 3 (Warm Leads)**: Tracking but no active ads
- GTM shows `google_ads_detected = TRUE`, DataForSEO shows `FALSE`
- Paused or failed campaigns
- **Reactivation opportunity**

**Tier 4 (Not Recommended)**: No tracking, no ads
- Both checks show `FALSE`
- Long sales cycle, educational selling required
- **Skip these for higher ROI targets**

## Combining with GTM/AdWords Detection

For best results, use both directives together:

### Step 1: Free HTML Analysis (check_gtm_adwords.md)
- Analyzes website HTML for GTM and Google Ads tracking code
- **Cost**: Free
- **Speed**: Fast (parallel processing)
- **Detects**: Tracking code presence on website

### Step 2: Paid SERP Analysis (this directive)
- Checks if ads actually appear in Google search results
- **Cost**: $0.0075 per lead
- **Speed**: Moderate (API rate limits)
- **Detects**: Active ad campaigns in search results

### Combined Insights
| GTM/AdWords (Free) | DataForSEO (Paid) | Interpretation |
|-------------------|-------------------|----------------|
| `google_ads_detected = TRUE` | `dataforseo_google_ads_detected = TRUE` | Confirmed active campaigns |
# DataForSEO Google Ads Check

## Goal
Detect if companies are running Google Ads by querying the DataForSEO **Google Ads Advertisers** API. This checks the Google Ads Transparency Center database for active advertisers.

## Inputs
- **Source**: Google Sheet URL
- **Sheet Name**: Name of the tab to read
- **Output Sheet**: Name of the tab to create/overwrite

## Logic
1. **Load Leads**: Reads leads from the Google Sheet.
2. **Filter**:
   - Checks if `google_ads_detected` is TRUE (from GTM check).
   - Skips leads without a valid Company Name.
3. **Query DataForSEO**:
   - Uses the `ads_advertisers` API endpoint (`/v3/serp/google/ads_advertisers/task_post`).
   - Searches by **Company Name** (e.g., "RVision Homes LTD").
   - **Multi-Period Analysis**: Queries 3 time periods for each lead:
     1. **All Time**: No date filter (default 12 months).
     2. **Last 1 Month**: Ads active in the last 30 days.
     3. **Last 3 Months**: Ads active in the last 90 days.
4. **Analyze Results**:
   - Extracts `approx_ads_count` from the advertiser data.
   - Determines if ads are detected based on the "All Time" count.
5. **Export**: Writes results to the output sheet.

## Outputs
The following columns are added to the output sheet:

| Column | Description |
|--------|-------------|
| `dataforseo_google_ads_detected` | `TRUE` if ads found (all-time), `FALSE` otherwise |
| `ads_count` | Total ads found (all-time) |
| `ads_count_all_time` | Total ads found (last 12 months) |
| `ads_count_1_month` | Ads found in the last 30 days |
| `ads_count_3_months` | Ads found in the last 90 days |
| `ads_position` | (Empty - not applicable for advertiser API) |
| `competitor_ads` | `FALSE` (Advertiser API only shows company's own ads) |
| `dataforseo_status` | `analyzed`, `failed`, `no_results` |
| `dataforseo_cost` | Cost of the API calls ($0.0018 per lead) |

## API Cost
- **Per Query**: $0.0006
- **Queries Per Lead**: 3 (All-time, 1-month, 3-months)
- **Total Cost Per Lead**: **$0.0018**
- **Example**: 100 leads = $0.18

## Usage

```bash
.venv/bin/python execution/dataforseo_check_google_ads.py \
  --source-url "https://docs.google.com/spreadsheets/d/..." \
  --sheet-name "Sheet1" \
  --output-sheet "Ads Analysis"
```

## Notes
- Requires `DATAFORSEO_API_USERNAME` and `DATAFORSEO_API_KEY` in `.env`.
- The script automatically handles batching (though effectively sequential due to multi-period logic).
- Rate limits are handled by the API client.
```bash
.venv/bin/python execution/dataforseo_check_google_ads.py \
  --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
  --sheet-name "All Leads" \
  --verbose
```

**Note**: Higher batch size = faster processing. DataForSEO supports up to 100 concurrent tasks.

## Expected Output Columns

The output will contain all original columns plus:

```
[Original Columns] + dataforseo_google_ads_detected + ads_count +
ads_position + competitor_ads + dataforseo_status + dataforseo_cost
```

- `dataforseo_google_ads_detected`: TRUE/FALSE (or empty if skipped)
- `ads_count`: Numeric (1, 2, 3+) or empty if 0
- `ads_position`: "top", "bottom", "both", or empty
- `competitor_ads`: TRUE/FALSE (or empty if skipped)
- `dataforseo_status`: "analyzed", "failed", "no_results", "no_website", or "skipped_no_gtm_tracking"
- `dataforseo_cost`: Numeric (0.0006 for analyzed leads, 0.0 for skipped)

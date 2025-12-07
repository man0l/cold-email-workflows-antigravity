# PageSpeed Analysis SOP

## Goal
Enrich leads with website performance and SEO scores using Google's PageSpeed Insights API to identify sales opportunities for web optimization services.

## Inputs
- **Data Source** (one of):
  - Google Spreadsheet URL (accessible via `credentials.json`)
  - JSON file path in `.tmp/` directory

**Note**: The script always analyzes **mobile performance** as it's the most relevant for modern web and uses stricter criteria.

## What Gets Added

The script adds these columns to your leads:

- `performance_score` (0-100) - Overall mobile performance rating
- `seo_score` (0-100) - Mobile SEO quality score
- `pagespeed_status` - "analyzed", "failed", or "no_website"

### Score Interpretation
- **90-100**: Good (fast, well-optimized)
- **50-89**: Needs Improvement (moderate performance/SEO)
- **0-49**: Poor (significant optimization needed)

## Use Cases

### 1. Web Performance Services
Target companies with low performance scores (<60):
- Website speed optimization
- Core Web Vitals improvements
- Hosting/CDN recommendations

### 2. SEO Services
Target companies with low SEO scores (<70):
- Technical SEO improvements
- On-page optimization
- Meta tag and schema markup fixes

### 3. Complete Web Overhaul
Target companies with BOTH scores <50:
- Full website rebuild
- Modern framework migration
- Comprehensive optimization

## Tools
- `execution/analyze_pagespeed.py` - PageSpeed analysis script

## Output
- **If Source is File**: A new JSON file with original lead data + PageSpeed scores
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
.venv/bin/python execution/analyze_pagespeed.py \
  --source-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit" \
  --output-sheet "Leads - PageSpeed Analysis (Dec 7)"
```

### Option 2: Analyze from JSON → New Google Sheet

```bash
.venv/bin/python execution/analyze_pagespeed.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Leads - PageSpeed Analysis (Dec 7)"
```

### Option 3: Analyze from JSON → New JSON

```bash
.venv/bin/python execution/analyze_pagespeed.py \
  --source-file .tmp/cleaned_leads.json \
  --output .tmp/leads_with_pagespeed.json
```

### Optional Flags
- `--verbose` or `-v`: Display detailed analysis for each lead
- `--sheet-name "Sheet1"`: Specify source sheet name when using Google Sheets (default: first sheet)
- `--batch-size 10`: Number of concurrent API requests (default: 5, max: 10)

## Example Workflow

1. **Start with cleaned leads** (from previous step):
   ```bash
   # Assume you have: "Cleaned Leads (Dec 7)" sheet
   ```

2. **Run PageSpeed analysis**:
   ```bash
   .venv/bin/python execution/analyze_pagespeed.py \
     --source-url "https://docs.google.com/spreadsheets/d/ABC123/edit" \
     --sheet-name "Cleaned Leads (Dec 7)" \
     --output-sheet "Leads - With PageSpeed (Dec 7)" \
     --verbose
   ```

3. **Review results**:
   ```
   Loading leads from Google Sheet...
   Total leads loaded: 120
   Leads with websites: 115

   Analyzing PageSpeed...
   Progress: 115/115 [====================] 100%

   Analysis complete:
     Successfully analyzed: 110 (95.7%)
     Failed: 5 (4.3%)
     No website: 5

   Performance Score Distribution:
     Good (90-100): 25 leads (22.7%)
     Needs Improvement (50-89): 60 leads (54.5%)
     Poor (0-49): 25 leads (22.7%)

   SEO Score Distribution:
     Good (90-100): 45 leads (40.9%)
     Needs Improvement (50-89): 50 leads (45.5%)
     Poor (0-49): 15 leads (13.6%)

   Average Scores:
     Performance: 68.3
     SEO: 81.2

   Exporting to Google Sheet: 'Leads - With PageSpeed (Dec 7)'...
   Sheet URL: https://docs.google.com/spreadsheets/d/XYZ789/edit
   ```

4. **Filter for opportunities**:
   Open the sheet and use filters:
   - `performance_score` < 50: High-priority web performance leads
   - `seo_score` < 70: SEO service opportunities
   - Both < 60: Full website overhaul candidates

## Field Matching Logic

The script checks for website URLs in these fields:
- `companyWebsite`, `company_website`, `website`
- `companyDomain`, `company_domain`, `domain`
- `Company Website`

URLs are automatically normalized:
- Adds `https://` if missing protocol
- Removes trailing slashes
- Validates URL format before analysis

## API Rate Limits & Performance

### Google PageSpeed Insights API (FREE)
- **Daily quota**: 25,000 requests per day (hard limit)
- **Rate limit**: 400 requests per 100 seconds (~4 per second theoretical max)
- **No cost**: Completely free API
- **Practical limit**: Script uses 1.5 requests/second to avoid undocumented throttling

### Performance Expectations
- **API response time**: ~2-5 seconds per website
- **100 leads**: ~7-12 minutes (with safe rate limiting)
- **500 leads**: ~35-60 minutes
- **1,000 leads**: ~70-120 minutes (1-2 hours)
- The script automatically:
  - Tracks requests per 100-second window
  - Enforces safe delays between requests
  - Warns if approaching daily quota
  - Shows time estimates before starting

### Rate Limiting Implementation
The script implements intelligent rate limiting:
1. **Safe delay**: 0.67 seconds between requests (~1.5 req/sec)
2. **Window tracking**: Monitors requests per 100-second window
3. **Auto-throttle**: Automatically waits if approaching 400 req/100sec limit
4. **Daily quota check**: Warns if lead count exceeds 25,000

## Error Handling

The script handles common issues gracefully:

| Issue | Behavior |
|-------|----------|
| No website found | Skips lead, sets `pagespeed_status` = "no_website" |
| Invalid URL | Skips lead, sets `pagespeed_status` = "failed" |
| API error | Retries 3x with exponential backoff, then marks "failed" |
| Rate limit hit | Automatically throttles requests |
| Timeout | Retries up to 3 times with increasing timeout |

## API Setup Requirements

### 1. Enable PageSpeed Insights API
Go to Google Cloud Console:
```
https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com
```
Click "Enable" for your project.

### 2. Authentication
Uses existing `credentials.json` (service account) - no additional setup needed.

### 3. Verify Access
The script will automatically verify API access on first run.

## Data Interpretation Guide

### Performance Score Segments

| Score Range | Category | What It Means | Sales Opportunity |
|------------|----------|---------------|-------------------|
| 90-100 | Excellent | Very fast, well-optimized | Low priority |
| 70-89 | Good | Decent performance, minor improvements | Medium priority |
| 50-69 | Moderate | Noticeable slowness, needs work | High priority |
| 0-49 | Poor | Very slow, major issues | Highest priority |

### SEO Score Segments

| Score Range | Category | What It Means | Sales Opportunity |
|------------|----------|---------------|-------------------|
| 90-100 | Excellent | SEO best practices followed | Low priority |
| 70-89 | Good | Minor SEO issues | Medium priority |
| 50-69 | Moderate | Missing important SEO elements | High priority |
| 0-49 | Poor | Major SEO problems | Highest priority |

### Sales Prioritization Strategy

**Tier 1 (Hot Leads)**: Both scores < 50
- Likely need complete website overhaul
- High-value opportunity for comprehensive services

**Tier 2 (Warm Leads)**: Performance < 60 OR SEO < 70
- Clear pain point identified
- Targeted service opportunity

**Tier 3 (Cold Leads)**: Both scores > 70
- Website is reasonably well-optimized
- Lower likelihood of needing services

## Troubleshooting

### API Errors
- **"API not enabled"**: Enable PageSpeed Insights API in Google Cloud Console
- **"Quota exceeded"**: You've hit 25,000 requests/day limit. Wait until tomorrow.
- **"Rate limit"**: Script handles this automatically with backoff

### Data Errors
- **"No website field found"**: Your leads don't have website/domain columns
- **"All analyses failed"**: Check your internet connection or API key permissions
- **Zero results**: Check that your source sheet/file has valid data

### Performance Issues
- **Very slow execution**: Reduce `--batch-size` to 3 for more stable processing
- **Timeout errors**: Normal for very slow websites, script will retry automatically

## Notes

- The API is **completely free** (25,000 requests/day)
- Results are cached by Google for ~24 hours (repeated analyses of same URL return cached data)
- Always uses **mobile analysis** as it's stricter and most relevant for modern web
- The script preserves all original lead fields in the output
- PageSpeed scores are based on **Lab Data** (simulated testing) which is available for all websites
- Field Data (real user metrics) is only available for popular sites and is NOT included in this analysis

## What Gets Analyzed

The PageSpeed Insights API analyzes:

### Performance Score Factors
- Largest Contentful Paint (LCP) - Main content load time
- First Contentful Paint (FCP) - First visual content
- Speed Index - Visual display speed
- Time to Interactive (TTI) - When page becomes interactive
- Total Blocking Time (TBT) - Blocking time
- Cumulative Layout Shift (CLS) - Visual stability

### SEO Score Factors
- Meta tags (title, description)
- Viewport configuration
- Font size readability
- Tap targets (mobile)
- Image alt attributes
- Structured data
- robots.txt and sitemap
- HTTPS usage
- Crawlability

## Advanced Usage

### Filter in Google Sheets After Analysis

1. **Find performance opportunities**:
   - Filter: `performance_score` < 60
   - Sort by: Performance score ascending (worst first)

2. **Find SEO opportunities**:
   - Filter: `seo_score` < 70
   - Sort by: SEO score ascending (worst first)

3. **Find high-value leads** (multiple issues):
   - Filter: `performance_score` < 50 AND `seo_score` < 70
   - These companies likely need comprehensive help

### Chain with Other Directives

```bash
# Step 1: Scrape leads
.venv/bin/python execution/scrape_apify_leads.py \
  --industries "marketing & advertising" \
  --fetch-count 100 \
  --output .tmp/raw_leads.json

# Step 2: Clean leads
.venv/bin/python execution/clean_leads.py \
  --source-file .tmp/raw_leads.json \
  --industries "Marketing & Advertising" \
  --output .tmp/cleaned_leads.json

# Step 3: Analyze PageSpeed
.venv/bin/python execution/analyze_pagespeed.py \
  --source-file .tmp/cleaned_leads.json \
  --output-sheet "Marketing Leads - With PageSpeed"
```

## Expected Output Columns

The output will contain all original columns plus:

```
[Original Columns] + performance_score + seo_score + pagespeed_status
```

- `performance_score`: Numeric (0-100) or empty if analysis failed
- `seo_score`: Numeric (0-100) or empty if analysis failed
- `pagespeed_status`: "analyzed", "failed", or "no_website"

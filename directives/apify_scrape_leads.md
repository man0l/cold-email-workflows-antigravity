# Apify Lead Scraping SOP

## Goal
Scrape B2B leads using the Apify `code_crafter/leads-finder` actor.

## Inputs
- **Job Titles**: List of job titles to target (e.g., "CEO", "Marketing Manager").
- **Locations**: List of contact locations (e.g., "united states", "london"). **Note**: Use lowercase for location names.
- **Keywords**: Company keywords to include (e.g., "Software", "SaaS").
- **Not Keywords**: Company keywords to exclude (e.g., "seo", "design").
- **Industries**: List of company industries (e.g., "marketing & advertising").
- **Seniority**: List of seniority levels. **Default (if not specified)**: `owner, founder, c_suite, partner, director, vp` (decision-makers).
  - Available options: `owner`, `founder`, `c_suite`, `partner`, `director`, `vp`, `head`, `manager`, `senior`, `entry`, `trainee`
- **Size**: List of company sizes (e.g., "1-10", "11-20").
- **Fetch Count**: Maximum number of leads to fetch (default: 50).

## Tools
- `execution/scrape_apify_leads.py` - Main scraping script
- `execution/qa_leads.py` - Quality assurance analysis tool

## Output
- JSON file containing the scraped leads, typically saved to `.tmp/leads.json`.

## Quality Assurance Protocol

**CRITICAL**: Before running a full scrape, you MUST perform a quality check.

### Step 1: Test Scrape
Run the scraper with `--fetch-count 25` and save to `.tmp/test_leads.json`.

### Step 2: Automated Quality Analysis
Use the dedicated QA tool to analyze results:

```bash
.venv/bin/python execution/qa_leads.py .tmp/test_leads.json \
  --keywords "your,target,keywords" \
  --threshold 80
```

**Exit Codes:**
- `0` = PASS (≥80% match rate) → Proceed to full scrape
- `1` = MARGINAL (60-79% match rate) → Ask user for approval
- `2` = FAIL (<60% match rate) → STOP and refine criteria
- `3` = ERROR (file not found or invalid JSON)

**Optional flags:**
- `--verbose` or `-v`: Show which specific keywords matched for each lead
- `--threshold N`: Set custom quality threshold (default: 80%)

### Step 3: Decision Framework

**If PASS (exit code 0):**
- Proceed to full scrape with confidence

**If MARGINAL (exit code 1):**
- Review the non-matching companies shown in output
- Ask user if acceptable or if criteria should be refined
- Consider the recommendations provided

**If FAIL (exit code 2):**
- DO NOT proceed with full scrape
- Review the recommendations in the tool output
- Common fixes:
  1. **Broaden keywords**: Add related terms (e.g., "copywriting,content writing,copywriter")
  2. **Add job titles**: Target specific roles (e.g., `--job-titles "Copywriter,Content Writer"`)
  3. **Remove restrictive filters**: Try without `--size` or `--industries`
  4. **Check keyword spelling**: Ensure keywords match industry terminology
- Run a new test scrape with adjusted parameters

## Instructions

1.  **Test Run (Quality Check)**:
    Execute the script with your target parameters but limit `fetch_count` to 25.
    ```bash
    .venv/bin/python execution/scrape_apify_leads.py \
      --industries "marketing & advertising" \
      --keywords "PPC" \
      --locations "united states" \
      --fetch-count 25 \
      --output .tmp/test_leads.json
    ```

2.  **Verify Results**:
    - Read `.tmp/test_leads.json`.
    - Check if the companies actually offer the services or match the profile requested.

3.  **Full Execution**:
    **ONLY** if the test run passes the 9/10 quality threshold, run the full command.
    
    **File Naming Convention**: Use format `apify_[size]_[date]` where:
    - `apify` = source
    - `[size]` = company size (e.g., `1-10_employees`, `11-20_employees`, `all_sizes`)
    - `[date]` = current date in format `DD_MMM_YYYY` (e.g., `27_Nov_2025`)

    **Example 1: PPC Agencies (1-10 employees)**
    ```bash
    .venv/bin/python execution/scrape_apify_leads.py \
      --industries "marketing & advertising" \
      --keywords "PPC" \
      --locations "united states" \
      --seniority "founder, owner, c_suite, director, partner, vp" \
      --size "1-10" \
      --fetch-count 5000 \
      --output .tmp/apify_1-10_employees_27_Nov_2025.json
    ```

    **Example 2: PPC Agencies (11-20 employees, excluding SEO/Design)**
    ```bash
    .venv/bin/python execution/scrape_apify_leads.py \
      --industries "marketing & advertising" \
      --keywords "PPC" \
      --not-keywords "seo, design" \
      --locations "united states" \
      --seniority "founder, owner, c_suite, director, partner, vp" \
      --size "11-20" \
      --fetch-count 1000 \
      --output .tmp/apify_11-20_employees_27_Nov_2025.json
    ```

    **Example 3: Copywriting Agencies (Various sizes)**
    ```bash
    .venv/bin/python execution/scrape_apify_leads.py \
      --industries "marketing & advertising" \
      --keywords "copywriting" \
      --locations "united states" \
      --seniority "founder, owner, c_suite, director, partner, vp" \
      --size "0-1, 2-10, 11-20, 21-50" \
      --fetch-count 1000 \
      --output .tmp/apify_0-50_employees_27_Nov_2025.json
    ```

4.  **Export to Google Sheets**:
    Export the scraped leads to a Google Sheet in the Shared Drive folder.
    ```bash
    .venv/bin/python execution/export_to_sheets.py \
      .tmp/apify_1-10_employees_27_Nov_2025.json \
      --sheet-name "PPC Leads 1-10 (27 Nov 2025)" \
      --folder-id "0ADWgx-M8Z5r-Uk9PVA"
    ```
    **Note**: The script will output the Google Sheet URL for easy access.

## Troubleshooting
- **Run Failed**: Check the Apify console for detailed logs if the script reports a failure.
- **Zero Results**: Try broadening your search criteria (e.g., remove specific keywords or add more locations).
- **Google Auth Error**: Ensure `credentials.json` is in the project root and has access to the Drive folder.

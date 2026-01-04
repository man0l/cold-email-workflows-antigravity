# Google Maps Lead Scraping SOP

## Goal
Scrape local business leads from Google Maps using the Apify `compass/crawler-google-places` actor (the most highly-rated and feature-rich Google Maps scraper).

## Inputs
- **Search Terms**: List of search queries (e.g., "plumbers in Austin", "coffee shops near me", "dentist in Miami").
- **Locations**: Optional list of specific locations to search (e.g., "New York, NY", "Los Angeles, CA", "Texas").
- **Max Results**: Maximum number of leads to fetch per search term (default: 100).
- **Language**: Search language code (default: "en").
- **Category Filter**: List of exact Google category names to filter results (e.g., ["Plumber", "Emergency plumbing service"]). **RECOMMENDED** for preventing irrelevant broad matches. Only businesses matching these exact categories will be included.
- **Scrape Reviews**: Whether to scrape reviews for each business (default: false). **WARNING**: Enabling reviews significantly increases runtime and costs.
- **Scrape Images**: Whether to scrape images for each business (default: false).

## Tools
- `execution/scrape_google_maps.py` - Main Google Maps scraping script (to be created)
- `execution/qa_leads.py` - Quality assurance analysis tool

## Output
- JSON file containing the scraped Google Maps leads, typically saved to `.tmp/google_maps_leads.json`.

## Data Fields
The scraper extracts comprehensive business information including:

**Core Business Details:**
- Business name
- Full address
- Phone number
- Website URL
- Email (if available on website)
- Google Maps URL
- Place ID

**Business Metrics:**
- Total reviews count
- Average rating (1-5 stars)
- Price level ($ to $$$$)
- Category/type (e.g., "Restaurant", "Plumber")

**Location Data:**
- Latitude/Longitude coordinates
- Neighborhood
- City, State, ZIP code
- Country

**Additional Info:**
- Business hours
- Popular times
- Menu/Services (if applicable)
- Description/About section
- Images (if enabled)
- Reviews (if enabled)

## Quality Assurance Protocol

**IMPORTANT**: Before running a full scrape, perform a quality check.

### Step 1: Test Scrape
Run the scraper with `--max-results 20` to get a small sample and save to `.tmp/test_google_maps.json`.

### Step 2: Manual Quality Check
Review the results:
```bash
.venv/bin/python execution/export_to_sheets.py \
  .tmp/test_google_maps.json \
  --sheet-name "Google Maps Test - [Date]" \
  --folder-id "0ADWgx-M8Z5r-Uk9PVA"
```

**Check for:**
- Are these the right types of businesses?
- Do they have contact information (phone, website)?
- Are they in the correct geographic area?
- Is the data quality sufficient for outreach?

### Step 3: Decision Framework

**If quality is good (8/10+ relevant businesses):**
- Proceed to full scrape with confidence

**If quality is marginal (5-7/10 relevant):**
- Refine search terms to be more specific
- Add location qualifiers
- Consider using negative keywords in search

**If quality is poor (<5/10 relevant):**
- DO NOT proceed with full scrape
- Review search terms - they may be too broad
- Try more specific queries (e.g., "emergency plumber" vs "plumber")
- Consider using category filters to restrict results to exact business types
- Consider different locations or search approaches

## Preventing Irrelevant Results with Category Filters

**Problem**: Google Maps often returns "close enough" matches when you search. For example, searching "plumbers in Austin" might return HVAC companies, general contractors, or hardware stores.

**Solution**: Use the `--category-filter` parameter to restrict results to ONLY businesses with exact matching Google categories.

### How Category Filtering Works

- Each Google Maps business has one or more categories (e.g., "Plumber", "Emergency plumbing service", "Plumbing supply store")
- The category filter discards any business whose categories don't match your filter
- If ANY category of a business matches ANY category in your filter, it's included
- **IMPORTANT**: Google has thousands of categories and many are synonymous. You must list ALL relevant categories including synonyms.

### Finding the Right Categories

**Method 1: Test Run First**
1. Run a small test scrape WITHOUT category filter (20 results)
2. Export to Google Sheets and review the "categoryName" column
3. Identify the exact category names you want to keep
4. Re-run with `--category-filter` using those exact names

**Method 2: Common Category Examples**

For **Plumbers**:
- "Plumber"
- "Emergency plumbing service"
- "Plumbing supply store"
- "Drainage service"

For **Restaurants**:
- "Restaurant"
- "Italian restaurant"
- "Pizza restaurant"
- "Fine dining restaurant"

For **Dentists**:
- "Dentist"
- "Cosmetic dentist"
- "Pediatric dentist"
- "Emergency dental service"

For **Coffee Shops**:
- "Coffee shop"
- "Espresso bar"
- "Cafe"

**Pro Tip**: Google has many synonymous categories. For example, "Divorce lawyer", "Divorce service", and "Divorce attorney" are three distinct categories. Some places might only have one of these, so you should include ALL synonyms in your filter to avoid missing relevant businesses.

### Category Filter Best Practices

1. **Start without filters on a test run** to see what categories appear
2. **Be inclusive with synonyms** - list all variations of your target category
3. **Some use cases need 20-100+ categories** to cover all synonyms and sub-types
4. **Balance precision vs coverage** - too restrictive = miss good leads, too broad = get irrelevant results

## Instructions

### 1. Test Run (Quality Check)

Execute the script with your target parameters but limit results to 20 per search.

```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "plumbers in Austin, TX" \
  --max-results 20 \
  --output .tmp/test_google_maps.json
```

**Multiple Search Terms:**
```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "coffee shops in Brooklyn, NY" "cafes in Brooklyn, NY" \
  --max-results 20 \
  --output .tmp/test_coffee_brooklyn.json
```

### 2. Verify Results

- Export to Google Sheets (see Step 2 in QA Protocol above)
- Review the businesses manually
- Check if contact information is present and accurate
- Verify geographic targeting worked correctly

### 3. Full Execution

**ONLY** if the test run meets quality standards, proceed with the full scrape.

**File Naming Convention**: Use format `google_maps_[category]_[location]_[date]` where:
- `google_maps` = source
- `[category]` = business type (e.g., `plumbers`, `restaurants`, `dentists`)
- `[location]` = city/region (e.g., `austin`, `nyc`, `california`)
- `[date]` = current date in format `DD_MMM_YYYY` (e.g., `30_Nov_2025`)

**Example 1: Plumbers in Austin (with category filter for exact matches)**
```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "plumbers in Austin, TX" "emergency plumber Austin" \
  --category-filter "Plumber" "Emergency plumbing service" "Drainage service" \
  --max-results 500 \
  --output .tmp/google_maps_plumbers_austin_30_Nov_2025.json
```

**Example 2: Coffee Shops in Multiple Cities (with category filter)**
```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "coffee shop in Brooklyn, NY" "coffee shop in Manhattan, NY" "coffee shop in Queens, NY" \
  --category-filter "Coffee shop" "Espresso bar" "Cafe" \
  --max-results 200 \
  --output .tmp/google_maps_coffee_nyc_30_Nov_2025.json
```

**Example 3: Restaurants with Reviews (High Cost)**
```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "restaurants in Miami, FL" \
  --category-filter "Restaurant" "Italian restaurant" "Fine dining restaurant" "Pizza restaurant" \
  --max-results 100 \
  --scrape-reviews \
  --output .tmp/google_maps_restaurants_miami_30_Nov_2025.json
```

**Example 4: Broad search without category filter (for discovering categories)**
```bash
.venv/bin/python execution/scrape_google_maps.py \
  --search-terms "plumbers in Austin, TX" \
  --max-results 20 \
  --output .tmp/test_plumbers_categories.json
# Then export to Sheets to review the categoryName column and identify exact categories to filter by
```

### 4. Export to Google Sheets

Export the scraped leads to a Google Sheet in the Shared Drive folder.

```bash
.venv/bin/python execution/export_to_sheets.py \
  .tmp/google_maps_plumbers_austin_30_Nov_2025.json \
  --sheet-name "Google Maps: Plumbers Austin (30 Nov 2025)" \
  --folder-id "0ADWgx-M8Z5r-Uk9PVA"
```

**Note**: The script will output the Google Sheet URL for easy access.

## Cost Considerations

**Apify Pricing (as of 2025):**
- New accounts get $5 in free monthly credits
- The `compass/crawler-google-places` actor typically costs:
  - **~$0.25 per 1,000 basic results** (no reviews)
  - **~$2-5 per 1,000 results with reviews** (significantly more expensive)

**Cost Optimization Tips:**
1. Start with small test runs (20-50 results)
2. Avoid scraping reviews unless absolutely necessary
3. Use specific search terms to reduce irrelevant results
4. Batch multiple searches in one run to minimize overhead
5. Monitor Apify usage dashboard to track costs

## Search Term Strategy

**Good Search Terms:**
- Specific + Location: "emergency plumber in Austin, TX"
- Service + Area: "Italian restaurant in downtown Miami"
- Category + Qualifier: "24-hour dentist near San Francisco"

**Poor Search Terms:**
- Too broad: "plumber" (returns global results)
- Too vague: "food" (returns mixed categories)
- Missing location: "coffee shop" (unpredictable targeting)

**Pro Tips:**
- Use multiple variations of the same search to increase coverage
- Include neighborhood names for hyper-local targeting
- Test different phrasings (e.g., "plumber" vs "plumbing service")
- Consider seasonal modifiers (e.g., "tax accountant" vs "tax preparation")

## Troubleshooting

- **Run Failed**: Check the Apify console at https://console.apify.com for detailed logs.
- **Zero Results**: Your search term may be too specific or have a typo. Try broader terms. If using `--category-filter`, your categories may be too restrictive or have typos.
- **Too Many Irrelevant Results**: Use `--category-filter` to restrict results to exact business categories. Run a test without filters first to identify the correct category names.
- **Wrong Location**: Google Maps uses IP-based location. Add explicit city/state to search terms.
- **Missing Contact Info**: Not all Google Maps listings have websites/emails. This is normal - you can enrich later with other tools.
- **Timeout Errors**: Large scrapes (>1000 results) may need to be broken into smaller batches.
- **Google Auth Error**: Ensure `credentials.json` is in the project root for Google Sheets export.
- **Category Filter Not Working**: Ensure category names match EXACTLY as they appear in Google Maps (check "categoryName" field in test results). Categories are case-sensitive.

## Known Limitations

1. **Email Availability**: Google Maps does not display emails. The scraper can only find them if they're on the business website (requires additional scraping).
2. **Rate Limits**: Google may block aggressive scraping. The Apify actor handles this with built-in rate limiting and proxy rotation.
3. **Data Freshness**: Listings are as current as Google Maps data, but some businesses may be closed or have outdated info.
4. **Review Scraping**: Extremely resource-intensive. Only enable if reviews are critical to your use case.

## Post-Scrape Processing

After scraping Google Maps leads, you may want to:

1. **Clean and Filter**: Use `directives/clean_leads.md` to filter by keywords, validate websites, etc.
   - **Important**: The clean_leads script will automatically clean all URLs to extract just the homepage (domain only), removing subpages, tracking parameters (like `?utm_source=google&utm_campaign=gmb`), and fragments. For example, `https://tilsonhomes.com/new-homes/tx/waco/?utm_campaign=gmb` becomes `https://tilsonhomes.com`.
2. **Find Emails**: Use `directives/find_emails.md` to enrich leads with email addresses.
3. **Deduplicate**: Remove duplicate businesses if you ran multiple overlapping searches.
4. **Enrich Data**: Add additional fields like company size, industry, social media profiles using other tools.

## Next Steps

Typical workflow after Google Maps scraping:
```
1. Scrape Google Maps → .tmp/google_maps_leads.json
2. Clean/Filter → execution/clean_leads.py
3. Find Emails → execution/find_emails.py
4. Export to Sheets → execution/export_to_sheets.py
5. Import to CRM/Email Tool
```

---

**Sources:**
- [Google Maps Scraper by Compass on Apify](https://apify.com/compass/crawler-google-places)
- [Top 5 Google Maps Scrapers for 2025](https://blog.apify.com/best-google-maps-scrapers/)

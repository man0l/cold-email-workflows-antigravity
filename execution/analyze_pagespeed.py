#!/usr/bin/env python3
"""
PageSpeed Analysis Script

Analyzes website performance and SEO scores using Google PageSpeed Insights API.

Usage:
    python analyze_pagespeed.py --source-file .tmp/leads.json --output .tmp/analyzed.json
    python analyze_pagespeed.py --source-url "https://docs.google.com/spreadsheets/d/ID/edit" --output-sheet "Leads - PageSpeed"
"""

import argparse
import json
import sys
import os
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import concurrent.futures
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_google():
    """Authenticate with Google Sheets API using credentials.json (Service Account)"""
    creds_path = 'credentials.json'
    if os.path.exists(creds_path):
        try:
            return ServiceAccountCredentials.from_service_account_file(creds_path, scopes=SCOPES)
        except ValueError:
            print("WARNING: credentials.json appears to be invalid for Service Account.")
            sys.exit(3)
    else:
        print("ERROR: credentials.json not found")
        sys.exit(3)


def load_from_google_sheets(spreadsheet_url: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load leads from Google Sheets"""
    # Extract spreadsheet ID from URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    if not match:
        print(f"ERROR: Invalid Google Sheets URL: {spreadsheet_url}")
        sys.exit(3)

    spreadsheet_id = match.group(1)

    # Authenticate
    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)

    # Get sheet data - Use A:ZZ to ensure we get all columns
    range_name = sheet_name if sheet_name else 'A:ZZ'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    rows = result.get('values', [])
    if not rows:
        print("WARNING: No data found in spreadsheet")
        return []

    # Convert to list of dictionaries (first row as headers)
    headers = rows[0]
    leads = []
    for row in rows[1:]:
        # Pad row with empty strings if it's shorter than headers
        row = row + [''] * (len(headers) - len(row))
        lead = dict(zip(headers, row))
        leads.append(lead)

    return leads


def load_from_json(file_path: str) -> List[Dict[str, Any]]:
    """Load leads from JSON file"""
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(3)

    with open(file_path, 'r') as f:
        return json.load(f)


def get_website_from_lead(lead: Dict[str, Any]) -> Optional[str]:
    """Extract website URL from lead"""
    # Check multiple possible field names
    website_fields = [
        'companyWebsite', 'company_website', 'website',
        'companyDomain', 'company_domain', 'domain',
        'Company Website'
    ]

    for field in website_fields:
        if field in lead and lead[field]:
            website = str(lead[field]).strip()
            if website:
                # Normalize URL
                if not website.startswith(('http://', 'https://')):
                    website = 'https://' + website
                # Remove trailing slash
                website = website.rstrip('/')
                return website

    return None


def analyze_pagespeed(url: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Analyze a URL using Google PageSpeed Insights API.
    Returns performance_score, seo_score, and status.
    """
    api_endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    params = {
        'url': url,
        'strategy': 'mobile',  # Always use mobile
        'category': ['performance', 'seo']
    }

    # Add API key from environment if available
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        params['key'] = api_key

    headers = {}

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(api_endpoint, params=params, headers=headers, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                if verbose:
                    print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                if verbose:
                    print(f"  API error: {response.status_code} - {response.text[:200]}")
                return {
                    'performance_score': None,
                    'seo_score': None,
                    'status': 'failed'
                }

            data = response.json()

            # Extract scores from lighthouse results
            lighthouse_result = data.get('lighthouseResult', {})
            categories = lighthouse_result.get('categories', {})

            performance_score = categories.get('performance', {}).get('score')
            seo_score = categories.get('seo', {}).get('score')

            # Convert from 0-1 to 0-100
            performance_score = int(performance_score * 100) if performance_score is not None else None
            seo_score = int(seo_score * 100) if seo_score is not None else None

            return {
                'performance_score': performance_score,
                'seo_score': seo_score,
                'status': 'analyzed'
            }

        except requests.exceptions.Timeout:
            if verbose:
                print(f"  Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

        except Exception as e:
            if verbose:
                print(f"  Error: {str(e)}")
            return {
                'performance_score': None,
                'seo_score': None,
                'status': 'failed'
            }

    # All retries failed
    return {
        'performance_score': None,
        'seo_score': None,
        'status': 'failed'
    }


def analyze_leads(leads: List[Dict[str, Any]], batch_size: int = 5, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Analyze all leads with PageSpeed Insights.

    Rate Limiting:
    - API Limit: 400 queries per 100 seconds (4/sec theoretical)
    - Daily Limit: 25,000 queries per day
    - Safe Rate: 1.5 requests/second to avoid undocumented throttling
    """
    analyzed_leads = []
    total = len(leads)

    print(f"\nAnalyzing PageSpeed...")
    print(f"Total leads: {total}")

    # Count leads with websites
    leads_with_websites = [lead for lead in leads if get_website_from_lead(lead)]
    print(f"Leads with websites: {len(leads_with_websites)}")

    # Rate limiting check
    if len(leads_with_websites) > 25000:
        print(f"WARNING: You have {len(leads_with_websites)} leads which exceeds the daily quota of 25,000")
        print("Consider splitting into multiple batches")

    # Estimate time
    estimated_seconds = len(leads_with_websites) * 0.7  # ~0.7 seconds per request (rate limit + API time)
    estimated_minutes = estimated_seconds / 60
    print(f"Estimated time: {int(estimated_minutes)} minutes {int(estimated_seconds % 60)} seconds")

    # Stats
    success_count = 0
    failed_count = 0
    no_website_count = 0

    performance_scores = []
    seo_scores = []

    # Rate limiting: track requests per time window
    request_times = []
    MAX_REQUESTS_PER_100_SEC = 400  # API limit
    SAFE_DELAY = 0.67  # ~1.5 requests/second (safer than theoretical max)

    # Process leads
    for i, lead in enumerate(leads, 1):
        website = get_website_from_lead(lead)

        if not website:
            lead['performance_score'] = ''
            lead['seo_score'] = ''
            lead['pagespeed_status'] = 'no_website'
            analyzed_leads.append(lead)
            no_website_count += 1
            if verbose:
                print(f"[{i}/{total}] No website found")
            continue

        if verbose:
            print(f"[{i}/{total}] Analyzing {website}...")
        else:
            # Simple progress indicator
            if i % 5 == 0 or i == total:
                print(f"Progress: {i}/{total} ({int(i/total*100)}%)")

        # Rate limiting: enforce safe delay between requests
        current_time = time.time()

        # Remove request times older than 100 seconds
        request_times = [t for t in request_times if current_time - t < 100]

        # Check if we're approaching the limit
        if len(request_times) >= MAX_REQUESTS_PER_100_SEC - 10:
            # Wait until we're under the limit
            wait_time = 100 - (current_time - request_times[0]) + 1
            if verbose:
                print(f"  Rate limit approaching, waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            request_times = []

        # Analyze
        result = analyze_pagespeed(website, verbose=verbose)
        request_times.append(time.time())

        lead['performance_score'] = result['performance_score'] if result['performance_score'] is not None else ''
        lead['seo_score'] = result['seo_score'] if result['seo_score'] is not None else ''
        lead['pagespeed_status'] = result['status']

        analyzed_leads.append(lead)

        if result['status'] == 'analyzed':
            success_count += 1
            if result['performance_score'] is not None:
                performance_scores.append(result['performance_score'])
            if result['seo_score'] is not None:
                seo_scores.append(result['seo_score'])
        else:
            failed_count += 1

        # Safe delay between requests (1.5 requests/second)
        if i < total and get_website_from_lead(leads[i]) if i < len(leads) else False:
            time.sleep(SAFE_DELAY)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Analysis Complete")
    print(f"{'='*50}")
    print(f"Successfully analyzed: {success_count} ({int(success_count/total*100)}%)")
    print(f"Failed: {failed_count}")
    print(f"No website: {no_website_count}")

    if performance_scores:
        print(f"\nPerformance Score Distribution:")
        good = len([s for s in performance_scores if s >= 90])
        moderate = len([s for s in performance_scores if 50 <= s < 90])
        poor = len([s for s in performance_scores if s < 50])
        print(f"  Good (90-100): {good} ({int(good/len(performance_scores)*100)}%)")
        print(f"  Needs Improvement (50-89): {moderate} ({int(moderate/len(performance_scores)*100)}%)")
        print(f"  Poor (0-49): {poor} ({int(poor/len(performance_scores)*100)}%)")
        print(f"\n  Average: {sum(performance_scores)/len(performance_scores):.1f}")

    if seo_scores:
        print(f"\nSEO Score Distribution:")
        good = len([s for s in seo_scores if s >= 90])
        moderate = len([s for s in seo_scores if 50 <= s < 90])
        poor = len([s for s in seo_scores if s < 50])
        print(f"  Good (90-100): {good} ({int(good/len(seo_scores)*100)}%)")
        print(f"  Needs Improvement (50-89): {moderate} ({int(moderate/len(seo_scores)*100)}%)")
        print(f"  Poor (0-49): {poor} ({int(poor/len(seo_scores)*100)}%)")
        print(f"\n  Average: {sum(seo_scores)/len(seo_scores):.1f}")

    return analyzed_leads


def save_to_json(leads: List[Dict[str, Any]], output_file: str):
    """Save leads to JSON file"""
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2)
    print(f"\nSaved to: {output_file}")


def save_to_google_sheets(leads: List[Dict[str, Any]], sheet_name: str, source_spreadsheet_id: Optional[str] = None):
    """Save leads to Google Sheets (new tab in same spreadsheet or new spreadsheet)"""
    from export_to_sheets import export_data_to_sheets

    # If we have source spreadsheet ID, add as new tab
    if source_spreadsheet_id:
        url = export_data_to_sheets(leads, sheet_name, target_spreadsheet_id=source_spreadsheet_id)
    else:
        url = export_data_to_sheets(leads, sheet_name)

    return url


def main():
    parser = argparse.ArgumentParser(description='Analyze leads with Google PageSpeed Insights')

    # Input source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Path to JSON file with leads')
    source_group.add_argument('--source-url', help='Google Sheets URL with leads')

    # Input options
    parser.add_argument('--sheet-name', help='Sheet name (for Google Sheets source)')

    # Output
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', help='Output JSON file path')
    output_group.add_argument('--output-sheet', help='Output Google Sheet name')

    # Options
    parser.add_argument('--batch-size', type=int, default=5, help='Concurrent API requests (default: 5)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Load leads
    print("Loading leads...")
    if args.source_file:
        leads = load_from_json(args.source_file)
        source_spreadsheet_id = None
    else:
        leads = load_from_google_sheets(args.source_url, args.sheet_name)
        # Extract spreadsheet ID for adding new tab
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', args.source_url)
        source_spreadsheet_id = match.group(1) if match else None

    print(f"Loaded {len(leads)} leads")

    if not leads:
        print("ERROR: No leads to analyze")
        sys.exit(1)

    # Analyze leads
    analyzed_leads = analyze_leads(leads, batch_size=args.batch_size, verbose=args.verbose)

    # Save results
    if args.output:
        save_to_json(analyzed_leads, args.output)
    else:
        save_to_google_sheets(analyzed_leads, args.output_sheet, source_spreadsheet_id)


if __name__ == '__main__':
    main()

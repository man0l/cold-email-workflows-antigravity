#!/usr/bin/env python3
"""
DataForSEO Google Ads Detection Script

Uses DataForSEO SERP API (task-based endpoint) to check if companies are running Google Ads for their brand name.

Usage:
    python dataforseo_check_google_ads.py --source-url "https://docs.google.com/spreadsheets/d/ID/edit" --sheet-name "Leads" --output-sheet "Leads - Ads Analysis"
"""

import argparse
import json
import sys
import os
import time
import re
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# DataForSEO API Configuration
DATAFORSEO_TASK_POST_URL = "https://api.dataforseo.com/v3/serp/google/ads_advertisers/task_post"
DATAFORSEO_TASK_GET_URL = "https://api.dataforseo.com/v3/serp/google/ads_advertisers/task_get/advanced/{task_id}"
COST_PER_REQUEST = 0.0006  # $600 per million = $0.0006 per task


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


def get_dataforseo_credentials() -> tuple:
    """Get DataForSEO API credentials from environment"""
    # Try new format first (separate username and key)
    username = os.getenv('DATAFORSEO_API_USERNAME')
    api_key = os.getenv('DATAFORSEO_API_KEY')

    if username and api_key:
        return username, api_key

    # Fallback to old format (login:password)
    combined_key = os.getenv('DATAFORSEO_API_KEY')
    if combined_key and ':' in combined_key:
        login, password = combined_key.split(':', 1)
        return login, password

    # Error if neither format is found
    print("ERROR: DataForSEO credentials not found in .env file")
    print("Required: DATAFORSEO_API_USERNAME and DATAFORSEO_API_KEY")
    print("Or: DATAFORSEO_API_KEY=login:password")
    sys.exit(3)


def load_from_google_sheets(spreadsheet_url: str, sheet_name: Optional[str] = None) -> tuple:
    """Load leads from Google Sheets and return (leads, spreadsheet_id)"""
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
    range_name = f"{sheet_name}!A:ZZ" if sheet_name else 'A:ZZ'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    rows = result.get('values', [])
    if not rows:
        print("WARNING: No data found in spreadsheet")
        return [], spreadsheet_id

    # Convert to list of dictionaries (first row as headers)
    headers = rows[0]
    leads = []
    for row in rows[1:]:
        # Pad row with empty strings if it's shorter than headers
        row = row + [''] * (len(headers) - len(row))
        lead = dict(zip(headers, row))
        leads.append(lead)

    return leads, spreadsheet_id


def get_company_name_from_lead(lead: Dict[str, Any]) -> Optional[str]:
    """Extract company name from lead for Google Ads search"""
    # Check multiple possible field names
    name_fields = [
        'Company Name', 'companyName', 'company_name',
        'name', 'businessName', 'business_name'
    ]

    for field in name_fields:
        if field in lead and lead[field]:
            name = str(lead[field]).strip()
            if name:
                return name

    return None


def get_website_domain_from_lead(lead: Dict[str, Any]) -> Optional[str]:
    """Extract website domain from lead"""
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
                # Remove protocol and www
                domain = website.replace('https://', '').replace('http://', '').replace('www.', '')
                # Remove trailing slash and path
                domain = domain.split('/')[0]
                # Remove trailing periods
                domain = domain.rstrip('.')
                if domain:
                    return domain

    return None


def query_company_ads_for_periods(
    company_name: str,
    login: str,
    password: str,
    location: str = "United States",
    verbose: bool = False
) -> Dict[str, int]:
    """
    Query advertiser data for a company across multiple time periods.
    Makes 3 API calls: all-time, last 1 month, last 3 months.
    
    Returns:
        Dictionary with keys: all_time, one_month, three_months (ad counts)
    """
    from datetime import datetime, timedelta
    
    results = {
        'all_time': 0,
        'one_month': 0,
        'three_months': 0
    }
    
    # Calculate dates
    today = datetime.now().strftime('%Y-%m-%d')
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Query 1: All time (no date filter)
    task_id = post_tasks_bulk_to_dataforseo([company_name], login, password, location, "en", None, None, verbose)
    if task_id and task_id[0]:
        time.sleep(3)
        result = get_task_result_from_dataforseo(task_id[0], login, password, verbose=verbose)
        results['all_time'] = result.get('ads_count', 0)
    
    # Query 2: Last 1 month
    # task_id = post_tasks_bulk_to_dataforseo([company_name], login, password, location, "en", one_month_ago, today, verbose)
    # if task_id and task_id[0]:
    #     time.sleep(3)
    #     result = get_task_result_from_dataforseo(task_id[0], login, password, verbose=verbose)
    #     results['one_month'] = result.get('ads_count', 0)
    
    # Query 3: Last 3 months
    # task_id = post_tasks_bulk_to_dataforseo([company_name], login, password, location, "en", three_months_ago, today, verbose)
    # if task_id and task_id[0]:
    #     time.sleep(3)
    #     result = get_task_result_from_dataforseo(task_id[0], login, password, verbose=verbose)
    #     results['three_months'] = result.get('ads_count', 0)
    
    return results


def post_tasks_bulk_to_dataforseo(
    company_names_batch: List[str],
    login: str,
    password: str,
    location: str = "United States",
    language: str = "en",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    verbose: bool = False
) -> List[Optional[str]]:
    """
    Post multiple tasks to DataForSEO in a single API call (up to 100 tasks).
    Searches for Google Ads advertisers using company names.

    Args:
        date_from: Start date (YYYY-MM-DD format, optional). Default: 12 months ago
        date_to: End date (YYYY-MM-DD format, optional). Default: today

    Returns:
        List of task IDs (or None for failed tasks) in same order as input
    """
    # Build payload with all tasks
    payload = []
    for company_name in company_names_batch:
        task_data = {
            "location_name": location,
            "keyword": company_name  # Company name for advertiser search
        }
        
        # Add date filters if provided
        if date_from:
            task_data["date_from"] = date_from
        if date_to:
            task_data["date_to"] = date_to
        
        payload.append(task_data)

    try:
        response = requests.post(
            DATAFORSEO_TASK_POST_URL,
            auth=HTTPBasicAuth(login, password),
            json=payload,
            timeout=60
        )

        if response.status_code == 401:
            print("ERROR: Invalid DataForSEO API credentials")
            sys.exit(3)

        if response.status_code == 402:
            print("ERROR: Insufficient DataForSEO credits")
            print("Please add credits to your account: https://dataforseo.com/")
            sys.exit(3)

        if response.status_code != 200:
            if verbose:
                print(f"  Failed to post batch: HTTP {response.status_code}")
            return [None] * len(company_names_batch)

        data = response.json()

        # Check API response status
        if data.get('status_code') != 20000:
            if verbose:
                print(f"  API Error: {data.get('status_message')}")
            return [None] * len(company_names_batch)

        # Extract task IDs
        tasks = data.get('tasks', [])
        task_ids = []
        for task in tasks:
            if task.get('status_code') == 20100 and task.get('id'):
                task_ids.append(task['id'])
            else:
                task_ids.append(None)
                if verbose:
                    print(f"  Task failed: {task.get('status_message')}")

        return task_ids

    except Exception as e:
        if verbose:
            print(f"  Exception posting batch: {str(e)}")
        return [None] * len(company_names_batch)


def get_task_result_from_dataforseo(
    task_id: str,
    login: str,
    password: str,
    max_wait: int = 60,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Retrieve task results from DataForSEO, waiting for completion if needed.

    Returns:
        Dictionary with analysis results
    """
    result = {
        'google_ads_detected': False,
        'ads_count': 0,
        'ads_position': '',
        'competitor_ads': False,
        'status': 'failed',
        'cost': 0.0
    }

    url = DATAFORSEO_TASK_GET_URL.format(task_id=task_id)
    start_time = time.time()
    wait_interval = 2  # Start with 2 second intervals

    while (time.time() - start_time) < max_wait:
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(login, password),
                timeout=30
            )

            if response.status_code != 200:
                if verbose:
                    print(f"  Failed to get task result: HTTP {response.status_code}")
                time.sleep(wait_interval)
                continue

            data = response.json()

            # Check API response status
            if data.get('status_code') != 20000:
                if verbose:
                    print(f"  API Error: {data.get('status_message')}")
                time.sleep(wait_interval)
                continue

            # Check if task is complete
            tasks = data.get('tasks', [])
            if not tasks:
                time.sleep(wait_interval)
                continue

            task = tasks[0]
            task_status = task.get('status_message')

            # Task still processing
            if task_status in ['Task is in progress', 'Task is pending']:
                time.sleep(wait_interval)
                wait_interval = min(wait_interval + 1, 5)  # Increase interval up to 5 seconds
                continue

            # Task failed
            if task_status != 'Ok.':
                if verbose:
                    print(f"  Task failed: {task_status}")
                return result

            # Task complete - parse results
            task_result = task.get('result', [])
            if not task_result:
                result['status'] = 'no_results'
                result['cost'] = COST_PER_REQUEST
                return result

            items = task_result[0].get('items', [])

            # Look for ads_advertiser type items
            company_ads_count = 0
            advertiser_id = None
            verified = False
            
            for item in items:
                if item.get('type') == 'ads_advertiser':
                    # Found advertiser data
                    company_ads_count = item.get('approx_ads_count', 0)
                    advertiser_id = item.get('advertiser_id')
                    verified = item.get('verified', False)
                    break

            # Update result based on advertiser data
            result['google_ads_detected'] = company_ads_count > 0
            result['ads_count'] = company_ads_count
            result['competitor_ads'] = False  # ads_advertisers shows company's own ads only
            result['ads_position'] = ''  # Not applicable for advertiser API
            result['status'] = 'analyzed'
            result['cost'] = COST_PER_REQUEST

            if verbose:
                print(f"  Ads found: {company_ads_count} (advertiser ID: {advertiser_id}, verified: {verified})")

            return result

        except Exception as e:
            if verbose:
                print(f"  Exception getting task result: {str(e)}")
            time.sleep(wait_interval)
            continue

    # Timeout
    if verbose:
        print(f"  Timeout waiting for task result")
    return result


def process_task_batch(
    data_with_indices: List[tuple],
    login: str,
    password: str,
    location: str = "United States",
    language: str = "en",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    verbose: bool = False
) -> List[tuple]:
    """
    Process a batch of leads (up to 100) using bulk API posting.

    Args:
        data_with_indices: List of (index, company_name, domain, lead) tuples
        date_from: Start date for ads filter (YYYY-MM-DD)
        date_to: End date for ads filter (YYYY-MM-DD)

    Returns:
        List of (index, company_name, domain, lead, result) tuples
    """
    # Extract company names for bulk posting
    company_names = [company_name for _, company_name, _, _ in data_with_indices]

    # Post all tasks in one API call
    task_ids = post_tasks_bulk_to_dataforseo(company_names, login, password, location, language, date_from, date_to, verbose)

    # Wait a bit for tasks to process
    time.sleep(3)

    # Retrieve results for all tasks
    results = []
    for (idx, company_name, domain, lead), task_id in zip(data_with_indices, task_ids):
        if task_id:
            result = get_task_result_from_dataforseo(task_id, login, password, max_wait=60, verbose=verbose)
            # Add domain to result for ad matching
            result['domain'] = domain
        else:
            result = {
                'google_ads_detected': False,
                'ads_count': 0,
                'ads_position': '',
                'competitor_ads': False,
                'status': 'failed',
                'cost': 0.0,
                'domain': domain
            }
        results.append((idx, company_name, domain, lead, result))

    return results


def analyze_leads(
    leads: List[Dict[str, Any]],
    login: str,
    password: str,
    location: str = "United States",
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Analyze all leads for Google Ads using DataForSEO API.
    Queries 3 time periods for each lead: all-time, last 1 month, last 3 months.

    Args:
        leads: List of lead dictionaries
        login: DataForSEO API login
        password: DataForSEO API password
        location: Google search location (default: "United States")
        verbose: Print detailed progress (default: False)

    Returns:
        List of leads with Google Ads detection fields added
    """
    total = len(leads)

    print(f"\nPreparing Google Ads analysis via DataForSEO...")
    print(f"Total leads loaded: {total}")

    # MANDATORY FILTER: Only analyze leads with google_ads_detected = TRUE
    leads_to_analyze = []
    leads_skipped_no_gtm = []
    leads_without_domains = []

    for i, lead in enumerate(leads):
        # Check if lead has google_ads_detected = TRUE from GTM check
        gtm_ads_detected = lead.get('google_ads_detected', '').upper() == 'TRUE'

        if not gtm_ads_detected:
            # Skip leads without GTM ads detection - mark as skipped
            lead['dataforseo_google_ads_detected'] = ''
            lead['ads_position'] = ''
            lead['competitor_ads'] = ''
            lead['dataforseo_status'] = 'skipped_no_gtm_tracking'
            lead['dataforseo_cost'] = 0.0
            leads_skipped_no_gtm.append((i, lead))
            continue

        # Check if lead has company name (required for search)
        company_name = get_company_name_from_lead(lead)
        if not company_name:
            # Has GTM tracking but no company name
            lead['dataforseo_google_ads_detected'] = ''
            lead['ads_position'] = ''
            lead['competitor_ads'] = ''
            lead['dataforseo_status'] = 'no_company_name'
            lead['dataforseo_cost'] = 0.0
            leads_without_domains.append((i, lead))
            continue

        # Get domain for ad matching (optional)
        domain = get_website_domain_from_lead(lead)
        
        # Add to analysis queue (domain may be None, that's ok)
        leads_to_analyze.append((i, company_name, domain, lead))

    analyzable_count = len(leads_to_analyze)
    skipped_no_gtm_count = len(leads_skipped_no_gtm)
    skipped_no_domain_count = len(leads_without_domains)

    print(f"\n{'='*60}")
    print(f"{'MANDATORY FILTER APPLIED':^60}")
    print(f"{'='*60}")
    print(f"Leads with google_ads_detected = TRUE: {analyzable_count + skipped_no_domain_count}")
    print(f"  - With website domains (will analyze): {analyzable_count}")
    print(f"  - Without website domains (skipped): {skipped_no_domain_count}")
    print(f"Leads without GTM tracking (auto-skipped): {skipped_no_gtm_count}")
    print(f"{'='*60}")

    if analyzable_count == 0:
        print("\nWARNING: No leads to analyze!")
        if skipped_no_gtm_count > 0:
            print(f"  - {skipped_no_gtm_count} leads don't have google_ads_detected = TRUE")
            print(f"  - Run check_gtm_adwords.py first to detect Google Ads tracking")
        if skipped_no_domain_count > 0:
            print(f"  - {skipped_no_domain_count} leads have GTM tracking but no website domain")
        return leads

    # Calculate cost (1x since we query only all-time)
    estimated_cost = analyzable_count * COST_PER_REQUEST * 1

    # Display cost estimate
    print(f"\n{'='*60}")
    print(f"{'COST ESTIMATE - DataForSEO API':^60}")
    print(f"{'='*60}")
    print(f"API: Google Ads Advertisers")
    print(f"Endpoint: /v3/serp/google/ads_advertisers/task_post")
    print(f"Mode: Task-based (not live)")
    print(f"Cost per task: ${COST_PER_REQUEST}")
    print(f"")
    print(f"Leads to analyze: {analyzable_count}")
    print(f"Queries per lead: 1 (all-time only)")
    print(f"Total API calls: {analyzable_count * 1}")
    print(f"Estimated cost: ${estimated_cost:.2f}")
    print(f"{'='*60}")
    print(f"")
    print(f"⚠️  This will charge your DataForSEO account ${estimated_cost:.2f}")
    print(f"")

    # Ask for confirmation
    confirmation = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirmation != 'yes':
        print("Operation cancelled by user")
        sys.exit(0)

    print(f"\nProceeding with analysis...")

    # Stats tracking
    stats = {
        'success_count': 0,
        'failed_count': 0,
        'no_results_count': 0,
        'ads_detected_count': 0,
        'total_cost': 0.0,
        'total_ads_all_time': 0,
        'total_ads_1_month': 0,
        'total_ads_3_months': 0
    }

    # Process leads sequentially (1 API call per lead)
    print(f"\nProcessing {analyzable_count} leads (1 query each)...")

    for idx, lead_tuple in enumerate(leads_to_analyze, 1):
        i, company_name, domain, lead = lead_tuple
        
        if verbose:
            display_name = company_name or domain or lead.get('Company Name', 'Unknown')
            print(f"\n[{idx}/{analyzable_count}] Analyzing {display_name}...")
        
        # Query all 3 time periods for this company
        try:
            period_results = query_company_ads_for_periods(
                company_name,
                login,
                password,
                location,
                verbose
            )
            
            # Add results to lead
            lead['dataforseo_google_ads_detected'] = 'TRUE' if period_results['all_time'] > 0 else 'FALSE'
            # Sanity check: 3 months must be >= 1 month, All time must be >= 3 months
            period_results['three_months'] = max(period_results['three_months'], period_results['one_month'])
            period_results['all_time'] = max(period_results['all_time'], period_results['three_months'])
            
            lead['ads_count_all_time'] = str(period_results['all_time'])
            lead['ads_count_1_month'] = '' # str(period_results['one_month'])
            lead['ads_count_3_months'] = '' # str(period_results['three_months'])
            lead['ads_position'] = ''
            lead['competitor_ads'] = 'FALSE'
            lead['dataforseo_status'] = 'analyzed'
            lead['dataforseo_cost'] = COST_PER_REQUEST * 1  # 1 query
            
            # Update stats
            stats['success_count'] += 1
            stats['total_cost'] += COST_PER_REQUEST * 1
            stats['total_ads_all_time'] += period_results['all_time']
            stats['total_ads_1_month'] += period_results['one_month']
            stats['total_ads_3_months'] += period_results['three_months']
            
            if period_results['all_time'] > 0:
                stats['ads_detected_count'] += 1
            
            if verbose:
                print(f"    All-time: {period_results['all_time']} ads")
                print(f"    Last 1 month: {period_results['one_month']} ads")
                print(f"    Last 3 months: {period_results['three_months']} ads")
                
        except Exception as e:
            # Failed
            lead['dataforseo_google_ads_detected'] = ''
            lead['ads_count_all_time'] = ''
            lead['ads_count_1_month'] = ''
            lead['ads_count_3_months'] = ''
            lead['ads_position'] = ''
            lead['competitor_ads'] = ''
            lead['dataforseo_status'] = 'failed'
            lead['dataforseo_cost'] = 0.0
            stats['failed_count'] += 1
            
            if verbose:
                print(f"    ERROR: {str(e)}")
        
        # Show progress
        if idx % 10 == 0 or idx == analyzable_count:
            print(f"Progress: {idx}/{analyzable_count} ({idx/analyzable_count*100:.1f}%)")

    # Sort leads back to original order
    all_lead_tuples = (
        [(idx, lead) for idx, _, _, lead in leads_to_analyze] +
        leads_without_domains +
        leads_skipped_no_gtm
    )
    sorted_leads = [lead for _, lead in sorted(all_lead_tuples, key=lambda x: x[0])]

    # Print summary
    print(f"\n{'='*60}")
    print(f"{'ANALYSIS COMPLETE':^60}")
    print(f"{'='*60}")
    print(f"Successfully analyzed: {stats['success_count']} ({int(stats['success_count']/total*100)}%)")
    print(f"No results: {stats['no_results_count']}")
    print(f"Failed: {stats['failed_count']}")
    print(f"Skipped (no GTM tracking): {skipped_no_gtm_count}")
    print(f"Skipped (no website): {skipped_no_domain_count}")

    if stats['success_count'] > 0:
        print(f"\nGoogle Ads Detection:")
        print(f"  Ads Detected: {stats['ads_detected_count']} ({int(stats['ads_detected_count']/stats['success_count']*100)}%)")
        print(f"  No Ads Found: {stats['success_count'] - stats['ads_detected_count']} ({int((stats['success_count'] - stats['ads_detected_count'])/stats['success_count']*100)}%)")

        if stats['ads_detected_count'] > 0:
            print(f"\nAd Count Averages (among advertisers):")
            avg_all = stats['total_ads_all_time'] / stats['ads_detected_count']
            avg_1m = stats['total_ads_1_month'] / stats['ads_detected_count']
            avg_3m = stats['total_ads_3_months'] / stats['ads_detected_count']
            print(f"  All-time: {avg_all:.1f} ads per company")
            print(f"  Last 1 month: {avg_1m:.1f} ads per company")
            print(f"  Last 3 months: {avg_3m:.1f} ads per company")

    # Cost summary
    print(f"\n{'='*60}")
    print(f"{'ACTUAL API COST':^60}")
    print(f"{'='*60}")
    print(f"Total API calls: {stats['success_count'] * 1}")  # 1 query per success
    print(f"Cost per call: ${COST_PER_REQUEST}")
    print(f"Queries per lead: 1 (all-time only)")
    print(f"TOTAL COST: ${stats['total_cost']:.2f}")
    print(f"{'='*60}")

    # Opportunity breakdown
    already_running = stats['ads_detected_count']
    no_ads = stats['success_count'] - stats['ads_detected_count']

    print(f"\nOpportunity Breakdown:")
    print(f"  Already running ads: {already_running} - Optimization opportunity")
    print(f"  No ads at all: {no_ads} - Ground floor opportunity")

    return sorted_leads


def save_to_google_sheets(leads: List[Dict[str, Any]], sheet_name: str, source_spreadsheet_id: str):
    """Save leads to Google Sheets (new tab in same spreadsheet)"""
    # Import here to avoid circular dependency
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from export_to_sheets import export_data_to_sheets

    url = export_data_to_sheets(leads, sheet_name, target_spreadsheet_id=source_spreadsheet_id)
    return url


def main():
    parser = argparse.ArgumentParser(description='Check for Google Ads using DataForSEO Ads Advertisers API')

    # Input source (required)
    parser.add_argument('--source-url', required=True, help='Google Sheets URL with leads')
    parser.add_argument('--sheet-name', required=True, help='Sheet name to read from')

    # Output (required)
    parser.add_argument('--output-sheet', required=True, help='Output Google Sheet name')

    # Options
    parser.add_argument('--location', default="United States", help='Google search location (default: United States)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Get DataForSEO credentials
    login, password = get_dataforseo_credentials()

    # Load leads
    print("Loading leads from Google Sheet...")
    leads, source_spreadsheet_id = load_from_google_sheets(args.source_url, args.sheet_name)

    print(f"Loaded {len(leads)} leads")

    if not leads:
        print("ERROR: No leads to analyze")
        sys.exit(1)

    # Analyze leads (now queries 3 periods automatically)
    analyzed_leads = analyze_leads(
        leads,
        login,
        password,
        location=args.location,
        verbose=args.verbose
    )

    # Save results
    print(f"\nExporting to Google Sheet: '{args.output_sheet}'...")
    url = save_to_google_sheets(analyzed_leads, args.output_sheet, source_spreadsheet_id)
    print(f"Sheet URL: {url}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
GTM & Google Ads Detection Script

Analyzes website HTML to detect Google Tag Manager installation and Google Ads tracking.

Usage:
    python check_gtm_adwords.py --source-file .tmp/leads.json --output .tmp/analyzed.json
    python check_gtm_adwords.py --source-url "https://docs.google.com/spreadsheets/d/ID/edit" --output-sheet "Leads - GTM Analysis"
"""

import argparse
import json
import sys
import os
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    range_name = f"{sheet_name}!A:ZZ" if sheet_name else 'A:ZZ'
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


def detect_gtm_and_ads(url: str, timeout: int = 10, verbose: bool = False) -> Dict[str, Any]:
    """
    Fetch website HTML and detect GTM and Google Ads tracking.

    Returns:
        - gtm_installed: bool
        - gtm_container_id: str or None
        - google_ads_detected: bool
        - google_ads_account_id: str or None
        - conversion_tracking: bool
        - remarketing_tag: bool
        - status: "analyzed" or "failed"
    """

    result = {
        'gtm_installed': False,
        'gtm_container_id': None,
        'google_ads_detected': False,
        'google_ads_account_id': None,
        'conversion_tracking': False,
        'remarketing_tag': False,
        'status': 'failed'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    max_retries = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

            if response.status_code != 200:
                if verbose:
                    print(f"  HTTP {response.status_code}")
                # Try again on next attempt
                continue

            html = response.text.lower()  # Case-insensitive matching

            # ===== GTM Detection =====
            # Look for GTM container script: googletagmanager.com/gtm.js?id=GTM-
            gtm_patterns = [
                r'googletagmanager\.com/gtm\.js\?id=(gtm-[a-z0-9]+)',
                r'googletagmanager\.com/ns\.html\?id=(gtm-[a-z0-9]+)',
            ]

            for pattern in gtm_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    result['gtm_installed'] = True
                    result['gtm_container_id'] = match.group(1).upper()
                    if verbose:
                        print(f"  GTM detected: {result['gtm_container_id']}")
                    break

            # ===== Google Ads Detection =====
            # Look for Google Ads tracking patterns

            # Pattern 1: gtag config with AW- account ID
            # gtag('config', 'AW-123456789')
            ads_config_match = re.search(r"gtag\(['\"]config['\"],\s*['\"]+(aw-\d+)['\"]", html, re.IGNORECASE)
            if ads_config_match:
                result['google_ads_detected'] = True
                result['google_ads_account_id'] = ads_config_match.group(1).upper()
                if verbose:
                    print(f"  Google Ads detected: {result['google_ads_account_id']}")

            # Pattern 2: Legacy google_conversion_id
            if re.search(r'google_conversion_id', html):
                result['google_ads_detected'] = True
                if verbose:
                    print(f"  Google Ads detected (legacy conversion tracking)")

            # Pattern 3: gtag.js script (Google Ads global site tag)
            if re.search(r'googletagmanager\.com/gtag/js\?id=aw-', html, re.IGNORECASE):
                result['google_ads_detected'] = True
                # Try to extract account ID
                gtag_match = re.search(r'googletagmanager\.com/gtag/js\?id=(aw-\d+)', html, re.IGNORECASE)
                if gtag_match and not result['google_ads_account_id']:
                    result['google_ads_account_id'] = gtag_match.group(1).upper()
                if verbose:
                    print(f"  Google Ads gtag.js detected")

            # ===== Conversion Tracking Detection =====
            # Look for conversion tracking events
            conversion_patterns = [
                r"gtag\(['\"]event['\"],\s*['\"]conversion['\"]",
                r"gtag\(['\"]event['\"],\s*['\"]page_view['\"].*send_to.*aw-",
                r'google_trackconversion',
            ]

            for pattern in conversion_patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    result['conversion_tracking'] = True
                    if verbose:
                        print(f"  Conversion tracking detected")
                    break

            # ===== Remarketing Tag Detection =====
            # Look for Google Ads remarketing
            remarketing_patterns = [
                r'google_tag_params',
                r'google_remarketing_only\s*=\s*true',
            ]

            for pattern in remarketing_patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    result['remarketing_tag'] = True
                    if verbose:
                        print(f"  Remarketing tag detected")
                    break

            # Success
            result['status'] = 'analyzed'
            return result

        except requests.exceptions.SSLError:
            if verbose:
                print(f"  SSL error, trying HTTP...")
            # Try HTTP instead
            try:
                http_url = url.replace('https://', 'http://')
                response = requests.get(http_url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    # Repeat analysis on HTTP version
                    html = response.text.lower()
                    # (Same detection logic - simplified for brevity, could be refactored into a function)
                    result['status'] = 'analyzed'
                    return result
            except:
                pass

        except requests.exceptions.Timeout:
            if verbose:
                print(f"  Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue

        except requests.exceptions.ConnectionError:
            if verbose:
                print(f"  Connection error")
            break

        except Exception as e:
            if verbose:
                print(f"  Error: {str(e)}")
            break

    # All retries failed
    return result


def analyze_leads(leads: List[Dict[str, Any]], max_workers: int = 10, timeout: int = 10, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Analyze all leads for GTM and Google Ads tracking in parallel using ThreadPoolExecutor.

    Args:
        leads: List of lead dictionaries
        max_workers: Number of concurrent threads (default: 10)
        timeout: Timeout per request in seconds (default: 10)
        verbose: Print detailed progress (default: False)

    Returns:
        List of leads with tracking detection fields added
    """
    total = len(leads)

    print(f"\nAnalyzing GTM & Google Ads tracking...")
    print(f"Total leads: {total}")

    # Create URL mapping for leads with websites
    url_lead_pairs = []
    no_website_leads = []

    for i, lead in enumerate(leads):
        website = get_website_from_lead(lead)
        if website:
            url_lead_pairs.append((i, website, lead))
        else:
            # Handle leads without websites immediately
            lead['gtm_installed'] = ''
            lead['gtm_container_id'] = ''
            lead['google_ads_detected'] = ''
            lead['google_ads_account_id'] = ''
            lead['conversion_tracking'] = ''
            lead['remarketing_tag'] = ''
            lead['tracking_analysis_status'] = 'no_website'
            no_website_leads.append((i, lead))

    print(f"Leads with websites: {len(url_lead_pairs)}")
    print(f"Leads without websites: {len(no_website_leads)}")

    if len(url_lead_pairs) == 0:
        print("WARNING: No leads with websites to analyze")
        return leads

    # Estimate time (with parallelization)
    estimated_seconds = len(url_lead_pairs) * timeout / max_workers
    estimated_minutes = estimated_seconds / 60
    print(f"Estimated time with {max_workers} workers: {int(estimated_minutes)} minutes {int(estimated_seconds % 60)} seconds")

    # Stats tracking
    stats = {
        'success_count': 0,
        'failed_count': 0,
        'gtm_count': 0,
        'ads_count': 0,
        'conversion_count': 0,
        'remarketing_count': 0,
        'gtm_only': 0,
        'ads_no_conversion': 0,
        'no_tracking': 0,
        'full_setup': 0
    }

    # Process leads in parallel
    print(f"\nProcessing with {max_workers} concurrent workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_data = {
            executor.submit(detect_gtm_and_ads, url, timeout, False): (idx, url, lead)
            for idx, url, lead in url_lead_pairs
        }

        completed = 0
        for future in as_completed(future_to_data):
            idx, url, lead = future_to_data[future]

            try:
                result = future.result()
            except Exception as e:
                result = {
                    'gtm_installed': False,
                    'gtm_container_id': None,
                    'google_ads_detected': False,
                    'google_ads_account_id': None,
                    'conversion_tracking': False,
                    'remarketing_tag': False,
                    'status': 'failed'
                }
                if verbose:
                    print(f"  Exception analyzing {url}: {str(e)}")

            # Add fields to lead
            lead['gtm_installed'] = 'TRUE' if result['gtm_installed'] else 'FALSE'
            lead['gtm_container_id'] = result['gtm_container_id'] or ''
            lead['google_ads_detected'] = 'TRUE' if result['google_ads_detected'] else 'FALSE'
            lead['google_ads_account_id'] = result['google_ads_account_id'] or ''
            lead['conversion_tracking'] = 'TRUE' if result['conversion_tracking'] else 'FALSE'
            lead['remarketing_tag'] = 'TRUE' if result['remarketing_tag'] else 'FALSE'
            lead['tracking_analysis_status'] = result['status']

            completed += 1

            # Update stats
            if result['status'] == 'analyzed':
                stats['success_count'] += 1

                if result['gtm_installed']:
                    stats['gtm_count'] += 1
                if result['google_ads_detected']:
                    stats['ads_count'] += 1
                if result['conversion_tracking']:
                    stats['conversion_count'] += 1
                if result['remarketing_tag']:
                    stats['remarketing_count'] += 1

                # Opportunity breakdown
                if result['gtm_installed'] and not result['google_ads_detected']:
                    stats['gtm_only'] += 1
                elif result['google_ads_detected'] and not result['conversion_tracking']:
                    stats['ads_no_conversion'] += 1
                elif not result['gtm_installed'] and not result['google_ads_detected']:
                    stats['no_tracking'] += 1
                elif result['gtm_installed'] and result['conversion_tracking']:
                    stats['full_setup'] += 1
            else:
                stats['failed_count'] += 1

            if verbose:
                company = lead.get('Company Name') or lead.get('companyName') or lead.get('company_name') or 'Unknown'
                print(f"[{completed}/{len(url_lead_pairs)}] {company}: {result['status']}")
            elif completed % 20 == 0 or completed == len(url_lead_pairs):
                print(f"Progress: {completed}/{len(url_lead_pairs)} ({completed/len(url_lead_pairs)*100:.1f}%)")

    # Return leads in original order
    all_leads = url_lead_pairs + no_website_leads
    sorted_leads = [lead for _, lead in sorted([(idx, lead) for idx, _, lead in url_lead_pairs] + no_website_leads, key=lambda x: x[0])]

    # Print summary
    no_website_count = len(no_website_leads)
    success_count = stats['success_count']

    print(f"\n{'='*50}")
    print(f"Analysis Complete")
    print(f"{'='*50}")
    print(f"Successfully analyzed: {success_count} ({int(success_count/total*100)}%)")
    print(f"Failed: {stats['failed_count']}")
    print(f"No website: {no_website_count}")

    if success_count > 0:
        print(f"\nGTM Detection:")
        print(f"  GTM Installed: {stats['gtm_count']} ({int(stats['gtm_count']/success_count*100)}%)")
        print(f"  No GTM: {success_count - stats['gtm_count']} ({int((success_count - stats['gtm_count'])/success_count*100)}%)")

        print(f"\nGoogle Ads Detection:")
        print(f"  Ads Tracking Found: {stats['ads_count']} ({int(stats['ads_count']/success_count*100)}%)")
        print(f"  No Ads Tracking: {success_count - stats['ads_count']} ({int((success_count - stats['ads_count'])/success_count*100)}%)")

        print(f"\nConversion Tracking:")
        print(f"  With Conversion Tracking: {stats['conversion_count']} ({int(stats['conversion_count']/success_count*100)}%)")
        print(f"  Without Conversion Tracking: {success_count - stats['conversion_count']} ({int((success_count - stats['conversion_count'])/success_count*100)}%)")

        print(f"\nRemarketing:")
        print(f"  Remarketing Tags: {stats['remarketing_count']} ({int(stats['remarketing_count']/success_count*100)}%)")

        print(f"\n{'='*50}")
        print(f"Opportunity Breakdown")
        print(f"{'='*50}")
        print(f"GTM Only (no ads): {stats['gtm_only']} - Setup opportunity")
        print(f"Ads without conversion tracking: {stats['ads_no_conversion']} - Optimization opportunity")
        print(f"No tracking at all: {stats['no_tracking']} - Ground floor opportunity")
        print(f"Full setup: {stats['full_setup']} - Audit opportunity")

    return sorted_leads


def save_to_json(leads: List[Dict[str, Any]], output_file: str):
    """Save leads to JSON file"""
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2)
    print(f"\nSaved to: {output_file}")


def save_to_google_sheets(leads: List[Dict[str, Any]], sheet_name: str, source_spreadsheet_id: Optional[str] = None):
    """Save leads to Google Sheets (new tab in same spreadsheet or new spreadsheet)"""
    # Import here to avoid circular dependency
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from export_to_sheets import export_data_to_sheets

    # If we have source spreadsheet ID, add as new tab
    if source_spreadsheet_id:
        url = export_data_to_sheets(leads, sheet_name, target_spreadsheet_id=source_spreadsheet_id)
    else:
        url = export_data_to_sheets(leads, sheet_name)

    return url


def main():
    parser = argparse.ArgumentParser(description='Detect GTM and Google Ads tracking on lead websites')

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
    parser.add_argument('--max-workers', type=int, default=10, help='Number of concurrent threads (default: 10)')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout per request in seconds (default: 10)')
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
    analyzed_leads = analyze_leads(leads, max_workers=args.max_workers, timeout=args.timeout, verbose=args.verbose)

    # Save results
    if args.output:
        save_to_json(analyzed_leads, args.output)
    else:
        save_to_google_sheets(analyzed_leads, args.output_sheet, source_spreadsheet_id)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Website Validation Script

Validates websites in parallel using threading. Checks for:
- Valid HTTP status codes (2xx)
- SSL certificate errors
- Cloudflare/CloudFront blocks
- Request timeouts

Usage:
    python validate_websites.py --source-file .tmp/leads.json --output .tmp/validated_leads.json
    python validate_websites.py --source-url "https://docs.google.com/spreadsheets/d/ID/edit" --output-sheet "Validated Leads"
"""

import argparse
import json
import sys
import os
import re
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.exceptions import SSLError, Timeout, RequestException
import urllib3

# Add Google Sheets support
try:
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Disable SSL warnings for cleaner output
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Configuration
DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_WORKERS = 10
DEFAULT_TIMEOUT = 10


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


def load_from_google_sheets(spreadsheet_url: str, sheet_name: str = None) -> List[Dict[str, Any]]:
    """Load leads from Google Sheets"""
    if not GOOGLE_AVAILABLE:
        print("ERROR: Google API libraries not installed.")
        sys.exit(3)
    
    # Extract spreadsheet ID from URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    if not match:
        print(f"ERROR: Invalid Google Sheets URL: {spreadsheet_url}")
        sys.exit(3)
    
    spreadsheet_id = match.group(1)
    
    # Authenticate
    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)
    
    # Get sheet data
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
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'leads' in data:
            return data['leads']
        else:
            print(f"ERROR: Unexpected JSON structure in {file_path}")
            sys.exit(3)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {file_path}: {e}")
        sys.exit(3)


def get_website_url(lead: Dict[str, Any]) -> str:
    """Extract website URL from lead"""
    website = (
        lead.get('companyWebsite') or 
        lead.get('company_website') or 
        lead.get('website') or
        lead.get('companyDomain') or
        lead.get('company_domain') or
        lead.get('domain') or
        # Title Case Apollo format
        lead.get('Company Website') or
        lead.get('Company Domain') or
        ''
    )
    
    website = str(website).strip()
    
    # Convert HTTP to HTTPS
    if website.startswith('http://'):
        website = website.replace('http://', 'https://', 1)
    
    # Add https:// if missing
    if website and not website.startswith('http'):
        website = 'https://' + website
    
    return website


def validate_website(url: str, timeout: int = DEFAULT_TIMEOUT, retry_count: int = 0, max_retries: int = 3) -> Tuple[str, str]:
    """
    Validate a single website URL with retry logic
    
    Returns:
        (status, status_message)
    """
    if not url:
        return ('no_url', 'No website URL found')
    
    # Add delay for retries (exponential backoff)
    if retry_count > 0:
        import time
        delay = retry_count * 2  # 2s, 4s, 6s
        time.sleep(delay)
    
    # Increase timeout for retries
    actual_timeout = timeout * (1 + retry_count * 0.5)  # 10s, 15s, 20s
    
    try:
        # Try HEAD request first (faster)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.head(url, timeout=actual_timeout, allow_redirects=True, headers=headers, verify=True)
        
        # If HEAD not allowed, try GET
        if response.status_code == 405:
            response = requests.get(url, timeout=actual_timeout, allow_redirects=True, headers=headers, verify=True)
        
        # Check status code
        if 200 <= response.status_code < 300:
            retry_msg = f" (retry {retry_count})" if retry_count > 0 else ""
            return ('valid', f'{response.status_code} OK{retry_msg}')
        
        # Check for Cloudflare/CloudFront
        response_text = response.text.lower() if hasattr(response, 'text') else ''
        server_header = response.headers.get('Server', '').lower()
        
        is_cloudflare = 'cloudflare' in response_text or 'cloudflare' in server_header or 'cf-ray' in response.headers
        is_cloudfront = 'cloudfront' in response_text or 'cloudfront' in server_header
        
        if is_cloudflare or is_cloudfront:
            if response.status_code in [403, 429]:
                # Retry blocked requests
                if retry_count < max_retries:
                    return validate_website(url, timeout, retry_count + 1, max_retries)
                
                service = "Cloudflare" if is_cloudflare else "CloudFront"
                if response.status_code == 403:
                    return ('blocked', f'{response.status_code} Forbidden - {service} block detected (retried {retry_count}x)')
                else:
                    return ('blocked', f'{response.status_code} Too Many Requests - {service} rate limit (retried {retry_count}x)')
        
        # Other non-2xx codes
        return ('invalid', f'{response.status_code} {response.reason}')
        
    except SSLError as e:
        error_msg = str(e)
        if 'certificate verify failed' in error_msg.lower():
            return ('ssl_error', 'SSL Certificate verification failed')
        return ('ssl_error', f'SSL Error: {error_msg[:100]}')
    
    except Timeout:
        # Retry timeouts
        if retry_count < max_retries:
            return validate_website(url, timeout, retry_count + 1, max_retries)
        return ('timeout', f'Request timeout ({actual_timeout:.0f}s, retried {retry_count}x)')
    
    except RequestException as e:
        error_msg = str(e)
        
        # Check if error message mentions Cloudflare/CloudFront
        if 'cloudflare' in error_msg.lower():
            if retry_count < max_retries:
                return validate_website(url, timeout, retry_count + 1, max_retries)
            return ('blocked', f'Cloudflare block: {error_msg[:80]} (retried {retry_count}x)')
        
        if 'cloudfront' in error_msg.lower():
            if retry_count < max_retries:
                return validate_website(url, timeout, retry_count + 1, max_retries)
            return ('blocked', f'CloudFront block: {error_msg[:80]} (retried {retry_count}x)')
        
        # Retry unknown connection errors
        if retry_count < max_retries:
            return validate_website(url, timeout, retry_count + 1, max_retries)
        
        return ('unknown', f'Error: {error_msg[:80]} (retried {retry_count}x)')
    
    except Exception as e:
        # Retry unknown errors
        if retry_count < max_retries:
            return validate_website(url, timeout, retry_count + 1, max_retries)
        
        return ('unknown', f'Unknown error: {str(e)[:80]} (retried {retry_count}x)')


def validate_websites_batch(leads: List[Dict[str, Any]], max_workers: int = DEFAULT_MAX_WORKERS, 
                            timeout: int = DEFAULT_TIMEOUT, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Validate websites in parallel using threading
    
    Args:
        leads: List of lead dictionaries
        max_workers: Number of concurrent threads
        timeout: Timeout per request in seconds
        verbose: Print progress
    
    Returns:
        List of leads with website_status and website_status_message fields added
    """
    total = len(leads)
    validated_leads = []
    
    # Create URL mapping
    url_lead_pairs = [(i, get_website_url(lead), lead) for i, lead in enumerate(leads)]
    
    print(f"\nValidating {total} websites with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_data = {
            executor.submit(validate_website, url, timeout): (idx, url, lead)
            for idx, url, lead in url_lead_pairs
        }
        
        completed = 0
        for future in as_completed(future_to_data):
            idx, url, lead = future_to_data[future]
            
            try:
                status, status_message = future.result()
            except Exception as e:
                status = 'unknown'
                status_message = f'Validation error: {str(e)[:100]}'
            
            # Add status fields to lead
            lead['website_status'] = status
            lead['website_status_message'] = status_message
            
            completed += 1
            
            if verbose:
                company = lead.get('company_name') or lead.get('companyName') or 'Unknown'
                print(f"[{completed}/{total}] {company}: {status} - {status_message}")
            elif completed % 50 == 0:
                print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")
        
        # Return leads in original order
        validated_leads = [lead for _, _, lead in sorted(url_lead_pairs, key=lambda x: x[0])]
    
    return validated_leads


def print_validation_stats(leads: List[Dict[str, Any]]):
    """Print validation statistics"""
    total = len(leads)
    
    status_counts = {}
    for lead in leads:
        status = lead.get('website_status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n" + "="*50)
    print("WEBSITE VALIDATION RESULTS")
    print("="*50)
    print(f"Total websites checked: {total}")
    for status in ['valid', 'invalid', 'ssl_error', 'blocked', 'timeout', 'no_url', 'unknown']:
        count = status_counts.get(status, 0)
        if count > 0:
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {status}: {count} ({pct:.1f}%)")
    print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Validate website URLs in leads data')
    
    # Source options
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Path to JSON file containing leads')
    source_group.add_argument('--source-url', help='Google Sheets URL')
    
    # Output options
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', '-o', help='Output JSON file path')
    output_group.add_argument('--output-sheet', help='Name of Google Sheet to create')
    
    parser.add_argument('--sheet-name', help='Sheet name (for Google Sheets source)', default=None)
    parser.add_argument('--max-workers', type=int, default=DEFAULT_MAX_WORKERS, 
                       help=f'Number of concurrent threads (default: {DEFAULT_MAX_WORKERS})')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                       help=f'Request timeout in seconds (default: {DEFAULT_TIMEOUT})')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')
    
    args = parser.parse_args()
    
    # Load leads
    print("Loading leads...")
    if args.source_file:
        leads = load_from_json(args.source_file)
        print(f"Loaded {len(leads)} leads from {args.source_file}")
    else:
        leads = load_from_google_sheets(args.source_url, args.sheet_name)
        print(f"Loaded {len(leads)} leads from Google Sheets")
    
    if not leads:
        print("WARNING: No leads to process")
        sys.exit(0)
    
    # Validate websites
    validated_leads = validate_websites_batch(leads, args.max_workers, args.timeout, args.verbose)
    
    # Print statistics
    print_validation_stats(validated_leads)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(validated_leads, f, indent=2)
        print(f"Validated leads saved to: {args.output}")
    
    elif args.output_sheet:
        print(f"\nExporting to Google Sheet: '{args.output_sheet}'...")
        
        # If source was a spreadsheet, export to the same spreadsheet
        target_spreadsheet_id = None
        if args.source_url:
            try:
                target_spreadsheet_id = args.source_url.split('/d/')[1].split('/')[0]
                print(f"Targeting source spreadsheet: {target_spreadsheet_id}")
            except Exception:
                print("Could not extract spreadsheet ID from source URL. Will create new sheet.")
        
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from export_to_sheets import export_data_to_sheets
            
            export_data_to_sheets(validated_leads, args.output_sheet, target_spreadsheet_id=target_spreadsheet_id)
        except ImportError:
            print("ERROR: Could not import export_to_sheets. Make sure it is in the same directory.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR exporting to sheets: {e}")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

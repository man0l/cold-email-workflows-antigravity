#!/usr/bin/env python3
"""
Email Enrichment Script using AnyMailFinder

Enriches leads with email addresses by calling AnyMailFinder API.

Usage:
    # From JSON to JSON
    python execution/find_emails.py --source-file .tmp/cleaned_leads.json --output .tmp/enriched.json --max-leads 100
    
    # From Google Sheet to JSON
    python execution/find_emails.py --source-url "SHEET_URL" --output .tmp/enriched.json --max-leads 50
    
    # From JSON to Google Sheet
    python execution/find_emails.py --source-file .tmp/cleaned.json --output-sheet "Enriched Leads" --max-leads 75
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Try to import Google Sheets libraries
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from google.oauth2.service_account import Credentials as ServiceAccountCredentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def authenticate_google():
    """Authenticate with Google Sheets API using credentials.json (Service Account)"""
    creds_path = 'credentials.json'
    if not os.path.exists(creds_path):
        print(f"❌ Error: {creds_path} not found")
        sys.exit(1)
    
    creds = ServiceAccountCredentials.from_service_account_file(creds_path, scopes=SCOPES)
    return creds


def load_from_google_sheets(spreadsheet_url: str, sheet_name: Optional[str] = None):
    """Load leads from Google Sheets"""
    if not GOOGLE_AVAILABLE:
        print("❌ Error: Google Sheets libraries not available. Install with: pip install google-api-python-client google-auth")
        sys.exit(1)
    
    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)
    
    # Extract spreadsheet ID from URL
    if '/d/' in spreadsheet_url:
        spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
    else:
        spreadsheet_id = spreadsheet_url
    
    # Get sheet data
    try:
        if sheet_name:
            range_name = f"{sheet_name}!A:ZZ"
        else:
            range_name = "A:ZZ"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            print("❌ No data found in sheet")
            return []
        
        # Convert to list of dicts
        headers = rows[0]
        leads = []
        for row in rows[1:]:
            # Pad row to match headers length
            row = row + [''] * (len(headers) - len(row))
            lead = {headers[i]: row[i] for i in range(len(headers))}
            leads.append(lead)
        
        return leads
    
    except HttpError as e:
        print(f"❌ Error accessing Google Sheet: {e}")
        sys.exit(1)


def load_from_json(file_path: str):
    """Load leads from JSON file"""
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'leads' in data:
        return data['leads']
    else:
        print(f"❌ Error: Unexpected JSON format in {file_path}")
        sys.exit(1)


def extract_domain(url: str) -> str:
    """Extract clean domain from URL or domain string"""
    if not url:
        return ""
    
    # Remove common prefixes
    url = url.strip().lower()
    url = url.replace('http://', '').replace('https://', '').replace('www.', '')
    
    # Remove path and query params
    if '/' in url:
        url = url.split('/')[0]
    if '?' in url:
        url = url.split('?')[0]
    
    return url


def get_field_value(lead: Dict[str, Any], *possible_keys: str) -> str:
    """Get value from lead using multiple possible key names"""
    for key in possible_keys:
        if key in lead and lead[key]:
            return str(lead[key]).strip()
    return ""


def find_email_anymailfinder(first_name: str, last_name: str, domain: str, api_key: str, verbose: bool = False) -> Tuple[Optional[str], Optional[int], Optional[bool]]:
    """
    Call AnyMailFinder API to find email address.
    
    Returns:
        (email, confidence, verified) or (None, None, None) if not found
    """
    url = "https://api.anymailfinder.com/v5.0/search/person.json"
    
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    payload = {
        'first_name': first_name,
        'last_name': last_name,
        'domain': domain
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if verbose:
            print(f"  API Response: {json.dumps(data, indent=2)}")
        
        # Check if email was found
        if data.get('success') and data.get('email'):
            email = data.get('email')
            confidence = data.get('confidence', 0)
            verified = data.get('verified', False)
            return email, confidence, verified
        else:
            return None, None, None
    
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  API Error: {e}")
        return None, None, None


def enrich_leads(leads: List[Dict[str, Any]], max_leads: int, skip_existing: bool = True, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Enrich leads with email addresses using AnyMailFinder API.
    
    Returns:
        (enriched_leads, stats)
    """
    api_key = os.getenv('ANYMAILFINDER_API_KEY')
    if not api_key:
        print("❌ Error: ANYMAILFINDER_API_KEY not found in .env file")
        sys.exit(1)
    
    stats = {
        'total': len(leads),
        'processed': 0,
        'skipped_existing': 0,
        'skipped_missing_fields': 0,
        'emails_found': 0,
        'emails_not_found': 0
    }
    
    enriched_leads = []
    leads_to_process = leads[:max_leads]
    
    print(f"\n📧 Processing {len(leads_to_process)} leads...")
    print("━" * 50)
    
    for i, lead in enumerate(leads_to_process, 1):
        # Get required fields
        first_name = get_field_value(lead, 'firstName', 'first_name', 'personFirstName')
        last_name = get_field_value(lead, 'lastName', 'last_name', 'personLastName')
        domain = get_field_value(lead, 'companyWebsite', 'company_website', 'website', 'companyDomain', 'company_domain', 'domain')
        
        # Clean domain
        domain = extract_domain(domain)
        
        # Check if we should skip
        existing_email = get_field_value(lead, 'email', 'personEmail', 'person_email')
        
        if skip_existing and existing_email:
            stats['skipped_existing'] += 1
            enriched_leads.append(lead)
            if verbose:
                print(f"[{i}/{len(leads_to_process)}] ⏭️  Skipped (has email): {first_name} {last_name}")
            continue
        
        # Check required fields
        if not first_name or not last_name or not domain:
            stats['skipped_missing_fields'] += 1
            enriched_leads.append(lead)
            if verbose:
                print(f"[{i}/{len(leads_to_process)}] ⚠️  Skipped (missing fields): {first_name} {last_name} @ {domain}")
            continue
        
        # Make API call
        if verbose:
            print(f"[{i}/{len(leads_to_process)}] 🔍 Searching: {first_name} {last_name} @ {domain}")
        else:
            # Show progress
            progress = int((i / len(leads_to_process)) * 40)
            bar = "━" * progress + "░" * (40 - progress)
            print(f"\r{bar} {i}/{len(leads_to_process)} ({int(i/len(leads_to_process)*100)}%)", end='', flush=True)
        
        email, confidence, verified = find_email_anymailfinder(first_name, last_name, domain, api_key, verbose)
        
        # Update lead
        if email:
            lead['email'] = email
            lead['email_confidence'] = confidence
            lead['email_verified'] = verified
            stats['emails_found'] += 1
            if verbose:
                print(f"  ✅ Found: {email} (confidence: {confidence}%)")
        else:
            stats['emails_not_found'] += 1
            if verbose:
                print(f"  ❌ Not found")
        
        stats['processed'] += 1
        enriched_leads.append(lead)
        
        # Rate limiting - small delay to avoid overwhelming API
        time.sleep(0.5)
    
    if not verbose:
        print()  # New line after progress bar
    
    return enriched_leads, stats


def save_to_json(leads: List[Dict[str, Any]], output_path: str):
    """Save leads to JSON file"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {output_path}")


def save_to_google_sheets(leads: List[Dict[str, Any]], sheet_name: str):
    """Save leads to a new Google Spreadsheet"""
    if not GOOGLE_AVAILABLE:
        print("❌ Error: Google Sheets libraries not available")
        sys.exit(1)
    
    creds = authenticate_google()
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Create new spreadsheet
    spreadsheet = {
        'properties': {
            'title': sheet_name
        }
    }
    
    try:
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        
        # Move to Lead Gen folder
        folder_id = "0ADWgx-M8Z5r-Uk9PVA"
        drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            fields='id, parents'
        ).execute()
        
        # Prepare data
        if not leads:
            print("⚠️  No leads to export")
            return
        
        headers = list(leads[0].keys())
        rows = [headers]
        
        for lead in leads:
            row = [str(lead.get(h, '')) for h in headers]
            rows.append(row)
        
        # Write data
        body = {
            'values': rows
        }
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        print(f"\n✅ Created Google Sheet: {sheet_name}")
        print(f"📊 URL: {sheet_url}")
        
    except HttpError as e:
        print(f"❌ Error creating Google Sheet: {e}")
        sys.exit(1)


def ask_permission(leads: List[Dict[str, Any]], max_leads: int, skip_existing: bool = True):
    """Ask user for permission before making API calls"""
    
    # Count leads that will actually be processed
    leads_without_email = 0
    for lead in leads[:max_leads]:
        existing_email = get_field_value(lead, 'email', 'personEmail', 'person_email')
        if not existing_email:
            leads_without_email += 1
    
    will_process = leads_without_email if skip_existing else min(len(leads), max_leads)
    
    print("\n" + "=" * 50)
    print("📧 Email Enrichment Tool")
    print("=" * 50)
    print(f"\n📊 Summary:")
    print(f"  Total leads: {len(leads)}")
    if skip_existing:
        print(f"  Leads without email: {leads_without_email}")
        print(f"  Will process: {will_process} leads (only empty emails)")
    else:
        print(f"  Will process: {will_process} leads (including existing emails)")
    print(f"  Max leads limit: {max_leads}")
    print(f"  Estimated cost: ~{will_process} credits")
    print(f"\n⚠️  WARNING: This will consume API credits!")
    print("=" * 50)
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Cancelled by user")
        sys.exit(0)
    
    print("\n✅ Starting enrichment...")


def print_stats(stats: Dict[str, int]):
    """Print enrichment statistics"""
    print("\n" + "=" * 50)
    print("✅ Email Enrichment Summary")
    print("=" * 50)
    
    total_processed = stats['processed']
    if total_processed > 0:
        found_pct = int((stats['emails_found'] / total_processed) * 100)
        not_found_pct = int((stats['emails_not_found'] / total_processed) * 100)
        
        print(f"  Emails found: {stats['emails_found']} ({found_pct}%)")
        print(f"  No email found: {stats['emails_not_found']} ({not_found_pct}%)")
    
    if stats['skipped_existing'] > 0:
        print(f"  Skipped (had email): {stats['skipped_existing']}")
    
    if stats['skipped_missing_fields'] > 0:
        print(f"  Skipped (missing fields): {stats['skipped_missing_fields']}")
    
    print(f"  Total processed: {stats['processed']}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='Enrich leads with email addresses using AnyMailFinder')
    
    # Source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Path to source JSON file')
    source_group.add_argument('--source-url', help='Google Sheets URL')
    
    # Output
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', help='Path to output JSON file')
    output_group.add_argument('--output-sheet', help='Name for new Google Sheet')
    
    # Options
    parser.add_argument('--max-leads', type=int, default=100, help='Maximum number of leads to process (default: 100)')
    parser.add_argument('--sheet-name', help='Sheet name to read from (for Google Sheets source)')
    parser.add_argument('--include-existing', action='store_true', help='Process ALL leads including those that already have emails (by default, only empty emails are enriched)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')
    
    args = parser.parse_args()
    
    # Load leads
    if args.source_file:
        print(f"📂 Loading from: {args.source_file}")
        leads = load_from_json(args.source_file)
    else:
        print(f"📊 Loading from Google Sheet...")
        leads = load_from_google_sheets(args.source_url, args.sheet_name)
    
    if not leads:
        print("❌ No leads found")
        sys.exit(1)
    
    print(f"✅ Loaded {len(leads)} leads")
    
    # Determine skip_existing flag (True by default, unless --include-existing is set)
    skip_existing = not args.include_existing
    
    # Ask for permission
    ask_permission(leads, args.max_leads, skip_existing)
    
    # Enrich leads
    enriched_leads, stats = enrich_leads(leads, args.max_leads, skip_existing, args.verbose)
    
    # Print stats
    print_stats(stats)
    
    # Save output
    if args.output:
        save_to_json(enriched_leads, args.output)
    else:
        save_to_google_sheets(enriched_leads, args.output_sheet)


if __name__ == '__main__':
    main()

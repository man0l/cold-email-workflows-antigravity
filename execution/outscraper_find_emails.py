#!/usr/bin/env python3
"""
Email & Contact Enrichment Script using Outscraper

Enriches leads with emails, phone numbers, social media, and company details by domain.

Usage:
    # From JSON to JSON
    python execution/outscraper_find_emails.py --source-file .tmp/cleaned_leads.json --output .tmp/enriched.json --max-leads 50

    # From Google Sheet to JSON
    python execution/outscraper_find_emails.py --source-url "SHEET_URL" --output .tmp/enriched.json --max-leads 50

    # From JSON to Google Sheet
    python execution/outscraper_find_emails.py --source-file .tmp/cleaned.json --output-sheet "Enriched Leads" --max-leads 50
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import Google Sheets libraries
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
except ImportError:
    ServiceAccountCredentials = None

# Try to import Outscraper
try:
    from outscraper import ApiClient
    OUTSCRAPER_AVAILABLE = True
except ImportError:
    OUTSCRAPER_AVAILABLE = False

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


def enrich_with_outscraper(client: ApiClient, domain: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Call Outscraper API to find emails, phones, and contacts.

    Returns:
        Enrichment data dict or None if error
    """
    try:
        results = client.emails_and_contacts([domain])

        if verbose:
            print(f"  API Response: {json.dumps(results, indent=2)}")

        if results and len(results) > 0:
            return results[0]
        else:
            return None

    except Exception as e:
        print(f"  ⚠️  API Error: {e}")
        return None


def has_email(lead: Dict[str, Any]) -> bool:
    """Check if lead already has an email address"""
    email = get_field_value(lead, 'email', 'personEmail', 'person_email', 'primary_email', 'Email')
    return bool(email)


def enrich_leads(leads: List[Dict[str, Any]], max_leads: int, verbose: bool = False, skip_confirm: bool = False, output_file: str = None, skip_existing_emails: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Enrich leads with contact data using Outscraper API.

    Args:
        leads: List of lead dictionaries
        max_leads: Maximum number of leads to process
        verbose: Print detailed output
        skip_confirm: Skip user confirmation
        output_file: Output file path for checkpoint
        skip_existing_emails: Only process leads missing email addresses (default: True)

    Returns:
        (enriched_leads, stats)
    """
    if not OUTSCRAPER_AVAILABLE:
        print("❌ Error: outscraper library not installed")
        print("   Install with: pip install outscraper")
        sys.exit(1)

    api_key = os.getenv('OUTSCRAPER_API')
    if not api_key:
        print("❌ Error: OUTSCRAPER_API not found in .env file")
        sys.exit(1)

    # Initialize Outscraper client
    client = ApiClient(api_key=api_key)

    stats = {
        'total': len(leads),
        'processed': 0,
        'skipped_no_domain': 0,
        'skipped_has_email': 0,
        'contacts_found': 0,
        'contacts_not_found': 0
    }

    # Filter leads with domains and optionally without emails
    leads_with_domains = []
    for lead in leads:
        # Skip if lead already has email and skip_existing_emails is True
        if skip_existing_emails and has_email(lead):
            stats['skipped_has_email'] += 1
            continue

        domain = get_field_value(lead, 'companyWebsite', 'website', 'companyDomain', 'domain', 'company_website', 'company_domain')
        domain = extract_domain(domain)
        if domain:
            leads_with_domains.append((lead, domain))

    stats['skipped_no_domain'] = len(leads) - len(leads_with_domains) - stats['skipped_has_email']

    # Limit to max_leads
    leads_to_process = leads_with_domains[:max_leads]

    # Show summary and ask for confirmation
    print("\n📧 Outscraper Email & Contact Finder")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"  Total leads: {stats['total']}")
    if skip_existing_emails:
        print(f"  Leads missing emails: {stats['total'] - stats['skipped_has_email']}")
        print(f"  Leads with valid domains: {len(leads_with_domains)}")
        if stats['skipped_has_email'] > 0:
            print(f"  Skipped (already have emails): {stats['skipped_has_email']}")
    else:
        print(f"  Leads with valid domains: {len(leads_with_domains)}")
    print(f"  Will process: {len(leads_to_process)} leads")
    print(f"  Estimated cost: ~{len(leads_to_process)} credits")
    print(f"\n⚠️  WARNING: This will consume API credits!")
    if skip_existing_emails and stats['skipped_has_email'] > 0:
        print(f"⚠️  NOTE: Skipping {stats['skipped_has_email']} leads that already have emails")
    print("=" * 60)

    if not skip_confirm:
        response = input("\nContinue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Aborted by user")
            sys.exit(0)
    else:
        print("\n✓ Auto-confirmed (--yes flag used)")

    enriched_leads = []
    completed_count = 0

    # Create checkpoint file path
    checkpoint_file = output_file.replace('.json', '_checkpoint.json') if output_file else '.tmp/outscraper_checkpoint.json'

    print(f"\n📧 Processing {len(leads_to_process)} leads in parallel...")
    print(f"💾 Checkpoint file: {checkpoint_file}")
    print("━" * 50)

    # Helper function to process a single lead
    def process_lead(lead_domain_tuple):
        lead, domain = lead_domain_tuple
        data = enrich_with_outscraper(client, domain, False)
        return lead, domain, data

    # Use ThreadPoolExecutor for parallel processing
    max_workers = 10  # Parallel threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_lead = {
            executor.submit(process_lead, (lead, domain)): (lead, domain)
            for lead, domain in leads_to_process
        }

        # Process completed tasks
        for future in as_completed(future_to_lead):
            lead, domain, data = future.result()
            completed_count += 1

            # Update lead with enriched data
            if data:
                # Emails
                emails = data.get('emails', [])
                if emails:
                    # Extract email values
                    email_list = [e.get('value', '') for e in emails if e.get('value')]
                    lead['emails'] = email_list
                    lead['primary_email'] = email_list[0] if email_list else ''
                    lead['emails_raw'] = emails  # Full email objects with names/titles
                    stats['contacts_found'] += 1
                    if verbose:
                        print(f"  ✅ {domain}: Found {len(email_list)} email(s)")
                else:
                    stats['contacts_not_found'] += 1
                    if verbose:
                        print(f"  ❌ {domain}: No contacts found")

                # Phones
                phones = data.get('phones', [])
                if phones:
                    phone_list = [p.get('value', '') for p in phones if p.get('value')]
                    lead['phones'] = phone_list
                    lead['primary_phone'] = phone_list[0] if phone_list else ''

                # Individual contacts (with names and titles)
                contacts = data.get('contacts', [])
                if contacts:
                    lead['contacts'] = contacts

                # Social media
                socials = data.get('socials', {})
                if socials:
                    lead['socials'] = socials
                    # Also add individual social fields for easier access
                    for platform, url in socials.items():
                        lead[f'social_{platform}'] = url

                # Company details
                details = data.get('details', {})
                if details:
                    lead['company_name'] = details.get('name', '')
                    lead['industry'] = details.get('industry', [])
                    lead['employees'] = details.get('employees', '')
                    lead['founded'] = details.get('founded', '')
                    lead['company_address'] = details.get('address', '')
                    lead['company_city'] = details.get('city', '')
                    lead['company_state'] = details.get('state', '')
                    lead['company_postal_code'] = details.get('postal_code', '')
                    lead['company_country'] = details.get('country', '')
            else:
                stats['contacts_not_found'] += 1
                if verbose:
                    print(f"  ❌ {domain}: No data returned")

            stats['processed'] += 1
            enriched_leads.append(lead)

            # Save checkpoint every 10 leads
            if completed_count % 10 == 0:
                checkpoint_data = {
                    'enriched_leads': enriched_leads,
                    'stats': stats,
                    'completed_count': completed_count,
                    'total_to_process': len(leads_to_process)
                }
                try:
                    with open(checkpoint_file, 'w', encoding='utf-8') as f:
                        json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    if verbose:
                        print(f"  ⚠️  Failed to save checkpoint: {e}")

            # Show progress
            if not verbose:
                progress = int((completed_count / len(leads_to_process)) * 40)
                bar = "━" * progress + "░" * (40 - progress)
                print(f"\r{bar} {completed_count}/{len(leads_to_process)} ({int(completed_count/len(leads_to_process)*100)}%)", end='', flush=True)

    if not verbose:
        print()  # New line after progress bar

    # Add leads that were skipped (no domain)
    for lead in leads:
        if lead not in enriched_leads:
            enriched_leads.append(lead)

    # Save final checkpoint
    checkpoint_data = {
        'enriched_leads': enriched_leads,
        'stats': stats,
        'completed_count': completed_count,
        'total_to_process': len(leads_to_process)
    }
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Final checkpoint saved: {checkpoint_file}")
    except Exception as e:
        print(f"⚠️  Failed to save final checkpoint: {e}")

    return enriched_leads, stats


def save_to_json(leads: List[Dict[str, Any]], output_path: str):
    """Save leads to JSON file"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to: {output_path}")


def save_to_google_sheets(leads: List[Dict[str, Any]], sheet_name: str, source_spreadsheet_id: Optional[str] = None):
    """Save leads to a new sheet in existing spreadsheet or create new spreadsheet"""
    if not GOOGLE_AVAILABLE:
        print("❌ Error: Google Sheets libraries not available")
        sys.exit(1)

    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    if source_spreadsheet_id:
        # Add new sheet to existing spreadsheet
        spreadsheet_id = source_spreadsheet_id

        # Create new sheet in existing spreadsheet
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }

        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            print(f"\n✅ Added new sheet '{sheet_name}' to existing spreadsheet")
        except HttpError as e:
            if 'already exists' in str(e):
                print(f"\n⚠️  Sheet '{sheet_name}' already exists, will overwrite")
            else:
                raise
    else:
        # Create new spreadsheet
        spreadsheet = {
            'properties': {
                'title': sheet_name
            }
        }

        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']

        print(f"\n✅ Created spreadsheet: {sheet_name}")
        print(f"   ID: {spreadsheet_id}")

    # Prepare data for sheets
    if not leads:
        print("⚠️  No leads to save")
        return

    # Flatten nested structures for Google Sheets
    flattened_leads = []
    for lead in leads:
        flat_lead = {}
        for key, value in lead.items():
            if isinstance(value, (list, dict)):
                flat_lead[key] = json.dumps(value, ensure_ascii=False)
            else:
                flat_lead[key] = value
        flattened_leads.append(flat_lead)

    # Get all unique headers
    headers = list(set(k for lead in flattened_leads for k in lead.keys()))
    headers.sort()

    # Build rows
    rows = [headers]
    for lead in flattened_leads:
        row = [str(lead.get(h, '')) for h in headers]
        rows.append(row)

    # Write to sheet
    body = {
        'values': rows
    }

    # Use sheet name in range if adding to existing spreadsheet
    range_name = f"'{sheet_name}'!A1" if source_spreadsheet_id else 'A1'

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    print(f"   Rows: {len(rows) - 1}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


def main():
    parser = argparse.ArgumentParser(description='Enrich leads with Outscraper emails & contacts')

    # Source options
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Source JSON file path')
    source_group.add_argument('--source-url', help='Source Google Spreadsheet URL')

    # Output options
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', help='Output JSON file path')
    output_group.add_argument('--output-sheet', help='Output Google Sheet name')

    # Optional arguments
    parser.add_argument('--sheet-name', help='Sheet name (for Google Sheets source)', default=None)
    parser.add_argument('--max-leads', type=int, default=50, help='Maximum leads to process (default: 50)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')

    # Email filtering options
    email_filter_group = parser.add_mutually_exclusive_group()
    email_filter_group.add_argument('--skip-existing-emails', action='store_true', default=True,
                                    help='Only process leads missing email addresses (default: enabled)')
    email_filter_group.add_argument('--process-all', action='store_true',
                                    help='Process ALL leads regardless of existing email data')

    args = parser.parse_args()

    # Handle the mutually exclusive group logic
    skip_existing_emails = not args.process_all

    # Load leads
    print("📂 Loading leads...")
    source_spreadsheet_id = None
    if args.source_file:
        leads = load_from_json(args.source_file)
        print(f"✓ Loaded {len(leads)} leads from {args.source_file}")
    else:
        leads = load_from_google_sheets(args.source_url, args.sheet_name)
        print(f"✓ Loaded {len(leads)} leads from Google Sheets")

        # Extract spreadsheet ID for later use
        if '/d/' in args.source_url:
            source_spreadsheet_id = args.source_url.split('/d/')[1].split('/')[0]

    if not leads:
        print("❌ No leads found")
        sys.exit(1)

    # Enrich leads
    enriched_leads, stats = enrich_leads(leads, args.max_leads, args.verbose, args.yes, args.output, skip_existing_emails)

    # Print summary
    print("\n" + "=" * 60)
    print("✅ Outscraper Enrichment Summary:")
    print(f"   Contacts found: {stats['contacts_found']} ({int(stats['contacts_found']/stats['processed']*100) if stats['processed'] > 0 else 0}%)")
    print(f"   No contacts found: {stats['contacts_not_found']} ({int(stats['contacts_not_found']/stats['processed']*100) if stats['processed'] > 0 else 0}%)")
    print(f"   Skipped (no domain): {stats['skipped_no_domain']}")
    if stats['skipped_has_email'] > 0:
        print(f"   Skipped (already had emails): {stats['skipped_has_email']}")
    print(f"   Total processed: {stats['processed']}")
    print("=" * 60)

    # Save results
    if args.output:
        save_to_json(enriched_leads, args.output)
    else:
        # ALWAYS save temporary backup before attempting Google Sheets upload
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f".tmp/outscraper_backup_{timestamp}.json"

        print(f"\n💾 Saving temporary backup to: {backup_path}")
        save_to_json(enriched_leads, backup_path)

        # Now attempt Google Sheets upload
        try:
            save_to_google_sheets(enriched_leads, args.output_sheet, source_spreadsheet_id)
        except Exception as e:
            print(f"\n⚠️  Google Sheets upload failed: {e}")
            print(f"✅ Data is safe in backup file: {backup_path}")
            print(f"   You can manually upload or retry later.")


if __name__ == '__main__':
    main()

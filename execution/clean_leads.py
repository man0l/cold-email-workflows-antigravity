#!/usr/bin/env python3
"""
Lead Cleaning Script

Filters leads from Google Sheets or JSON files based on:
1. Positive keywords (must match at least one)
2. Negative keywords (must NOT match any)
3. Industries (must match at least one)

Usage:
    python clean_leads.py --source-file .tmp/leads.json --keywords "video,editing" --industries "Media Production" --output .tmp/cleaned.json
    python clean_leads.py --source-url "https://docs.google.com/spreadsheets/d/ID/edit" --keywords "video" --not-keywords "marketing" --output .tmp/cleaned.json
"""

import argparse
import json
import sys
import os
from typing import List, Dict, Any, Optional
import re

# Add Google Sheets support
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
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
    if os.path.exists(creds_path):
        try:
            return ServiceAccountCredentials.from_service_account_file(creds_path, scopes=SCOPES)
        except ValueError:
            # Fallback for user credentials if needed, but primarily support Service Account
            print("WARNING: credentials.json appears to be invalid for Service Account.")
            sys.exit(3)
    else:
        print("ERROR: credentials.json not found")
        sys.exit(3)


def load_from_google_sheets(spreadsheet_url: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load leads from Google Sheets"""
    if not GOOGLE_AVAILABLE:
        print("ERROR: Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
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
    # Use A:ZZ to ensure we get all columns (A:Z cuts off at 26 columns)
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


def normalize_text(text: Any) -> str:
    """Normalize text for matching: lowercase, strip whitespace"""
    if text is None or text == '':
        return ''
    return str(text).lower().strip()


def check_keywords(lead: Dict[str, Any], keywords: List[str]) -> bool:
    """Check if lead matches at least one positive keyword"""
    if not keywords:
        return True
    
    # Fields to check for keywords
    searchable_fields = [
        'companyName', 'companyDescription', 'companyIndustry', 
        'companyTagline', 'personHeadline', 'name', 'headline',
        'description', 'industry', 'tagline',
        # Snake case variants (common in Apify exports)
        'company_name', 'company_description', 'company_industry',
        'company_tagline', 'person_headline', 'job_title',
        'keywords' # Apify keywords field
    ]
    
    # Combine all searchable text
    searchable_text = ' '.join([
        normalize_text(lead.get(field, '')) 
        for field in searchable_fields
    ])
    
    # Check if any keyword matches
    for keyword in keywords:
        if normalize_text(keyword) in searchable_text:
            return True
    
    return False


def check_not_keywords(lead: Dict[str, Any], not_keywords: List[str]) -> bool:
    """Check if lead matches any negative keyword (returns False if matched)"""
    if not not_keywords:
        return True
    
    # Fields to check for NOT keywords
    searchable_fields = [
        'companyName', 'companyDescription', 'companyIndustry',
        'companyTagline', 'personHeadline', 'name', 'headline',
        'description', 'industry', 'tagline',
        # Snake case variants
        'company_name', 'company_description', 'company_industry',
        'company_tagline', 'person_headline', 'job_title'
    ]
    
    # Combine all searchable text
    searchable_text = ' '.join([
        normalize_text(lead.get(field, '')) 
        for field in searchable_fields
    ])
    
    # Check if any NOT keyword matches (if so, reject the lead)
    for not_keyword in not_keywords:
        if normalize_text(not_keyword) in searchable_text:
            return False
    
    return True


def check_industries(lead: Dict[str, Any], industries: List[str]) -> bool:
    """Check if lead matches at least one target industry"""
    if not industries:
        return True
    
    # Get lead's industry (try multiple fields)
    lead_industry = normalize_text(
        lead.get('companyIndustry') or 
        lead.get('industry') or 
        lead.get('company_industry', '')
    )
    
    if not lead_industry:
        return False
    
    # Check if any target industry matches
    for industry in industries:
        if normalize_text(industry) in lead_industry:
            return True
    
    return False


def get_company_name(lead: Dict[str, Any]) -> str:
    """Get company name from lead using various possible keys"""
    return (
        lead.get('companyName') or 
        lead.get('company_name') or 
        lead.get('company') or 
        'Unknown'
    )


def check_website(lead: Dict[str, Any]) -> bool:
    """Check if lead has a website or domain"""
    website = (
        lead.get('companyWebsite') or 
        lead.get('company_website') or 
        lead.get('website') or
        lead.get('companyDomain') or
        lead.get('company_domain') or
        lead.get('domain')
    )
    
    if website and str(website).strip() and str(website).lower() != 'none':
        return True
    return False


def extract_domain(url: str) -> str:
    """Extract domain from URL or email string"""
    if not url:
        return ''
    
    s = str(url).lower().strip()
    
    # Remove protocol
    if '://' in s:
        s = s.split('://')[1]
    
    # Remove path
    if '/' in s:
        s = s.split('/')[0]
    
    # Remove www.
    if s.startswith('www.'):
        s = s[4:]
        
    return s


def verify_email_match(lead: Dict[str, Any]) -> bool:
    """
    Check if email domain matches website domain.
    If mismatch, clear email fields and return False.
    If match or no email/website, return True.
    """
    # Get email
    email_field = None
    email = None
    for field in ['email', 'emailAddress', 'contact_email', 'workEmail']:
        if lead.get(field):
            email = lead.get(field)
            email_field = field
            break
            
    if not email or '@' not in str(email):
        return True

    # Get website
    website = (
        lead.get('companyWebsite') or 
        lead.get('company_website') or 
        lead.get('website') or
        lead.get('companyDomain') or
        lead.get('company_domain') or
        lead.get('domain')
    )
    
    if not website:
        return True

    # Compare domains
    try:
        email_domain = extract_domain(str(email).split('@')[1])
        website_domain = extract_domain(str(website))
        
        if not email_domain or not website_domain:
            return True
            
        if email_domain != website_domain:
            # Mismatch - clear all email fields
            for field in ['email', 'emailAddress', 'contact_email', 'workEmail', 'personalEmail']:
                if field in lead:
                    lead[field] = ''
            return False
            
    except Exception:
        return True
        
    return True


def clean_leads(
    leads: List[Dict[str, Any]],
    keywords: List[str],
    not_keywords: List[str],
    industries: List[str],
    require_website: bool = False,
    verbose: bool = False
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Clean leads based on filters.
    
    Returns:
        (cleaned_leads, stats)
    """
    stats = {
        'total': len(leads),
        'after_keywords': 0,
        'after_not_keywords': 0,
        'after_industries': 0,
        'after_website': 0,
        'emails_removed': 0,
        'final': 0
    }
    
    cleaned = []
    
    for lead in leads:
        company_name = get_company_name(lead)
        
        # Filter 1: Check positive keywords
        if not check_keywords(lead, keywords):
            if verbose:
                print(f"FILTERED (keywords): {company_name}")
            continue
        
        stats['after_keywords'] += 1
        
        # Filter 2: Check NOT keywords
        if not check_not_keywords(lead, not_keywords):
            if verbose:
                print(f"FILTERED (NOT keywords): {company_name}")
            continue
        
        stats['after_not_keywords'] += 1
        
        # Filter 3: Check industries
        if not check_industries(lead, industries):
            if verbose:
                print(f"FILTERED (industry): {company_name} - {lead.get('companyIndustry') or lead.get('industry') or lead.get('company_industry', 'N/A')}")
            continue
        
        stats['after_industries'] += 1
        
        # Filter 4: Check website (optional)
        if require_website and not check_website(lead):
            if verbose:
                print(f"FILTERED (no website): {company_name}")
            continue
            
        stats['after_website'] += 1
        
        # Check email domain match (modify lead in place)
        if not verify_email_match(lead):
            stats['emails_removed'] += 1
            if verbose:
                print(f"EMAIL REMOVED (domain mismatch): {company_name}")
        
        # Lead passed all filters
        if verbose:
            print(f"PASSED: {company_name}")
        cleaned.append(lead)
    
    stats['final'] = len(cleaned)
    return cleaned, stats


def print_stats(stats: Dict[str, int]) -> None:
    """Print cleaning statistics"""
    total = stats['total']
    
    print("\n" + "="*50)
    print("LEAD CLEANING RESULTS")
    print("="*50)
    print(f"Total leads loaded:        {total}")
    print(f"After keyword filter:      {stats['after_keywords']} ({stats['after_keywords']/total*100:.1f}%)" if total > 0 else "After keyword filter:      0")
    print(f"After NOT keyword filter:  {stats['after_not_keywords']} ({stats['after_not_keywords']/total*100:.1f}%)" if total > 0 else "After NOT keyword filter:  0")
    print(f"After industry filter:     {stats['after_industries']} ({stats['after_industries']/total*100:.1f}%)" if total > 0 else "After industry filter:     0")
    if 'after_website' in stats and stats['after_website'] != stats['after_industries']:
         print(f"After website filter:      {stats['after_website']} ({stats['after_website']/total*100:.1f}%)" if total > 0 else "After website filter:      0")
    
    if 'emails_removed' in stats and stats['emails_removed'] > 0:
        print(f"Emails removed (mismatch): {stats['emails_removed']} ({(stats['emails_removed']/stats['final'])*100:.1f}% of final)" if stats['final'] > 0 else f"Emails removed (mismatch): {stats['emails_removed']}")
        
    print("="*50)
    print(f"FINAL CLEAN LEADS:         {stats['final']} ({stats['final']/total*100:.1f}%)" if total > 0 else "FINAL CLEAN LEADS:         0")
    print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Clean leads based on keywords and industries')
    
    # Source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Path to JSON file containing leads')
    source_group.add_argument('--source-url', help='Google Sheets URL')
    
    # Filter options
    parser.add_argument('--keywords', help='Comma-separated list of positive keywords', default='')
    parser.add_argument('--not-keywords', help='Comma-separated list of negative keywords', default='')
    parser.add_argument('--industries', help='Comma-separated list of target industries', default='')
    
    # Output options (mutually exclusive)
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--output', '-o', help='Output JSON file path')
    output_group.add_argument('--output-sheet', help='Name of new Google Sheet to create')
    
    parser.add_argument('--sheet-name', help='Sheet name (for Google Sheets source)', default=None)
    parser.add_argument('--require-website', action='store_true', default=True, help='Require leads to have a website or domain (default: True)')
    parser.add_argument('--no-require-website', dest='require_website', action='store_false', help='Allow leads without a website')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed filtering output')
    
    args = parser.parse_args()
    
    # Safety check: Prevent overwriting source file
    if args.source_file and args.output and os.path.abspath(args.source_file) == os.path.abspath(args.output):
        print("ERROR: Output file cannot be the same as source file. This tool is designed to never overwrite original data.")
        sys.exit(1)

    # Parse filter lists
    keywords = [k.strip() for k in args.keywords.split(',') if k.strip()] if args.keywords else []
    not_keywords = [k.strip() for k in args.not_keywords.split(',') if k.strip()] if args.not_keywords else []
    industries = [i.strip() for i in args.industries.split(',') if i.strip()] if args.industries else []
    
    # Show filter configuration
    print("\nLead Cleaning Configuration:")
    print(f"  Keywords (MUST match):     {keywords if keywords else '(none - all pass)'}")
    print(f"  NOT Keywords (MUST avoid): {not_keywords if not_keywords else '(none)'}")
    print(f"  Industries (MUST match):   {industries if industries else '(none - all pass)'}")
    print(f"  Require Website:           {'Yes' if args.require_website else 'No'}")
    print()
    
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
    
    # Data Quality Check
    if keywords or not_keywords:
        sample_lead = leads[0]
        rich_fields = ['companyDescription', 'company_description', 'companyTagline', 'company_tagline']
        available_rich_fields = [f for f in rich_fields if sample_lead.get(f)]
        
        if not available_rich_fields:
            print("\n" + "!"*60)
            print("WARNING: LIMITED DATA DETECTED")
            print("The leads appear to lack 'description' or 'tagline' fields.")
            print("Keyword filtering will only apply to Company Name, Industry, and Job Titles.")
            print("This may result in filtering out relevant companies.")
            print("Consider using only Industry filters or broadening your keywords.")
            print("!"*60 + "\n")

    # Clean leads
    print("\nCleaning leads...")
    cleaned_leads, stats = clean_leads(leads, keywords, not_keywords, industries, args.require_website, args.verbose)
    
    # Print statistics
    print_stats(stats)
    
    if stats['final'] == 0:
        print("\nWARNING: No leads passed the filters!")
        sys.exit(1)
    
    # Validate websites
    print("\nValidating websites...")
    try:
        # Import validation function
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from validate_websites import validate_websites_batch
        
        cleaned_leads = validate_websites_batch(
            cleaned_leads, 
            max_workers=10, 
            timeout=10, 
            verbose=args.verbose
        )
        
        # Print validation statistics
        status_counts = {}
        for lead in cleaned_leads:
            status = lead.get('website_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(cleaned_leads)
        print("\nWebsite Validation Summary:")
        for status in ['valid', 'invalid', 'ssl_error', 'blocked', 'timeout', 'no_url', 'unknown']:
            count = status_counts.get(status, 0)
            if count > 0:
                pct = (count / total * 100) if total > 0 else 0
                print(f"  {status}: {count} ({pct:.1f}%)")
        print()
        
        # Filter out non-valid websites
        print("Filtering out invalid websites...")
        original_count = len(cleaned_leads)
        cleaned_leads = [lead for lead in cleaned_leads if lead.get('website_status') == 'valid']
        removed_count = original_count - len(cleaned_leads)
        print(f"Removed {removed_count} leads with invalid/unreachable websites.")
        print(f"Final count after website validation: {len(cleaned_leads)}")
        
        # Remove status columns from output
        leads_without_email = 0
        for lead in cleaned_leads:
            lead.pop('website_status', None)
            lead.pop('website_status_message', None)
            
            # Check if email is missing
            has_email = False
            for field in ['email', 'emailAddress', 'contact_email', 'workEmail', 'personalEmail']:
                if lead.get(field) and str(lead.get(field)).strip():
                    has_email = True
                    break
            if not has_email:
                leads_without_email += 1
                
        print(f"Final count after website validation: {len(cleaned_leads)}")
        print(f"Leads without email: {leads_without_email} ({(leads_without_email/len(cleaned_leads))*100:.1f}%)")
            
    except ImportError as e:
        print(f"WARNING: Could not import validate_websites module: {e}")
        print("Proceeding without website validation...")
    except Exception as e:
        print(f"WARNING: Website validation failed: {e}")
        print("Proceeding with unvalidated leads...")

    # Save cleaned leads
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(cleaned_leads, f, indent=2)
        print(f"Cleaned leads saved to: {args.output}")
    # Export to Sheets
    elif args.output_sheet:
        print(f"\nExporting to Google Sheet: '{args.output_sheet}'...")
        
        # If source was a spreadsheet, try to export to the same spreadsheet
        target_spreadsheet_id = None
        if args.source_url:
            try:
                # Extract ID from URL
                target_spreadsheet_id = args.source_url.split('/d/')[1].split('/')[0]
                print(f"Targeting source spreadsheet: {target_spreadsheet_id}")
            except Exception:
                print("Could not extract spreadsheet ID from source URL. Will create new sheet.")
        
        try:
            # Import here to avoid circular dependency issues if not needed
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from export_to_sheets import export_data_to_sheets
            
            export_data_to_sheets(cleaned_leads, args.output_sheet, target_spreadsheet_id=target_spreadsheet_id)
        except ImportError:
            print("ERROR: Could not import export_to_sheets. Make sure it is in the same directory.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR exporting to sheets: {e}")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

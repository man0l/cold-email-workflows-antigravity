#!/usr/bin/env python3
"""
Casualise Company Name Script

Shortens company names to their casual, conversational form using OpenAI API.

Examples:
    "XYZ Agency" → "XYZ"
    "Love AMS Professional Services" → "Love AMS"
    "Love Mayo Inc." → "Love Mayo"

Usage:
    python casualise_company_name.py --source-url "SHEET_URL" --column "Company Name" --output-column "Casual Name"
    python casualise_company_name.py --source-file .tmp/leads.json --output .tmp/casualised.json
    python casualise_company_name.py --name "XYZ Agency"
"""

import argparse
import json
import sys
import os
import re
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API support
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("WARNING: openai package not installed. Run: pip install openai")
    print("Falling back to regex-based casualization")

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

# Suffixes to remove (in order of priority - more specific first)
SUFFIXES = [
    # Legal entities
    r'\s+Corporation\s*$',
    r'\s+Incorporated\s*$',
    r'\s+Limited\s*$',
    r'\s+Corp\.?\s*$',
    r'\s+Inc\.?\s*$',
    r'\s+LLC\.?\s*$',
    r'\s+Ltd\.?\s*$',
    r'\s+L\.L\.C\.?\s*$',
    r'\s+Co\.?\s*$',
    r'\s+Company\s*$',

    # Professional services
    r'\s+Professional\s+Services\s*$',
    r'\s+Consulting\s+Services\s*$',
    r'\s+Consultancy\s*$',
    r'\s+Consulting\s*$',
    r'\s+Consultant\s*$',
    r'\s+Consultants\s*$',

    # Business descriptors
    r'\s+Agency\s*$',
    r'\s+Agencies\s*$',
    r'\s+Services\s*$',
    r'\s+Service\s*$',
    r'\s+Solutions\s*$',
    r'\s+Technologies\s*$',
    r'\s+Technology\s*$',
    r'\s+Tech\s*$',
    r'\s+Group\s*$',
    r'\s+Partners\s*$',
    r'\s+Partnership\s*$',
    r'\s+Associates\s*$',

    # Media/Creative
    r'\s+Media\s*$',
    r'\s+Digital\s*$',
    r'\s+Studios\s*$',
    r'\s+Studio\s*$',
    r'\s+Productions\s*$',
    r'\s+Production\s*$',
    r'\s+Creatives\s*$',
    r'\s+Creative\s*$',
    r'\s+Software\s*$',
]


def authenticate_google():
    """Authenticate with Google Sheets API using credentials.json"""
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


def casualise_company_name_regex(name: str, verbose: bool = False) -> str:
    """
    Casualise a company name using regex patterns (fallback method).

    Args:
        name: The full company name
        verbose: Whether to print the casualization process

    Returns:
        The casualised company name
    """
    if not name or not isinstance(name, str):
        return name

    original = name.strip()
    if not original:
        return original

    casualised = original

    # Apply suffix removal patterns
    for pattern in SUFFIXES:
        new_name = re.sub(pattern, '', casualised, flags=re.IGNORECASE)
        if new_name != casualised:
            if verbose:
                print(f"  Applied pattern '{pattern}': '{casualised}' → '{new_name}'")
            casualised = new_name.strip()

    # Safety check: if we removed everything or left < 2 chars, use original
    if len(casualised) < 2:
        if verbose:
            print(f"  WARNING: Casualisation too aggressive, keeping original")
        return original

    # Remove trailing punctuation that might be left over
    casualised = re.sub(r'[,\s]+$', '', casualised)

    if verbose and casualised != original:
        print(f"  Final: '{original}' → '{casualised}'")

    return casualised


def casualise_company_names_batch_openai(names: List[str], verbose: bool = False) -> List[str]:
    """
    Casualise a batch of company names using OpenAI API.

    Args:
        names: List of company names to casualise
        verbose: Whether to print progress

    Returns:
        List of casualised company names
    """
    if not OPENAI_AVAILABLE:
        if verbose:
            print("OpenAI not available, using regex fallback for all names")
        return [casualise_company_name_regex(name, verbose) for name in names]

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        if verbose:
            print("OPENAI_API_KEY not found in .env, using regex fallback")
        return [casualise_company_name_regex(name, verbose) for name in names]

    client = OpenAI(api_key=api_key)

    # Process in batches of 50 to avoid token limits
    batch_size = 50
    all_results = []

    for i in range(0, len(names), batch_size):
        batch = names[i:i + batch_size]
        batch_indices = list(range(len(batch)))

        if verbose:
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} names)...")

        # Create numbered list for the prompt
        numbered_names = "\n".join([f"{idx + 1}. {name}" for idx, name in enumerate(batch)])

        prompt = f"""You are a company name casualizer. Your job is to shorten formal company names to their casual, conversational form.

Rules:
- Remove legal entity suffixes: Inc., LLC, Ltd., Corporation, etc.
- Remove business descriptors: Agency, Professional Services, Solutions, Technologies, Group, Partners, etc.
- Keep the core brand name intact
- Preserve acronyms and multi-word brand names
- If the name is already casual or removing suffixes would leave < 2 characters, keep it as-is

Examples:
"XYZ Agency" → "XYZ"
"Love AMS Professional Services" → "Love AMS"
"Love Mayo Inc." → "Love Mayo"
"Smith & Co. LLC" → "Smith & Co."
"TechCorp Solutions" → "TechCorp"

Casualise these company names. Return ONLY the casualised names, one per line, in the same order:

{numbered_names}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that casualizes company names. Return only the casualised names, one per line, without numbers or extra text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content.strip()
            casualised_names = [line.strip() for line in result_text.split('\n') if line.strip()]

            # Remove any numbering that might have been included
            casualised_names = [re.sub(r'^\d+\.\s*', '', name) for name in casualised_names]

            # Validate we got the right number of results
            if len(casualised_names) != len(batch):
                if verbose:
                    print(f"  WARNING: Got {len(casualised_names)} results for {len(batch)} names, using regex fallback for this batch")
                casualised_names = [casualise_company_name_regex(name, verbose) for name in batch]

            all_results.extend(casualised_names)

            if verbose:
                for orig, casual in zip(batch, casualised_names):
                    if orig != casual:
                        print(f"  '{orig}' → '{casual}'")

            # Rate limiting: small delay between batches
            if i + batch_size < len(names):
                time.sleep(0.5)

        except Exception as e:
            if verbose:
                print(f"  ERROR calling OpenAI API: {e}")
                print(f"  Falling back to regex for this batch")
            # Fallback to regex for this batch
            casualised_batch = [casualise_company_name_regex(name, verbose) for name in batch]
            all_results.extend(casualised_batch)

    return all_results


def casualise_company_name(name: str, verbose: bool = False, use_openai: bool = True) -> str:
    """
    Casualise a single company name.

    Args:
        name: The company name
        verbose: Whether to print details
        use_openai: Whether to use OpenAI API (default: True)

    Returns:
        The casualised company name
    """
    if use_openai and OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
        results = casualise_company_names_batch_openai([name], verbose)
        return results[0] if results else name
    else:
        return casualise_company_name_regex(name, verbose)


def load_from_google_sheets(spreadsheet_url: str, sheet_name: Optional[str] = None) -> tuple:
    """Load data from Google Sheets and return (spreadsheet_id, sheet_id, headers, rows)"""
    if not GOOGLE_AVAILABLE:
        print("ERROR: Google API libraries not installed.")
        sys.exit(3)

    # Extract spreadsheet ID and gid from URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    if not match:
        print(f"ERROR: Invalid Google Sheets URL: {spreadsheet_url}")
        sys.exit(3)

    spreadsheet_id = match.group(1)

    # Extract gid (sheet ID) if present
    gid_match = re.search(r'[#&]gid=(\d+)', spreadsheet_url)
    sheet_id = int(gid_match.group(1)) if gid_match else None

    # Authenticate
    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)

    # Get sheet metadata to find sheet name from gid
    if sheet_id is not None and not sheet_name:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['sheetId'] == sheet_id:
                sheet_name = sheet['properties']['title']
                break

    # Get sheet data
    range_name = f"{sheet_name}!A:ZZ" if sheet_name else 'A:ZZ'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    rows = result.get('values', [])
    if not rows:
        print("WARNING: No data found in spreadsheet")
        return spreadsheet_id, sheet_id, [], []

    headers = rows[0]
    data_rows = rows[1:]

    return spreadsheet_id, sheet_id, sheet_name, headers, data_rows


def update_google_sheet(spreadsheet_id: str, sheet_name: str, headers: List[str], rows: List[List[str]]):
    """Update Google Sheet with casualised company names"""
    creds = authenticate_google()
    service = build('sheets', 'v4', credentials=creds)

    # Prepare data with headers
    all_rows = [headers] + rows

    # Update the sheet
    range_name = f"{sheet_name}!A1"
    body = {'values': all_rows}

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    print(f"\n✓ Updated sheet '{sheet_name}' with {len(rows)} rows")


def find_company_name_column(headers: List[str]) -> Optional[int]:
    """Find the company name column index"""
    company_fields = ['companyName', 'company_name', 'Company Name', 'name', 'Name',
                      'business_name', 'Business Name', 'company', 'Company']

    for idx, header in enumerate(headers):
        if header in company_fields:
            return idx

    return None


def main():
    parser = argparse.ArgumentParser(description='Casualise company names by removing common suffixes')

    # Input options
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--source-url', help='Google Sheets URL')
    input_group.add_argument('--source-file', help='JSON file path')
    input_group.add_argument('--name', help='Single company name to casualise')

    # Column options for Google Sheets
    parser.add_argument('--column', help='Column name containing company names (default: auto-detect)')
    parser.add_argument('--output-column', help='Column name for casualised names (default: "Casual Name")')
    parser.add_argument('--sheet-name', help='Sheet name (optional, will use gid from URL if present)')

    # Output options for files
    parser.add_argument('--output', help='Output file path (for JSON input)')

    # General options
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed processing info')

    args = parser.parse_args()

    # Single name mode
    if args.name:
        result = casualise_company_name(args.name, verbose=args.verbose)
        print(result)
        return

    # Google Sheets mode
    if args.source_url:
        print(f"Loading data from Google Sheets...")
        spreadsheet_id, sheet_id, sheet_name, headers, rows = load_from_google_sheets(
            args.source_url,
            args.sheet_name
        )

        print(f"Loaded {len(rows)} rows from sheet '{sheet_name}'")

        # Find company name column
        if args.column:
            try:
                company_col_idx = headers.index(args.column)
            except ValueError:
                print(f"ERROR: Column '{args.column}' not found in sheet")
                print(f"Available columns: {', '.join(headers)}")
                sys.exit(1)
        else:
            company_col_idx = find_company_name_column(headers)
            if company_col_idx is None:
                print(f"ERROR: Could not auto-detect company name column")
                print(f"Available columns: {', '.join(headers)}")
                print(f"Please specify --column")
                sys.exit(1)

        company_col_name = headers[company_col_idx]
        print(f"Using column: '{company_col_name}'")

        # Add or find output column
        output_col_name = args.output_column or 'Casual Name'
        if output_col_name not in headers:
            headers.append(output_col_name)
            output_col_idx = len(headers) - 1
            print(f"Creating new column: '{output_col_name}'")
        else:
            output_col_idx = headers.index(output_col_name)
            print(f"Updating existing column: '{output_col_name}'")

        # Collect all company names for batch processing
        company_names = []
        name_indices = []  # Track which rows have names
        for idx, row in enumerate(rows):
            # Pad row if needed
            while len(row) <= max(company_col_idx, output_col_idx):
                row.append('')

            original_name = row[company_col_idx] if company_col_idx < len(row) else ''
            if original_name:
                company_names.append(original_name)
                name_indices.append(idx)

        print(f"\nProcessing {len(company_names)} company names using OpenAI API...")

        # Batch process all names
        casualised_names = casualise_company_names_batch_openai(company_names, verbose=args.verbose)

        # Update rows with casualised names
        for name_idx, row_idx in enumerate(name_indices):
            rows[row_idx][output_col_idx] = casualised_names[name_idx]

        print(f"✓ Casualised {len(company_names)} company names")

        # Update sheet
        print(f"Updating Google Sheet...")
        update_google_sheet(spreadsheet_id, sheet_name, headers, rows)

        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
        print(f"\n✓ Done! View updated sheet: {sheet_url}")

    # JSON file mode
    elif args.source_file:
        if not args.output:
            print("ERROR: --output required when using --source-file")
            sys.exit(1)

        print(f"Loading data from {args.source_file}...")
        with open(args.source_file, 'r') as f:
            leads = json.load(f)

        print(f"Processing {len(leads)} leads...")

        # Find company name field
        company_field = None
        for field in ['companyName', 'company_name', 'Company Name', 'name', 'Name']:
            if leads and field in leads[0]:
                company_field = field
                break

        if not company_field:
            print("ERROR: Could not find company name field")
            sys.exit(1)

        print(f"Using field: '{company_field}'")

        # Process leads
        for lead in leads:
            if company_field in lead:
                original = lead[company_field]
                casualised = casualise_company_name(original, verbose=args.verbose)
                lead['casual_name'] = casualised

        # Save output
        with open(args.output, 'w') as f:
            json.dump(leads, f, indent=2)

        print(f"\n✓ Saved casualised leads to {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

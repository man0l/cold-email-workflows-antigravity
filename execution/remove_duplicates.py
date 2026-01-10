#!/usr/bin/env python3
"""
Remove Duplicates Between Spreadsheets Script

Removes duplicate entries from a destination spreadsheet based on matches
found in a source spreadsheet.

Usage:
    python remove_duplicates.py --source-url <URL> --dest-url <URL> --output-sheet "Deduplicated"
    python remove_duplicates.py --source-url <URL> --source-sheet "Sheet1" --dest-url <URL> --dest-sheet "Sheet2" --output-sheet "Clean"
"""

import argparse
import os
import sys
from typing import List, Dict, Set, Any, Optional

# Import Google Sheets utilities
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from clean_leads import load_from_google_sheets, authenticate_google
    from export_to_sheets import export_data_to_sheets
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


def normalize_field_value(value: Any) -> str:
    """Normalize a field value for comparison (lowercase, strip whitespace)."""
    if value is None:
        return ""
    return str(value).lower().strip()


def extract_match_keys(data: List[Dict[str, Any]], match_fields: List[str]) -> Dict[str, Set[str]]:
    """
    Extract sets of unique values from the specified match fields.

    Args:
        data: List of dictionaries (leads/entries)
        match_fields: List of field names to extract values from (e.g., ['email', 'phone'])

    Returns:
        Dict mapping field name to set of normalized values
    """
    all_keys = {}

    for match_field in match_fields:
        keys = set()

        # Try multiple variations of the field name
        field_variations = [
            match_field,
            match_field.lower(),
            match_field.upper(),
            match_field.title(),
            match_field.replace('_', ''),
            match_field.replace('_', ' '),
            match_field.replace(' ', '_'),
        ]

        for entry in data:
            for field_var in field_variations:
                if field_var in entry and entry[field_var]:
                    normalized = normalize_field_value(entry[field_var])
                    if normalized:
                        keys.add(normalized)
                    break

        all_keys[match_field] = keys

    return all_keys


def find_match_field_name(data: List[Dict[str, Any]], match_field: str) -> Optional[str]:
    """
    Find the actual field name in the data that matches the requested field.
    Returns the first match found, or None if not found.

    Smart matching handles common field name variations:
    - "Company Name" matches "title", "companyName", "company_name"
    - "Company Phone" matches "phone", "companyPhone", "company_phone"
    - "Company Website" matches "website", "companyWebsite", "company_website", "url"
    """
    if not data:
        return None

    sample = data[0]

    # Try exact match first
    if match_field in sample:
        return match_field

    # Normalize the match field for comparison
    match_normalized = match_field.lower().replace('_', '').replace(' ', '')

    # Smart field mapping for common variations
    field_mappings = {
        'companyname': ['title', 'name', 'companyName', 'company_name', 'Company Name'],
        'title': ['companyname', 'company_name', 'Company Name', 'name'],
        'companyphone': ['phone', 'phoneUnformatted', 'companyPhone', 'company_phone', 'Company Phone'],
        'phone': ['companyphone', 'phoneUnformatted', 'company_phone', 'Company Phone'],
        'companywebsite': ['website', 'url', 'companyWebsite', 'company_website', 'Company Website'],
        'website': ['companywebsite', 'url', 'company_website', 'Company Website', 'companyDomain'],
        'url': ['website', 'companywebsite', 'company_website', 'Company Website'],
    }

    # Check smart mappings
    if match_normalized in field_mappings:
        for candidate in field_mappings[match_normalized]:
            if candidate in sample:
                return candidate

    # Try standard variations
    field_variations = [
        match_field.lower(),
        match_field.upper(),
        match_field.title(),
        match_field.replace('_', ''),
        match_field.replace('_', ' '),
        match_field.replace(' ', '_'),
    ]

    for field_var in field_variations:
        if field_var in sample:
            return field_var

    return None


def remove_duplicates_logic(
    source_data: List[Dict[str, Any]],
    dest_data: List[Dict[str, Any]],
    match_fields: List[str]
) -> tuple[List[Dict[str, Any]], int, Dict[str, int], Dict[str, Set[str]]]:
    """
    Remove entries from dest_data that have matching values in source_data on ANY of the match fields.

    Args:
        source_data: Reference list (e.g., already contacted leads)
        dest_data: List to deduplicate
        match_fields: List of fields to match on (e.g., ['email', 'phone', 'website'])

    Returns:
        (deduplicated_data, total_duplicate_count, duplicates_by_field, match_keys_from_source)
    """
    # Extract match keys from source for all fields
    source_keys = extract_match_keys(source_data, match_fields)

    # Find the actual field names in dest data
    dest_field_mapping = {}
    for match_field in match_fields:
        dest_field_name = find_match_field_name(dest_data, match_field)
        if dest_field_name:
            dest_field_mapping[match_field] = dest_field_name
        else:
            print(f"⚠️  Warning: Field '{match_field}' not found in destination data - skipping this field")

    if not dest_field_mapping:
        print(f"❌ Error: None of the match fields found in destination data.")
        print(f"Available fields: {', '.join(dest_data[0].keys()) if dest_data else 'none'}")
        return dest_data, 0, {}, source_keys

    print(f"✓ Matching on {len(dest_field_mapping)} field(s): {', '.join(dest_field_mapping.keys())}")

    # Filter dest_data
    deduplicated = []
    total_duplicates = 0
    duplicates_by_field = {field: 0 for field in match_fields}

    for entry in dest_data:
        is_duplicate = False
        matched_field = None

        # Check each match field
        for match_field, dest_field_name in dest_field_mapping.items():
            value = entry.get(dest_field_name)
            normalized = normalize_field_value(value)

            # Skip if no value
            if not normalized:
                continue

            # Check if value exists in source for this field
            if normalized in source_keys.get(match_field, set()):
                is_duplicate = True
                matched_field = match_field
                duplicates_by_field[match_field] += 1
                break

        if is_duplicate:
            total_duplicates += 1
            continue

        deduplicated.append(entry)

    return deduplicated, total_duplicates, duplicates_by_field, source_keys


def main():
    parser = argparse.ArgumentParser(
        description='Remove duplicates from destination spreadsheet based on source spreadsheet'
    )

    # Source spreadsheet
    parser.add_argument('--source-url', required=True, help='Source Google Sheets URL')
    parser.add_argument('--source-sheet', help='Source sheet name (default: last sheet)')

    # Destination spreadsheet
    parser.add_argument('--dest-url', required=True, help='Destination Google Sheets URL')
    parser.add_argument('--dest-sheet', help='Destination sheet name (default: last sheet)')

    # Match configuration
    parser.add_argument(
        '--match-fields',
        default='email',
        help='Comma-separated list of fields to match on (default: email). Examples: email,phone,website or "Company Name,Company Phone,Company Website"'
    )

    # Output configuration
    output_group = parser.add_mutually_exclusive_group(required=False)
    output_group.add_argument('--output-sheet', help='Output sheet name (adds to dest spreadsheet)')
    output_group.add_argument('--output-spreadsheet', help='Create new spreadsheet with this name')

    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if not GOOGLE_AVAILABLE:
        print("ERROR: Google Sheets support not available.")
        print("Make sure clean_leads.py and export_to_sheets.py are available.")
        sys.exit(1)

    # Default output sheet name if not specified
    if not args.output_sheet and not args.output_spreadsheet:
        args.output_sheet = "Deduplicated Leads"

    print("=" * 60)
    print("REMOVE DUPLICATES")
    print("=" * 60)

    # Load source spreadsheet
    print(f"\n📊 Loading source spreadsheet...")
    print(f"   URL: {args.source_url}")
    if args.source_sheet:
        print(f"   Sheet: {args.source_sheet}")
    else:
        print(f"   Sheet: (last sheet)")

    source_data = load_from_google_sheets(args.source_url, sheet_name=args.source_sheet)
    print(f"   ✓ Loaded {len(source_data)} entries")

    # Load destination spreadsheet
    print(f"\n📊 Loading destination spreadsheet...")
    print(f"   URL: {args.dest_url}")
    if args.dest_sheet:
        print(f"   Sheet: {args.dest_sheet}")
    else:
        print(f"   Sheet: (last sheet)")

    dest_data = load_from_google_sheets(args.dest_url, sheet_name=args.dest_sheet)
    print(f"   ✓ Loaded {len(dest_data)} entries")

    if not dest_data:
        print("\n⚠️  No data in destination spreadsheet. Nothing to deduplicate.")
        sys.exit(0)

    # Show available fields if verbose
    if args.verbose and source_data and dest_data:
        print(f"\nSource fields: {', '.join(source_data[0].keys())}")
        print(f"Destination fields: {', '.join(dest_data[0].keys())}")

    # Parse match fields
    match_fields = [f.strip() for f in args.match_fields.split(',')]
    print(f"\n🔍 Requested match fields: {', '.join(match_fields)}")

    # Remove duplicates
    deduplicated, duplicate_count, duplicates_by_field, source_keys = remove_duplicates_logic(
        source_data,
        dest_data,
        match_fields
    )

    # Statistics
    print("\n" + "=" * 60)
    print("DEDUPLICATION SUMMARY")
    print("=" * 60)
    print(f"Source entries:        {len(source_data):,}")
    for field, keys in source_keys.items():
        if keys:
            print(f"  - {field}: {len(keys):,} unique values")
    print(f"Destination entries:   {len(dest_data):,}")
    print(f"Duplicates found:      {duplicate_count:,} ({duplicate_count/len(dest_data)*100:.1f}%)")
    for field, count in duplicates_by_field.items():
        if count > 0:
            print(f"  - by {field}: {count:,}")
    print(f"Unique entries:        {len(deduplicated):,} ({len(deduplicated)/len(dest_data)*100:.1f}%)")
    print("=" * 60)

    if duplicate_count == 0:
        print("\n✓ No duplicates found! Your destination list is already unique.")

    # Export results
    if len(deduplicated) == 0:
        print("\n⚠️  All entries were duplicates. No data to export.")
        sys.exit(0)

    print(f"\n📤 Exporting results...")

    if args.output_sheet:
        # Add to destination spreadsheet
        dest_spreadsheet_id = args.dest_url.split('/d/')[1].split('/')[0]
        print(f"   Creating new sheet: '{args.output_sheet}'")
        export_data_to_sheets(
            deduplicated,
            args.output_sheet,
            target_spreadsheet_id=dest_spreadsheet_id
        )
    else:
        # Create new spreadsheet
        print(f"   Creating new spreadsheet: '{args.output_spreadsheet}'")
        export_data_to_sheets(
            deduplicated,
            args.output_spreadsheet
        )

    print("\n✓ Deduplication complete!")


if __name__ == '__main__':
    main()

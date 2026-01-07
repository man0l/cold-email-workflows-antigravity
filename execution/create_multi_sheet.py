#!/usr/bin/env python3
"""
Create a single spreadsheet with multiple worksheets from JSON files.
"""

import json
import argparse
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    return Credentials.from_service_account_file('credentials.json', scopes=SCOPES)

def create_multi_sheet_spreadsheet(segments, spreadsheet_name, folder_id):
    """
    Create a spreadsheet with multiple worksheets.

    Args:
        segments: List of tuples (sheet_name, json_file_path)
        spreadsheet_name: Name of the spreadsheet
        folder_id: Google Drive folder ID
    """
    creds = get_credentials()
    gc = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)

    # Create new spreadsheet
    print(f"Creating spreadsheet: {spreadsheet_name}")
    spreadsheet = gc.create(spreadsheet_name)
    spreadsheet_id = spreadsheet.id

    # Move to folder
    print(f"Moving to folder: {folder_id}")
    drive_service.files().update(
        fileId=spreadsheet_id,
        addParents=folder_id,
        removeParents=','.join([p for p in spreadsheet.properties.get('parents', [])])
    ).execute()

    # Get the default sheet
    default_sheet = spreadsheet.sheet1

    for idx, (sheet_name, json_file) in enumerate(segments):
        print(f"\nProcessing {sheet_name}...")

        # Load data
        with open(json_file, 'r') as f:
            data = json.load(f)

        print(f"  Loaded {len(data)} leads")

        # Prepare data
        if not data:
            print(f"  No data in {json_file}, skipping")
            continue

        # Get headers
        headers = list(data[0].keys())
        rows = [headers]
        for item in data:
            row = [str(item.get(key, '')) for key in headers]
            rows.append(row)

        # Create or use worksheet
        if idx == 0:
            # Rename the default sheet
            worksheet = default_sheet
            worksheet.update_title(sheet_name)
        else:
            # Add new worksheet
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(rows)+10, cols=len(headers))

        print(f"  Writing {len(rows)} rows to worksheet...")
        worksheet.update(rows, value_input_option='RAW')

        # Format header row (bold)
        worksheet.format('1:1', {'textFormat': {'bold': True}})

        print(f"  ✓ {sheet_name} completed")

    print(f"\n✅ Spreadsheet created successfully!")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    return spreadsheet_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create multi-sheet spreadsheet')
    parser.add_argument('--segments', nargs='+', required=True, help='List of sheet_name:json_file pairs')
    parser.add_argument('--name', required=True, help='Spreadsheet name')
    parser.add_argument('--folder-id', required=True, help='Google Drive folder ID')

    args = parser.parse_args()

    # Parse segments
    segments = []
    for seg in args.segments:
        sheet_name, json_file = seg.split(':', 1)
        segments.append((sheet_name, json_file))

    create_multi_sheet_spreadsheet(segments, args.name, args.folder_id)

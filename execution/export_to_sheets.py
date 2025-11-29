import os
import json
import argparse
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    """
    Tries to load credentials from credentials.json.
    """
    creds_path = "credentials.json"
    if os.path.exists(creds_path):
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        raise FileNotFoundError(
            "credentials.json not found. Creating a new Sheet requires a Service Account.\n"
            "Please place your 'credentials.json' file in the project root."
        )

def get_or_create_folder(drive_service, folder_name, folder_id=None):
    """
    Checks if a folder exists, creates it if not.
    If folder_id is provided, uses it directly.
    """
    if folder_id:
        # Use the provided folder ID directly
        print(f"Using provided folder ID: {folder_id}")
        return folder_id
    
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = drive_service.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
    items = results.get("files", [])

    if not items:
        print(f"Folder '{folder_name}' not found. Creating...")
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = drive_service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")
    else:
        folder_id = items[0]["id"]
        print(f"Found folder '{folder_name}' (ID: {folder_id})")
        return folder_id

def export_data_to_sheets(data, sheet_name, folder_id=None, target_spreadsheet_id=None):
    """
    Exports a list of dictionaries to a Google Sheet.
    If target_spreadsheet_id is provided, adds/updates a tab in that spreadsheet.
    Otherwise, creates a new spreadsheet.
    """
    if not data:
        print("No data to export.")
        return

    creds = get_credentials()
    gc = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)

    # 1. Get or Create "Lead Gen" folder (only if creating new sheet)
    if not target_spreadsheet_id:
        # Use provided folder_id or default to "Lead Gen" folder
        if not folder_id:
            folder_id = os.getenv("LEAD_GEN_FOLDER_ID", "0ADWgx-M8Z5r-Uk9PVA")
        folder_id = get_or_create_folder(drive_service, "Lead Gen", folder_id=folder_id)

    # 2. Prepare Data
    # Flatten data if necessary (simple flattening for now)
    # Assuming data is a list of dicts. We'll take keys from the first item as headers.
    headers = list(data[0].keys())
    rows = [headers]
    for item in data:
        row = [str(item.get(k, "")) for k in headers]
        rows.append(row)

    # 3. Create or Open Sheet
    if target_spreadsheet_id:
        # Open existing spreadsheet
        try:
            sh = gc.open_by_key(target_spreadsheet_id)
            print(f"Opened target spreadsheet (ID: {target_spreadsheet_id})")
            spreadsheet_id = target_spreadsheet_id
        except Exception as e:
            print(f"Error opening spreadsheet {target_spreadsheet_id}: {e}")
            return None
    else:
        # Check if sheet exists in the folder
        query = f"mimeType='application/vnd.google-apps.spreadsheet' and name='{sheet_name}' and '{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(
            q=query, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        items = results.get("files", [])

        if items:
            spreadsheet_id = items[0]["id"]
            sh = gc.open_by_key(spreadsheet_id)
            print(f"Opened existing sheet '{sheet_name}'")
        else:
            # Create spreadsheet using Drive API with parent folder set
            file_metadata = {
                'name': sheet_name,
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [folder_id]
            }
            file = drive_service.files().create(
                body=file_metadata, 
                fields='id',
                supportsAllDrives=True
            ).execute()
            spreadsheet_id = file.get('id')
            sh = gc.open_by_key(spreadsheet_id)
            print(f"Created new sheet '{sheet_name}' in folder")

    # 4. Get or Create Worksheet
    try:
        worksheet = sh.worksheet(sheet_name)
        print(f"Updating existing worksheet '{sheet_name}'")
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=len(rows)+100, cols=len(headers))
        print(f"Created new worksheet '{sheet_name}'")

    # Clear and update
    worksheet.clear()
    worksheet.update(rows)
    
    # Output URL for easy access
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={worksheet.id}"
    print(f"Exported {len(data)} leads to '{sheet_name}'")
    print(f"Sheet URL: {sheet_url}")
    return sheet_url

def export_to_sheets(input_file, sheet_name, folder_id=None):
    """
    Wrapper to load data from JSON file and export to sheets.
    """
    # Load Data
    with open(input_file, "r") as f:
        data = json.load(f)
    
    export_data_to_sheets(data, sheet_name, folder_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export leads to Google Sheets")
    parser.add_argument("input_file", help="Path to JSON file containing leads")
    parser.add_argument("--sheet-name", required=True, help="Name of the Google Sheet")
    parser.add_argument("--folder-id", help="Google Drive folder ID (defaults to Lead Gen folder)")

    args = parser.parse_args()

    try:
        export_to_sheets(args.input_file, args.sheet_name, folder_id=args.folder_id)
    except Exception as e:
        print(f"Error: {e}")

#!/usr/bin/env python3
"""
Clean Instantly Leads Script

Filters leads from a CSV or Google Sheet by removing those that already exist
in a specific Instantly.ai campaign.

Usage:
    python clean_instantly_leads.py --source-file leads.csv --campaign-id <ID> --output cleaned.csv
    python clean_instantly_leads.py --source-url <URL> --campaign-id <ID> --output-sheet "Cleaned"
"""

import argparse
import csv
import json
import os
import sys
import requests
from typing import List, Dict, Set, Any, Optional
from dotenv import load_dotenv

# Reuse Google Sheets logic if available
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from clean_leads import load_from_google_sheets, load_from_json, authenticate_google
    from export_to_sheets import export_data_to_sheets
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

load_dotenv()

INSTANTLY_API_URL = "https://api.instantly.ai/api/v2"

def get_instantly_campaign_leads(campaign_id: str, api_key: str) -> Set[str]:
    """
    Fetch all leads from an Instantly campaign and return a set of their emails.
    Uses Instantly API V2 POST /leads/list endpoint.
    """
    print(f"Fetching leads from Instantly campaign: {campaign_id}...")
    
    emails = set()
    limit = 100  # Maximum allowed by API
    starting_after = None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    while True:
        try:
            # API V2: POST /leads/list
            url = f"{INSTANTLY_API_URL}/leads/list"
            payload = {
                "campaign": campaign_id,
                "limit": limit
            }
            
            if starting_after:
                payload["starting_after"] = starting_after
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
                
            data = response.json()
            
            leads = data.get('items', [])
            
            if not leads:
                break
                
            for lead in leads:
                email = lead.get('email')
                if email:
                    emails.add(str(email).lower().strip())
            
            # Check if there are more results
            next_cursor = data.get('next_starting_after')
            if not next_cursor:
                break
                
            starting_after = next_cursor
            print(f"Fetched {len(emails)} leads so far...")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching leads from Instantly: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response Text: {e.response.text}")
                print(f"Request URL: {e.response.url}")
                print(f"Request Body: {payload}")
            sys.exit(1)
            
    print(f"Total existing leads in campaign: {len(emails)}")
    return emails

def load_leads_csv(file_path: str) -> List[Dict[str, Any]]:
    """Load leads from a CSV file."""
    leads = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    return leads

def save_leads_csv(leads: List[Dict[str, Any]], file_path: str):
    """Save leads to a CSV file."""
    if not leads:
        print("No leads to save.")
        return
        
    keys = leads[0].keys()
    try:
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(leads)
        print(f"Saved {len(leads)} leads to {file_path}")
    except Exception as e:
        print(f"Error saving CSV file: {e}")
        sys.exit(1)

def clean_leads_logic(leads: List[Dict[str, Any]], existing_emails: Set[str]) -> tuple[List[Dict[str, Any]], int]:
    """
    Filter out leads that are in the existing emails set.
    Returns (cleaned_leads, duplicate_count)
    """
    cleaned_leads = []
    duplicates = 0
    
    for lead in leads:
        # Find email field
        email = None
        for field in ['email', 'Email', 'emailAddress', 'contact_email']:
            if field in lead and lead[field]:
                email = str(lead[field]).lower().strip()
                break
        
        if email and email in existing_emails:
            duplicates += 1
            continue
            
        cleaned_leads.append(lead)
        
    return cleaned_leads, duplicates


def main():
    parser = argparse.ArgumentParser(description='Clean leads against Instantly campaign')
    
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source-file', help='Path to CSV or JSON file')
    source_group.add_argument('--source-url', help='Google Sheets URL')
    
    parser.add_argument('--campaign-id', required=True, help='Instantly Campaign ID')
    
    output_group = parser.add_mutually_exclusive_group(required=False)
    output_group.add_argument('--output', help='Output file path (CSV/JSON)')
    output_group.add_argument('--output-sheet', help='Output Google Sheet name')
    
    args = parser.parse_args()
    
    api_key = os.getenv('INSTANTLY_API_KEY')
    if not api_key:
        print("ERROR: INSTANTLY_API_KEY not found in environment variables.")
        sys.exit(1)
        
    # Load Source Leads
    print("Loading source leads...")
    leads = []
    if args.source_file:
        if args.source_file.endswith('.json'):
            leads = load_from_json(args.source_file)
        elif args.source_file.endswith('.csv'):
            leads = load_leads_csv(args.source_file)
        else:
            print("Unsupported file format. Use .csv or .json")
            sys.exit(1)
    elif args.source_url:
        if not GOOGLE_AVAILABLE:
            print("Google Sheets support not available.")
            sys.exit(1)
        leads = load_from_google_sheets(args.source_url)
        
    print(f"Loaded {len(leads)} source leads.")
    
    if not leads:
        print("No leads found in source.")
        sys.exit(0)

    # Fetch Campaign Leads
    existing_emails = get_instantly_campaign_leads(args.campaign_id, api_key)
    
    # Clean Leads
    print("Cleaning leads...")
    cleaned_leads, duplicates = clean_leads_logic(leads, existing_emails)
        
    print(f"Removed {duplicates} duplicates.")
    print(f"Remaining leads: {len(cleaned_leads)}")
    
    # Save Output
    if args.output_sheet:
        if not GOOGLE_AVAILABLE:
            print("Google Sheets support not available.")
            sys.exit(1)
            
        # Determine target spreadsheet ID
        target_spreadsheet_id = None
        if args.source_url:
             try:
                target_spreadsheet_id = args.source_url.split('/d/')[1].split('/')[0]
             except:
                 pass
                 
        export_data_to_sheets(cleaned_leads, args.output_sheet, target_spreadsheet_id=target_spreadsheet_id)
        
    else:
        output_path = args.output or '.tmp/cleaned_leads.csv'
        if output_path.endswith('.json'):
            with open(output_path, 'w') as f:
                json.dump(cleaned_leads, f, indent=2)
            print(f"Saved to {output_path}")
        else:
            save_leads_csv(cleaned_leads, output_path)

if __name__ == '__main__':
    main()

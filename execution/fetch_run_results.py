import os
import json
import requests
import argparse
from dotenv import load_dotenv

load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
ACTOR_ID = "code_crafter~leads-finder"

def fetch_run_results(run_id, output_file):
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY not found in .env")

    print(f"Fetching details for run ID: {run_id}")
    
    # Get Run Details (to get defaultDatasetId and Input)
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_KEY}"
    run_response = requests.get(run_url)
    run_response.raise_for_status()
    run_data = run_response.json()["data"]
    
    default_dataset_id = run_data["defaultDatasetId"]
    status = run_data["status"]
    
    # Get Input (to see what parameters were used)
    # The input is often stored in a key-value store, but the run object might have a link to it.
    # Actually, for recent runs, we might need to fetch the input from the default key-value store.
    # The run object has "defaultKeyValueStoreId".
    default_kv_store_id = run_data["defaultKeyValueStoreId"]
    input_url = f"https://api.apify.com/v2/key-value-stores/{default_kv_store_id}/records/INPUT?token={APIFY_API_KEY}"
    input_response = requests.get(input_url)
    
    run_input = {}
    if input_response.ok:
        run_input = input_response.json()
    else:
        print(f"Warning: Could not fetch INPUT from key-value store. Status: {input_response.status_code}")

    print(f"Run Status: {status}")
    print(f"Input Parameters: {json.dumps(run_input, indent=2)}")
    
    if status != "SUCCEEDED":
        print(f"Warning: Run status is {status}. Results might be incomplete.")

    # Fetch Results from Dataset
    print(f"Fetching results from dataset: {default_dataset_id}")
    dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_API_KEY}"
    dataset_response = requests.get(dataset_url)
    dataset_response.raise_for_status()
    items = dataset_response.json()

    # Save to file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(items, f, indent=2)
    
    print(f"Saved {len(items)} items to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch results for an Apify run")
    parser.add_argument("run_id", help="Apify Run ID")
    parser.add_argument("--output", default=".tmp/recovered_leads.json", help="Output JSON file path")
    
    args = parser.parse_args()
    
    fetch_run_results(args.run_id, args.output)

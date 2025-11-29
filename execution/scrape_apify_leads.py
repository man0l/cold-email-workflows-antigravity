import os
import time
import json
import argparse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
ACTOR_ID = "code_crafter~leads-finder"

def scrape_leads(job_titles, contact_location, keywords, not_keywords, industries, seniority, size, fetch_count, output_file):
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY not found in .env")

    # Default seniority levels for decision-makers (if not specified)
    if not seniority:
        seniority = ["owner", "founder", "c_suite", "partner", "director", "vp"]
        print("Using default seniority levels (decision-makers): owner, founder, c_suite, partner, director, vp")

    # Construct input
    actor_input = {
        "fetch_count": fetch_count,
        "job_titles": job_titles,
        "contact_location": contact_location,
        "company_keywords": keywords,
        "company_not_keywords": not_keywords,
        "company_industry": industries,
        "seniority_level": seniority,
        "size": size,
        "email_status": ["validated"] # Default to validated for quality
    }
    
    # Remove empty lists to avoid cluttering input
    actor_input = {k: v for k, v in actor_input.items() if v}

    print(f"Starting actor {ACTOR_ID} with input: {json.dumps(actor_input, indent=2)}")

    # Start Run
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_KEY}"
    response = requests.post(url, json=actor_input)
    
    if not response.ok:
        print(f"Error response: {response.status_code}")
        print(f"Response body: {response.text}")
    
    response.raise_for_status()
    run_data = response.json()["data"]
    run_id = run_data["id"]
    default_dataset_id = run_data["defaultDatasetId"]
    
    print(f"Run started. ID: {run_id}")

    # Poll for completion
    while True:
        status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_KEY}"
        status_response = requests.get(status_url)
        status_response.raise_for_status()
        status_data = status_response.json()["data"]
        status = status_data["status"]
        
        print(f"Status: {status}")
        
        if status == "SUCCEEDED":
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            raise RuntimeError(f"Run failed with status: {status}")
        
        time.sleep(5)

    # Fetch Results
    print("Run succeeded. Fetching results...")
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
    parser = argparse.ArgumentParser(description="Scrape leads using Apify code_crafter/leads-finder")
    parser.add_argument("--job-titles", help="Comma-separated list of job titles")
    parser.add_argument("--locations", help="Comma-separated list of contact locations")
    parser.add_argument("--keywords", help="Comma-separated list of company keywords")
    parser.add_argument("--not-keywords", help="Comma-separated list of company keywords to exclude")
    parser.add_argument("--industries", help="Comma-separated list of company industries")
    parser.add_argument("--seniority", help="Comma-separated list of seniority levels")
    parser.add_argument("--size", help="Comma-separated list of company sizes")
    parser.add_argument("--fetch-count", type=int, default=50, help="Number of leads to fetch")
    parser.add_argument("--output", default=".tmp/leads.json", help="Output JSON file path")

    args = parser.parse_args()

    job_titles_list = [x.strip() for x in args.job_titles.split(",")] if args.job_titles else []
    locations_list = [x.strip() for x in args.locations.split(",")] if args.locations else []
    keywords_list = [x.strip() for x in args.keywords.split(",")] if args.keywords else []
    not_keywords_list = [x.strip() for x in args.not_keywords.split(",")] if args.not_keywords else []
    industries_list = [x.strip() for x in args.industries.split(",")] if args.industries else []
    seniority_list = [x.strip() for x in args.seniority.split(",")] if args.seniority else []
    size_list = [x.strip() for x in args.size.split(",")] if args.size else []

    scrape_leads(
        job_titles=job_titles_list,
        contact_location=locations_list,
        keywords=keywords_list,
        not_keywords=not_keywords_list,
        industries=industries_list,
        seniority=seniority_list,
        size=size_list,
        fetch_count=args.fetch_count,
        output_file=args.output
    )

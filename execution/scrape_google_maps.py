#!/usr/bin/env python3
"""
Google Maps Lead Scraper
Uses the Apify compass/crawler-google-places actor to scrape business leads from Google Maps.
"""

import os
import time
import json
import argparse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
ACTOR_ID = "compass~crawler-google-places"  # Note: Use tilde (~) for API calls, not slash (/)

def scrape_google_maps(search_terms, max_results, language="en", scrape_reviews=False, scrape_images=False, output_file=".tmp/google_maps_leads.json"):
    """
    Scrape Google Maps leads using the compass/crawler-google-places Apify actor.

    Args:
        search_terms: List of search queries (e.g., ["plumbers in Austin", "dentist Miami"])
        max_results: Maximum number of results per search term
        language: Language code (default: "en")
        scrape_reviews: Whether to scrape reviews (WARNING: expensive and slow)
        scrape_images: Whether to scrape images
        output_file: Path to save the JSON results
    """
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY not found in .env file")

    if not search_terms:
        raise ValueError("At least one search term is required")

    # Construct input for the actor
    # See: https://apify.com/compass/crawler-google-places/input-schema
    actor_input = {
        "searchStringsArray": search_terms,
        "maxCrawledPlacesPerSearch": max_results,
        "language": language,
        "includeReviews": scrape_reviews,
        "includeImages": scrape_images,
        "includeHistogram": False,  # Not needed for lead gen
        "includePeopleAlsoSearch": False,  # Not needed for lead gen
        "maxReviews": 10 if scrape_reviews else 0,  # Limit reviews to reduce cost
        "maxImages": 5 if scrape_images else 0,  # Limit images to reduce cost
    }

    print("=" * 60)
    print(f"Starting Google Maps scrape with {len(search_terms)} search term(s)")
    print("=" * 60)
    print(f"\nActor: {ACTOR_ID}")
    print(f"Max results per search: {max_results}")
    print(f"Language: {language}")
    print(f"Scrape reviews: {scrape_reviews}")
    print(f"Scrape images: {scrape_images}")
    print(f"\nSearch terms:")
    for i, term in enumerate(search_terms, 1):
        print(f"  {i}. {term}")
    print()

    # Start the actor run
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_KEY}"

    print("Starting Apify actor run...")
    response = requests.post(url, json=actor_input)

    if not response.ok:
        print(f"❌ Error response: {response.status_code}")
        print(f"Response body: {response.text}")
        response.raise_for_status()

    run_data = response.json()["data"]
    run_id = run_data["id"]
    default_dataset_id = run_data["defaultDatasetId"]

    print(f"✓ Run started successfully")
    print(f"  Run ID: {run_id}")
    print(f"  Dataset ID: {default_dataset_id}")
    print(f"  Monitor at: https://console.apify.com/actors/{ACTOR_ID}/runs/{run_id}")
    print()

    # Poll for completion
    print("Waiting for run to complete...")
    start_time = time.time()
    poll_count = 0

    while True:
        status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_KEY}"
        status_response = requests.get(status_url)
        status_response.raise_for_status()
        status_data = status_response.json()["data"]
        status = status_data["status"]

        poll_count += 1
        elapsed = int(time.time() - start_time)

        # Show status every 5 polls (25 seconds)
        if poll_count % 5 == 0:
            print(f"  Status: {status} (elapsed: {elapsed}s)")

        if status == "SUCCEEDED":
            print(f"\n✓ Run succeeded in {elapsed}s")
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            raise RuntimeError(f"❌ Run failed with status: {status}")

        time.sleep(5)

    # Fetch results from the dataset
    print("\nFetching results from dataset...")
    dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_API_KEY}"
    dataset_response = requests.get(dataset_url)
    dataset_response.raise_for_status()
    items = dataset_response.json()

    if not items:
        print("⚠️  Warning: No results returned. Your search may be too specific or have no matches.")
        print("   Try broadening your search terms or checking for typos.")

    # Save to file
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".tmp", exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(items, f, indent=2)

    print(f"\n✓ Saved {len(items)} business(es) to {output_file}")

    # Show summary statistics
    if items:
        print("\n" + "=" * 60)
        print("SCRAPE SUMMARY")
        print("=" * 60)

        with_phone = sum(1 for item in items if item.get("phone"))
        with_website = sum(1 for item in items if item.get("website"))
        with_email = sum(1 for item in items if item.get("email"))
        avg_rating = sum(item.get("totalScore", 0) for item in items) / len(items) if items else 0

        print(f"Total businesses: {len(items)}")
        print(f"With phone number: {with_phone} ({with_phone/len(items)*100:.1f}%)")
        print(f"With website: {with_website} ({with_website/len(items)*100:.1f}%)")
        print(f"With email: {with_email} ({with_email/len(items)*100:.1f}%)")
        print(f"Average rating: {avg_rating:.2f} stars")
        print()

        # Sample business for verification
        print("Sample business (first result):")
        sample = items[0]
        print(f"  Name: {sample.get('title', 'N/A')}")
        print(f"  Address: {sample.get('address', 'N/A')}")
        print(f"  Phone: {sample.get('phone', 'N/A')}")
        print(f"  Website: {sample.get('website', 'N/A')}")
        print(f"  Rating: {sample.get('totalScore', 'N/A')} ({sample.get('reviewsCount', 0)} reviews)")
        print(f"  Category: {sample.get('categoryName', 'N/A')}")
        print()

    print("=" * 60)
    print("Next steps:")
    print("  1. Review the results to ensure quality")
    print("  2. Export to Google Sheets:")
    print(f"     .venv/bin/python execution/export_to_sheets.py \\")
    print(f"       {output_file} \\")
    print(f"       --sheet-name \"Google Maps [Your Title]\" \\")
    print(f"       --folder-id \"0ADWgx-M8Z5r-Uk9PVA\"")
    print("=" * 60)

    return items

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape Google Maps leads using Apify compass/crawler-google-places actor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scrape - plumbers in Austin
  python execution/scrape_google_maps.py \\
    --search-terms "plumbers in Austin, TX" \\
    --max-results 100 \\
    --output .tmp/plumbers_austin.json

  # Multiple search terms
  python execution/scrape_google_maps.py \\
    --search-terms "coffee shop in Brooklyn" "cafe in Brooklyn" \\
    --max-results 50 \\
    --output .tmp/coffee_brooklyn.json

  # With reviews (expensive!)
  python execution/scrape_google_maps.py \\
    --search-terms "restaurants in Miami" \\
    --max-results 100 \\
    --scrape-reviews \\
    --output .tmp/restaurants_miami.json
"""
    )

    parser.add_argument(
        "--search-terms",
        nargs="+",
        required=True,
        help="Search queries (e.g., 'plumbers in Austin' 'dentist Miami')"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum results per search term (default: 100)"
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code (default: en)"
    )
    parser.add_argument(
        "--scrape-reviews",
        action="store_true",
        help="Scrape reviews (WARNING: significantly increases cost and runtime)"
    )
    parser.add_argument(
        "--scrape-images",
        action="store_true",
        help="Scrape images (increases cost)"
    )
    parser.add_argument(
        "--output",
        default=".tmp/google_maps_leads.json",
        help="Output JSON file path (default: .tmp/google_maps_leads.json)"
    )

    args = parser.parse_args()

    try:
        scrape_google_maps(
            search_terms=args.search_terms,
            max_results=args.max_results,
            language=args.language,
            scrape_reviews=args.scrape_reviews,
            scrape_images=args.scrape_images,
            output_file=args.output
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

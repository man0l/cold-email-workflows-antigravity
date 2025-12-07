import json
import argparse
import sys
import os

def convert_to_apollo(input_file, output_file):
    """
    Converts Google Maps enriched leads to Apollo format.
    """
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    apollo_leads = []

    for company in data:
        # Extract company-level info
        # Prefer Title Case for City (from 'city') and Abbreviation for State (from 'company_state' if 2 chars)
        
        c_city = company.get("city") or company.get("company_city")
        
        raw_state = company.get("state")
        comp_state = company.get("company_state")
        # Prefer full state name (raw_state) if available, otherwise fallback to whatever we have
        c_state = raw_state or comp_state
        
        c_country = company.get("countryCode") or company.get("company_country")
        if c_country == "US":
            c_country = "United States"

        company_info = {
            "Company Name": company.get("title") or company.get("company_name"),
            "Company Website": company.get("website") or company.get("company_website"),
            "Company Phone": company.get("phone") or company.get("company_phone"),
            "Company City": c_city,
            "Company State": c_state,
            "Company Country": c_country,
            "Company Postal Code": company.get("postalCode") or company.get("company_postal_code"),
            "Industry": company.get("categoryName") or company.get("industry"),
            "Company Linkedin Url": company.get("socials", {}).get("linkedin") or company.get("company_linkedin"),
            "Company Address": company.get("address") or company.get("company_address"),
            
            # Contact Location (default to company location)
            "City": c_city,
            "State": c_state,
            "Country": c_country
        }

        # Check for enriched contacts
        # User requested ONLY the primary email.
        # Strategy:
        # 1. Look for 'primary_email' field.
        # 2. If found, try to find matching details in 'emails_raw'.
        # 3. If not found, check 'emails' list and take the first one.
        # 4. If no emails, just output company info.
        
        target_email = company.get("primary_email")
        if not target_email and company.get("emails"):
             # Fallback to first email if primary_email is missing but emails list exists
             first_email = company["emails"][0]
             if isinstance(first_email, str):
                 target_email = first_email
        
        if target_email:
            # Try to find details for this email in emails_raw
            contact_details = None
            if "emails_raw" in company and company["emails_raw"]:
                for contact in company["emails_raw"]:
                    if contact.get("value") == target_email:
                        contact_details = contact
                        break
            
            new_lead = company_info.copy()
            new_lead["Email"] = target_email
            
            if contact_details:
                full_name = contact_details.get("full_name")
                if full_name:
                    parts = full_name.split()
                    new_lead["First Name"] = parts[0]
                    new_lead["Last Name"] = " ".join(parts[1:]) if len(parts) > 1 else ""
                    new_lead["Full Name"] = full_name
                new_lead["Job Title"] = contact_details.get("title")
            
            apollo_leads.append(new_lead)
        else:
            # No email found, just add company info
            apollo_leads.append(company_info)

    try:
        with open(output_file, 'w') as f:
            json.dump(apollo_leads, f, indent=2)
        print(f"Successfully converted {len(data)} companies into {len(apollo_leads)} leads.")
        print(f"Output saved to: {output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Google Maps leads to Apollo format")
    parser.add_argument("--input", required=True, help="Input JSON file (Google Maps format)")
    parser.add_argument("--output", required=True, help="Output JSON file (Apollo format)")
    
    args = parser.parse_args()
    
    convert_to_apollo(args.input, args.output)

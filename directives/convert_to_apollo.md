# Convert Google Maps Leads to Apollo Format

## Goal
Convert scraped and enriched Google Maps leads (JSON) into an Apollo-compatible format (JSON).

## Inputs
- `input_file`: Path to the source JSON file (Google Maps enriched leads).
- `output_file`: Path to the destination JSON file (Apollo format).

## Tools
- `execution/convert_to_apollo.py`

## Execution Steps
1. Run the conversion script:
   ```bash
   python3 execution/convert_to_apollo.py --input <input_file> --output <output_file>
   ```

## Output
- A JSON file at `output_file` containing the converted leads.
- **Logic**:
    - **One lead per company**: Prioritizes `primary_email`. If missing, uses the first available email.
    - **Field Mapping**:
        - `full_name` is split into `first_name` and `last_name`.
        - `company_country` is normalized to "United States".
        - `job_title` is extracted if available.

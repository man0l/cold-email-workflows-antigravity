# Cold Email Workflows - Antigravity

A 3-layer architecture system for automated lead generation and cold email workflows using LLMs for orchestration and deterministic Python scripts for execution.

## Architecture

This project follows a 3-layer architecture:

1. **Directives** (`directives/`) - Natural language SOPs that define what to do
2. **Orchestration** - LLM agents that make decisions and route tasks
3. **Execution** (`execution/`) - Deterministic Python scripts that do the actual work

## Project Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

- **APIFY_API_KEY** - Get from [Apify Console](https://console.apify.com/account/integrations)
- **ANYMAILFINDER_API_KEY** - Get from [AnyMailFinder](https://anymailfinder.com/)
- **INSTANTLY_API_KEY** - Get from [Instantly Settings](https://app.instantly.ai/app/settings/api)
- **LEAD_GEN_FOLDER_ID** - (Optional) Google Drive folder ID for outputs

### 3. Set Up Google OAuth Credentials

This project uses Google Sheets and Google Drive for deliverables. You need to set up OAuth credentials:

#### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Drive API

#### Step 2: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Choose **Desktop app** as the application type
4. Download the credentials JSON file
5. Rename it to `credentials.json` and place it in the project root

#### Step 3: First-Time Authentication

The first time you run a script that uses Google APIs, it will:
1. Open a browser window for authentication
2. Ask you to grant permissions
3. Save the authentication token to `token.json`

Both `credentials.json` and `token.json` are gitignored for security.

### 4. Create Required Directories

The `.tmp/` directory for intermediate files is already created. All intermediate processing files go here.

## Directory Structure

```
.
├── directives/          # SOPs in Markdown
│   ├── apify_scrape_leads.md
│   ├── clean_instantly_leads.md
│   ├── clean_leads.md
│   └── find_emails.md
├── execution/           # Python scripts (deterministic tools)
│   ├── clean_instantly_leads.py
│   ├── clean_leads.py
│   ├── export_to_sheets.py
│   ├── fetch_run_results.py
│   ├── find_emails.py
│   ├── qa_leads.py
│   ├── scrape_apify_leads.py
│   └── validate_websites.py
├── .tmp/               # Intermediate files (gitignored)
├── .env                # Environment variables (gitignored)
├── credentials.json    # Google OAuth credentials (gitignored)
├── token.json         # Google OAuth token (gitignored)
└── requirements.txt   # Python dependencies
```

## Available Workflows

Check the `directives/` folder for detailed SOPs on each workflow:

- **Apify Scrape Leads** - Scrape leads from websites using Apify
- **Find Emails** - Find email addresses for leads
- **Clean Leads** - Clean and validate lead data
- **Clean Instantly Leads** - Clean leads specifically for Instantly.ai

## Operating Principles

1. **Check for tools first** - Always use existing scripts in `execution/` before creating new ones
2. **Self-anneal when things break** - Fix errors, update scripts, test, and update directives
3. **Update directives as you learn** - Keep SOPs current with new learnings
4. **Deliverables in the cloud** - All outputs go to Google Sheets/Drive, not local files
5. **Intermediates in .tmp/** - All temporary processing files can be regenerated

## Usage

Interact with an LLM agent (Claude, Gemini, etc.) and reference the directives. The agent will:
1. Read the appropriate directive
2. Call the execution scripts with proper inputs
3. Handle errors and edge cases
4. Update directives with learnings

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.json`
- All sensitive files are in `.gitignore`
- API keys should be kept secure and rotated regularly

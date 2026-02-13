# LeadGen AI -- Command Reference

All commands are run from the `leadgen-ai/` directory.

```
python main.py <command> [options]
```

---

## Lead Ingestion

These commands get leads into the database.

| Command | Purpose |
|---|---|
| `test-scraper` | Generate 5 synthetic test leads for development purposes. Prompts before saving to database. Does not touch any real website. |
| `scrape [limit] [location] [category]` | Scrape live business listings from Hotfrog directory. Default: 20 leads from US restaurants. Rate-limited to avoid blocking. |
| `add-lead "Name" "URL" [flags]` | Insert a single lead manually. Only business name and URL are required. Optional flags: `--email`, `--phone`, `--industry`, `--location`. |
| `import-csv <filepath>` | Bulk-import leads from a CSV file. Requires `business_name` and `website_url` columns. Skips duplicates automatically. |
| `import-csv --template` | Generate a sample CSV file at `data/sample_leads.csv` showing the expected column format. |

**Examples:**

```
python main.py test-scraper
python main.py scrape 10 us dental
python main.py add-lead "Joe's Diner" "https://joesdiner.com" --industry restaurant --location "Austin, TX"
python main.py import-csv /path/to/my_leads.csv
python main.py import-csv --template
```

---

## Intelligence Pipeline

These commands analyze leads and prepare outreach material.

| Command | Purpose |
|---|---|
| `audit [limit]` | Run website audits on leads that have not been audited yet. Calls Google PageSpeed Insights API for each site. Default limit: 10. |
| `score [limit]` | Score audited leads using the weighted formula. Assigns HOT, WARM, COLD, or SKIP classification. Default limit: 20. |
| `generate [limit]` | Generate personalized outreach emails for scored leads. Uses Gemini AI with deterministic fallback. Default limit: 10. |

**Examples:**

```
python main.py audit 5
python main.py score
python main.py generate 3
```

---

## Full Pipeline

Run the entire sequence in one command.

| Command | Purpose |
|---|---|
| `run-all [audit_limit] [gen_limit]` | Execute the complete pipeline in order: audit unaudited leads, score them, generate outreach emails, export results to CSV. |

**Example:**

```
python main.py run-all 5 5
```

This audits up to 5 leads, scores all audited leads, generates up to 5 emails, and exports the results.

---

## Review and Reporting

These commands let you inspect what the system has done.

| Command | Purpose |
|---|---|
| `stats` | Display database summary: total leads, leads added today, pending audits, pending outreach, emails sent today. |
| `list-leads [limit]` | List recent leads with their website, industry, source, and audit status. Default: 10 most recent. |
| `preview <lead_id>` | Preview the outreach email that would be (or was) generated for a specific lead. |
| `export` | Export all pending outreach records to a CSV file in the `exports/` directory. |
| `audit-report` | Display a summary table of all audited leads with scores and issue counts in the terminal. |
| `audit-report <lead_id>` | Display a detailed audit report for a specific lead in the terminal, including score breakdowns, Core Web Vitals, and detected issues. |
| `audit-export` | Export all audit reports as professional HTML files to `data/reports/`. |
| `audit-export <lead_id>` | Export a single lead's audit report as an HTML file. |
| `conversion-stats` | Display the conversion funnel: emails sent, replies received, meetings booked, deals closed, revenue generated. |

**Examples:**

```
python main.py stats
python main.py list-leads 20
python main.py preview 7
python main.py export
python main.py audit-report
python main.py audit-report 8
python main.py audit-export
python main.py conversion-stats
```

---

## Email Sending

These commands handle SMTP delivery of generated outreach emails.

| Command | Purpose |
|---|---|
| `test-smtp` | Test the SMTP connection to verify credentials and relay access. Does not send any email. |
| `send [limit]` | Send pending outreach emails in batch. Respects the configured delay between sends and daily limit. Default: 5. |
| `send-one <outreach_id>` | Send a single specific outreach email by its database ID. Useful for manual, controlled sending. |

**Examples:**

```
python main.py test-smtp
python main.py send 3
python main.py send-one 4
```

**Note on batch sending:** The `send` command introduces a delay (default 8 minutes) between each email to mimic human sending patterns. For large batches, this means the command runs for a long time. If you prefer more control, use `send-one` for each email individually.

---

## Setup Checklist

Before running any commands:

1. Create and activate the virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure credentials:
   ```
   cp config/.env.example config/.env
   ```
   Then edit `config/.env` with your API keys and SMTP credentials.

4. Verify the setup:
   ```
   python main.py stats
   ```

---

## Typical Workflow

A normal session looks like this:

```
# Add some leads
python main.py import-csv my_leads.csv

# Audit their websites
python main.py audit

# Score them
python main.py score

# Generate outreach emails
python main.py generate

# Review what was generated
python main.py preview 12

# Send the emails
python main.py send-one 7
python main.py send-one 8

# Check your funnel
python main.py conversion-stats
```

Or, if you want to run everything at once:

```
python main.py import-csv my_leads.csv
python main.py run-all
python main.py send 5
```

---

## CSV Import Format

The CSV file must have a header row. Required columns are `business_name` and `website_url`. All other columns are optional.

| Column | Required | Description |
|---|---|---|
| `business_name` | Yes | Name of the business |
| `website_url` | Yes | Website address (https:// prefix added automatically if missing) |
| `email` | No | Contact email address |
| `phone` | No | Contact phone number |
| `industry` | No | Business category (restaurant, dental, law firm, etc.) |
| `location` | No | City, state, or full address |

Run `python main.py import-csv --template` to generate a sample file you can use as a starting point.

AI Lead Intelligence System — MVP Blueprint
1. MVP Philosophy
1.1 Purpose of MVP

The MVP exists to validate business value, not to build the final empire.

Primary MVP Goals:

Prove automated lead generation works

Validate AI-generated outreach effectiveness

Build working data pipeline

Test conversion workflow

Create foundation for scaling

1.2 MVP Success Criteria

The MVP is successful if it can:

Scrape at least one lead source reliably

Analyze business websites automatically

Generate personalized outreach drafts using Gemini

Store and export structured leads

Produce usable outreach content

2. MVP Feature Scope
2.1 Included Features (Must Build)
Lead Collection

Scrape 1–2 directory sources

Extract business contact data

Website Audit

Performance score

Mobile friendliness check

Basic SEO detection

AI Outreach Generator

Generate personalized cold email drafts

Summarize website problems

Lead Storage

Store leads in database

Export CSV

Basic CLI or Script Control

Run pipeline manually

2.2 Excluded Features (Later Phases)

Full CRM dashboard

Automated email sending

Multi-thread distributed scraping

SaaS UI

Complex lead scoring AI

3. MVP System Architecture
Scraper Module
      ↓
Database Storage
      ↓
Website Audit Module
      ↓
Gemini AI Processor
      ↓
Output Generator (CSV + Message Drafts)
4. Technology Stack (MVP)
Backend

Python 3.11+

Libraries
Purpose	Library
HTTP Requests	requests
HTML Parsing	BeautifulSoup
Browser Automation	Playwright
Database ORM	SQLAlchemy
CSV Export	pandas
Async Tasks (optional)	asyncio
AI Integration	Gemini API
Database

SQLite (MVP simplicity)

5. Folder Structure Blueprint
ai-lead-system/
│
├── config/
│   ├── settings.py
│   └── secrets.env
│
├── database/
│   ├── models.py
│   ├── connection.py
│   └── migrations/
│
├── scraper/
│   ├── hotfrog_scraper.py
│   ├── base_scraper.py
│   └── parser_utils.py
│
├── audit/
│   ├── website_audit.py
│   ├── pagespeed.py
│   └── seo_checker.py
│
├── ai/
│   ├── gemini_client.py
│   ├── prompts.py
│   └── outreach_generator.py
│
├── pipeline/
│   ├── lead_pipeline.py
│   └── orchestrator.py
│
├── output/
│   ├── csv_exporter.py
│   └── report_generator.py
│
├── logs/
│
├── main.py
└── requirements.txt
6. Database Schema (MVP)
Leads Table
Lead
-----
id
business_name
website_url
phone
email
industry
location
source
created_at
Audit Table
Audit
------
lead_id (FK)
performance_score
mobile_friendly
seo_score
major_issues (JSON)
audit_timestamp
Outreach Table
Outreach
---------
lead_id (FK)
generated_message
ai_summary
created_at
7. Core Module Design
7.1 Scraper Module
Responsibilities

Fetch directory pages

Extract business metadata

Validate contact fields

Scraper Workflow
Fetch directory page
↓
Extract business listings
↓
Normalize fields
↓
Save to database
Scraper Pseudocode
def scrape_hotfrog():
    html = fetch_page()
    businesses = parse_business_cards(html)


    for business in businesses:
        save_lead(business)
7.2 Website Audit Module
Responsibilities

Visit business website

Run performance check

Detect mobile compatibility

Extract SEO metadata

Audit Workflow
Fetch Website
↓
Run PageSpeed API
↓
Check Mobile Layout
↓
Extract SEO Tags
↓
Save Results
Audit Output Example
{
    performance_score: 72,
    mobile_friendly: True,
    seo_score: 55,
    major_issues: [
        "Missing meta description",
        "Large unoptimized images"
    ]
}
7.3 Gemini AI Module
Responsibilities

Summarize audit findings

Generate outreach email

Provide business impact explanation

Gemini Integration Flow
Prepare structured prompt
↓
Send audit + business data
↓
Receive outreach message
↓
Store output
Gemini Client Pseudocode
def generate_outreach(lead, audit):
    prompt = build_prompt(lead, audit)
    response = gemini_api(prompt)
    return response
7.4 Pipeline Orchestrator
Responsibilities

Control entire workflow

Handle execution order

Log system activity

Pipeline Flow
Scrape Leads
↓
Run Audit
↓
Generate Outreach
↓
Export Results
Pipeline Pseudocode
def run_pipeline():
    leads = scrape_leads()


    for lead in leads:
        audit = run_audit(lead.website)
        outreach = generate_outreach(lead, audit)
        store_results()
8. Configuration Management
settings.py Should Store

API endpoints

Rate limits

Scraper delays

Email templates

secrets.env Should Store

Gemini API key

Database credentials

External service tokens

9. Logging Strategy

Log:

Scraping success/failure

Website audit results

AI generation errors

Pipeline execution status

10. Error Handling Strategy
Scraping Errors

Retry logic

Skip invalid listings

Timeout protection

AI Errors

Retry failed API calls

Store fallback templates

Validate output length

Website Audit Failures

Detect offline websites

Mark audit as skipped

Continue pipeline execution

11. Rate Limiting Strategy

3–5 second delay between website audits

Directory scraping delay 5–10 seconds

Gemini API request throttling

12. Output System
CSV Export Format
Business Name
Website
Phone
Performance Score
SEO Score
Major Issues
Outreach Message
13. MVP CLI Control
CLI Commands
python main.py scrape
python main.py audit
python main.py generate
python main.py export
python main.py run-all
14. Development Timeline (Realistic)
Week 1

Project setup

Database schema

Basic scraper

Week 2

Website audit integration

PageSpeed API

Week 3

Gemini outreach generator

Pipeline orchestration

Week 4

CSV export

Logging

Testing & stabilization

15. Testing Strategy
Unit Testing

Scraper parser validation

Audit scoring logic

AI output formatting

Integration Testing

Full pipeline execution

Database integrity

Export validation

16. MVP Risk Mitigation
Data Quality Risk

Validate extracted fields

Remove duplicate leads

API Dependency Risk

Store fallback audit templates

Add retry logic

Performance Risk

Limit concurrent scraping

Cache repeated audits

17. Future Expansion Hooks

Design MVP with extension points for:

Multi-source scraping

Email automation

Lead scoring AI

Web dashboard

SaaS deployment

18. Deployment Strategy (MVP)
Environment

Local machine or VPS

Docker container optional

Execution Method

Manual CLI pipeline trigger

Cron-based scheduled runs

19. Security Practices

Never hardcode API keys

Use environment variables

Restrict database access

Encrypt backups

20. MVP Completion Checklist

 Scraper working

 Database storing leads

 Website audit functional

 Gemini outreach generated

 Pipeline orchestration working

 CSV export validated

Final Strategic Reality

Your MVP is NOT supposed to be pretty.
Your MVP is supposed to prove you can turn data into clients.
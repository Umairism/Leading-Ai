# AI Lead Intelligence and Outreach Automation System

## Technical and Business Specification

---

## 1. Project Overview

### 1.1 Objective

This system exists to solve a real problem: finding freelance clients is slow, repetitive, and manual. Every hour spent researching businesses, reading their websites, and writing cold emails is an hour not spent doing actual paid work.

The objective is to build a pipeline that handles the tedious parts of client acquisition automatically:

- Collect business leads from publicly available directory sources
- Analyze each business's website for technical and marketing weaknesses
- Use AI to write outreach emails that reference those specific weaknesses
- Manage the full lifecycle from lead discovery through email delivery and conversion tracking
- Do all of this without crossing ethical or legal boundaries

The system is not trying to replace human judgment. It is trying to eliminate the grunt work that sits between you and a qualified conversation with a potential client.

### 1.2 Core Value Proposition

Manual freelance prospecting typically looks like this: search directories, visit websites, make notes, draft emails, send them, repeat. That process takes hours per lead. This system compresses it into minutes.

What it replaces:

- **Manual research** becomes automated website auditing via Google PageSpeed Insights
- **Gut-feeling targeting** becomes deterministic lead scoring based on real audit data
- **Generic cold emails** become AI-written outreach that references specific problems found on the prospect's site
- **Scattered notes** become a structured database with full audit history and conversion tracking

### 1.3 Expected Outcomes

- Significantly higher client acquisition throughput without sacrificing personalization
- Outreach emails that read like a human wrote them, because they reference real observations about the recipient's website
- A structured, queryable database of every lead, audit, and outreach attempt
- Reduced time-to-first-contact for any new market or industry vertical
- A codebase that could, with further development, become a commercial SaaS product

---

## 2. System Architecture

The system follows a linear pipeline architecture. Each stage feeds into the next, and each stage can be run independently or as part of a full pipeline execution.

```
Lead Sources (directories, CSV imports, manual entry)
    |
    v
Scraping and Ingestion Layer
    |
    v
SQLite Database (leads, audits, outreach records)
    |
    v
Website Audit Engine (Google PageSpeed Insights API)
    |
    v
Lead Scoring Engine (deterministic, weighted scoring)
    |
    v
AI Intelligence Layer (Google Gemini 2.0 Flash)
    |
    v
Outreach Email Generation (AI-written with fallback templates)
    |
    v
SMTP Email Delivery (Brevo relay)
    |
    v
Conversion Tracking (reply, meeting, close, deal value)
```

Each component is a separate Python module. The pipeline orchestrator coordinates them. The CLI provides command-level access to every stage.

---

## 3. Technology Stack

### 3.1 Language and Runtime

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| Environment | Virtual environment (venv) |
| Entry Point | CLI via `main.py` |

### 3.2 Data Layer

| Purpose | Technology |
|---|---|
| ORM | SQLAlchemy |
| Database | SQLite (file-based, zero configuration) |
| Session Management | Context manager with automatic commit/rollback |

SQLite was chosen for the MVP deliberately. It requires no server process, no credentials, and no network configuration. The database is a single file in the `data/` directory. When the system outgrows SQLite, the SQLAlchemy ORM layer means switching to PostgreSQL requires changing one connection string.

### 3.3 Website Analysis

| Purpose | Technology |
|---|---|
| Performance and SEO Auditing | Google PageSpeed Insights API (v5) |
| Content Analysis | Requests + custom HTML parsing |
| Score Extraction | Lighthouse categories via PageSpeed response |

The PageSpeed API returns Lighthouse audit data including performance scores, SEO scores, accessibility scores, Core Web Vitals, and specific diagnostic recommendations. This data forms the foundation of both lead scoring and outreach personalization.

### 3.4 AI Integration

| Purpose | Technology |
|---|---|
| Outreach Generation | Google Gemini API (gemini-2.0-flash) |
| SDK | `google-genai` (current generation SDK) |
| Fallback | Deterministic template engine when API is unavailable |

The system never relies entirely on the AI. Every AI-powered function has a deterministic fallback that produces reasonable output using the audit data directly. If Gemini is down, rate-limited, or over budget, the pipeline continues without interruption.

### 3.5 Email Delivery

| Purpose | Technology |
|---|---|
| SMTP Relay | Brevo (formerly Sendinblue) |
| Protocol | SMTP over TLS (port 587) |
| Rate Limiting | Configurable delay between sends, daily cap |

### 3.6 Supporting Libraries

| Library | Purpose |
|---|---|
| `requests` | HTTP requests for scraping and API calls |
| `beautifulsoup4` | HTML parsing for content extraction |
| `python-dotenv` | Environment variable management |
| `pandas` | CSV export formatting |

---

## 4. Core System Modules

### 4.1 Lead Scraper Module

**Location:** `scraper/`

**What it does:** Collects business information from online directory listings and normalizes it into a consistent format for database storage.

**Data fields extracted per lead:**

| Field | Description |
|---|---|
| `business_name` | Legal or trading name of the business |
| `website_url` | Primary website (used as unique identifier) |
| `phone` | Contact phone number |
| `email` | Contact email address |
| `industry` | Business category (restaurant, dental, law firm, etc.) |
| `location` | City, state, country |
| `source` | Where the lead came from (hotfrog, csv_import, manual_add) |

**Duplicate handling:** The `website_url` field has a unique constraint in the database. If a scraper or import tries to insert a lead with a URL that already exists, the system skips it and logs the duplicate.

**Current sources:**
- Hotfrog directory scraper (live scraping with rate limiting)
- CSV bulk import (any properly formatted CSV file)
- Manual CLI entry (single lead at a time)
- Test lead generator (synthetic data for development)

**Scraping discipline:**
- Configurable delay between requests (default: 5 seconds)
- Respects rate limits to avoid IP blocking
- Validates extracted fields before database insertion
- Logs every skip, failure, and duplicate for auditability

### 4.2 Website Audit Engine

**Location:** `audit/`

**What it does:** Takes a lead's website URL and runs it through the Google PageSpeed Insights API to produce a structured quality assessment. The raw API response is stored in full, and key metrics are extracted into dedicated database columns for querying and scoring.

**Audit output structure:**

```json
{
    "performance_score": 42,
    "seo_score": 77,
    "accessibility_score": 65,
    "mobile_friendly": false,
    "major_issues": [
        "Missing meta description",
        "Images not optimized",
        "No viewport meta tag"
    ],
    "raw_data": { }
}
```

**Additional analysis (via WebsiteAnalyzer):**
- SSL certificate validity
- Page load time measurement
- Title tag presence and content
- Meta description presence
- Open Graph tags for social sharing
- Favicon detection
- Viewport meta tag for mobile

**Report generation:**
- Terminal-formatted audit reports with visual score bars
- Professional HTML reports with inline CSS for client-facing use
- Batch export of all audit reports to `data/reports/`

**Failure handling:** If a website is unreachable, times out, or returns an error, the audit is marked as `failed` with an error message. The pipeline continues to the next lead. Failed audits are still stored so you can see which sites had problems.

### 4.3 Lead Scoring Engine

**Location:** `audit/lead_scorer.py`

**What it does:** Takes audit results and produces a deterministic priority classification. This is not machine learning. It is a weighted scoring formula based on the audit metrics, designed to surface the leads most likely to need your services.

**Scoring weights:**

| Factor | Weight | Rationale |
|---|---|---|
| Performance score | 25% | Slow sites lose visitors |
| Mobile usability | 20% | Over half of web traffic is mobile |
| SEO condition | 20% | Poor SEO means invisible to search |
| Accessibility score | 15% | Legal liability and user experience |
| Technical issues count | 10% | More problems means more opportunity |
| Content completeness | 10% | Missing basics signal neglect |

**Priority classifications:**

| Classification | Score Range | Meaning |
|---|---|---|
| HOT | 70-100 | Significant problems, high likelihood of needing services |
| WARM | 40-69 | Some problems worth addressing |
| COLD | 20-39 | Minor issues, lower urgency |
| SKIP | 0-19 | Site is in reasonable shape, not worth pursuing |

The scoring is deliberately conservative. A lead scored HOT genuinely has meaningful problems on their website. This matters because every outreach email references those problems by name. If the scoring were generous and labeled a decent website as HOT, the outreach would sound dishonest.

### 4.4 AI Intelligence Layer

**Location:** `ai/`

**What it does:** Takes business information and audit data, then generates a personalized outreach email that reads like a human wrote it after actually looking at the prospect's website.

**Gemini integration flow:**

```
Business data + Audit results
    |
    v
Structured prompt construction (ai/prompts.py)
    |
    v
Gemini 2.0 Flash API call
    |
    v
Response parsing and validation
    |
    v
Email stored in outreach table
```

**Prompt design principles:**
- The prompt instructs the AI to write as a real person, not a marketer
- No buzzwords, no jargon, no "leverage" or "synergy"
- Reference specific audit findings (actual scores, actual missing elements)
- Keep the tone conversational and direct
- Include a clear, low-pressure call to action

**Fallback system:** When the Gemini API is unavailable (quota exhaustion, rate limiting, network issues), the system falls back to a deterministic template engine. The template uses the same audit data to construct an email that follows the same structure and tone guidelines. The fallback emails are not as varied as AI-generated ones, but they are accurate and functional.

**Quality safeguards:**
- Industry-specific language handling (correct plurals: "dental offices" not "dentals")
- Proper possessive handling for business names (including LLC/Inc suffixes)
- Competitive fear paragraph grounded in real data, not scare tactics
- Authority establishment through specific audit findings

### 4.5 Outreach and Email Delivery

**Location:** `outreach/`

**What it does:** Takes generated email content from the database and delivers it via SMTP through the Brevo relay service.

**Delivery controls:**
- Configurable daily send limit (default: 30 emails per day)
- Configurable delay between sends (default: 8 minutes)
- Individual send capability for manual control
- SMTP connection testing without sending any email

**Compliance features:**
- Sender identity matches configured business name and email
- Reply-To header set to actual business email
- Each email is logged with timestamp for audit trail

### 4.6 Pipeline Orchestrator

**Location:** `pipeline/orchestrator.py`

**What it does:** Coordinates the execution of multiple pipeline stages in sequence. When you run `run-all`, the orchestrator handles: audit unaudited leads, score them, generate outreach emails, and export results.

**Design:** Each stage is independent. The orchestrator simply calls them in order and passes configuration. If any stage fails, the error is logged and the next stage proceeds with whatever data is available.

### 4.7 Conversion Tracking

**Location:** Built into the Outreach database model and repository.

**What it tracks:**

| Field | Purpose |
|---|---|
| `sent_at` | When the email was delivered |
| `positive_reply` | Whether the prospect responded positively |
| `meeting_booked` | Whether a meeting was scheduled |
| `meeting_date` | When the meeting is/was |
| `client_closed` | Whether the lead became a paying client |
| `deal_value` | Revenue from the closed deal |
| `outcome_notes` | Free-text notes on what happened |

This gives you a complete funnel: leads collected, audited, scored, emailed, replied, met, closed, and the dollar value of each conversion. Over time, this data tells you which industries, which score ranges, and which email styles produce actual revenue.

---

## 5. Database Schema

### Leads Table

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | Integer | Primary key, auto-increment | Unique identifier |
| `business_name` | String(255) | Not null | Business name |
| `website_url` | String(500) | Not null, unique | Primary website URL |
| `phone` | String(50) | Nullable | Contact phone |
| `email` | String(255) | Nullable | Contact email |
| `industry` | String(100) | Nullable | Business category |
| `location` | String(255) | Nullable | Geographic location |
| `source` | String(100) | Nullable | Lead origin |
| `created_at` | DateTime | Default: now | Insertion timestamp |

### Audits Table

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | Integer | Primary key | Unique identifier |
| `lead_id` | Integer | Foreign key to leads | Associated lead |
| `performance_score` | Integer | Nullable | Lighthouse performance (0-100) |
| `seo_score` | Integer | Nullable | Lighthouse SEO (0-100) |
| `accessibility_score` | Integer | Nullable | Lighthouse accessibility (0-100) |
| `mobile_friendly` | Boolean | Default: false | Mobile compatibility |
| `major_issues` | JSON | Nullable | List of detected problems |
| `raw_data` | JSON | Nullable | Full API response |
| `audit_timestamp` | DateTime | Default: now | When the audit ran |
| `audit_status` | String(50) | Default: completed | completed, failed, skipped |
| `error_message` | Text | Nullable | Error details if audit failed |

### Outreach Table

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | Integer | Primary key | Unique identifier |
| `lead_id` | Integer | Foreign key to leads | Associated lead |
| `subject_line` | String(255) | Nullable | Email subject |
| `email_body` | Text | Nullable | Full email content |
| `ai_summary` | Text | Nullable | AI analysis of the lead |
| `qualification_score` | Integer | Nullable | Priority score (0-100) |
| `sent_at` | DateTime | Nullable | Delivery timestamp |
| `positive_reply` | Boolean | Default: false | Positive response received |
| `meeting_booked` | Boolean | Default: false | Meeting scheduled |
| `meeting_date` | DateTime | Nullable | Scheduled meeting date |
| `client_closed` | Boolean | Default: false | Converted to client |
| `deal_value` | Float | Nullable | Revenue from deal |
| `outcome_notes` | Text | Nullable | Manual notes |
| `created_at` | DateTime | Default: now | Record creation time |

---

## 6. Project Structure

```
leadgen-ai/
|
|-- config/
|   |-- settings.py          Configuration management, environment variables
|   |-- .env                  API keys, SMTP credentials, business identity
|   |-- .env.example          Template for new installations
|
|-- database/
|   |-- models.py             SQLAlchemy models (Lead, Audit, Outreach)
|   |-- connection.py         Database engine, session management
|   |-- repository.py         Data access layer (CRUD operations)
|
|-- scraper/
|   |-- base_scraper.py       Abstract scraper interface
|   |-- hotfrog_scraper.py    Hotfrog directory scraper
|   |-- parser_utils.py       HTML parsing utilities
|   |-- test_lead_generator.py  Synthetic lead generator for testing
|
|-- audit/
|   |-- pagespeed_audit.py    Google PageSpeed Insights API client
|   |-- website_analyzer.py   Content and technical analysis
|   |-- lead_scorer.py        Deterministic lead scoring engine
|   |-- report_generator.py   Terminal and HTML audit reports
|
|-- ai/
|   |-- gemini_client.py      Google Gemini API client (google-genai SDK)
|   |-- prompts.py            Structured prompt templates
|   |-- outreach_generator.py Email generation with AI and fallback
|
|-- pipeline/
|   |-- orchestrator.py       Multi-stage pipeline coordinator
|
|-- outreach/
|   |-- email_sender.py       SMTP delivery via Brevo
|
|-- utils/
|   |-- csv_importer.py       Bulk CSV lead import with validation
|
|-- data/
|   |-- leadgen.db            SQLite database file
|   |-- reports/              Exported HTML audit reports
|   |-- sample_leads.csv      CSV import template
|
|-- exports/                  CSV export output directory
|-- logs/                     Application log files
|-- main.py                   CLI entry point (all commands)
|-- requirements.txt          Python dependencies
|-- GUIDE.md                  Operational documentation
```

---

## 7. Configuration Management

### Environment Variables (config/.env)

All sensitive values and deployment-specific settings live in the `.env` file. Nothing is hardcoded.

**Required variables:**

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API authentication |
| `PAGESPEED_API_KEY` | Google PageSpeed Insights API authentication |
| `SMTP_EMAIL` | SMTP login username |
| `SMTP_ApiKey` | SMTP authentication password or API key |
| `SMTP_HOST` | SMTP relay hostname |
| `SMTP_PORT` | SMTP relay port (typically 587) |
| `BUSINESS_NAME` | Your business name (used in emails) |
| `BUSINESS_EMAIL` | Your reply-to email address |

**Optional variables:**

| Variable | Default | Purpose |
|---|---|---|
| `MAX_DAILY_LEADS` | 50 | Maximum leads to process per day |
| `MAX_DAILY_EMAILS` | 30 | Maximum emails to send per day |
| `SCRAPER_DELAY_SECONDS` | 5 | Delay between scraping requests |
| `EMAIL_DELAY_MINUTES` | 8 | Delay between email sends |
| `GEMINI_TEMPERATURE` | 0.7 | AI creativity level (0.0-1.0) |
| `GEMINI_MAX_TOKENS` | 1000 | Maximum AI response length |

### Settings Module (config/settings.py)

The `Config` class loads all environment variables at import time and provides them as class attributes. It also handles path resolution (ensuring SQLite uses absolute paths), directory creation, and configuration validation.

---

## 8. Legal and Compliance

### Email Compliance

The system is designed to comply with CAN-SPAM Act requirements:

- Every email identifies the sender by business name
- Reply-To header points to a real, monitored email address
- No deceptive subject lines -- subjects reference actual audit findings
- Daily volume limits prevent bulk-sending behavior

### Scraping Ethics

- Rate limiting on all HTTP requests to avoid overloading target servers
- Only publicly listed business information is collected
- No scraping of authenticated or login-protected content
- No resale or redistribution of collected data

### Deliverability Protection

- SMTP relay through Brevo (established deliverability infrastructure)
- Low daily volume to avoid spam classification
- Personalized content to avoid template-detection filters
- No misleading claims in email body

---

## 9. Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| API rate limiting | Pipeline stalls | Fallback templates, retry logic, daily budgets |
| Website unreachable | Incomplete audit | Mark as failed, continue pipeline, log error |
| AI hallucination | Inaccurate outreach | Structured prompts, audit data anchoring, manual review |
| Database corruption | Data loss | SQLite WAL mode, regular backups |
| IP blocking | Scraping failure | Request delays, rotating user agents |

### Business Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Spam reputation | Email deliverability drops | Daily limits, personalization, quality scoring |
| Low conversion rate | Wasted effort | Lead scoring refinement, industry targeting |
| Inaccurate audits | Credibility damage | Validate audit data against manual checks |

---

## 10. Deployment Strategy

### Phase 1 -- MVP (Current)

Everything runs locally via CLI. SQLite database, single-user, manual pipeline triggers. This phase validates that the core pipeline works: scrape, audit, score, generate, send, track.

**Status:** Operational. Leads are being collected, audited, scored, emailed, and tracked.

### Phase 2 -- Automation

- Scheduled pipeline runs (cron or task scheduler)
- Automated follow-up email sequences
- Response detection and notification
- PostgreSQL migration for concurrent access

### Phase 3 -- Scaling

- Multi-source scraping (additional directories beyond Hotfrog)
- Web dashboard for pipeline monitoring
- Multi-user support with role-based access
- SaaS packaging for commercial deployment
- Advanced analytics on conversion patterns across industries

---

## 11. Monitoring and Metrics

The system tracks a complete conversion funnel:

| Metric | Source | Purpose |
|---|---|---|
| Leads collected | Lead count by source | Measure ingestion volume |
| Audit completion rate | Completed vs failed audits | Monitor API reliability |
| Score distribution | HOT/WARM/COLD/SKIP counts | Assess lead quality |
| Emails sent | Daily send count | Track outreach volume |
| Reply rate | Positive replies / emails sent | Measure email effectiveness |
| Meeting rate | Meetings booked / positive replies | Measure follow-through |
| Close rate | Clients closed / meetings held | Measure conversion |
| Revenue | Sum of deal values | Measure business impact |

The `conversion-stats` CLI command provides a snapshot of the current funnel state.

---

## 12. Security Practices

- All API keys and credentials stored in `.env`, never in source code
- `.env` excluded from version control via `.gitignore`
- Database file excluded from version control
- SMTP authentication over TLS
- No credentials logged to console or log files
- Environment variables validated at startup before operations begin

---

## 13. Design Principles

This system was built with a few non-negotiable principles:

**Quality over quantity.** It is better to send five well-researched, personalized emails than fifty generic ones. The scoring engine exists specifically to filter out leads that are not worth contacting.

**Honesty over persuasion.** The outreach emails reference real problems found during real audits. They do not exaggerate, invent issues, or use fear tactics. If a website scores well, the system does not email them.

**Resilience over perfection.** Every external dependency (Gemini API, PageSpeed API, SMTP relay) has a fallback path. The system degrades gracefully rather than crashing when something external is unavailable.

**Transparency over cleverness.** Every action is logged. Every lead has a traceable history. Every email sent is recorded with its content and timestamp. If something goes wrong, you can trace exactly what happened and why.

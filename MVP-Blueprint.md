# AI Lead Intelligence System -- MVP Blueprint

---

## 1. What the MVP Is For

The MVP is not the final product. It is the minimum working version that answers one question: can this pipeline turn raw directory data into a sent email that sounds like a human wrote it?

Everything in the MVP exists to validate that question. If the answer is yes, the architecture is proven and the system can be extended. If the answer is no, the MVP tells you exactly where the chain breaks.

**What success looks like at MVP stage:**

- At least one lead source can be scraped or imported reliably
- Website audits produce accurate, usable data
- AI-generated outreach emails reference real audit findings and read naturally
- The full pipeline runs end-to-end without manual intervention between stages
- Leads, audits, and emails are stored in a structured database with export capability

**What the MVP deliberately does not include:**

- No web dashboard or GUI. Everything runs through the command line.
- No automated scheduling. You trigger each run manually.
- No multi-user support. Single operator, single machine.
- No advanced analytics. The conversion tracking columns exist, but reporting is basic.

The MVP is allowed to be rough. It is not allowed to be broken.

---

## 2. What Got Built

The original blueprint outlined a phased approach. Here is what actually exists in the working system today, mapped against those plans.

### Planned vs Delivered

| Planned Feature | Status | Implementation Notes |
|---|---|---|
| Scrape 1-2 directory sources | Delivered | Hotfrog scraper built; CSV import and manual entry added later |
| Extract business contact data | Delivered | Name, URL, phone, email, industry, location |
| Performance score | Delivered | Google PageSpeed Insights API integration |
| Mobile friendliness check | Delivered | Extracted from Lighthouse mobile audit |
| Basic SEO detection | Delivered | SEO score, meta tags, title, Open Graph, favicon |
| Generate cold email drafts | Delivered | Gemini AI with deterministic fallback |
| Summarize website problems | Delivered | AI summary stored per outreach record |
| Store leads in database | Delivered | SQLAlchemy + SQLite with full schema |
| Export CSV | Delivered | Pending outreach exported to CSV |
| Basic CLI control | Delivered | 20+ commands covering every pipeline stage |
| Automated email sending | Delivered | SMTP via Brevo (was originally listed as "later phase") |
| Lead scoring | Delivered | Deterministic weighted scoring (was originally "later phase") |
| Conversion tracking | Delivered | Full funnel: sent, replied, met, closed, deal value |
| Audit HTML reports | Delivered | Professional reports with inline CSS |

Several features that were originally planned for later phases ended up in the MVP because the pipeline needed them to be genuinely useful. Lead scoring without email sending, for example, produces data but no outcomes. So the email sender was built early.

---

## 3. Architecture as Built

```
Lead Ingestion
  |-- Hotfrog scraper (scraper/hotfrog_scraper.py)
  |-- CSV bulk import (utils/csv_importer.py)
  |-- Manual CLI entry (main.py add-lead command)
  |-- Test data generator (scraper/test_lead_generator.py)
      |
      v
SQLite Database (data/leadgen.db)
  |-- Leads table
  |-- Audits table
  |-- Outreach table
      |
      v
Website Audit (audit/)
  |-- PageSpeed Insights API call
  |-- Website content analysis (SSL, meta tags, load time)
  |-- Raw data storage for later reference
      |
      v
Lead Scoring (audit/lead_scorer.py)
  |-- Weighted formula across audit metrics
  |-- HOT / WARM / COLD / SKIP classification
      |
      v
Email Generation (ai/)
  |-- Gemini 2.0 Flash prompt with business + audit data
  |-- Deterministic fallback template if AI unavailable
  |-- Industry-aware language and possessive handling
      |
      v
Email Delivery (outreach/email_sender.py)
  |-- SMTP via Brevo relay
  |-- Rate-limited sending with daily cap
  |-- Per-email send tracking
      |
      v
Conversion Tracking
  |-- Reply, meeting, close, deal value columns
  |-- Funnel reporting via CLI
```

---

## 4. Technology Choices and Why

| Decision | Choice | Reasoning |
|---|---|---|
| Database | SQLite | Zero-config, file-based, no server needed. SQLAlchemy ORM makes migration to PostgreSQL a one-line change when needed. |
| AI Model | Gemini 2.0 Flash | Fast, cost-effective, good at following structured prompts. Free tier available for MVP validation. |
| AI SDK | `google-genai` | Current generation SDK. The older `google-generativeai` package is deprecated. |
| SMTP | Brevo relay | Established deliverability reputation. Free tier sufficient for MVP volume. Avoids Gmail sending limits. |
| Email pacing | 8-minute delay, 30/day cap | Prevents spam classification. Mimics human sending patterns. |
| Scoring | Deterministic formula | Reproducible, debuggable, no training data needed. ML scoring is a Phase 2 consideration. |
| Fallback emails | Template engine | Pipeline never stalls on AI unavailability. Audit data drives the template directly. |

---

## 5. Database Schema (Actual)

### Leads

Stores every business the system knows about, regardless of source.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Auto-increment primary key |
| business_name | String(255) | Required |
| website_url | String(500) | Required, unique (used for deduplication) |
| phone | String(50) | Optional |
| email | String(255) | Optional |
| industry | String(100) | Optional |
| location | String(255) | Optional |
| source | String(100) | Origin: hotfrog, csv_import, manual_add, test_generator |
| created_at | DateTime | Defaults to insertion time |

### Audits

One audit record per website analysis run. A lead can have multiple audits if re-audited.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Auto-increment primary key |
| lead_id | Integer | Foreign key to leads |
| performance_score | Integer | Lighthouse performance, 0-100 |
| seo_score | Integer | Lighthouse SEO, 0-100 |
| accessibility_score | Integer | Lighthouse accessibility, 0-100 |
| mobile_friendly | Boolean | Viewport and responsive checks |
| major_issues | JSON | List of problem descriptions |
| raw_data | JSON | Complete PageSpeed API response |
| audit_timestamp | DateTime | When the audit executed |
| audit_status | String | completed, failed, or skipped |
| error_message | Text | Error details if status is failed |

### Outreach

One record per generated email. Tracks the full lifecycle from creation through conversion.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Auto-increment primary key |
| lead_id | Integer | Foreign key to leads |
| subject_line | String(255) | Email subject |
| email_body | Text | Complete email content |
| ai_summary | Text | AI analysis of the lead's website |
| qualification_score | Integer | Priority score, 0-100 |
| sent_at | DateTime | Null until sent |
| positive_reply | Boolean | Updated manually when reply arrives |
| meeting_booked | Boolean | Updated when meeting is scheduled |
| meeting_date | DateTime | Date of the meeting |
| client_closed | Boolean | Updated when deal closes |
| deal_value | Float | Revenue from the closed deal |
| outcome_notes | Text | Free-text notes |
| created_at | DateTime | Record creation time |

---

## 6. Project Structure (Actual)

```
leadgen-ai/
|-- main.py                   CLI entry point
|-- requirements.txt          Python dependencies
|-- GUIDE.md                  Operational documentation
|
|-- config/
|   |-- settings.py           Environment loading and Config class
|   |-- .env                  Credentials and settings (not in git)
|   |-- .env.example          Template for new installations
|
|-- database/
|   |-- models.py             Lead, Audit, Outreach, SystemLog models
|   |-- connection.py         Engine creation and session management
|   |-- repository.py         LeadRepository, AuditRepository, OutreachRepository
|
|-- scraper/
|   |-- base_scraper.py       Abstract interface
|   |-- hotfrog_scraper.py    Hotfrog directory scraper
|   |-- parser_utils.py       HTML parsing helpers
|   |-- test_lead_generator.py  Synthetic data for testing
|
|-- audit/
|   |-- pagespeed_audit.py    PageSpeed Insights API client
|   |-- website_analyzer.py   HTML content analysis
|   |-- lead_scorer.py        Weighted scoring and classification
|   |-- report_generator.py   Terminal display and HTML export
|
|-- ai/
|   |-- gemini_client.py      Gemini API client
|   |-- prompts.py            Prompt templates
|   |-- outreach_generator.py Email generation with fallback
|
|-- pipeline/
|   |-- orchestrator.py       Multi-stage coordinator
|
|-- outreach/
|   |-- email_sender.py       SMTP delivery
|
|-- utils/
|   |-- csv_importer.py       CSV import with validation
|
|-- data/                     Database, reports, sample files
|-- exports/                  CSV output
|-- logs/                     Application logs
```

---

## 7. Error Handling

The system was built with the assumption that external services will fail. The question is not whether PageSpeed will return an error or Gemini will hit a quota limit. The question is what happens when they do.

**Scraping failures:** Invalid listings are skipped. Duplicate URLs are detected and logged. Network timeouts trigger a skip, not a crash.

**Audit failures:** If PageSpeed returns an error or the target website is unreachable, the audit is saved with status `failed` and an error message. The pipeline moves to the next lead.

**AI failures:** If Gemini is unavailable (quota exhaustion is the most common cause), the fallback template engine takes over. The generated email uses real audit data and follows the same tone guidelines. The pipeline does not stall.

**Email failures:** If SMTP delivery fails for a specific email, the error is logged and `sent_at` remains null. The email can be retried later.

**Database errors:** SQLAlchemy's session scope context manager handles commit and rollback automatically. If an operation fails mid-transaction, changes are rolled back.

---

## 8. Rate Limiting and Pacing

| Operation | Default Delay | Configurable Via |
|---|---|---|
| Scraping requests | 5 seconds between requests | `SCRAPER_DELAY_SECONDS` |
| Email sending | 8 minutes between sends | `EMAIL_DELAY_MINUTES` |
| Daily email cap | 30 emails per day | `MAX_DAILY_EMAILS` |
| Daily lead cap | 50 leads per day | `MAX_DAILY_LEADS` |

These defaults are conservative by design. The goal is to avoid triggering spam filters, IP blocks, or API rate limits. They can be adjusted in the `.env` file, but loosening them carries risk.

---

## 9. Development Timeline (What Actually Happened)

| Phase | What Was Built |
|---|---|
| Week 1 | Project structure, configuration system, database models, scraper framework, CLI entry point |
| Week 2 | PageSpeed audit integration, website analyzer, lead scorer, Gemini client, outreach generator, pipeline orchestrator |
| Post-MVP additions | Email sender (SMTP via Brevo), CSV import, manual lead entry, audit HTML reports, conversion tracking, Gemini SDK migration |

The original blueprint estimated four weeks. The core pipeline was functional in two. The additional features (email sending, reporting, CSV import) were built as operational needs emerged.

---

## 10. What Comes Next

The MVP has answered its central question: the pipeline works. Leads go in, personalized emails come out, and every step is logged and traceable.

**Phase 2 priorities:**

- Scheduled runs via cron so the pipeline operates without manual triggers
- Follow-up email sequences for leads that do not reply
- Response detection (monitoring the inbox for replies)
- PostgreSQL migration for multi-user and concurrent access

**Phase 3 considerations:**

- Additional lead sources beyond Hotfrog
- Web dashboard for non-technical users
- Conversion analytics across industries and scoring bands
- SaaS packaging if the system proves commercially viable

---

## 11. What the MVP Proved

The system can take a business name and website URL, analyze the site for real technical problems, and produce an email that sounds like someone actually sat down and looked at the website. That is the entire thesis of this project, and it works.

The emails are not perfect. The scoring could be more nuanced. The scraper covers one directory. But the pipeline is end-to-end functional, every component has error handling, and the whole thing runs from a single command line.

That is what an MVP is supposed to do. Not impress anyone with polish. Prove that the idea works.

# LeadGen AI — The Human Guide

> *This system finds businesses with bad websites, figures out exactly what's wrong, and writes them an email that sounds like a real person noticed.*

This isn't a manual. It's a walkthrough of how this thing actually works, what each part does in plain English, and how to use it without shooting yourself in the foot.

---

## What This System Actually Does

In one sentence: **It finds small businesses with weak websites, audits them, scores how bad the problems are, writes a personalized cold email explaining what you found, and tracks whether they replied.**

The pipeline has four stages. Each one feeds the next:

```
Find leads → Audit their websites → Score how urgent the problems are → Write the email
```

Every stage can run alone or as part of the full chain. You're in control of when each piece fires.

---

## Project Structure — What Lives Where

```
leadgen-ai/
│
├── main.py                  ← The front door. Every command starts here.
│
├── config/
│   ├── settings.py          ← All configuration in one place
│   └── .env                 ← Your API keys, SMTP creds, business info (NEVER commit this)
│
├── database/
│   ├── models.py            ← What the database tables look like (Lead, Audit, Outreach, SystemLog)
│   ├── connection.py        ← Database session management
│   └── repository.py        ← Clean functions to read/write data (no raw SQL anywhere)
│
├── scraper/
│   ├── base_scraper.py      ← Shared scraping logic (rate limiting, headers, retries)
│   ├── hotfrog_scraper.py   ← Scrapes Hotfrog business directory
│   ├── parser_utils.py      ← Cleans up scraped data (phone formats, URL normalization)
│   └── test_lead_generator.py ← Generates fake sample leads for safe testing
│
├── audit/
│   ├── pagespeed_audit.py   ← Talks to Google PageSpeed Insights API
│   ├── website_analyzer.py  ← Combines PageSpeed + SSL + HTTP + meta tags into one report
│   └── lead_scorer.py       ← Deterministic scoring: HOT / WARM / COLD / SKIP
│
├── ai/
│   ├── gemini_client.py     ← Gemini API wrapper (retries, rate limits, quota detection)
│   ├── prompts.py           ← Structured prompts that force consistent AI output
│   └── outreach_generator.py ← The brain — combines everything into a personalized email
│
├── pipeline/
│   └── orchestrator.py      ← Runs audit → score → generate → export in sequence
│
├── data/                    ← SQLite database lives here (auto-created)
├── exports/                 ← CSV exports land here
├── logs/                    ← Everything gets logged here
├── output/                  ← Misc output files
└── requirements.txt         ← Python dependencies
```

---

## The Four Modules — In Human Terms

### 1. Scraper — Finding the Leads

**What it does:** Finds small businesses with websites. Right now it pulls from Hotfrog (a business directory). There's also a test generator that creates fake leads so you can test the pipeline safely.

**Key files:**
- `scraper/test_lead_generator.py` — Creates sample leads with fake but realistic data (restaurants, law firms, dental offices). Each gets a plausible name, website, phone, location, and industry. Perfect for testing without touching real businesses.
- `scraper/hotfrog_scraper.py` — Scrapes real leads from Hotfrog. Set location and industry category. Respects rate limits so you don't get blocked.

**When to use what:**
- Building/testing something? → `test-scraper` (always safe)
- Ready for real data? → `scrape` with a small limit first

---

### 2. Audit — Understanding Their Website

**What it does:** Takes a lead's website URL and runs it through four checks:

| Check | What It Measures | Source |
|-------|-----------------|--------|
| **PageSpeed Insights** | Performance, SEO, accessibility scores (0-100) | Google's own API |
| **SSL Check** | Does the site show "Secure" or "Not Secure"? | Direct socket connection |
| **HTTP Health** | Is the site reachable? How fast does it load? Any redirects? | Direct HTTP request |
| **Meta Tags** | Does it have a title? Description? Mobile viewport? Social sharing tags? Favicon? | HTML parsing |

All four results merge into one audit report and get saved to the database.

**Key files:**
- `audit/pagespeed_audit.py` — Calls Google PageSpeed API. Handles rate limits (429 errors) gracefully — if the API is exhausted, it returns `None` instead of crashing, and the rest of the audit continues with what it has.
- `audit/website_analyzer.py` — The aggregation layer. Runs all four checks, combines results, saves to database. Even if PageSpeed fails, you still get SSL, load time, and meta tag data.
- `audit/lead_scorer.py` — **This is deterministic. No AI involved.** Purely math-based scoring:

**How Scoring Works:**

| Factor | Weight | How It's Measured |
|--------|--------|-------------------|
| Performance | 25% | PageSpeed performance score |
| SEO | 20% | PageSpeed SEO score |
| Accessibility | 15% | PageSpeed accessibility score |
| Mobile | 15% | Has viewport meta tag? (0 or 100) |
| SSL | 10% | Valid certificate? (0 or 100) |
| Meta Quality | 10% | Title + description + viewport + OG tags + favicon (20 pts each) |
| Load Speed | 5% | Under 1s = 100, over 5s = 0, linear in between |

The weighted composite gives you a number 0-100. Then it classifies:

| Score | Priority | What It Means |
|-------|----------|---------------|
| 0-49 | 🔴 HOT | Terrible website. They're losing customers right now. Highest conversion chance. |
| 50-69 | 🟡 WARM | Weak website. Clear problems. Good opportunity to help. |
| 70-84 | 🔵 COLD | Decent website. Minor issues. Lower urgency. |
| 85-100 | ⚪ SKIP | Good website. Don't waste an email — they don't need you. |

*Exception: If a COLD lead has 3+ critical issues, it gets bumped to WARM. Numbers don't tell the whole story sometimes.*

---

### 3. AI Layer — Writing the Email

**What it does:** Takes the audit data, the score, and the lead's info — then writes a personalized email that sounds like a real freelancer noticed their site and is offering help.

**Two paths to get there:**

1. **Gemini AI (primary)** — Sends a structured prompt to Google's Gemini 2.0 Flash model. The prompt forces JSON output with a subject line and email body. The AI writes something unique every time.

2. **Fallback Template (backup)** — If Gemini's daily quota is exhausted, rate-limited, or returns garbage, the system writes the email itself using a hand-tuned template. No AI needed. Still personalized — it uses the lead's name, location, industry, and specific audit problems.

**The fallback isn't a dumbed-down version.** It translates raw technical issues into business language:

| Technical Issue | What The Email Says |
|----------------|---------------------|
| Missing meta description | "Google has no description to show for your site in search results" |
| No page title | "Your website doesn't have a proper page title for search engines" |
| No SSL | "Visitors see a 'Not Secure' warning when they visit your site" |
| Load time > 3s | "Your website takes X seconds to load — most visitors leave after 3" |
| No OG tags | "When someone shares your site on social media, it shows up without an image or preview" |
| Not mobile friendly | "Your site may not display correctly on phones" |

**Email Psychology Built In:**

Every email — whether AI-written or template — includes these elements:

- **Authority hint:** "I run performance audits for small local businesses" — not bragging, just existence proof
- **Competitive fear:** "visitors tend to check the next option instead — and in [their city], there's always a next option"
- **Social proof:** "I've helped similar local businesses improve their load speed and search visibility"
- **Low-pressure close:** "If you're open to it, I can walk you through what I found"
- **Safety valve:** "P.S. If this isn't relevant, just ignore this — no follow-ups"

**Key files:**
- `ai/gemini_client.py` — Wraps the Gemini API. Handles retries, rate limits, and daily quota detection. If the error says "PerDay", it stops immediately instead of wasting 3 minutes on retries.
- `ai/prompts.py` — Structured prompts that force consistent output. Two main prompts: one for the audit summary (understanding the problem), one for the email (writing the pitch).
- `ai/outreach_generator.py` — **The brain of the system.** Loads lead + audit from database, scores it, gets AI summary (or builds fallback), generates email (or builds fallback), saves everything. This is where all the pieces come together.

---

### 4. Pipeline — Running Everything Together

**What it does:** Coordinates the stages in order. You can run them individually or let the orchestrator chain them.

**Key file:** `pipeline/orchestrator.py`

The orchestrator runs: `Audit → Score → Generate → Export`

It also exports results to CSV files in the `exports/` folder for easy review.

---

## How to Operate It — Day-to-Day Commands

Every command runs from the project root:

```bash
cd /path/to/leadgen-ai
source venv/bin/activate
python main.py <command>
```

### Getting Started (First Time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your environment file
# Edit config/.env with your real API keys

# 3. Generate test leads
python main.py test-scraper
# → Say 'y' to save them

# 4. Run the full pipeline on test data
python main.py run-all 5 5
# → Audits 5 leads, generates 5 emails
```

### Daily Workflow

| What You Want | Command | What Happens |
|---------------|---------|--------------|
| Add test leads | `python main.py test-scraper` | Creates 5 sample leads, asks to save |
| Scrape real leads | `python main.py scrape 20 us restaurant` | Scrapes 20 restaurants in US from Hotfrog |
| Audit websites | `python main.py audit 10` | Audits up to 10 unaudited leads |
| Score leads | `python main.py score` | Scores all audited leads, shows HOT/WARM/COLD |
| Generate emails | `python main.py generate 5` | Writes outreach emails for 5 scored leads |
| Run everything | `python main.py run-all 10 10` | Full pipeline: audit 10 → score all → generate 10 → export |
| Preview an email | `python main.py preview 6` | Shows the email for lead #6 (generates if needed) |
| Check stats | `python main.py stats` | Database overview: total leads, pending audits, emails sent |
| List leads | `python main.py list-leads 10` | Shows 10 most recent leads with audit status |
| Export to CSV | `python main.py export` | Saves pending outreach to `exports/` folder |

### Checking an Email Before Sending

```bash
python main.py preview 6
```

This shows you the full email — subject line, body, scoring breakdown, and AI summary. **Always preview before sending.** Read it out loud. If it sounds like a robot wrote it, something went wrong.

---

## Outcome Tracking — Measuring What Matters

The database tracks the full conversion funnel:

```
Email Generated → Sent → Opened → Replied → Positive Reply → Meeting Booked → Client Closed
```

**Columns in the outreach table:**

| Column | Type | What It Tracks |
|--------|------|----------------|
| `sent_at` | DateTime | When you actually sent the email |
| `opened` | Boolean | Did they open it? (requires tracking pixel — not built yet) |
| `replied` | Boolean | Did they respond at all? |
| `positive_reply` | Boolean | Was the reply interested, not just "unsubscribe"? |
| `meeting_booked` | Boolean | Did you get a call/meeting scheduled? |
| `meeting_date` | DateTime | When is the meeting? |
| `client_closed` | Boolean | Did they become a paying client? |
| `deal_value` | Float | How much revenue from this client? |
| `outcome_notes` | Text | Your notes on what happened |

**Checking your conversion stats:**

```bash
python -c "
from database.connection import Database
from database.repository import OutreachRepository
from config.settings import Config
Config.ensure_directories()
Database.initialize()
stats = OutreachRepository.get_conversion_stats()
for k, v in stats.items():
    print(f'  {k}: {v}')
"
```

**Recording outcomes (when someone replies, books, or closes):**

```python
from database.repository import OutreachRepository

# Someone replied positively
OutreachRepository.track_outcome(1, replied=True, positive_reply=True)

# Meeting booked
from datetime import datetime
OutreachRepository.track_outcome(1, meeting_booked=True, meeting_date=datetime(2026, 2, 20))

# Client closed
OutreachRepository.track_outcome(1, client_closed=True, deal_value=500.0, outcome_notes="Monthly SEO package")
```

---

## Configuration — What You Need to Set Up

Everything lives in `config/.env`. Here's what each value does:

### API Keys
| Key | What It's For | Where to Get It |
|-----|---------------|-----------------|
| `GEMINI_API_KEY` | AI email writing | [Google AI Studio](https://aistudio.google.com/) |
| `PAGESPEED_API_KEY` | Website performance audits | [Google Cloud Console](https://console.cloud.google.com/) |

### Email / SMTP (Brevo)
| Key | Value | Notes |
|-----|-------|-------|
| `SMTP_EMAIL` | Your Brevo login | The one ending in `@smtp-brevo.com` |
| `SMTP_ApiKey` | Your Brevo SMTP key | Starts with `xsmtpsib-` |
| `SMTP_HOST` | `smtp-relay.brevo.com` | Don't change this |
| `SMTP_PORT` | `587` | TLS port |

### Business Info (Shows in Emails)
| Key | What It's For |
|-----|---------------|
| `BUSINESS_NAME` | Your name/brand in email signature |
| `BUSINESS_EMAIL` | Your reply-to address |
| `BUSINESS_PHONE` | Optional — for CAN-SPAM compliance |
| `UNSUBSCRIBE_URL` | Link for opt-out (legal requirement) |

### Rate Limits
| Key | Default | What It Controls |
|-----|---------|------------------|
| `MAX_DAILY_LEADS` | 50 | Max leads scraped per day |
| `MAX_DAILY_EMAILS` | 30 | Max emails sent per day |
| `SCRAPER_DELAY_SECONDS` | 5 | Pause between scraping requests |
| `EMAIL_DELAY_MINUTES` | 8 | Pause between sending emails |

---

## How the System Handles Failure

This was designed to **never crash and lose your work.** Here's what happens when things break:

| Failure | What Happens | Your Data |
|---------|-------------|-----------|
| PageSpeed API rate-limited (429) | Skips PageSpeed, audit continues with SSL + HTTP + meta | ✅ Safe. Partial audit saved. |
| PageSpeed API key invalid | Detected at startup, skips API calls entirely | ✅ Safe. Scores default to 0. |
| Gemini daily quota exhausted | Detected instantly (no 3-minute retry stall). Falls back to template email. | ✅ Safe. Email still generated. |
| Gemini returns invalid JSON | Caught, logged, falls back to template | ✅ Safe. |
| Website unreachable | Audit records the failure, moves to next lead | ✅ Safe. Lead stays in DB for retry. |
| SSL check fails | SSL marked as invalid, audit continues | ✅ Safe. |
| Database already has the lead | Duplicate detection skips it | ✅ Safe. No duplicates. |

---

## The Database — What's In There

SQLite database at `data/leadgen.db`. Four tables:

### `leads` — Every business you've found
| Column | What It Stores |
|--------|---------------|
| `business_name` | "The Golden Spoon Diner" |
| `website_url` | "https://goldenspoon.com" (unique — no duplicates) |
| `phone`, `email` | Contact info if available |
| `industry` | "restaurant", "law firm", "dental", etc. |
| `location` | "Fullerton, CA, USA" |
| `source` | Where you found them: "hotfrog", "manual", "test_generator" |

### `audits` — What we found on their website
| Column | What It Stores |
|--------|---------------|
| `performance_score` | Google PageSpeed performance (0-100) |
| `seo_score` | Google PageSpeed SEO (0-100) |
| `accessibility_score` | Google PageSpeed accessibility (0-100) |
| `mobile_friendly` | True/False |
| `major_issues` | JSON list of specific problems found |
| `raw_data` | Full audit data (SSL, load time, meta tags, etc.) |

### `outreach` — The emails you've generated
| Column | What It Stores |
|--------|---------------|
| `subject_line` | The email subject |
| `email_body` | The full email text |
| `ai_summary` | AI's analysis of why this lead matters |
| `qualification_score` | How likely they are to need your help (0-100) |
| `sent_at` → `deal_value` | Full conversion funnel tracking |

### `system_logs` — What the system did and when
Timestamped log of every action. Useful for debugging.

---

## Common Patterns — Things You'll Actually Do

### "I want to add a real business manually"

```python
python -c "
from database.connection import Database
from database.repository import LeadRepository
from config.settings import Config
Config.ensure_directories()
Database.initialize()

LeadRepository.create(
    business_name='Cafe Milano',
    website_url='https://cafemilano.com',
    phone='555-123-4567',
    industry='restaurant',
    location='Austin, TX, USA',
    source='manual'
)
print('Done.')
"
```

Then run `python main.py preview <lead_id>` to see the email.

### "I want to re-audit a lead with fresh data"

Delete the old audit first, then re-run:

```bash
python -c "
from database.connection import Database
from database.models import Audit
from config.settings import Config
Config.ensure_directories()
Database.initialize()

with Database.session_scope() as session:
    session.query(Audit).filter(Audit.lead_id == 6).delete()
print('Audit cleared.')
"

python main.py audit 1
# → It will pick up lead #6 since it no longer has an audit
```

### "I want to regenerate an email for a lead"

Clear the old outreach record first:

```bash
python -c "
from database.connection import Database
from database.models import Outreach
from config.settings import Config
Config.ensure_directories()
Database.initialize()

with Database.session_scope() as session:
    session.query(Outreach).filter(Outreach.lead_id == 6).delete()
print('Outreach cleared.')
"

python main.py preview 6
```

### "I want to see all my HOT leads"

```bash
python main.py score
# → Shows all scored leads sorted by priority
# HOT leads appear first with full scoring breakdown
```

---

## Golden Rules

1. **Always preview before sending.** Read the email out loud. If any sentence sounds like a bot, fix the template or prompt.

2. **Start with 5-10 manual sends.** Don't automate delivery until you know the emails actually get replies. You're testing persuasion first, infrastructure second.

3. **Track everything.** When someone replies, log it. When they book a call, log it. When they close, log it. The data tells you what to change.

4. **Respect rate limits.** The defaults (50 leads/day, 30 emails/day, 8 minutes between sends) exist to keep you off spam blacklists and within API quotas. Don't crank them up.

5. **Never commit `.env`.** Your API keys and SMTP credentials are in there. The `.gitignore` already excludes it, but double-check.

6. **When Gemini quota runs out, don't panic.** The fallback template is good. It's been rewritten to sound human. Let it work. Gemini resets daily.

7. **HOT leads are your money.** A business with a 35/100 score has a terrible website and probably knows it. They're the most likely to say yes. Focus there.

8. **SKIP means skip.** If a lead scores 85+, their website is fine. Emailing them wastes your credibility and their time.

---

## Tech Stack at a Glance

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.14 | You know it. It works. |
| Database | SQLite via SQLAlchemy | Zero setup, file-based, plenty fast for thousands of leads |
| AI | Google Gemini 2.0 Flash | Cheap, fast, good enough for email writing |
| Website Audits | Google PageSpeed Insights API | The same tool Google uses to rank websites |
| Email Sending | Brevo SMTP (not built yet) | 300 free emails/day, professional deliverability |
| Scraping | Requests + BeautifulSoup | Lightweight, no browser needed for directories |

---

## What's Built vs. What's Next

| Feature | Status |
|---------|--------|
| Lead scraping (test data) | ✅ Working |
| Lead scraping (Hotfrog) | ✅ Built, needs refinement for current site structure |
| Website auditing (PageSpeed + SSL + HTTP + meta) | ✅ Working |
| Deterministic lead scoring | ✅ Working |
| AI email generation (Gemini) | ✅ Working (quota-dependent) |
| Fallback email template | ✅ Working — humanized, psychology-tuned |
| Conversion funnel tracking | ✅ Database ready |
| CSV export | ✅ Working |
| Email preview | ✅ Working |
| SMTP email sending | 🔜 Config ready, module not built yet |
| Open/click tracking | 🔜 Planned |
| Additional scraper sources | 🔜 Planned |
| Dashboard / web UI | 🔜 Planned |

---

*Built by hand. Tested on real businesses. Designed to sound like a person, not a machine.*

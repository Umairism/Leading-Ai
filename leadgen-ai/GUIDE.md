# LeadGen AI — How This Thing Works

> Find businesses with bad websites. Figure out what's wrong. Write them an email about it. That's the whole pitch.

This isn't your typical documentation. I'm going to walk you through how this system actually works, what each piece does, and how to use it day-to-day without breaking anything. Think of it as the guide I wish I had when I started building this.

---

## The Big Picture

The system has four stages. Each one feeds into the next:

```
Find leads → Audit their websites → Score the opportunity → Write the email
```

You can run them individually or chain the whole thing together with one command. Either way, you stay in control.

The philosophy behind it is straightforward — a generic "hey, need a website?" email gets deleted in two seconds. But if you can say "hey, your site takes 6 seconds to load on mobile and you're missing a meta description, which means Google isn't showing your business properly in search" — suddenly they're paying attention. That's what this tool automates.

---

## Where Everything Lives

Here's the project structure. I'll explain what each folder does below, but this gives you the bird's eye view:

```
leadgen-ai/
│
├── main.py                  ← front door — every command goes through here
│
├── config/
│   ├── settings.py          ← reads your .env file, exposes everything as Config.WHATEVER
│   └── .env                 ← API keys, SMTP passwords, business info (gitignored, obviously)
│
├── database/
│   ├── models.py            ← table definitions: Lead, Audit, Outreach, SystemLog
│   ├── connection.py        ← database session management
│   └── repository.py        ← all database reads & writes go through here (no raw SQL)
│
├── scraper/
│   ├── base_scraper.py      ← shared scraping logic — rate limiting, headers, retries
│   ├── hotfrog_scraper.py   ← pulls real businesses from Hotfrog directory
│   ├── parser_utils.py      ← cleans up scraped data (phone formatting, URL normalization)
│   └── test_lead_generator.py  ← generates fake but realistic leads for safe testing
│
├── audit/
│   ├── pagespeed_audit.py   ← talks to Google PageSpeed Insights API
│   ├── website_analyzer.py  ← combines PageSpeed + SSL + HTTP + meta tags into one report
│   ├── lead_scorer.py       ← pure math scoring — no AI, just weighted factors
│   └── report_generator.py  ← formats audit data into readable reports and HTML exports
│
├── ai/
│   ├── gemini_client.py     ← Gemini API wrapper with retry logic and quota detection
│   ├── prompts.py           ← structured prompts that force consistent output format
│   └── outreach_generator.py ← the brain — pulls everything together into a ready-to-send email
│
├── pipeline/
│   └── orchestrator.py      ← chains audit → score → generate → export in sequence
│
├── outreach/
│   └── email_sender.py      ← SMTP sending with rate limiting and batch support
│
├── utils/
│   └── csv_importer.py      ← bulk lead import from CSV files
│
├── data/                    ← SQLite DB, PageSpeed cache, HTML audit reports
├── exports/                 ← CSV exports land here
├── logs/                    ← timestamped logs of everything
└── requirements.txt
```

---

## The Four Stages — What Each One Actually Does

### Stage 1: Getting Leads Into the System

Before the system can do anything useful, it needs businesses to work with. There are several ways to feed them in.

**Test data** — Run `python main.py test-scraper` and you'll get 5 fake but realistic leads (restaurants, law firms, dental offices — that sort of thing). Great for testing the pipeline without touching real businesses. It'll ask if you want to save them to the database.

**Hotfrog scraper** — `python main.py scrape 20 us restaurant` hits the Hotfrog business directory and pulls back real businesses. Set the count, country, and category. It respects rate limits so you won't get IP-banned. Fair warning though — Hotfrog's site structure changes sometimes, so this may need tweaking.

**Manual add** — Got a specific business in mind? Add it directly:

```bash
python main.py add-lead "Bella's Bakery" "bellasbakery.com" --industry restaurant --location "Portland, OR" --email hello@bellasbakery.com
```

The system auto-adds `https://` if you leave it off the URL.

**CSV import** — This is probably the most practical option for bulk work. Prepare a CSV with columns like `business_name`, `website_url`, `email`, `phone`, `industry`, `location` and import it:

```bash
python main.py import-csv my_leads.csv
```

If your location has a comma (like "Islamabad, Pakistan"), wrap it in quotes in the CSV. The system also has a template generator if you want a starting point:

```bash
python main.py import-csv --template
```

Duplicates are detected by URL — the system won't add the same website twice.

---

### Stage 2: Auditing Their Website

This is where it gets interesting. The audit module takes a lead's website and runs it through four separate checks:

**PageSpeed Insights** — Calls Google's actual PageSpeed API. You get performance, SEO, and accessibility scores on a 0-100 scale. This is the same data Google uses internally, so it's credible.

**SSL check** — Does the site show "Secure" or "Not Secure" in the browser? A surprising number of small business sites still don't have proper SSL certificates.

**HTTP health** — Is the site even reachable? How fast does it load? Are there redirect chains? This is a basic "can a customer actually visit your site" check.

**Meta tag analysis** — Does the page have a title tag? A meta description? A mobile viewport? Open Graph tags for social sharing? A favicon? These are the little things that affect how a site shows up in Google and on social media, and most small businesses miss at least a couple.

All four results get merged into one audit record and saved to the database. Even if one check fails (say, PageSpeed is rate-limited), the others still run and save what they found. Nothing gets lost.

Run it with:

```bash
python main.py audit 10    # audit up to 10 unaudited leads
```

Want to see the results? Two options:

```bash
python main.py audit-report       # print all audit reports in the terminal
python main.py audit-report 3     # just lead #3
python main.py audit-export       # export everything as professional HTML files
python main.py audit-export 3     # just one
```

The HTML reports end up in `data/reports/` and look pretty decent — you could even share them with a prospect as a "free audit."

---

### Stage 3: Scoring the Lead

Once a lead has been audited, the scorer crunches the numbers and classifies it. This part is 100% deterministic — no AI, no randomness, just weighted math.

Here's what it considers and how much each factor weighs:

| Factor | Weight | How it's measured |
|--------|--------|-------------------|
| Performance | 25% | PageSpeed performance score (0-100) |
| SEO | 20% | PageSpeed SEO score (0-100) |
| Accessibility | 15% | PageSpeed accessibility score (0-100) |
| Mobile | 15% | Does it have a viewport meta tag? Binary — 0 or 100 |
| SSL | 10% | Valid certificate? Also binary |
| Meta quality | 10% | Title + description + viewport + OG tags + favicon (20 pts each) |
| Load speed | 5% | Under 1 second = 100, over 5 seconds = 0, linear in between |

The weighted total gives a composite score. Then it slots into a bucket:

| Composite | Priority | Translation |
|-----------|----------|-------------|
| 0–49 | HOT | This website is actively costing them business. They'll feel the pain. |
| 50–69 | WARM | Obvious problems. A good candidate for outreach. |
| 70–84 | COLD | Site's okay. Some issues, but probably not urgent to them. |
| 85–100 | SKIP | Their site is solid. Emailing them would just be noise. |

One wrinkle: if a COLD lead has 3 or more critical issues flagged, it bumps up to WARM automatically. I added that because sometimes the numbers look okay in aggregate but the individual issues are still bad enough to care about.

Run scoring with:

```bash
python main.py score
```

It'll show you all scored leads sorted by priority, with HOT leads at the top.

---

### Stage 4: Writing the Outreach Email

This is the part that turns audit data into an actual email someone might respond to.

There are two paths here, and the system picks the right one automatically:

**Path A — Gemini AI.** The system sends a structured prompt to Google Gemini 2.0 Flash with the lead's info, their audit results, and their score. The prompt is engineered to return JSON with a subject line and email body. Every email comes out different because the AI adapts to the specific issues it sees.

**Path B — Fallback template.** If Gemini's daily free quota is exhausted (or it returns garbage, or the API is down), the system writes the email itself using a hand-crafted template. It's not some "Dear Sir/Madam" placeholder — it pulls the lead's real name, location, industry, and specific audit problems into a template that's been tuned to sound like a person wrote it.

The fallback translates technical jargon into language a business owner actually understands:

- "Missing meta description" becomes → *"Google has no description to show for your site in search results"*
- "No SSL" becomes → *"Visitors see a 'Not Secure' warning when they visit your site"*
- "Load time > 3s" becomes → *"Your website takes X seconds to load — most visitors leave after 3"*
- "No OG tags" becomes → *"When someone shares your site on social media, it shows up without an image or preview"*

Both paths — AI and fallback — bake in some email psychology. There's an authority hint ("I run performance audits for local businesses"), a bit of competitive pressure ("in your city, there's always a next option"), social proof, a low-pressure ask, and a P.S. that says "if this isn't relevant, just ignore it — no follow-ups." That last part matters more than you'd think. It lowers the threat level and makes people more willing to respond.

Generate emails with:

```bash
python main.py generate 5     # write emails for 5 leads
```

Always preview before doing anything with them:

```bash
python main.py preview 3      # see the full email for lead #3
```

Read it out loud. Seriously. If any sentence sounds like a machine wrote it, either the prompt needs work or the fallback template needs a tweak. The whole point of this system is that the outreach doesn't *feel* automated.

---

## Running the Full Pipeline

Don't want to run each stage by hand? Chain them all together:

```bash
python main.py run-all 10 5
```

That runs: audit up to 10 leads → score everything → generate up to 5 emails → export results to CSV.

The export lands in the `exports/` folder as a timestamped CSV file. It's useful for reviewing what the system produced or importing into another tool.

---

## Day-to-Day Workflow

Here's what a typical session looks like once you're set up:

```bash
# check where things stand
python main.py stats

# import some new leads
python main.py import-csv new_batch.csv

# run the pipeline
python main.py run-all

# review the emails it generated
python main.py preview 12
python main.py preview 13

# happy with them? send a small batch
python main.py send 3

# or send one specific email
python main.py send-one 7

# check conversion stats over time
python main.py conversion-stats
```

Start small. Send 5-10 emails manually first and see what kind of replies you get. Once you're happy with the tone and the response rate, you can start scaling up.

---

## Tracking Results

The database tracks the full lifecycle of every lead, from first contact to closed deal:

```
Email Generated → Sent → Opened → Replied → Positive Reply → Meeting Booked → Client Closed
```

The outreach table has fields for all of this — `sent_at`, `replied`, `positive_reply`, `meeting_booked`, `meeting_date`, `client_closed`, `deal_value`, and `outcome_notes`. Most of this you'll update manually (or through your own scripts) as deals progress.

To record outcomes:

```python
from database.connection import Database
from database.repository import OutreachRepository
from config.settings import Config

Config.ensure_directories()
Database.initialize()

# someone replied positively
OutreachRepository.track_outcome(1, replied=True, positive_reply=True)

# meeting booked
from datetime import datetime
OutreachRepository.track_outcome(1, meeting_booked=True, meeting_date=datetime(2026, 3, 1))

# deal closed
OutreachRepository.track_outcome(1, client_closed=True, deal_value=500.0, outcome_notes="Monthly SEO retainer")
```

Check your funnel at any time:

```bash
python main.py conversion-stats
```

---

## Configuration Reference

All settings live in `config/.env`. Here's the full list:

### API Keys

| Key | What for | Where to get it |
|-----|----------|-----------------|
| `GEMINI_API_KEY` | AI-powered email writing | [Google AI Studio](https://aistudio.google.com/) — free tier is enough |
| `PAGESPEED_API_KEY` | Website performance audits | [Google Cloud Console](https://console.cloud.google.com/) — also free |

### Email / SMTP

| Key | Example | Notes |
|-----|---------|-------|
| `SMTP_EMAIL` | your-email@gmail.com | Or your Brevo login |
| `SMTP_PASSWORD` | app-password-here | Gmail app password or Brevo SMTP key |
| `SMTP_HOST` | smtp.gmail.com | Or `smtp-relay.brevo.com` for Brevo |
| `SMTP_PORT` | 587 | TLS port, usually 587 |

### Your Business Info (shows up in emails)

| Key | What it does |
|-----|--------------|
| `BUSINESS_NAME` | Your name or brand — goes in the email signature |
| `BUSINESS_EMAIL` | Reply-to address |
| `BUSINESS_PHONE` | Optional but good for CAN-SPAM compliance |
| `UNSUBSCRIBE_URL` | Legal requirement for commercial emails |

### Rate Limits

| Key | Default | What it controls |
|-----|---------|------------------|
| `MAX_DAILY_LEADS` | 50 | How many leads you can scrape per day |
| `MAX_DAILY_EMAILS` | 30 | How many outreach emails to send per day |
| `SCRAPER_DELAY_SECONDS` | 5 | Pause between scraping requests |
| `EMAIL_DELAY_MINUTES` | 8 | Gap between sending emails |

### Gemini Settings

| Key | Default | What it does |
|-----|---------|--------------|
| `GEMINI_MAX_TOKENS` | 1000 | Max output length per generation |
| `GEMINI_TEMPERATURE` | 0.7 | Higher = more creative, lower = more predictable |
| `GEMINI_DAILY_BUDGET` | 20 | API cost ceiling (mostly irrelevant on free tier) |

---

## How It Handles Failures

I built this to be resilient. Here's what happens when things go sideways:

**PageSpeed API gets rate-limited (429 error)** — The audit skips PageSpeed but still runs SSL, HTTP health, and meta tag checks. You get a partial audit, which is better than nothing. The lead stays in queue so you can re-audit later when the quota resets.

**PageSpeed API key is invalid** — Detected at startup. It won't waste time trying API calls that'll fail. Scores based on whatever non-PageSpeed data is available.

**Gemini hits its daily quota** — The system catches this immediately (it checks the error message for "PerDay" instead of burning through 3 minutes of retries). Switches to the fallback email template on the spot. Your leads still get an email.

**Gemini returns broken JSON** — Caught, logged, falls back to the template. Happens occasionally; no big deal.

**A website is completely unreachable** — The audit records the failure and moves on. The lead stays in the database, so you can try again tomorrow.

**You try to import a duplicate lead** — Duplicate detection is built into every import path. Matching is by URL. No doubles in the database.

In every case, the system saves whatever progress it made before the failure. You never lose work.

---

## The Database

It's a single SQLite file at `data/leadgen.db`. There are four tables:

**leads** — Every business in the system. Stores name, website URL (unique — no dupes), phone, email, industry, location, and where you found them (source).

**audits** — One per lead. Performance, SEO, and accessibility scores from PageSpeed, plus all the raw data (SSL status, load time, meta tags, the full report). The `major_issues` column holds a JSON list of specific problems.

**outreach** — Generated emails. Subject line, body, AI summary, qualification score. Also tracks the full conversion funnel: sent, opened, replied, meeting booked, client closed, deal value.

**system_logs** — Timestamped record of every action. Mostly useful for debugging.

If you ever want to start completely fresh, just delete `data/leadgen.db` and run any command — the system rebuilds the database automatically.

---

## Common Things You'll Want to Do

### Re-audit a lead

Delete the old audit record, then run audits again. The system will pick up any lead that's missing an audit:

```python
python -c "
from database.connection import Database
from database.models import Audit
from config.settings import Config
Config.ensure_directories()
Database.initialize()
with Database.session_scope() as session:
    session.query(Audit).filter(Audit.lead_id == 3).delete()
print('Audit cleared for lead #3')
"
```

Then: `python main.py audit 1`

### Regenerate an email for a lead

Same idea — delete the old outreach record:

```python
python -c "
from database.connection import Database
from database.models import Outreach
from config.settings import Config
Config.ensure_directories()
Database.initialize()
with Database.session_scope() as session:
    session.query(Outreach).filter(Outreach.lead_id == 3).delete()
print('Outreach cleared for lead #3')
"
```

Then: `python main.py preview 3`

### See all your HOT leads

```bash
python main.py score
```

Prints all scored leads sorted by priority. HOT leads show up first with a full breakdown of their scores.

### Export audit reports as HTML

```bash
python main.py audit-export
```

Creates a nice-looking HTML report for every lead and saves them to `data/reports/`. You could share these with prospects as a free site audit — good way to start a conversation.

---

## Rules I Follow (and You Should Too)

**Preview every email before you send it.** Read it out loud. If any part of it sounds like it was written by a machine, go fix the prompt or the template. The whole value of this tool dies the moment a recipient thinks "ah, another bot email."

**Start with small batches.** Don't blast 50 people on day one. Send 5, see what happens, adjust the tone, send 5 more. You're testing the message, not just the infrastructure.

**Log everything.** When someone replies, update the tracking. When they book a meeting, log it. When they close, log the deal value. Three months from now you'll be glad you have the data.

**Respect the rate limits.** The defaults are there to keep you off blacklists and inside API quotas. Cranking up the numbers feels productive but it's usually not.

**Don't email SKIP leads.** If someone scores 85+, their website is in good shape. Emailing them about problems they don't have wastes your credibility.

**Focus on HOT leads.** A business with a score under 50 has a genuinely bad website. They probably know something is off. They're the most likely to respond. That's where your time pays off.

**Never commit your .env file.** It's already in .gitignore, but just... double-check. API keys and passwords in a public repo is the kind of mistake that ruins a weekend.

---

## Tech Stack

Just in case you're curious about the choices:

- **Python** — because it works and I didn't want to fight a framework
- **SQLite via SQLAlchemy** — zero config, single file, plenty fast for this use case
- **Google Gemini 2.0 Flash** — inexpensive, fast, writes good enough copy for cold emails
- **Google PageSpeed Insights API** — can't argue with Google's own website analysis tool
- **Brevo SMTP** — 300 free emails/day and solid deliverability
- **Requests + BeautifulSoup** — lightweight HTTP and HTML parsing without spinning up a headless browser

---

*Built for people who'd rather spend their time closing deals than writing cold emails.*

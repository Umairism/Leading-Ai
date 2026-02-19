# LeadGen AI

Cold outreach that actually works. This tool finds small businesses with weak websites, figures out exactly what's wrong, and writes them a personalized email offering to help — all on autopilot.

I built this because I was tired of sending generic cold emails that nobody replies to. The idea is simple: if you can tell someone *specifically* what's broken on their site, they're way more likely to listen. So that's what this does.

## What it does, in short

1. You feed it business leads (scrape them, import a CSV, or add them by hand)
2. It audits each website — performance, SEO, SSL, mobile, load speed, meta tags
3. It scores each lead as HOT, WARM, COLD, or SKIP based on how bad the site is
4. It writes a personalized outreach email using Google's Gemini AI (or a solid fallback template if the API quota runs out)
5. You review, send, and track replies

The whole thing runs from the command line. No web UI, no fluff — just `python main.py run-all` and let it work.

## Getting started

You'll need Python 3.10+ and a couple of free API keys.

```bash
# clone and enter the project
cd leadgen-ai

# set up a virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

Next, set up your environment file. There's an example included:

```bash
cp config/env.example config/.env
```

Open `config/.env` in your editor and fill in your keys:

- **GEMINI_API_KEY** — grab one from [Google AI Studio](https://aistudio.google.com/) (free tier works fine)
- **PAGESPEED_API_KEY** — get it from [Google Cloud Console](https://console.cloud.google.com/) (also free)
- **SMTP credentials** — if you want to send emails through Brevo or Gmail

That's it. You're ready to go.

## Quick test run

Try this to make sure everything's wired up:

```bash
# generate some fake leads to play with
python main.py test-scraper
# say 'y' when it asks to save them

# run the full pipeline on those test leads
python main.py run-all

# check what happened
python main.py stats
```

You should see leads get audited, scored, and emails generated. If Gemini's quota is up, the fallback template kicks in — it still does a solid job.

## All the commands

Here's every command the CLI supports. They're grouped by what stage of the pipeline they touch.

### Feeding in leads

```bash
python main.py test-scraper                        # 5 fake leads for testing
python main.py scrape 20 us restaurant             # scrape 20 US restaurants from Hotfrog
python main.py add-lead "Joe's Diner" "joesdiner.com" --industry restaurant --location "Austin, TX"
python main.py import-csv leads.csv                # bulk import from a CSV file
python main.py import-csv --template               # generate a blank CSV template to fill in
```

### Running the pipeline

```bash
python main.py audit 10          # audit up to 10 unaudited websites
python main.py score             # score all audited leads
python main.py generate 5        # write outreach emails for 5 scored leads
python main.py run-all 10 5      # do it all: audit 10, score, generate 5, export
```

### Reviewing output

```bash
python main.py stats             # quick overview — total leads, pending audits, emails sent
python main.py list-leads 15     # show the last 15 leads and their audit status
python main.py preview 3         # preview the outreach email for lead #3
python main.py audit-report      # print audit reports for all leads
python main.py audit-report 3    # print audit report for a specific lead
python main.py audit-export      # export all audits as HTML files
python main.py export            # export pending outreach to CSV
python main.py conversion-stats  # see your reply/meeting/close rates
```

### Sending emails

```bash
python main.py test-smtp         # test your SMTP connection (doesn't send anything)
python main.py send 5            # send up to 5 pending outreach emails
python main.py send-one 12       # send one specific outreach by its ID
```

## Project layout

```
leadgen-ai/
├── main.py              — CLI entry point, every command starts here
├── config/
│   ├── settings.py      — all config in one place
│   └── .env             — your API keys and SMTP creds (never commit this)
├── scraper/             — lead collection (Hotfrog scraper + test data generator)
├── audit/               — website analysis (PageSpeed, SSL, HTTP checks, meta tags, scoring)
├── ai/                  — Gemini integration and prompt templates
├── pipeline/            — orchestrator that chains everything together
├── outreach/            — email sending via SMTP
├── database/            — SQLAlchemy models and repository layer
├── utils/               — CSV importer and helpers
├── data/                — SQLite database + cached audit data + HTML reports
├── exports/             — CSV exports go here
└── logs/                — application logs
```

## How scoring works

The scorer is deterministic — no AI involved, just math. It looks at performance, SEO, accessibility, mobile-friendliness, SSL, meta tag quality, and load speed. Each factor has a weight, and the composite score maps to a priority:

| Score range | Priority | What it means |
|-------------|----------|---------------|
| 0–49        | HOT      | Terrible site. They need help yesterday. Best conversion odds. |
| 50–69       | WARM     | Weak site with clear problems. Good opportunity. |
| 70–84       | COLD     | Decent site. Minor stuff. Lower urgency. |
| 85–100      | SKIP     | Their site's fine. Don't waste their time or yours. |

If a COLD lead has 3 or more critical issues, it gets bumped up to WARM. Sometimes the numbers don't tell the whole story.

## Configuration

Everything's controlled through `config/.env`. The defaults are sane — you really only need to set your API keys and email credentials to get going. Rate limits, Gemini settings, and business info for email signatures are all configurable too. Check `config/env.example` for the full list with comments.

## A few things worth knowing

- **Rate limits exist for a reason.** 50 leads/day and 30 emails/day with 8-minute gaps between sends. Don't crank these up unless you enjoy landing on spam blacklists.
- **Always preview before sending.** Run `python main.py preview <id>` and read the email out loud. If it sounds robotic, something's off.
- **The fallback template is actually good.** When Gemini's daily quota runs out, emails still get written using a hand-tuned template that pulls in the lead's real audit issues. It's not a downgrade.
- **Your .env file is gitignored**, but double-check anyway. Your API keys and SMTP passwords are in there.
- **The database is just a SQLite file** at `data/leadgen.db`. Delete it and re-run to start fresh. The system recreates it automatically.

## Tech stack

| What | Why |
|------|-----|
| Python 3 | It works, it's readable, it gets out of the way |
| SQLite + SQLAlchemy | Zero setup, file-based, handles thousands of leads without breaking a sweat |
| Google Gemini 2.0 Flash | Cheap, fast, writes decent cold emails |
| Google PageSpeed Insights API | Same tool Google uses to evaluate sites — hard to argue with that |
| Brevo SMTP | 300 free emails/day with good deliverability |
| Requests + BeautifulSoup | Lightweight scraping, no headless browser needed |

## License

Do whatever you want with it. Just don't be a jerk about it.

# LeadGen AI - MVP System

An automated lead intelligence system that scrapes business directories, audits websites, and generates AI-powered personalized outreach.

## Quick Start

### 1. Install Dependencies

```bash
cd leadgen-ai
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

```bash
cp config/.env.example config/.env
```

Edit `config/.env` and add your API keys:
- Gemini API Key (get from https://makersuite.google.com/)
- PageSpeed API Key (get from https://console.cloud.google.com/)
- Email credentials

### 3. Test the System

```bash
python main.py test-scraper
```

This will scrape 5 sample leads and show you the results.

## CLI Commands

### Scraping

```bash
# Scrape 20 US restaurants (default)
python main.py scrape

# Scrape 50 UK law firms
python main.py scrape 50 uk "law firm"

# Scrape 30 Australian dental clinics
python main.py scrape 30 au dental
```

### Database Management

```bash
# Show database statistics
python main.py stats

# List recent leads
python main.py list-leads 20
```

## Project Structure

```
leadgen-ai/
├── config/          # Configuration and environment variables
├── database/        # Database models and data access
├── scraper/         # Web scraping modules
├── audit/           # Website audit tools (coming in Week 2)
├── ai/              # Gemini AI integration (coming in Week 2)
├── pipeline/        # Workflow orchestration (coming in Week 3)
├── outreach/        # Email automation (coming in Week 3)
├── output/          # Export and reporting (coming in Week 4)
├── logs/            # Application logs
├── data/            # SQLite database
└── main.py          # CLI entry point
```

## Current Status

**Week 1: Foundation** ✓
- [x] Project setup
- [x] Database models
- [x] Configuration system
- [x] Base scraper architecture
- [x] Hotfrog scraper implementation

**Week 2: Intelligence** (Next)
- [ ] PageSpeed API integration
- [ ] Website audit module
- [ ] Gemini AI client
- [ ] Prompt engineering

**Week 3: Outreach**
- [ ] Lead scoring
- [ ] Email generation
- [ ] SMTP integration

**Week 4: Pipeline**
- [ ] Full orchestration
- [ ] Error handling
- [ ] CSV export

## Target Industries

- Restaurants
- Law firms
- Real estate agencies
- Dental/medical clinics
- Local service businesses

## Supported Locations

- USA (us)
- UK (uk)
- Canada (ca)
- Australia (au)

## Notes

- Rate limited to 50 leads/day (configurable)
- Respects robots.txt
- Includes retry logic and error handling
- All scraped data stored in SQLite database

## Next Steps

After Week 1 completion:
1. Get API keys for Gemini and PageSpeed
2. Test scraper with multiple categories
3. Verify lead quality
4. Move to Week 2: Website audit integration

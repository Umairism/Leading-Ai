"""
Main CLI entry point for LeadGen AI system.
Provides command-line interface for running the pipeline.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Config

# Ensure all directories exist before anything else
Config.ensure_directories()

# Setup logging (after directories are created)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / 'leadgen.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Now import database (which may auto-initialize)
from database.connection import Database
from database.repository import LeadRepository, AuditRepository, OutreachRepository
from scraper.hotfrog_scraper import HotfrogScraper
from scraper.test_lead_generator import TestLeadGenerator

# Initialize database explicitly
Database.initialize()

# Lazy imports for heavy modules (only loaded when needed)
def _get_orchestrator():
    from pipeline.orchestrator import PipelineOrchestrator
    return PipelineOrchestrator()

def _get_analyzer():
    from audit.website_analyzer import WebsiteAnalyzer
    return WebsiteAnalyzer()

def _get_scorer():
    from audit.lead_scorer import LeadScorer
    return LeadScorer


def test_scraper():
    """Test the scraper functionality."""
    logger.info("=== Testing Lead Generation (Sample Data) ===")
    
    # For MVP testing, use sample data instead of live scraping
    # This lets us test the full pipeline without website dependencies
    logger.info("Generating 5 sample leads for testing...")
    leads = TestLeadGenerator.generate(count=5)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Generated {len(leads)} test leads")
    logger.info(f"{'='*60}\n")
    
    for i, lead in enumerate(leads, 1):
        logger.info(f"\nLead {i}:")
        logger.info(f"  Business: {lead.get('business_name')}")
        logger.info(f"  Website: {lead.get('website_url')}")
        logger.info(f"  Phone: {lead.get('phone', 'N/A')}")
        logger.info(f"  Location: {lead.get('location', 'N/A')}")
        logger.info(f"  Industry: {lead.get('industry', 'N/A')}")
    
    return leads


def test_real_scraper():
    """Test the real Hotfrog scraper (use with caution)."""
    logger.info("=== Testing Hotfrog Scraper (Live) ===")
    logger.warning("Note: This scraper needs adjustment for current Hotfrog structure")
    
    scraper = HotfrogScraper()
    
    # Test with small limit
    leads = scraper.scrape(limit=5, location="us", category="restaurant")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Scraped {len(leads)} leads")
    logger.info(f"{'='*60}\n")
    
    for i, lead in enumerate(leads, 1):
        logger.info(f"\nLead {i}:")
        logger.info(f"  Business: {lead.get('business_name')}")
        logger.info(f"  Website: {lead.get('website_url')}")
        logger.info(f"  Phone: {lead.get('phone', 'N/A')}")
        logger.info(f"  Location: {lead.get('location', 'N/A')}")
    
    return leads


def save_leads_to_db(leads):
    """Save scraped leads to database."""
    logger.info("\n=== Saving Leads to Database ===")
    
    saved_count = 0
    duplicate_count = 0
    
    for lead in leads:
        website = lead.get('website_url')
        
        # Check if lead already exists
        if LeadRepository.exists(website):
            logger.info(f"Duplicate lead (skipping): {lead.get('business_name')}")
            duplicate_count += 1
            continue
        
        # Create new lead
        try:
            LeadRepository.create(
                business_name=lead.get('business_name'),
                website_url=website,
                phone=lead.get('phone'),
                email=lead.get('email'),
                industry=lead.get('industry'),
                location=lead.get('location'),
                source=lead.get('source')
            )
            saved_count += 1
            logger.info(f"Saved: {lead.get('business_name')}")
        except Exception as e:
            logger.error(f"Error saving lead {lead.get('business_name')}: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Saved: {saved_count} leads")
    logger.info(f"Duplicates: {duplicate_count} leads")
    logger.info(f"{'='*60}\n")


def show_stats():
    """Show database statistics."""
    logger.info("\n=== Database Statistics ===")
    
    all_leads = LeadRepository.get_all()
    leads_today = LeadRepository.count_today()
    leads_without_audit = LeadRepository.get_without_audit()
    pending_outreach = OutreachRepository.get_pending()
    sent_today = OutreachRepository.count_sent_today()
    
    logger.info(f"Total leads:         {len(all_leads)}")
    logger.info(f"Leads today:         {leads_today}")
    logger.info(f"Pending audit:       {len(leads_without_audit)}")
    logger.info(f"Pending outreach:    {len(pending_outreach)}")
    logger.info(f"Emails sent today:   {sent_today}")


def run_audit(limit: int = 10):
    """Run website audits on unaudited leads."""
    orchestrator = _get_orchestrator()
    results = orchestrator.run_audits(limit=limit)
    return results


def run_score(limit: int = 20):
    """Score audited leads and display results."""
    orchestrator = _get_orchestrator()
    results = orchestrator.run_scoring(limit=limit)
    
    if results:
        LeadScorer = _get_scorer()
        # Show detailed report for top lead
        top = results[0]
        audit_record = AuditRepository.get_by_lead(top['lead_id'])
        if audit_record:
            raw = audit_record.raw_data or {}
            audit_dict = {
                'performance_score': audit_record.performance_score,
                'seo_score': audit_record.seo_score,
                'accessibility_score': audit_record.accessibility_score,
                'mobile_friendly': audit_record.mobile_friendly,
                'major_issues': audit_record.major_issues or [],
                'ssl_valid': raw.get('ssl_valid', False),
                'load_time_ms': raw.get('load_time_ms'),
                'has_title': raw.get('has_title', False),
                'has_meta_description': raw.get('has_meta_description', False),
                'has_viewport': raw.get('has_viewport', False),
                'has_og_tags': raw.get('has_og_tags', False),
                'has_favicon': raw.get('has_favicon', False),
            }
            scoring = LeadScorer.score(audit_dict)
            print(LeadScorer.format_report(scoring, audit_dict))
    
    return results


def run_generate(limit: int = 10):
    """Generate outreach emails for scored leads."""
    orchestrator = _get_orchestrator()
    results = orchestrator.run_generation(limit=limit)
    return results


def run_pipeline(audit_limit: int = 10, generate_limit: int = 10):
    """Run the full pipeline: audit → score → generate → export."""
    orchestrator = _get_orchestrator()
    summary = orchestrator.run_all(
        audit_limit=audit_limit,
        generate_limit=generate_limit,
        export=True
    )
    return summary


def run_export():
    """Export pending outreach to CSV."""
    orchestrator = _get_orchestrator()
    filepath = orchestrator.export_results()
    if filepath:
        logger.info(f"Export saved to: {filepath}")
    else:
        logger.info("Nothing to export.")


def preview_outreach(lead_id: int):
    """Preview outreach for a specific lead."""
    from ai.outreach_generator import OutreachGenerator
    generator = OutreachGenerator()
    output = generator.preview(lead_id)
    if output:
        print(output)
    else:
        logger.error(f"Could not generate preview for lead {lead_id}")


def main():
    """Main CLI entry point."""
    logger.info("\n" + "="*60)
    logger.info("LeadGen AI - MVP System")
    logger.info("="*60 + "\n")
    
    # Check if .env file exists
    env_file = Path(__file__).parent / 'config' / '.env'
    if not env_file.exists():
        logger.warning("⚠️  No .env file found!")
        logger.info("Creating .env from template...")
        
        example_file = Path(__file__).parent / 'config' / '.env.example'
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            logger.info(f"✓ Created {env_file}")
            logger.info("⚠️  Please edit config/.env with your API keys before running!")
            return
    
    # Parse command
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == 'test-scraper':
            leads = test_scraper()
            if leads and input("\nSave these leads to database? (y/n): ").lower() == 'y':
                save_leads_to_db(leads)
        
        elif command == 'test-real-scraper':
            leads = test_real_scraper()
            if leads and input("\nSave these leads to database? (y/n): ").lower() == 'y':
                save_leads_to_db(leads)
        
        elif command == 'scrape':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            location = sys.argv[3] if len(sys.argv) > 3 else "us"
            category = sys.argv[4] if len(sys.argv) > 4 else "restaurant"
            
            scraper = HotfrogScraper()
            leads = scraper.scrape(limit=limit, location=location, category=category)
            save_leads_to_db(leads)
        
        elif command == 'stats':
            show_stats()
        
        elif command == 'list-leads':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            leads = LeadRepository.get_all(limit=limit)
            
            logger.info(f"\n=== Recent Leads (Last {limit}) ===\n")
            for lead in leads:
                # Check audit status
                audit = AuditRepository.get_by_lead(lead.id)
                audit_status = f"✓ Audited (Perf: {audit.performance_score})" if audit else "⏳ Pending audit"
                
                logger.info(f"{lead.business_name}")
                logger.info(f"  Website:  {lead.website_url}")
                logger.info(f"  Industry: {lead.industry or 'N/A'}")
                logger.info(f"  Source:   {lead.source}")
                logger.info(f"  Audit:    {audit_status}")
                logger.info(f"  Created:  {lead.created_at}\n")
        
        elif command == 'audit':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            run_audit(limit)
        
        elif command == 'score':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            run_score(limit)
        
        elif command == 'generate':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            run_generate(limit)
        
        elif command == 'run-all':
            audit_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            gen_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            run_pipeline(audit_limit, gen_limit)
        
        elif command == 'export':
            run_export()
        
        elif command == 'preview':
            if len(sys.argv) < 3:
                logger.error("Usage: python main.py preview <lead_id>")
                return
            lead_id = int(sys.argv[2])
            preview_outreach(lead_id)
        
        else:
            print_usage()
    
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


def print_usage():
    """Print CLI usage information."""
    usage = """
Usage: python main.py <command> [options]

── Data Collection ──
  test-scraper              Generate 5 sample leads for testing
  scrape [limit] [loc] [cat]  Scrape leads from Hotfrog

── Intelligence Layer ──
  audit [limit]             Run website audits on unaudited leads
  score [limit]             Score audited leads (HOT/WARM/COLD/SKIP)
  generate [limit]          Generate outreach emails via AI

── Full Pipeline ──
  run-all [audit_limit] [gen_limit]
                            Run everything: audit → score → generate → export

── Output & Review ──
  stats                     Show database statistics
  list-leads [limit]        List recent leads with audit status
  export                    Export pending outreach to CSV
  preview <lead_id>         Preview outreach for a specific lead

Examples:
  python main.py test-scraper        # Create sample leads
  python main.py audit 5             # Audit 5 websites
  python main.py score               # Score all audited leads
  python main.py generate 3          # Generate 3 outreach emails
  python main.py run-all 5 5         # Full pipeline (5 audits, 5 emails)
  python main.py preview 1           # Preview outreach for lead #1
  python main.py export              # Export results to CSV

Setup:
  1. pip install -r requirements.txt
  2. Copy config/.env.example to config/.env
  3. Add your API keys to config/.env
  4. python main.py test-scraper   → then audit → score → generate
"""
    print(usage)


if __name__ == '__main__':
    main()

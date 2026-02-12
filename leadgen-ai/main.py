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
from database.connection import Database
from database.repository import LeadRepository
from scraper.hotfrog_scraper import HotfrogScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / 'leadgen.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def test_scraper():
    """Test the scraper functionality."""
    logger.info("=== Testing Hotfrog Scraper ===")
    
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
    
    logger.info(f"Total leads: {len(all_leads)}")
    logger.info(f"Leads today: {leads_today}")
    logger.info(f"Leads pending audit: {len(leads_without_audit)}")


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
                logger.info(f"{lead.business_name}")
                logger.info(f"  Website: {lead.website_url}")
                logger.info(f"  Source: {lead.source}")
                logger.info(f"  Created: {lead.created_at}\n")
        
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

Commands:
  test-scraper              Test scraper with 5 sample leads
  scrape [limit] [location] [category]
                            Scrape leads (default: 20 leads from US restaurants)
  stats                     Show database statistics
  list-leads [limit]        List recent leads (default: 10)

Examples:
  python main.py test-scraper
  python main.py scrape 50 us restaurant
  python main.py scrape 30 uk "law firm"
  python main.py stats
  python main.py list-leads 20

Setup:
  1. Install dependencies: pip install -r requirements.txt
  2. Copy config/.env.example to config/.env
  3. Add your API keys to config/.env
  4. Run: python main.py test-scraper
"""
    print(usage)


if __name__ == '__main__':
    main()

"""
Base scraper abstract class.
Defines the interface that all scrapers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import time
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config.settings import Config

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.delay = Config.SCRAPER_DELAY_SECONDS
        self.max_retries = 3
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the scraping source."""
        pass
    
    @abstractmethod
    def scrape(self, limit: int = None) -> List[Dict]:
        """
        Main scraping method to be implemented by subclasses.
        
        Args:
            limit: Maximum number of leads to scrape
            
        Returns:
            List of lead dictionaries with standard fields
        """
        pass
    
    def fetch_page(self, url: str, retries: int = 0) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a webpage with retry logic.
        
        Args:
            url: URL to fetch
            retries: Current retry attempt
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Add delay to be respectful
            time.sleep(self.delay)
            
            return BeautifulSoup(response.content, 'lxml')
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            
            if retries < self.max_retries:
                wait_time = (retries + 1) * 5
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.fetch_page(url, retries + 1)
            
            return None
    
    def validate_lead(self, lead: Dict) -> bool:
        """
        Validate lead data before returning.
        
        Args:
            lead: Lead dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['business_name', 'website_url']
        
        # Check required fields exist and are not empty
        for field in required_fields:
            if not lead.get(field):
                logger.warning(f"Lead missing required field: {field}")
                return False
        
        # Basic URL validation
        website = lead.get('website_url', '')
        if not website.startswith(('http://', 'https://')):
            lead['website_url'] = f"https://{website}"
        
        return True
    
    def normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize phone number format.
        
        Args:
            phone: Raw phone string
            
        Returns:
            Normalized phone or None
        """
        if not phone:
            return None
        
        # Remove common separators and spaces
        cleaned = ''.join(c for c in phone if c.isdigit() or c in ['+', '-', '(', ')'])
        return cleaned if cleaned else None
    
    def normalize_email(self, email: str) -> Optional[str]:
        """
        Normalize email format.
        
        Args:
            email: Raw email string
            
        Returns:
            Normalized email or None
        """
        if not email:
            return None
        
        email = email.strip().lower()
        
        # Basic email validation
        if '@' in email and '.' in email.split('@')[1]:
            return email
        
        return None
    
    def extract_text(self, element, default: str = '') -> str:
        """
        Safely extract text from BeautifulSoup element.
        
        Args:
            element: BeautifulSoup element
            default: Default value if extraction fails
            
        Returns:
            Extracted text or default
        """
        if element:
            return element.get_text(strip=True)
        return default
    
    def log_scrape_stats(self, total: int, valid: int, source: str):
        """
        Log scraping statistics.
        
        Args:
            total: Total leads found
            valid: Valid leads after validation
            source: Source name
        """
        logger.info(f"Scrape complete - Source: {source}")
        logger.info(f"Total found: {total}, Valid: {valid}, Filtered: {total - valid}")

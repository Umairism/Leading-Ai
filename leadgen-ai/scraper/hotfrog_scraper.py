"""
Hotfrog business directory scraper.
Extracts business leads from Hotfrog.com listings.
"""

from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, quote

from scraper.base_scraper import BaseScraper
from scraper.parser_utils import (
    extract_business_name, extract_website, extract_phone,
    extract_email, extract_location, is_valid_business_website
)

logger = logging.getLogger(__name__)


class HotfrogScraper(BaseScraper):
    """Scraper for Hotfrog business directory."""
    
    BASE_URL = "https://www.hotfrog.com"
    
    def __init__(self):
        super().__init__()
        self.source_name = "hotfrog"
    
    def get_source_name(self) -> str:
        """Return the source name."""
        return self.source_name
    
    def build_search_url(self, location: str = "us", category: str = "", page: int = 1) -> str:
        """
        Build Hotfrog search URL.
        
        Args:
            location: Country/region code (us, uk, ca, au)
            category: Business category/industry
            page: Page number
            
        Returns:
            Complete search URL
        """
        # Hotfrog URL structure: https://www.hotfrog.com/search/{location}/{category}
        
        if category:
            category_encoded = quote(category.lower().replace(' ', '-'))
            url = f"{self.BASE_URL}/search/{location.lower()}/{category_encoded}"
        else:
            url = f"{self.BASE_URL}/search/{location.lower()}"
        
        if page > 1:
            url += f"?page={page}"
        
        return url
    
    def scrape(self, limit: int = 50, location: str = "us", category: str = "restaurant") -> List[Dict]:
        """
        Scrape business leads from Hotfrog.
        
        Args:
            limit: Maximum number of leads to collect
            location: Country code (us, uk, ca, au)
            category: Business category to search
            
        Returns:
            List of lead dictionaries
        """
        logger.info(f"Starting Hotfrog scrape - Location: {location}, Category: {category}, Limit: {limit}")
        
        leads = []
        page = 1
        max_pages = 10  # Safety limit
        
        while len(leads) < limit and page <= max_pages:
            url = self.build_search_url(location, category, page)
            soup = self.fetch_page(url)
            
            if not soup:
                logger.warning(f"Failed to fetch page {page}")
                break
            
            # Extract business listings from page
            page_leads = self._extract_businesses(soup)
            
            if not page_leads:
                logger.info(f"No more businesses found on page {page}")
                break
            
            # Add valid leads
            for lead in page_leads:
                if len(leads) >= limit:
                    break
                
                lead['source'] = self.source_name
                lead['location'] = location.upper()
                lead['industry'] = category
                
                if self.validate_lead(lead):
                    leads.append(lead)
            
            logger.info(f"Page {page}: Found {len(page_leads)} businesses, {len(leads)} total valid")
            page += 1
        
        self.log_scrape_stats(len(leads), len(leads), self.source_name)
        return leads
    
    def _extract_businesses(self, soup) -> List[Dict]:
        """
        Extract business data from Hotfrog page.
        
        Args:
            soup: BeautifulSoup page object
            
        Returns:
            List of business dictionaries
        """
        businesses = []
        
        # Hotfrog uses h3 tags for business names
        h3_tags = soup.find_all('h3')
        
        if not h3_tags:
            logger.warning("No business listings found (no h3 tags)")
            return businesses
        
        logger.debug(f"Found {len(h3_tags)} potential business listings")
        
        for h3 in h3_tags:
            try:
                business = self._parse_listing_v2(h3)
                if business:
                    businesses.append(business)
            except Exception as e:
                logger.error(f"Error parsing listing: {e}")
                continue
        
        return businesses
    
    def _parse_listing(self, listing) -> Optional[Dict]:
        """
        Parse individual business listing.
        
        Args:
            listing: BeautifulSoup element for single business
            
        Returns:
            Business dictionary or None
        """
        business = {}
        
        # Extract business name
        name_selectors = ['h2 a', 'h3 a', '.business-name', '.company-name', 'a.name']
        name_elem = None
        for selector in name_selectors:
            name_elem = listing.select_one(selector)
            if name_elem:
                break
        
        if name_elem:
            business['business_name'] = extract_business_name(name_elem)
        else:
            return None  # Business name is required
        
        # Extract website URL
        website_selectors = ['a[href*="website"]', 'a.website', '.website-link', 'a[title*="website"]']
        website_elem = None
        for selector in website_selectors:
            website_elem = listing.select_one(selector)
            if website_elem:
                break
        
        if website_elem:
            website = extract_website(website_elem, self.BASE_URL)
            if website and is_valid_business_website(website):
                business['website_url'] = website
        
        # If no website found, try to extract from business name link
        if 'website_url' not in business and name_elem:
            href = name_elem.get('href', '')
            if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                potential_url = urljoin(self.BASE_URL, href)
                # Check if this is a detail page we should visit
                if '/company/' in potential_url:
                    # Visit detail page to get website
                    detail_website = self._get_website_from_detail(potential_url)
                    if detail_website:
                        business['website_url'] = detail_website
        
        # Extract phone
        phone_elem = listing.select_one('.phone, .telephone, [itemprop="telephone"]')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            business['phone'] = self.normalize_phone(phone_text)
        
        # Extract email (less common on listing pages)
        email_elem = listing.select_one('a[href^="mailto:"]')
        if email_elem:
            email = email_elem.get('href', '').replace('mailto:', '')
            business['email'] = self.normalize_email(email)
        
        # Extract location/address
        location_selectors = ['.address', '.location', '[itemprop="address"]', '.locality']
        for selector in location_selectors:
            location_elem = listing.select_one(selector)
            if location_elem:
                business['location'] = extract_location(location_elem)
                break
        
        return business if 'website_url' in business else None
    
    def _parse_listing_v2(self, h3_tag) -> Optional[Dict]:
        """
        Parse individual business listing from h3 tag (Hotfrog 2026 structure).
        
        Args:
            h3_tag: BeautifulSoup h3 element containing business name
            
        Returns:
            Business dictionary or None
        """
        business = {}
        
        # Extract business name from h3
        business_name = h3_tag.get_text(strip=True)
        if not business_name or len(business_name) < 3:
            return None
        
        business['business_name'] = business_name
        
        # Get the row container
        container = h3_tag.find_parent('div', class_='row')
        if not container:
            container = h3_tag.find_parent('div')
        
        if not container:
            return None
        
        # Extract phone
        phone_link = container.find('a', href=lambda x: x and x.startswith('tel:'))
        if phone_link:
            phone_text = phone_link.get_text(strip=True)
            business['phone'] = self.normalize_phone(phone_text)
        
        # Extract address
        address_span = container.find('span')
        if address_span:
            address_text = address_span.get_text(strip=True)
            if address_text and 'claim this business' not in address_text.lower():
                business['location'] = address_text
        
        # Extract website URL - look for detail page link
        detail_link = container.find('a', href=lambda x: x and '/company/' in x)
        if detail_link:
            detail_url = urljoin(self.BASE_URL, detail_link.get('href'))
            # For MVP, use a placeholder website based on business name
            # In production, we'd visit the detail page
            # website = self._get_website_from_detail(detail_url)
            
            # Extract any http links in the container as potential website
            http_links = container.find_all('a', href=lambda x: x and ('http://' in x or 'https://' in x))
            for link in http_links:
                href = link.get('href')
                if is_valid_business_website(href):
                    business['website_url'] = href
                    break
            
            # If no website found, use detail page as placeholder
            if 'website_url' not in business:
                # Generate a placeholder - in real use we'd visit detail page
                # For now, skip businesses without direct website links
                return None
        
        # Must have website to be useful
        return business if 'website_url' in business else None
    
    def _get_website_from_detail(self, detail_url: str) -> Optional[str]:
        """
        Visit business detail page to extract website URL.
        
        Args:
            detail_url: URL of business detail page
            
        Returns:
            Website URL or None
        """
        try:
            soup = self.fetch_page(detail_url)
            if not soup:
                return None
            
            # Look for website link on detail page
            website_selectors = [
                'a[href*="website"]',
                'a.btn-website',
                'a[title*="Visit Website"]',
                '.website-url a'
            ]
            
            for selector in website_selectors:
                elem = soup.select_one(selector)
                if elem:
                    website = extract_website(elem, self.BASE_URL)
                    if website and is_valid_business_website(website):
                        return website
            
        except Exception as e:
            logger.error(f"Error fetching detail page {detail_url}: {e}")
        
        return None
    
    def scrape_multiple_categories(self, categories: List[str], limit_per_category: int = 20, 
                                   location: str = "us") -> List[Dict]:
        """
        Scrape multiple business categories.
        
        Args:
            categories: List of category names
            limit_per_category: Max leads per category
            location: Country code
            
        Returns:
            Combined list of leads
        """
        all_leads = []
        
        for category in categories:
            logger.info(f"Scraping category: {category}")
            leads = self.scrape(limit=limit_per_category, location=location, category=category)
            all_leads.extend(leads)
            logger.info(f"Category '{category}' complete: {len(leads)} leads")
        
        return all_leads

"""
Parsing utilities for extracting structured data from HTML.
"""

import re
from typing import Optional, List
from urllib.parse import urljoin, urlparse
import validators


def extract_business_name(element) -> Optional[str]:
    """Extract and clean business name from element."""
    if not element:
        return None
    
    name = element.get_text(strip=True)
    
    # Remove common suffixes and clean
    name = re.sub(r'\s+(LLC|Inc|Corp|Ltd|Limited)\.?$', '', name, flags=re.IGNORECASE)
    
    return name.strip() if name else None


def extract_website(element, base_url: str = '') -> Optional[str]:
    """
    Extract and validate website URL.
    
    Args:
        element: BeautifulSoup element containing URL
        base_url: Base URL for relative links
        
    Returns:
        Validated absolute URL or None
    """
    if not element:
        return None
    
    # Try to get href attribute
    url = element.get('href', '')
    
    if not url:
        # Try to extract from text
        text = element.get_text(strip=True)
        url = text
    
    # Clean URL
    url = url.strip()
    
    # Handle relative URLs
    if url and not url.startswith(('http://', 'https://')):
        if base_url:
            url = urljoin(base_url, url)
        else:
            url = f"https://{url}"
    
    # Validate URL
    if url and validators.url(url):
        return url
    
    return None


def extract_phone(text: str) -> Optional[str]:
    """
    Extract phone number from text using regex patterns.
    
    Args:
        text: Text potentially containing phone number
        
    Returns:
        Extracted phone number or None
    """
    if not text:
        return None
    
    # Common phone patterns
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-234-567-8900
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (234) 567-8900
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # 234-567-8900
        r'\+\d{10,15}',  # +12345678900
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from text.
    
    Args:
        text: Text potentially containing email
        
    Returns:
        Extracted email or None
    """
    if not text:
        return None
    
    # Email pattern
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    match = re.search(pattern, text)
    if match:
        email = match.group(0).lower()
        # Avoid common false positives
        if not email.endswith(('.png', '.jpg', '.gif')):
            return email
    
    return None


def extract_location(element) -> Optional[str]:
    """Extract location/address information."""
    if not element:
        return None
    
    location = element.get_text(strip=True)
    
    # Clean up common artifacts
    location = re.sub(r'\s+', ' ', location)
    
    return location if location else None


def extract_industry(text: str, keywords: List[str] = None) -> Optional[str]:
    """
    Extract or infer industry from text.
    
    Args:
        text: Text to analyze
        keywords: Optional list of industry keywords
        
    Returns:
        Industry classification or None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Default industry keywords
    if keywords is None:
        keywords = [
            'restaurant', 'cafe', 'food', 'dining',
            'law', 'attorney', 'legal',
            'real estate', 'property', 'realtor',
            'dental', 'dentist', 'orthodontic',
            'medical', 'clinic', 'doctor', 'health',
            'salon', 'spa', 'beauty',
            'contractor', 'construction', 'builder',
            'plumber', 'electrician', 'hvac'
        ]
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return keyword.title()
    
    return None


def clean_html_text(text: str) -> str:
    """
    Clean text extracted from HTML.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ''
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common HTML artifacts
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    
    return text.strip()


def is_valid_business_website(url: str) -> bool:
    """
    Check if URL appears to be a legitimate business website.
    
    Args:
        url: Website URL
        
    Returns:
        True if appears valid, False otherwise
    """
    if not url:
        return False
    
    # Parse URL
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except:
        return False
    
    # Exclude common non-business domains
    excluded_domains = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'google.com', 'yelp.com', 'yellowpages.com',
        'craigslist.org', 'wikipedia.org'
    ]
    
    for excluded in excluded_domains:
        if excluded in domain:
            return False
    
    return True

"""
Simple lead generator for testing the system.
Creates sample leads for development and testing.
"""

from typing import List, Dict
import random


class TestLeadGenerator:
    """Generate test leads for development."""
    
    SAMPLE_BUSINESSES = [
        {
            'business_name': 'Bella Vista Restaurant',
            'website_url': 'https://bellavistarestaurant.com',
            'phone': '555-123-4567',
            'email': 'info@bellavistarestaurant.com',
            'industry': 'restaurant',
            'location': 'New York, NY'
        },
        {
            'business_name': 'Smith & Associates Law Firm',
            'website_url': 'https://smithlawfirm.com',
            'phone': '555-234-5678',
            'email': 'contact@smithlawfirm.com',
            'industry': 'law firm',
            'location': 'Los Angeles, CA'
        },
        {
            'business_name': 'Sunrise Dental Clinic',
            'website_url': 'https://sunrisedentalclinic.com',
            'phone': '555-345-6789',
            'email': 'appointments@sunrisedentalclinic.com',
            'industry': 'dental',
            'location': 'Chicago, IL'
        },
        {
            'business_name': 'Premier Real Estate Group',
            'website_url': 'https://premierrealestategroup.com',
            'phone': '555-456-7890',
            'email': 'sales@premierrealestategroup.com',
            'industry': 'real estate',
            'location': 'Miami, FL'
        },
        {
            'business_name': 'Downtown Medical Center',
            'website_url': 'https://downtownmedicalcenter.com',
            'phone': '555-567-8901',
            'email': 'info@downtownmedicalcenter.com',
            'industry': 'medical',
            'location': 'Houston, TX'
        },
        {
            'business_name': 'The Coffee Corner Cafe',
            'website_url': 'https://coffeecornercafe.com',
            'phone': '555-678-9012',
            'email': 'hello@coffeecornercafe.com',
            'industry': 'restaurant',
            'location': 'Seattle, WA'
        },
        {
            'business_name': 'Johnson & Partners Legal Services',
            'website_url': 'https://johnsonpartnerslegal.com',
            'phone': '555-789-0123',
            'email': 'inquiries@johnsonpartnerslegal.com',
            'industry': 'law firm',
            'location': 'Boston, MA'
        },
        {
            'business_name': 'Bright Smile Orthodontics',
            'website_url': 'https://brightsmileortho.com',
            'phone': '555-890-1234',
            'email': 'reception@brightsmileortho.com',
            'industry': 'dental',
            'location': 'Austin, TX'
        },
        {
            'business_name': 'Coastal Properties Realty',
            'website_url': 'https://coastalpropertiesrealty.com',
            'phone': '555-901-2345',
            'email': 'agents@coastalpropertiesrealty.com',
            'industry': 'real estate',
            'location': 'San Diego, CA'
        },
        {
            'business_name': 'Family Health Clinic',
            'website_url': 'https://familyhealthclinic.com',
            'phone': '555-012-3456',
            'email': 'appointments@familyhealthclinic.com',
            'industry': 'medical',
            'location': 'Phoenix, AZ'
        }
    ]
    
    @classmethod
    def generate(cls, count: int = 5, source: str = 'test_generator') -> List[Dict]:
        """
        Generate test leads.
        
        Args:
            count: Number of leads to generate
            source: Source identifier
            
        Returns:
            List of lead dictionaries
        """
        leads = []
        samples = cls.SAMPLE_BUSINESSES.copy()
        random.shuffle(samples)
        
        for i, sample in enumerate(samples[:count]):
            lead = sample.copy()
            lead['source'] = source
            leads.append(lead)
        
        return leads

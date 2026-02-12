"""
Configuration management for LeadGen AI system.
Loads environment variables and provides centralized settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / 'config' / '.env')


class Config:
    """Centralized configuration class."""
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    PAGESPEED_API_KEY = os.getenv('PAGESPEED_API_KEY', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/leadgen.db')
    
    # Email Configuration
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    
    # Rate Limits
    MAX_DAILY_LEADS = int(os.getenv('MAX_DAILY_LEADS', 50))
    MAX_DAILY_EMAILS = int(os.getenv('MAX_DAILY_EMAILS', 30))
    SCRAPER_DELAY_SECONDS = int(os.getenv('SCRAPER_DELAY_SECONDS', 5))
    EMAIL_DELAY_MINUTES = int(os.getenv('EMAIL_DELAY_MINUTES', 8))
    
    # Gemini Configuration
    GEMINI_MAX_TOKENS = int(os.getenv('GEMINI_MAX_TOKENS', 1000))
    GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', 0.7))
    GEMINI_DAILY_BUDGET = float(os.getenv('GEMINI_DAILY_BUDGET', 20.0))
    
    # Business Info (for email compliance)
    BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Your Business')
    BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL', '')
    BUSINESS_PHONE = os.getenv('BUSINESS_PHONE', '')
    UNSUBSCRIBE_URL = os.getenv('UNSUBSCRIBE_URL', '')
    
    # Directories
    LOGS_DIR = BASE_DIR / 'logs'
    DATA_DIR = BASE_DIR / 'data'
    EXPORTS_DIR = BASE_DIR / 'exports'
    
    # Target Industries
    TARGET_INDUSTRIES = [
        'restaurant',
        'law firm',
        'real estate',
        'dental',
        'medical',
        'clinic'
    ]
    
    # Target Locations (for filtering)
    TARGET_COUNTRIES = ['USA', 'UK', 'Canada', 'Australia']
    
    @classmethod
    def validate(cls):
        """Validate critical configuration values."""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        
        if not cls.PAGESPEED_API_KEY:
            errors.append("PAGESPEED_API_KEY is not set")
        
        if not cls.SMTP_EMAIL or not cls.SMTP_PASSWORD:
            errors.append("Email credentials are not configured")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.EXPORTS_DIR.mkdir(exist_ok=True)


# Initialize directories on import
Config.ensure_directories()

"""
Google PageSpeed Insights API integration.
Fetches performance, SEO, accessibility, and best practices scores.
"""

import requests
import logging
import time
import json
from typing import Dict, Optional
from pathlib import Path

from config.settings import Config

logger = logging.getLogger(__name__)

# Local cache directory
CACHE_DIR = Config.DATA_DIR / 'pagespeed_cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class PageSpeedAuditor:
    """Google PageSpeed Insights API client."""
    
    API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    def __init__(self):
        self.api_key = Config.PAGESPEED_API_KEY
        self.delay = 3  # seconds between API calls
    
    def _get_cache_path(self, url: str) -> Path:
        """Generate a cache file path for a URL."""
        # Simple hash-based filename
        safe_name = url.replace('https://', '').replace('http://', '')
        safe_name = safe_name.replace('/', '_').replace('.', '_')[:80]
        return CACHE_DIR / f"{safe_name}.json"
    
    def _load_cache(self, url: str) -> Optional[Dict]:
        """Load cached result if it exists and is fresh (30 days)."""
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                import os
                # Check if cache is less than 30 days old
                age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
                if age_days < 30:
                    with open(cache_path, 'r') as f:
                        logger.info(f"Cache hit for {url} (age: {age_days:.0f} days)")
                        return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_cache(self, url: str, data: Dict):
        """Save result to cache."""
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache for {url}: {e}")
    
    def analyze(self, url: str, strategy: str = "mobile") -> Optional[Dict]:
        """
        Run PageSpeed analysis on a URL.
        
        Args:
            url: Website URL to analyze
            strategy: 'mobile' or 'desktop'
            
        Returns:
            Structured audit result dict or None on failure
        """
        # Check cache first
        cached = self._load_cache(url)
        if cached:
            return cached
        
        logger.info(f"Running PageSpeed analysis: {url} ({strategy})")
        
        params = {
            'url': url,
            'strategy': strategy,
            'category': ['performance', 'seo', 'accessibility', 'best-practices'],
        }
        
        # Only use API key if it's a real key (not placeholder)
        if self.api_key and not self.api_key.startswith('your_'):
            params['key'] = self.api_key
        
        try:
            response = requests.get(self.API_URL, params=params, timeout=60)
            
            if response.status_code == 429:
                logger.warning(f"PageSpeed API rate limited for {url}. Skipping.")
                return self._error_result(url, "Rate limited by API (quota exceeded)")
            
            if response.status_code != 200:
                logger.error(f"PageSpeed API HTTP {response.status_code} for {url}")
                return self._error_result(url, f"HTTP error: {response.status_code}")
            
            raw = response.json()
            result = self._parse_response(raw, url)
            
            # Cache successful result
            if result:
                self._save_cache(url, result)
            
            time.sleep(self.delay)
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"PageSpeed API timeout for {url}")
            return self._error_result(url, "API request timed out")
            
        except requests.exceptions.ConnectionError:
            logger.error(f"PageSpeed API connection error for {url}")
            return self._error_result(url, "Connection error")
            
        except Exception as e:
            logger.error(f"PageSpeed analysis failed for {url}: {e}")
            return self._error_result(url, str(e))
    
    def _parse_response(self, raw: Dict, url: str) -> Dict:
        """
        Parse raw PageSpeed API response into clean structure.
        
        Args:
            raw: Raw API response
            url: Original URL
            
        Returns:
            Structured result dict
        """
        lighthouse = raw.get('lighthouseResult', {})
        categories = lighthouse.get('categories', {})
        audits = lighthouse.get('audits', {})
        
        # Extract category scores (0-100)
        performance = self._score(categories.get('performance', {}))
        seo = self._score(categories.get('seo', {}))
        accessibility = self._score(categories.get('accessibility', {}))
        best_practices = self._score(categories.get('best-practices', {}))
        
        # Extract Core Web Vitals
        core_web_vitals = self._extract_cwv(audits)
        
        # Extract major issues
        issues = self._extract_issues(audits, categories)
        
        # Mobile friendliness (from viewport audit)
        viewport = audits.get('viewport', {})
        mobile_friendly = viewport.get('score', 0) == 1
        
        return {
            'url': url,
            'status': 'completed',
            'performance_score': performance,
            'seo_score': seo,
            'accessibility_score': accessibility,
            'best_practices_score': best_practices,
            'mobile_friendly': mobile_friendly,
            'core_web_vitals': core_web_vitals,
            'major_issues': issues,
            'raw_scores': {
                'performance': performance,
                'seo': seo,
                'accessibility': accessibility,
                'best_practices': best_practices,
            }
        }
    
    def _score(self, category: Dict) -> int:
        """Extract and convert score to 0-100."""
        score = category.get('score')
        if score is not None:
            return int(score * 100)
        return 0
    
    def _extract_cwv(self, audits: Dict) -> Dict:
        """Extract Core Web Vitals from audits."""
        cwv = {}
        
        # Largest Contentful Paint
        lcp = audits.get('largest-contentful-paint', {})
        if lcp:
            cwv['lcp'] = {
                'value': lcp.get('displayValue', 'N/A'),
                'score': self._score(lcp),
                'label': 'Largest Contentful Paint'
            }
        
        # First Input Delay / Interaction to Next Paint
        inp = audits.get('interaction-to-next-paint', {}) or audits.get('max-potential-fid', {})
        if inp:
            cwv['inp'] = {
                'value': inp.get('displayValue', 'N/A'),
                'score': self._score(inp),
                'label': 'Interaction to Next Paint'
            }
        
        # Cumulative Layout Shift
        cls_audit = audits.get('cumulative-layout-shift', {})
        if cls_audit:
            cwv['cls'] = {
                'value': cls_audit.get('displayValue', 'N/A'),
                'score': self._score(cls_audit),
                'label': 'Cumulative Layout Shift'
            }
        
        # First Contentful Paint
        fcp = audits.get('first-contentful-paint', {})
        if fcp:
            cwv['fcp'] = {
                'value': fcp.get('displayValue', 'N/A'),
                'score': self._score(fcp),
                'label': 'First Contentful Paint'
            }
        
        # Total Blocking Time
        tbt = audits.get('total-blocking-time', {})
        if tbt:
            cwv['tbt'] = {
                'value': tbt.get('displayValue', 'N/A'),
                'score': self._score(tbt),
                'label': 'Total Blocking Time'
            }
        
        # Speed Index
        si = audits.get('speed-index', {})
        if si:
            cwv['speed_index'] = {
                'value': si.get('displayValue', 'N/A'),
                'score': self._score(si),
                'label': 'Speed Index'
            }
        
        return cwv
    
    def _extract_issues(self, audits: Dict, categories: Dict) -> list:
        """
        Extract actionable issues that failed or need improvement.
        These become your selling points for outreach.
        """
        issues = []
        
        # Check specific high-impact audits
        checks = {
            'meta-description': 'Missing meta description',
            'document-title': 'Missing or poor page title',
            'viewport': 'Not mobile optimized (no viewport meta)',
            'image-alt': 'Images missing alt text',
            'link-text': 'Non-descriptive link text',
            'is-crawlable': 'Website blocks search engine crawling',
            'robots-txt': 'Missing or misconfigured robots.txt',
            'canonical': 'Missing canonical URL',
            'font-display': 'Font loading causes layout shift',
            'render-blocking-resources': 'Render-blocking CSS/JS slowing load',
            'uses-optimized-images': 'Unoptimized images increasing load time',
            'uses-responsive-images': 'Images not properly sized for device',
            'uses-text-compression': 'Text not compressed (missing gzip/brotli)',
            'efficient-animated-content': 'Inefficient animated content',
            'unminified-css': 'CSS files not minified',
            'unminified-javascript': 'JavaScript files not minified',
            'unused-css-rules': 'Large amount of unused CSS',
            'unused-javascript': 'Large amount of unused JavaScript',
            'uses-long-cache-ttl': 'Static assets not cached properly',
            'redirects': 'Multiple page redirects slowing load',
            'server-response-time': 'Slow server response time (TTFB)',
            'dom-size': 'Excessively large DOM size',
            'http-status-code': 'Page returns unsuccessful HTTP status',
            'hreflang': 'Missing hreflang tags for international SEO',
            'structured-data': 'Missing structured data markup',
        }
        
        for audit_key, description in checks.items():
            audit = audits.get(audit_key, {})
            score = audit.get('score')
            if score is not None and score < 0.9:  # Failed or needs improvement
                issues.append({
                    'issue': description,
                    'severity': 'critical' if score == 0 else 'warning',
                    'score': int(score * 100),
                    'details': audit.get('displayValue', '')
                })
        
        # Sort by severity (critical first)
        issues.sort(key=lambda x: (0 if x['severity'] == 'critical' else 1, x['score']))
        
        return issues
    
    def _error_result(self, url: str, error: str) -> Dict:
        """Create an error result structure."""
        return {
            'url': url,
            'status': 'failed',
            'error': error,
            'performance_score': None,
            'seo_score': None,
            'accessibility_score': None,
            'best_practices_score': None,
            'mobile_friendly': None,
            'core_web_vitals': {},
            'major_issues': [],
            'raw_scores': {}
        }

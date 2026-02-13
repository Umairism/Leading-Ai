"""
Website audit aggregation layer.
Combines PageSpeed data with additional checks into a complete audit report.
"""

import requests
import logging
import ssl
import socket
from typing import Dict, Optional
from urllib.parse import urlparse

from audit.pagespeed_audit import PageSpeedAuditor
from database.repository import AuditRepository

logger = logging.getLogger(__name__)


class WebsiteAnalyzer:
    """
    Aggregates multiple data sources into a single website audit.
    
    Combines:
    - PageSpeed Insights (performance, SEO, accessibility)
    - SSL certificate check
    - Basic HTTP health
    - Meta tag extraction
    """
    
    def __init__(self):
        self.pagespeed = PageSpeedAuditor()
    
    def full_audit(self, url: str, lead_id: int = None) -> Dict:
        """
        Run complete website audit and optionally save to database.
        
        Args:
            url: Website URL
            lead_id: Optional lead ID to associate audit with
            
        Returns:
            Complete audit result dict
        """
        logger.info(f"Starting full audit for: {url}")
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # 1. PageSpeed analysis (the heavy hitter)
        pagespeed_result = self.pagespeed.analyze(url)
        
        # 2. SSL check
        ssl_info = self._check_ssl(url)
        
        # 3. Basic HTTP health check
        http_info = self._check_http(url)
        
        # 4. Meta tag extraction
        meta_info = self._extract_meta(http_info.get('html', ''))
        
        # Combine into single audit report
        audit = self._build_report(url, pagespeed_result, ssl_info, http_info, meta_info)
        
        # Save to database if lead_id provided
        if lead_id:
            self._save_audit(lead_id, audit)
        
        logger.info(f"Audit complete for {url} - Performance: {audit['performance_score']}, SEO: {audit['seo_score']}")
        return audit
    
    def _check_ssl(self, url: str) -> Dict:
        """Check if website has valid SSL certificate."""
        result = {'has_ssl': False, 'ssl_valid': False, 'ssl_error': None}
        
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            
            if not hostname:
                return result
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    result['has_ssl'] = True
                    result['ssl_valid'] = True
                    result['ssl_issuer'] = dict(x[0] for x in cert.get('issuer', []))
                    result['ssl_expiry'] = cert.get('notAfter', '')
                    
        except ssl.SSLCertVerificationError as e:
            result['has_ssl'] = True
            result['ssl_valid'] = False
            result['ssl_error'] = str(e)
        except Exception as e:
            result['ssl_error'] = str(e)
        
        return result
    
    def _check_http(self, url: str) -> Dict:
        """Basic HTTP health check."""
        result = {
            'reachable': False,
            'status_code': None,
            'load_time_ms': None,
            'redirects': 0,
            'final_url': url,
            'html': ''
        }
        
        try:
            import time
            start = time.time()
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })
            
            elapsed = (time.time() - start) * 1000  # ms
            
            result['reachable'] = True
            result['status_code'] = response.status_code
            result['load_time_ms'] = round(elapsed)
            result['redirects'] = len(response.history)
            result['final_url'] = response.url
            result['html'] = response.text[:50000]  # Cap at 50KB
            
        except requests.exceptions.ConnectionError:
            result['error'] = 'Connection refused or DNS failure'
        except requests.exceptions.Timeout:
            result['error'] = 'Request timed out (15s)'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _extract_meta(self, html: str) -> Dict:
        """Extract important meta tags from HTML."""
        result = {
            'has_title': False,
            'title': '',
            'has_meta_description': False,
            'meta_description': '',
            'has_viewport': False,
            'has_og_tags': False,
            'has_favicon': False,
            'h1_count': 0,
        }
        
        if not html:
            return result
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Title
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                result['has_title'] = True
                result['title'] = title_tag.string.strip()[:200]
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                result['has_meta_description'] = True
                result['meta_description'] = meta_desc['content'][:300]
            
            # Viewport
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            result['has_viewport'] = viewport is not None
            
            # Open Graph tags
            og_tag = soup.find('meta', attrs={'property': lambda x: x and x.startswith('og:')})
            result['has_og_tags'] = og_tag is not None
            
            # Favicon
            favicon = soup.find('link', attrs={'rel': lambda x: x and 'icon' in str(x).lower()})
            result['has_favicon'] = favicon is not None
            
            # H1 count
            result['h1_count'] = len(soup.find_all('h1'))
            
        except Exception as e:
            logger.warning(f"Meta extraction error: {e}")
        
        return result
    
    def _build_report(self, url: str, pagespeed: Dict, ssl_info: Dict, 
                      http_info: Dict, meta_info: Dict) -> Dict:
        """Combine all data sources into unified report."""
        
        # Start with pagespeed data
        report = {
            'url': url,
            'status': pagespeed.get('status', 'failed') if pagespeed else 'failed',
            
            # Core scores from PageSpeed
            'performance_score': pagespeed.get('performance_score') if pagespeed else None,
            'seo_score': pagespeed.get('seo_score') if pagespeed else None,
            'accessibility_score': pagespeed.get('accessibility_score') if pagespeed else None,
            'best_practices_score': pagespeed.get('best_practices_score') if pagespeed else None,
            'mobile_friendly': pagespeed.get('mobile_friendly', False) if pagespeed else False,
            
            # Core Web Vitals
            'core_web_vitals': pagespeed.get('core_web_vitals', {}) if pagespeed else {},
            
            # SSL info
            'has_ssl': ssl_info.get('has_ssl', False),
            'ssl_valid': ssl_info.get('ssl_valid', False),
            
            # HTTP health
            'reachable': http_info.get('reachable', False),
            'status_code': http_info.get('status_code'),
            'load_time_ms': http_info.get('load_time_ms'),
            'redirects': http_info.get('redirects', 0),
            
            # Meta info
            'has_title': meta_info.get('has_title', False),
            'has_meta_description': meta_info.get('has_meta_description', False),
            'has_viewport': meta_info.get('has_viewport', False),
            'has_og_tags': meta_info.get('has_og_tags', False),
            'has_favicon': meta_info.get('has_favicon', False),
            'h1_count': meta_info.get('h1_count', 0),
            'title': meta_info.get('title', ''),
            
            # Combined issues
            'major_issues': pagespeed.get('major_issues', []) if pagespeed else [],
        }
        
        # Add extra issues from our own checks
        extra_issues = []
        
        if not ssl_info.get('ssl_valid'):
            extra_issues.append({
                'issue': 'SSL certificate missing or invalid',
                'severity': 'critical',
                'score': 0,
                'details': ssl_info.get('ssl_error', 'No valid SSL')
            })
        
        if not meta_info.get('has_meta_description'):
            extra_issues.append({
                'issue': 'Missing meta description',
                'severity': 'warning',
                'score': 0,
                'details': 'Search engines use this for result snippets'
            })
        
        if not meta_info.get('has_viewport'):
            extra_issues.append({
                'issue': 'Missing viewport meta tag (not mobile optimized)',
                'severity': 'critical',
                'score': 0,
                'details': 'Site will display poorly on mobile devices'
            })
        
        if meta_info.get('h1_count', 0) == 0:
            extra_issues.append({
                'issue': 'No H1 heading found',
                'severity': 'warning',
                'score': 0,
                'details': 'Bad for SEO and content structure'
            })
        elif meta_info.get('h1_count', 0) > 1:
            extra_issues.append({
                'issue': f"Multiple H1 headings found ({meta_info['h1_count']})",
                'severity': 'warning',
                'score': 30,
                'details': 'Best practice is one H1 per page'
            })
        
        if not meta_info.get('has_og_tags'):
            extra_issues.append({
                'issue': 'Missing Open Graph tags',
                'severity': 'warning',
                'score': 20,
                'details': 'Social media shares will look unprofessional'
            })
        
        if http_info.get('load_time_ms') and http_info['load_time_ms'] > 3000:
            extra_issues.append({
                'issue': f"Slow page load ({http_info['load_time_ms']}ms)",
                'severity': 'critical' if http_info['load_time_ms'] > 5000 else 'warning',
                'score': 20,
                'details': 'Users abandon sites that take over 3 seconds'
            })
        
        if http_info.get('redirects', 0) > 2:
            extra_issues.append({
                'issue': f"Too many redirects ({http_info['redirects']})",
                'severity': 'warning',
                'score': 40,
                'details': 'Each redirect adds load time'
            })
        
        # Merge issues, avoiding duplicates
        existing_descriptions = {i['issue'] for i in report['major_issues']}
        for issue in extra_issues:
            if issue['issue'] not in existing_descriptions:
                report['major_issues'].append(issue)
        
        return report
    
    def _save_audit(self, lead_id: int, audit: Dict):
        """Save audit results to database."""
        try:
            AuditRepository.create(
                lead_id=lead_id,
                performance_score=audit.get('performance_score') or 0,
                seo_score=audit.get('seo_score') or 0,
                accessibility_score=audit.get('accessibility_score') or 0,
                mobile_friendly=audit.get('mobile_friendly', False),
                major_issues=audit.get('major_issues', []),
                raw_data=audit,
                audit_status=audit.get('status', 'completed'),
                error_message=audit.get('error')
            )
            logger.info(f"Audit saved for lead_id: {lead_id}")
        except Exception as e:
            logger.error(f"Failed to save audit for lead_id {lead_id}: {e}")

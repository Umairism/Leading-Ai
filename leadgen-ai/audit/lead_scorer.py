"""
Deterministic lead scoring engine.
Assigns priority based on audit numbers, not AI opinions.
Numbers sell credibility. AI adds flavor later.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LeadScorer:
    """
    Deterministic lead scoring based on website audit data.
    
    Priority levels:
    - HOT (0-49):   Terrible website. Urgent need. High conversion potential.
    - WARM (50-69): Weak website. Clear improvement areas. Good opportunity.
    - COLD (70-84): Decent website. Minor issues. Lower urgency.
    - SKIP (85-100): Good website. Unlikely to convert. Don't waste outreach.
    """
    
    # Weights for composite score
    WEIGHTS = {
        'performance': 0.25,
        'seo': 0.20,
        'accessibility': 0.15,
        'mobile': 0.15,
        'ssl': 0.10,
        'meta_quality': 0.10,
        'load_speed': 0.05,
    }
    
    @classmethod
    def score(cls, audit: Dict) -> Dict:
        """
        Calculate deterministic lead score from audit data.
        
        Args:
            audit: Audit result dictionary from WebsiteAnalyzer
            
        Returns:
            Scoring result with composite score and priority
        """
        scores = {}
        
        # Performance score (from PageSpeed)
        scores['performance'] = audit.get('performance_score') or 0
        
        # SEO score (from PageSpeed)
        scores['seo'] = audit.get('seo_score') or 0
        
        # Accessibility score
        scores['accessibility'] = audit.get('accessibility_score') or 0
        
        # Mobile friendliness (binary → 0 or 100)
        scores['mobile'] = 100 if audit.get('mobile_friendly') else 0
        
        # SSL (binary → 0 or 100)
        scores['ssl'] = 100 if audit.get('ssl_valid') else 0
        
        # Meta quality (composite of meta checks)
        meta_score = 0
        meta_checks = ['has_title', 'has_meta_description', 'has_viewport', 'has_og_tags', 'has_favicon']
        for check in meta_checks:
            if audit.get(check):
                meta_score += 20  # 5 checks × 20 = 100
        scores['meta_quality'] = meta_score
        
        # Load speed (convert ms to score: <1000ms=100, >5000ms=0)
        load_ms = audit.get('load_time_ms')
        if load_ms:
            if load_ms <= 1000:
                scores['load_speed'] = 100
            elif load_ms >= 5000:
                scores['load_speed'] = 0
            else:
                scores['load_speed'] = int(100 - ((load_ms - 1000) / 4000) * 100)
        else:
            scores['load_speed'] = 50  # Unknown defaults to middle
        
        # Calculate weighted composite
        composite = sum(
            scores[key] * cls.WEIGHTS[key]
            for key in cls.WEIGHTS
        )
        composite = round(composite)
        
        # Determine priority
        priority = cls._classify(composite)
        
        # Count critical issues
        issues = audit.get('major_issues', [])
        critical_count = sum(1 for i in issues if i.get('severity') == 'critical')
        warning_count = sum(1 for i in issues if i.get('severity') == 'warning')
        
        # Boost priority if many critical issues (even if scores are mediocre)
        if critical_count >= 3 and priority == 'COLD':
            priority = 'WARM'
        if critical_count >= 5:
            priority = 'HOT'
        
        # Determine best service to pitch
        service_angle = cls._recommend_service(scores, audit)
        
        result = {
            'composite_score': composite,
            'priority': priority,
            'individual_scores': scores,
            'critical_issues': critical_count,
            'warning_issues': warning_count,
            'total_issues': len(issues),
            'recommended_service': service_angle,
            'qualification_score': cls._qualification_score(composite, critical_count),
        }
        
        logger.info(f"Lead scored: {composite}/100 → {priority} | Service: {service_angle}")
        return result
    
    @classmethod
    def _classify(cls, score: int) -> str:
        """Classify lead priority from composite score."""
        if score < 50:
            return 'HOT'
        elif score < 70:
            return 'WARM'
        elif score < 85:
            return 'COLD'
        else:
            return 'SKIP'
    
    @classmethod
    def _qualification_score(cls, composite: int, critical_count: int) -> int:
        """
        Generate outreach qualification score (0-100).
        Higher = more worth contacting.
        Inverse of website quality + issue severity.
        """
        # Invert: bad websites = high qualification
        base = 100 - composite
        
        # Boost for critical issues
        boost = min(critical_count * 5, 25)
        
        return min(base + boost, 100)
    
    @classmethod
    def _recommend_service(cls, scores: Dict, audit: Dict) -> str:
        """
        Determine which service to pitch based on weakest area.
        
        Returns the service angle that addresses the worst problem.
        Businesses respond to specific pain, not generic offers.
        """
        # Find weakest category
        pitch_map = {
            'performance': {
                'service': 'Performance Optimization',
                'pitch': 'Your website loads slowly, causing visitors to leave before seeing your services.'
            },
            'seo': {
                'service': 'SEO Improvement',
                'pitch': 'Your website is nearly invisible in search results. Competitors are getting your potential customers.'
            },
            'mobile': {
                'service': 'Mobile Responsiveness',
                'pitch': 'Over 60% of web traffic is mobile. Your website doesn\'t work properly on phones.'
            },
            'accessibility': {
                'service': 'Accessibility & UX Fix',
                'pitch': 'Your website has accessibility issues that could limit your audience and create legal risk.'
            },
            'ssl': {
                'service': 'Security Setup',
                'pitch': 'Your website shows a "Not Secure" warning to visitors, destroying trust immediately.'
            },
            'meta_quality': {
                'service': 'SEO Foundation',
                'pitch': 'Your website is missing basic SEO tags that search engines need to find and display your business.'
            }
        }
        
        # Find lowest scoring category (excluding load_speed which is minor)
        weakest = min(
            [(k, v) for k, v in scores.items() if k != 'load_speed'],
            key=lambda x: x[1]
        )
        
        category = weakest[0]
        return pitch_map.get(category, {}).get('service', 'Website Improvement')
    
    @classmethod
    def format_report(cls, scoring: Dict, audit: Dict) -> str:
        """
        Format scoring into a human-readable report.
        Useful for CLI output and debugging.
        """
        s = scoring
        lines = [
            f"{'='*50}",
            f"LEAD SCORE REPORT",
            f"{'='*50}",
            f"",
            f"Composite Score: {s['composite_score']}/100",
            f"Priority:        {s['priority']}",
            f"Qualification:   {s['qualification_score']}/100",
            f"",
            f"--- Individual Scores ---",
        ]
        
        for key, val in s['individual_scores'].items():
            bar = '█' * (val // 5) + '░' * (20 - val // 5)
            lines.append(f"  {key:15s} {bar} {val:3d}/100")
        
        lines.extend([
            f"",
            f"Issues: {s['critical_issues']} critical, {s['warning_issues']} warnings",
            f"Recommended Service: {s['recommended_service']}",
            f"{'='*50}",
        ])
        
        return '\n'.join(lines)

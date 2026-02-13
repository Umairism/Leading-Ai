"""
Pipeline orchestrator.
Coordinates the full workflow: scrape → audit → score → generate → export.
Each stage can run independently or as part of the full pipeline.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from config.settings import Config
from database.repository import LeadRepository, AuditRepository, OutreachRepository
from audit.website_analyzer import WebsiteAnalyzer
from audit.lead_scorer import LeadScorer
from ai.outreach_generator import OutreachGenerator

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Runs the lead generation pipeline end-to-end.
    
    Stages:
    1. AUDIT   - Analyze websites for leads without audits
    2. SCORE   - Score audited leads deterministically
    3. GENERATE - Create personalized outreach via AI
    4. EXPORT  - Export results to CSV for review
    """
    
    def __init__(self):
        self.analyzer = WebsiteAnalyzer()
        self.generator = OutreachGenerator()
        self.stats = {
            'audited': 0,
            'audit_failed': 0,
            'scored': 0,
            'generated': 0,
            'skipped': 0,
            'exported': 0,
        }
    
    # ── Stage 1: Audit ─────────────────────────────────────────
    
    def run_audits(self, limit: int = 10) -> List[Dict]:
        """
        Audit websites for leads that haven't been audited yet.
        
        Args:
            limit: Max number of leads to audit
            
        Returns:
            List of audit results
        """
        leads = LeadRepository.get_without_audit()
        
        if not leads:
            logger.info("No leads pending audit.")
            return []
        
        leads = leads[:limit]
        logger.info(f"Auditing {len(leads)} websites...")
        results = []
        
        for i, lead in enumerate(leads, 1):
            logger.info(f"\n[{i}/{len(leads)}] Auditing: {lead.business_name}")
            logger.info(f"  URL: {lead.website_url}")
            
            try:
                audit = self.analyzer.full_audit(
                    url=lead.website_url,
                    lead_id=lead.id
                )
                
                results.append({
                    'lead_id': lead.id,
                    'business_name': lead.business_name,
                    'performance': audit.get('performance_score'),
                    'seo': audit.get('seo_score'),
                    'accessibility': audit.get('accessibility_score'),
                    'issues': len(audit.get('major_issues', [])),
                    'status': 'completed'
                })
                self.stats['audited'] += 1
                logger.info(f"  ✓ Performance: {audit.get('performance_score')}/100, "
                          f"SEO: {audit.get('seo_score')}/100")
                
            except Exception as e:
                logger.error(f"  ✗ Audit failed: {e}")
                results.append({
                    'lead_id': lead.id,
                    'business_name': lead.business_name,
                    'status': 'failed',
                    'error': str(e)
                })
                self.stats['audit_failed'] += 1
        
        self._print_audit_summary(results)
        return results
    
    # ── Stage 2: Score ──────────────────────────────────────────
    
    def run_scoring(self, limit: int = 20) -> List[Dict]:
        """
        Score all audited leads that haven't been scored/outreached yet.
        
        Returns:
            List of scoring results sorted by priority
        """
        from database.connection import Database
        from database.models import Lead, Audit, Outreach
        
        # Get leads with audits but no outreach
        with Database.session_scope() as session:
            leads = session.query(Lead)\
                .join(Audit)\
                .outerjoin(Outreach)\
                .filter(Outreach.id == None)\
                .limit(limit)\
                .all()
            
            # Detach from session — we just need IDs and names
            lead_data = [(l.id, l.business_name) for l in leads]
        
        if not lead_data:
            logger.info("No leads ready for scoring (all scored or no audits).")
            return []
        
        logger.info(f"Scoring {len(lead_data)} leads...")
        results = []
        
        for lead_id, business_name in lead_data:
            audit_record = AuditRepository.get_by_lead(lead_id)
            if not audit_record:
                continue
            
            # Build audit dict
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
            
            results.append({
                'lead_id': lead_id,
                'business_name': business_name,
                'composite_score': scoring['composite_score'],
                'priority': scoring['priority'],
                'qualification_score': scoring['qualification_score'],
                'recommended_service': scoring['recommended_service'],
                'critical_issues': scoring['critical_issues'],
            })
            self.stats['scored'] += 1
        
        # Sort by qualification score (highest first = worst websites)
        results.sort(key=lambda x: x['qualification_score'], reverse=True)
        
        self._print_scoring_summary(results)
        return results
    
    # ── Stage 3: Generate Outreach ─────────────────────────────
    
    def run_generation(self, limit: int = 10, lead_ids: List[int] = None) -> List[Dict]:
        """
        Generate outreach emails for scored leads.
        
        Args:
            limit: Max emails to generate
            lead_ids: Specific lead IDs, or None for auto-selection
            
        Returns:
            List of generation results
        """
        results = self.generator.generate_batch(lead_ids=lead_ids, limit=limit)
        
        for r in results:
            if r.get('skipped'):
                self.stats['skipped'] += 1
            else:
                self.stats['generated'] += 1
        
        return results
    
    # ── Stage 4: Export ─────────────────────────────────────────
    
    def export_results(self, filename: str = None) -> str:
        """
        Export outreach results to CSV.
        
        Returns:
            Path to the exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"outreach_export_{timestamp}.csv"
        
        filepath = Config.EXPORTS_DIR / filename
        Config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get all pending outreach (not yet sent)
        outreach_records = OutreachRepository.get_pending()
        
        if not outreach_records:
            logger.info("No outreach records to export.")
            return None
        
        rows = []
        for record in outreach_records:
            lead = LeadRepository.get_by_id(record.lead_id)
            if not lead:
                continue
            
            rows.append({
                'business_name': lead.business_name,
                'website': lead.website_url,
                'email': lead.email or '',
                'phone': lead.phone or '',
                'industry': lead.industry or '',
                'location': lead.location or '',
                'subject_line': record.subject_line or '',
                'email_body': record.email_body or '',
                'qualification_score': record.qualification_score or 0,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M') if record.created_at else '',
            })
        
        if not rows:
            logger.info("No exportable records found.")
            return None
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        self.stats['exported'] = len(rows)
        logger.info(f"✓ Exported {len(rows)} records to: {filepath}")
        return str(filepath)
    
    # ── Full Pipeline ──────────────────────────────────────────
    
    def run_all(self, audit_limit: int = 10, generate_limit: int = 10, 
                export: bool = True) -> Dict:
        """
        Run the complete pipeline: audit → score → generate → export.
        
        Args:
            audit_limit: Max leads to audit
            generate_limit: Max emails to generate
            export: Whether to export results to CSV
            
        Returns:
            Pipeline summary
        """
        logger.info("\n" + "="*60)
        logger.info("FULL PIPELINE RUN")
        logger.info("="*60)
        
        start_time = datetime.now()
        
        # Stage 1: Audit
        logger.info("\n── STAGE 1: WEBSITE AUDITS ──")
        self.run_audits(limit=audit_limit)
        
        # Stage 2: Score (informational — scoring happens inside generation too)
        logger.info("\n── STAGE 2: LEAD SCORING ──")
        scoring_results = self.run_scoring(limit=audit_limit)
        
        # Stage 3: Generate outreach
        logger.info("\n── STAGE 3: OUTREACH GENERATION ──")
        # Only generate for HOT and WARM leads
        hot_warm_ids = [
            r['lead_id'] for r in scoring_results 
            if r['priority'] in ('HOT', 'WARM')
        ]
        
        if hot_warm_ids:
            self.run_generation(limit=generate_limit, lead_ids=hot_warm_ids)
        else:
            logger.info("No HOT/WARM leads found for outreach.")
        
        # Stage 4: Export
        export_path = None
        if export:
            logger.info("\n── STAGE 4: EXPORT ──")
            export_path = self.export_results()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        summary = {
            **self.stats,
            'elapsed_seconds': round(elapsed, 1),
            'export_file': export_path,
        }
        
        self._print_pipeline_summary(summary)
        return summary
    
    # ── Reporting ──────────────────────────────────────────────
    
    def _print_audit_summary(self, results: List[Dict]):
        """Print audit stage summary."""
        completed = [r for r in results if r['status'] == 'completed']
        failed = [r for r in results if r['status'] == 'failed']
        
        logger.info(f"\n{'─'*40}")
        logger.info(f"AUDIT SUMMARY")
        logger.info(f"  Completed: {len(completed)}")
        logger.info(f"  Failed:    {len(failed)}")
        
        if completed:
            avg_perf = sum(r.get('performance', 0) or 0 for r in completed) / len(completed)
            avg_seo = sum(r.get('seo', 0) or 0 for r in completed) / len(completed)
            logger.info(f"  Avg Performance: {avg_perf:.0f}/100")
            logger.info(f"  Avg SEO:         {avg_seo:.0f}/100")
        logger.info(f"{'─'*40}")
    
    def _print_scoring_summary(self, results: List[Dict]):
        """Print scoring stage summary."""
        hot = [r for r in results if r['priority'] == 'HOT']
        warm = [r for r in results if r['priority'] == 'WARM']
        cold = [r for r in results if r['priority'] == 'COLD']
        skip = [r for r in results if r['priority'] == 'SKIP']
        
        logger.info(f"\n{'─'*40}")
        logger.info(f"SCORING SUMMARY")
        logger.info(f"  🔥 HOT:  {len(hot)} leads")
        logger.info(f"  🟡 WARM: {len(warm)} leads")
        logger.info(f"  🔵 COLD: {len(cold)} leads")
        logger.info(f"  ⚪ SKIP: {len(skip)} leads")
        
        for r in results[:5]:  # Show top 5
            logger.info(f"  [{r['priority']:4s}] {r['business_name']} — "
                       f"Score: {r['composite_score']}/100, "
                       f"Service: {r['recommended_service']}")
        logger.info(f"{'─'*40}")
    
    def _print_pipeline_summary(self, summary: Dict):
        """Print full pipeline summary."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PIPELINE COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"  Audited:   {summary['audited']} websites")
        logger.info(f"  Failed:    {summary['audit_failed']} audits")
        logger.info(f"  Scored:    {summary['scored']} leads")
        logger.info(f"  Generated: {summary['generated']} emails")
        logger.info(f"  Skipped:   {summary['skipped']} (good websites)")
        logger.info(f"  Exported:  {summary['exported']} records")
        logger.info(f"  Time:      {summary['elapsed_seconds']}s")
        if summary.get('export_file'):
            logger.info(f"  File:      {summary['export_file']}")
        logger.info(f"{'='*60}")

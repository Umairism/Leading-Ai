"""
Outreach generation engine.
Combines audit data + lead info + Gemini AI to produce personalized cold emails.
Deterministic scoring drives the narrative. AI writes the words.
"""

import json
import logging
from typing import Dict, Optional, List

from ai.gemini_client import GeminiClient
from ai.prompts import audit_summary_prompt, outreach_email_prompt, lead_qualification_prompt
from audit.lead_scorer import LeadScorer
from config.settings import Config
from database.repository import LeadRepository, AuditRepository, OutreachRepository

logger = logging.getLogger(__name__)


class OutreachGenerator:
    """
    Generates personalized outreach emails for scored leads.
    
    Pipeline:
    1. Load lead + audit data from database
    2. Score the lead deterministically
    3. Get AI audit summary from Gemini
    4. Generate personalized email from Gemini
    5. Save outreach record to database
    """
    
    def __init__(self):
        self.gemini = GeminiClient()
        self.sender_name = Config.BUSINESS_NAME or 'Web Performance Consultant'
    
    def generate_for_lead(self, lead_id: int) -> Optional[Dict]:
        """
        Generate full outreach package for a single lead.
        
        Args:
            lead_id: Database ID of the lead
            
        Returns:
            Dict with email content, scoring, and AI summary, or None on failure
        """
        # Step 1: Load lead data
        lead = LeadRepository.get_by_id(lead_id)
        if not lead:
            logger.error(f"Lead {lead_id} not found")
            return None
        
        # Step 2: Load audit data
        audit_record = AuditRepository.get_by_lead(lead_id)
        if not audit_record:
            logger.warning(f"No audit found for lead {lead_id} ({lead.business_name}). Run audit first.")
            return None
        
        # Build audit dict from database record
        audit_data = self._build_audit_dict(audit_record)
        
        # Step 3: Score deterministically
        scoring = LeadScorer.score(audit_data)
        
        if scoring['priority'] == 'SKIP':
            logger.info(f"Skipping {lead.business_name} — website scored {scoring['composite_score']}/100 (too good)")
            return {
                'lead_id': lead_id,
                'business_name': lead.business_name,
                'priority': 'SKIP',
                'composite_score': scoring['composite_score'],
                'skipped': True,
                'reason': 'Website quality too high for outreach'
            }
        
        # Step 4: Get AI audit summary
        ai_summary = self._get_audit_summary(
            business_name=lead.business_name,
            industry=lead.industry or 'business',
            location=lead.location or 'unknown',
            audit=audit_data
        )
        
        if not ai_summary:
            logger.warning(f"AI summary failed for {lead.business_name}. Using fallback.")
            ai_summary = self._fallback_summary(lead, audit_data, scoring)
        
        # Step 5: Generate personalized email
        email = self._generate_email(
            business_name=lead.business_name,
            industry=lead.industry or 'business',
            location=lead.location or 'unknown',
            audit_summary=ai_summary,
            service=scoring['recommended_service']
        )
        
        if not email:
            logger.error(f"Email generation failed for {lead.business_name}")
            return None
        
        # Step 6: Save to database
        outreach = self._save_outreach(
            lead_id=lead_id,
            email=email,
            ai_summary=ai_summary,
            scoring=scoring
        )
        
        result = {
            'lead_id': lead_id,
            'business_name': lead.business_name,
            'priority': scoring['priority'],
            'composite_score': scoring['composite_score'],
            'qualification_score': scoring['qualification_score'],
            'recommended_service': scoring['recommended_service'],
            'subject_line': email.get('subject_line', ''),
            'email_body': email.get('email_body', ''),
            'ai_summary': ai_summary,
            'skipped': False,
            'outreach_id': outreach.id if outreach else None,
        }
        
        logger.info(f"✓ Outreach generated for {lead.business_name} [{scoring['priority']}]")
        return result
    
    def generate_batch(self, lead_ids: List[int] = None, limit: int = 10) -> List[Dict]:
        """
        Generate outreach for multiple leads.
        
        Args:
            lead_ids: Specific lead IDs. If None, picks leads with audits but no outreach.
            limit: Max leads to process
            
        Returns:
            List of outreach results
        """
        if lead_ids is None:
            # Get leads that have been audited but don't have outreach yet
            leads = self._get_ready_leads(limit)
            lead_ids = [l.id for l in leads]
        
        if not lead_ids:
            logger.info("No leads ready for outreach generation.")
            return []
        
        logger.info(f"Generating outreach for {len(lead_ids)} leads...")
        results = []
        
        for i, lead_id in enumerate(lead_ids[:limit], 1):
            logger.info(f"\n--- Processing lead {i}/{min(len(lead_ids), limit)} ---")
            
            result = self.generate_for_lead(lead_id)
            if result:
                results.append(result)
        
        # Summary
        generated = [r for r in results if not r.get('skipped')]
        skipped = [r for r in results if r.get('skipped')]
        
        logger.info(f"\n{'='*50}")
        logger.info(f"OUTREACH GENERATION COMPLETE")
        logger.info(f"Generated: {len(generated)} emails")
        logger.info(f"Skipped:   {len(skipped)} (good websites)")
        logger.info(f"Failed:    {len(lead_ids[:limit]) - len(results)}")
        logger.info(f"{'='*50}")
        
        return results
    
    def _build_audit_dict(self, audit_record) -> Dict:
        """Convert database Audit record to dict for scoring/prompts."""
        raw = audit_record.raw_data or {}
        
        return {
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
    
    def _get_audit_summary(self, business_name: str, industry: str,
                            location: str, audit: Dict) -> Optional[Dict]:
        """Get AI-generated audit summary from Gemini."""
        prompt = audit_summary_prompt(business_name, industry, location, audit)
        
        response = self.gemini.generate(prompt, expect_json=True)
        if not response:
            return None
        
        try:
            summary = json.loads(response)
            # Validate expected keys
            required = ['summary', 'business_impact', 'top_problems', 'urgency']
            if all(k in summary for k in required):
                return summary
            else:
                logger.warning(f"AI summary missing keys: {[k for k in required if k not in summary]}")
                return summary  # Return partial — better than nothing
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI summary JSON: {e}")
            logger.debug(f"Raw response: {response[:200]}")
            return None
    
    def _fallback_summary(self, lead, audit: Dict, scoring: Dict) -> Dict:
        """
        Generate deterministic fallback summary when AI is unavailable.
        No Gemini needed — translates raw audit data into business language.
        """
        score = scoring['composite_score']
        critical = scoring['critical_issues']
        load_ms = audit.get('load_time_ms')
        
        # Translate technical issues into plain English
        problems = []
        if load_ms and load_ms > 3000:
            problems.append(f'your website takes {load_ms / 1000:.1f} seconds to load — most visitors leave after 3')
        if not audit.get('has_meta_description'):
            problems.append('Google has no description to show for your site in search results')
        if not audit.get('has_title') or audit.get('has_title') == '':
            problems.append("your website doesn't have a proper page title for search engines")
        if not audit.get('mobile_friendly'):
            problems.append("your site may not display correctly on phones")
        if not audit.get('ssl_valid'):
            problems.append('visitors see a "Not Secure" warning when they visit your site')
        if not audit.get('has_og_tags'):
            problems.append("when someone shares your site on social media, it shows up without an image or preview")
        
        if not problems:
            problems = ['your website has some technical issues that could be affecting how customers find you']
        
        if score < 50:
            urgency = 'high'
            summary = (
                f"{lead.business_name}'s website has significant issues that are likely "
                f"costing them customers right now."
            )
        elif score < 70:
            urgency = 'medium'
            summary = (
                f"{lead.business_name}'s website has a few areas where small changes "
                f"could bring in more local customers."
            )
        else:
            urgency = 'low'
            summary = (
                f"{lead.business_name}'s website is decent but missing some easy wins "
                f"that could improve their online visibility."
            )
        
        return {
            'summary': summary,
            'business_impact': (
                f"When someone in {lead.location or 'the area'} searches for a "
                f"{lead.industry or 'business'}, these issues make it harder for them "
                f"to find and trust {lead.business_name}."
            ),
            'top_problems': problems,
            'urgency': urgency,
        }
    
    def _generate_email(self, business_name: str, industry: str, location: str,
                        audit_summary: Dict, service: str) -> Optional[Dict]:
        """Generate personalized outreach email via Gemini, with template fallback."""
        prompt = outreach_email_prompt(
            business_name=business_name,
            industry=industry,
            location=location,
            audit_summary=audit_summary,
            service=service,
            sender_name=self.sender_name
        )
        
        response = self.gemini.generate(prompt, expect_json=True)
        if not response:
            logger.warning(f"Gemini unavailable. Using template fallback for {business_name}.")
            return self._fallback_email(business_name, industry, location, audit_summary, service)
        
        try:
            email = json.loads(response)
            # Validate
            if 'subject_line' in email and 'email_body' in email:
                return email
            else:
                logger.warning("Email response missing required fields. Using fallback.")
                return self._fallback_email(business_name, industry, location, audit_summary, service)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse email JSON: {e}")
            logger.debug(f"Raw response: {response[:200]}")
            return self._fallback_email(business_name, industry, location, audit_summary, service)
    
    def _fallback_email(self, business_name: str, industry: str, location: str,
                        audit_summary: Dict, service: str) -> Dict:
        """
        Template-based fallback email when Gemini is unavailable.
        Uses audit data directly. Written to sound like a real person.
        """
        problems = audit_summary.get('top_problems', [])
        urgency = audit_summary.get('urgency', 'medium')
        
        # Pick the most concrete, understandable problem for the opener
        main_problem = problems[0] if problems else 'a few things that might be costing you customers'
        
        # Subject line — specific, curiosity-driven, not generic
        if any('load' in p or 'seconds' in p for p in problems):
            subject_line = f"{business_name} — your site might be losing visitors"
        elif any('search' in p or 'Google' in p for p in problems):
            subject_line = f"Is {business_name} showing up in local search?"
        elif any('Not Secure' in p or 'ssl' in p.lower() for p in problems):
            subject_line = f"{business_name}'s website shows a security warning"
        else:
            subject_line = f"Spotted something on {business_name}'s website"
        
        # Build email body — conversational, specific, short
        body_lines = [
            f"Hi,",
            f"",
            f"I came across {business_name} while researching {industry}s in {location} "
            f"and took a quick look at your website.",
            f"",
            # Improvement 1: Authority hint — subtle, not arrogant
            f"I run performance audits for small local businesses and spotted "
            f"a couple things on your site.",
            f"",
            f"The main one: {main_problem}.",
        ]
        
        # Add second problem if available, naturally
        if len(problems) > 1:
            body_lines.append(f"There's also an issue where {problems[1]}.")
        
        body_lines.append(f"")
        
        # Improvement 2: Competitive fear — make loss visual
        if urgency == 'high':
            body_lines.append(
                f"When a {industry}'s site is slow or hard to find, visitors tend to "
                f"check the next option instead — and in {location}, there's always "
                f"a next option. That's traffic and bookings going to a competitor."
            )
        else:
            body_lines.append(
                f"These are the kinds of small things that quietly push potential "
                f"customers toward a competitor — someone searches for a {industry} "
                f"nearby, your site doesn't load right, and they just pick the next one."
            )
        
        body_lines.extend([
            f"",
            f"I've helped similar local businesses improve their load speed and "
            f"search visibility. Happy to show you exactly what I found — takes about "
            f"10 minutes, no strings attached.",
            f"",
            # Improvement 3: Slightly stronger close
            f"If you're open to it, I can walk you through what I found.",
            f"",
            f"{self.sender_name}",
            f"",
            f"P.S. If this isn't relevant, just ignore this — no follow-ups.",
            f"",
            f"---",
            f"Reply 'unsubscribe' to opt out.",
        ])
        
        return {
            'subject_line': subject_line,
            'email_body': '\n'.join(body_lines),
        }
    
    def _save_outreach(self, lead_id: int, email: Dict, 
                       ai_summary: Dict, scoring: Dict):
        """Save generated outreach to database."""
        try:
            outreach = OutreachRepository.create(
                lead_id=lead_id,
                subject_line=email.get('subject_line', ''),
                email_body=email.get('email_body', ''),
                ai_summary=json.dumps(ai_summary) if ai_summary else '',
                qualification_score=scoring.get('qualification_score', 0)
            )
            return outreach
        except Exception as e:
            logger.error(f"Failed to save outreach for lead {lead_id}: {e}")
            return None
    
    def _get_ready_leads(self, limit: int):
        """Get leads that have audits but no outreach yet."""
        from database.connection import Database
        from database.models import Lead, Audit, Outreach
        
        with Database.session_scope() as session:
            return session.query(Lead)\
                .join(Audit)\
                .outerjoin(Outreach)\
                .filter(Outreach.id == None)\
                .order_by(Lead.created_at.desc())\
                .limit(limit)\
                .all()
    
    def preview(self, lead_id: int) -> Optional[str]:
        """
        Generate and display outreach preview without saving.
        Useful for testing and reviewing before committing.
        """
        result = self.generate_for_lead(lead_id)
        if not result:
            return None
        
        if result.get('skipped'):
            return (
                f"\n{'='*50}\n"
                f"SKIPPED: {result['business_name']}\n"
                f"Reason: {result.get('reason', 'Website quality too high')}\n"
                f"Score: {result['composite_score']}/100\n"
                f"{'='*50}"
            )
        
        return (
            f"\n{'='*60}\n"
            f"OUTREACH PREVIEW — {result['business_name']}\n"
            f"{'='*60}\n"
            f"\n"
            f"Priority:     {result['priority']}\n"
            f"Score:        {result['composite_score']}/100\n"
            f"Service:      {result['recommended_service']}\n"
            f"Qualification: {result['qualification_score']}/100\n"
            f"\n"
            f"--- SUBJECT LINE ---\n"
            f"{result['subject_line']}\n"
            f"\n"
            f"--- EMAIL BODY ---\n"
            f"{result['email_body']}\n"
            f"\n"
            f"--- AI SUMMARY ---\n"
            f"Urgency: {result['ai_summary'].get('urgency', 'N/A')}\n"
            f"Impact:  {result['ai_summary'].get('business_impact', 'N/A')}\n"
            f"{'='*60}"
        )

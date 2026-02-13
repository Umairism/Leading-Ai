"""
Data access layer for database operations.
Provides clean interface for CRUD operations.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import logging

from database.connection import Database
from database.models import Lead, Audit, Outreach, SystemLog

logger = logging.getLogger(__name__)


class LeadRepository:
    """Data access for Lead operations."""
    
    @staticmethod
    def create(business_name: str, website_url: str, **kwargs) -> Lead:
        """Create a new lead."""
        with Database.session_scope() as session:
            lead = Lead(
                business_name=business_name,
                website_url=website_url,
                **kwargs
            )
            session.add(lead)
            session.flush()
            session.refresh(lead)
            logger.info(f"Created lead: {business_name} ({website_url})")
            return lead
    
    @staticmethod
    def get_by_id(lead_id: int) -> Optional[Lead]:
        """Get lead by ID."""
        with Database.session_scope() as session:
            return session.query(Lead).filter(Lead.id == lead_id).first()
    
    @staticmethod
    def get_by_website(website_url: str) -> Optional[Lead]:
        """Get lead by website URL."""
        with Database.session_scope() as session:
            return session.query(Lead).filter(Lead.website_url == website_url).first()
    
    @staticmethod
    def exists(website_url: str) -> bool:
        """Check if lead already exists."""
        with Database.session_scope() as session:
            return session.query(Lead).filter(Lead.website_url == website_url).count() > 0
    
    @staticmethod
    def get_all(limit: int = None) -> List[Lead]:
        """Get all leads."""
        with Database.session_scope() as session:
            query = session.query(Lead).order_by(Lead.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
    
    @staticmethod
    def get_without_audit() -> List[Lead]:
        """Get leads that haven't been audited yet."""
        with Database.session_scope() as session:
            return session.query(Lead)\
                .outerjoin(Audit)\
                .filter(Audit.id == None)\
                .all()
    
    @staticmethod
    def count_today() -> int:
        """Count leads created today."""
        with Database.session_scope() as session:
            today = datetime.utcnow().date()
            return session.query(Lead)\
                .filter(Lead.created_at >= today)\
                .count()


class AuditRepository:
    """Data access for Audit operations."""
    
    @staticmethod
    def create(lead_id: int, **kwargs) -> Audit:
        """Create a new audit record."""
        with Database.session_scope() as session:
            audit = Audit(lead_id=lead_id, **kwargs)
            session.add(audit)
            session.flush()
            session.refresh(audit)
            logger.info(f"Created audit for lead_id: {lead_id}")
            return audit
    
    @staticmethod
    def get_by_lead(lead_id: int) -> Optional[Audit]:
        """Get most recent audit for a lead."""
        with Database.session_scope() as session:
            return session.query(Audit)\
                .filter(Audit.lead_id == lead_id)\
                .order_by(Audit.audit_timestamp.desc())\
                .first()
    
    @staticmethod
    def get_all_by_lead(lead_id: int) -> List[Audit]:
        """Get all audits for a lead (audit history)."""
        with Database.session_scope() as session:
            return session.query(Audit)\
                .filter(Audit.lead_id == lead_id)\
                .order_by(Audit.audit_timestamp.desc())\
                .all()


class OutreachRepository:
    """Data access for Outreach operations."""
    
    @staticmethod
    def create(lead_id: int, subject_line: str, email_body: str, **kwargs) -> Outreach:
        """Create a new outreach record."""
        with Database.session_scope() as session:
            outreach = Outreach(
                lead_id=lead_id,
                subject_line=subject_line,
                email_body=email_body,
                **kwargs
            )
            session.add(outreach)
            session.flush()
            session.refresh(outreach)
            logger.info(f"Created outreach for lead_id: {lead_id}")
            return outreach
    
    @staticmethod
    def mark_sent(outreach_id: int):
        """Mark outreach as sent."""
        with Database.session_scope() as session:
            outreach = session.query(Outreach).filter(Outreach.id == outreach_id).first()
            if outreach:
                outreach.sent_at = datetime.utcnow()
                logger.info(f"Marked outreach {outreach_id} as sent")
    
    @staticmethod
    def get_pending() -> List[Outreach]:
        """Get outreach records that haven't been sent yet."""
        with Database.session_scope() as session:
            return session.query(Outreach)\
                .filter(Outreach.sent_at == None)\
                .order_by(Outreach.qualification_score.desc())\
                .all()
    
    @staticmethod
    def count_sent_today() -> int:
        """Count emails sent today."""
        with Database.session_scope() as session:
            today = datetime.utcnow().date()
            return session.query(Outreach)\
                .filter(Outreach.sent_at >= today)\
                .count()
    
    @staticmethod
    def get_top_qualified(limit: int = 10) -> List[Outreach]:
        """Get top qualified leads for outreach."""
        with Database.session_scope() as session:
            return session.query(Outreach)\
                .filter(Outreach.sent_at == None)\
                .order_by(Outreach.qualification_score.desc())\
                .limit(limit)\
                .all()
    
    @staticmethod
    def track_outcome(outreach_id: int, **kwargs):
        """
        Update outcome tracking fields for an outreach record.
        
        Usage:
            OutreachRepository.track_outcome(1, replied=True, positive_reply=True)
            OutreachRepository.track_outcome(1, meeting_booked=True, meeting_date=datetime)
            OutreachRepository.track_outcome(1, client_closed=True, deal_value=500.0)
        """
        with Database.session_scope() as session:
            outreach = session.query(Outreach).filter(Outreach.id == outreach_id).first()
            if not outreach:
                logger.warning(f"Outreach {outreach_id} not found")
                return
            
            for key, value in kwargs.items():
                if hasattr(outreach, key):
                    setattr(outreach, key, value)
            
            logger.info(f"Updated outcome for outreach {outreach_id}: {kwargs}")
    
    @staticmethod
    def get_conversion_stats() -> dict:
        """Get conversion funnel stats across all outreach."""
        with Database.session_scope() as session:
            total = session.query(Outreach).count()
            sent = session.query(Outreach).filter(Outreach.sent_at != None).count()
            replied = session.query(Outreach).filter(Outreach.replied == True).count()
            positive = session.query(Outreach).filter(Outreach.positive_reply == True).count()
            meetings = session.query(Outreach).filter(Outreach.meeting_booked == True).count()
            closed = session.query(Outreach).filter(Outreach.client_closed == True).count()
            
            return {
                'total_generated': total,
                'sent': sent,
                'replied': replied,
                'positive_replies': positive,
                'meetings_booked': meetings,
                'clients_closed': closed,
                'reply_rate': f"{(replied/sent*100):.1f}%" if sent else "0%",
                'close_rate': f"{(closed/sent*100):.1f}%" if sent else "0%",
            }


class SystemLogRepository:
    """Data access for SystemLog operations."""
    
    @staticmethod
    def log(level: str, module: str, message: str, details: dict = None):
        """Create a system log entry."""
        with Database.session_scope() as session:
            log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=details
            )
            session.add(log)
    
    @staticmethod
    def get_recent(limit: int = 100) -> List[SystemLog]:
        """Get recent log entries."""
        with Database.session_scope() as session:
            return session.query(SystemLog)\
                .order_by(SystemLog.timestamp.desc())\
                .limit(limit)\
                .all()

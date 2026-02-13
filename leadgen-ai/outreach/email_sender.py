"""
Email sender module.
Sends outreach emails via SMTP (Brevo) with rate limiting and tracking.
"""

import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict

from config.settings import Config
from database.repository import OutreachRepository, LeadRepository

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Sends outreach emails via SMTP.
    Handles connection management, rate limiting, and delivery tracking.
    """
    
    def __init__(self):
        self.smtp_host = Config.SMTP_HOST
        self.smtp_port = Config.SMTP_PORT
        self.smtp_login = Config.SMTP_EMAIL
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.BUSINESS_EMAIL
        self.from_name = Config.BUSINESS_NAME
        self.delay_minutes = Config.EMAIL_DELAY_MINUTES
        self.max_daily = Config.MAX_DAILY_EMAILS
        self._connection = None
    
    def _connect(self) -> smtplib.SMTP:
        """Establish SMTP connection with TLS."""
        if self._connection:
            try:
                self._connection.noop()
                return self._connection
            except Exception:
                self._connection = None
        
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.smtp_login, self.smtp_password)
            self._connection = server
            logger.info(f"SMTP connected: {self.smtp_host}:{self.smtp_port}")
            return server
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            raise
    
    def _disconnect(self):
        """Close SMTP connection."""
        if self._connection:
            try:
                self._connection.quit()
            except Exception:
                pass
            self._connection = None
    
    def _build_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        """Build a properly formatted email message."""
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Reply-To'] = self.from_email
        
        # Plain text version
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        return msg
    
    def send_one(self, outreach_id: int) -> bool:
        """
        Send a single outreach email by outreach ID.
        
        Returns True if sent successfully, False otherwise.
        """
        # Check daily limit
        sent_today = OutreachRepository.count_sent_today()
        if sent_today >= self.max_daily:
            logger.warning(f"Daily email limit reached ({self.max_daily}). Try again tomorrow.")
            return False
        
        # Load outreach record
        from database.connection import Database
        from database.models import Outreach, Lead
        
        with Database.session_scope() as session:
            outreach = session.query(Outreach).filter(Outreach.id == outreach_id).first()
            if not outreach:
                logger.error(f"Outreach #{outreach_id} not found")
                return False
            
            if outreach.sent_at:
                logger.warning(f"Outreach #{outreach_id} already sent at {outreach.sent_at}")
                return False
            
            lead = session.query(Lead).filter(Lead.id == outreach.lead_id).first()
            if not lead:
                logger.error(f"Lead not found for outreach #{outreach_id}")
                return False
            
            if not lead.email:
                logger.error(f"No email address for {lead.business_name} (lead #{lead.id})")
                return False
            
            to_email = lead.email
            subject = outreach.subject_line
            body = outreach.email_body
            business_name = lead.business_name
        
        # Send
        try:
            server = self._connect()
            msg = self._build_message(to_email, subject, body)
            server.sendmail(self.from_email, to_email, msg.as_string())
            
            # Mark as sent
            OutreachRepository.mark_sent(outreach_id)
            
            logger.info(f"✓ Email sent to {business_name} ({to_email})")
            logger.info(f"  Subject: {subject}")
            return True
            
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"✗ Recipient refused: {to_email} — {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"✗ SMTP error sending to {to_email}: {e}")
            self._connection = None
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error sending to {to_email}: {e}")
            self._connection = None
            return False
    
    def send_batch(self, outreach_ids: List[int] = None, limit: int = 5) -> Dict:
        """
        Send a batch of outreach emails with delay between sends.
        
        Args:
            outreach_ids: Specific outreach IDs. If None, sends top pending.
            limit: Max emails to send this batch.
            
        Returns:
            Summary dict with sent/failed counts.
        """
        # Check daily limit
        sent_today = OutreachRepository.count_sent_today()
        remaining = self.max_daily - sent_today
        
        if remaining <= 0:
            logger.warning(f"Daily limit reached ({self.max_daily}). Try again tomorrow.")
            return {'sent': 0, 'failed': 0, 'skipped': 0, 'reason': 'daily_limit'}
        
        actual_limit = min(limit, remaining)
        
        if outreach_ids is None:
            pending = OutreachRepository.get_pending()
            # Filter to only those with email addresses
            from database.connection import Database
            from database.models import Outreach, Lead
            
            valid_ids = []
            with Database.session_scope() as session:
                for p in pending:
                    lead = session.query(Lead).filter(Lead.id == p.lead_id).first()
                    if lead and lead.email:
                        valid_ids.append(p.id)
            
            outreach_ids = valid_ids[:actual_limit]
        else:
            outreach_ids = outreach_ids[:actual_limit]
        
        if not outreach_ids:
            logger.info("No emails ready to send (need outreach records with lead email addresses).")
            return {'sent': 0, 'failed': 0, 'skipped': 0, 'reason': 'no_pending'}
        
        logger.info(f"\n{'='*50}")
        logger.info(f"SENDING {len(outreach_ids)} EMAILS")
        logger.info(f"Sent today so far: {sent_today}/{self.max_daily}")
        logger.info(f"Delay between sends: {self.delay_minutes} minutes")
        logger.info(f"{'='*50}\n")
        
        sent = 0
        failed = 0
        
        try:
            for i, oid in enumerate(outreach_ids, 1):
                logger.info(f"[{i}/{len(outreach_ids)}] Sending outreach #{oid}...")
                
                success = self.send_one(oid)
                if success:
                    sent += 1
                else:
                    failed += 1
                
                # Delay between sends (skip after last one)
                if i < len(outreach_ids):
                    delay_sec = self.delay_minutes * 60
                    logger.info(f"  Waiting {self.delay_minutes} minutes before next send...")
                    time.sleep(delay_sec)
        
        finally:
            self._disconnect()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"BATCH COMPLETE")
        logger.info(f"  Sent:   {sent}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total today: {sent_today + sent}/{self.max_daily}")
        logger.info(f"{'='*50}")
        
        return {'sent': sent, 'failed': failed, 'total_today': sent_today + sent}
    
    def test_connection(self) -> bool:
        """Test SMTP connection without sending."""
        try:
            self._connect()
            logger.info("✓ SMTP connection test passed")
            self._disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ SMTP connection test failed: {e}")
            return False

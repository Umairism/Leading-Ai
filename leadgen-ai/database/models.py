"""
Database models for LeadGen AI system.
Defines the structure for leads, audits, and outreach tracking.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, 
    DateTime, ForeignKey, JSON, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Lead(Base):
    """Business lead information."""
    
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_name = Column(String(255), nullable=False)
    website_url = Column(String(500), unique=True, nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    industry = Column(String(100))
    location = Column(String(255))
    source = Column(String(100))  # e.g., 'hotfrog', 'yellowpages'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audits = relationship('Audit', back_populates='lead', cascade='all, delete-orphan')
    outreach_records = relationship('Outreach', back_populates='lead', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.business_name}', website='{self.website_url}')>"


class Audit(Base):
    """Website audit results."""
    
    __tablename__ = 'audits'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    
    # Performance Metrics
    performance_score = Column(Integer)  # 0-100
    seo_score = Column(Integer)  # 0-100
    accessibility_score = Column(Integer)  # 0-100
    mobile_friendly = Column(Boolean, default=False)
    
    # Detailed Issues
    major_issues = Column(JSON)  # List of critical problems
    
    # Raw API Response (for debugging)
    raw_data = Column(JSON)
    
    # Metadata
    audit_timestamp = Column(DateTime, default=datetime.utcnow)
    audit_status = Column(String(50), default='completed')  # completed, failed, skipped
    error_message = Column(Text)
    
    # Relationship
    lead = relationship('Lead', back_populates='audits')
    
    def __repr__(self):
        return f"<Audit(id={self.id}, lead_id={self.lead_id}, perf={self.performance_score})>"


class Outreach(Base):
    """Outreach campaign tracking."""
    
    __tablename__ = 'outreach'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    
    # Email Content
    subject_line = Column(String(255))
    email_body = Column(Text)
    ai_summary = Column(Text)  # AI's analysis of the lead
    
    # Scoring
    qualification_score = Column(Integer)  # 0-100, AI-generated priority
    
    # Tracking
    sent_at = Column(DateTime)
    opened = Column(Boolean, default=False)
    replied = Column(Boolean, default=False)
    converted = Column(Boolean, default=False)
    
    # Response Data
    reply_received_at = Column(DateTime)
    reply_content = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    campaign_id = Column(String(100))  # For batch tracking
    
    # Relationship
    lead = relationship('Lead', back_populates='outreach_records')
    
    def __repr__(self):
        return f"<Outreach(id={self.id}, lead_id={self.lead_id}, sent={self.sent_at})>"


class SystemLog(Base):
    """System activity logging for monitoring."""
    
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20))  # INFO, WARNING, ERROR
    module = Column(String(100))  # scraper, audit, ai, outreach
    message = Column(Text)
    details = Column(JSON)
    
    def __repr__(self):
        return f"<SystemLog(level={self.level}, module={self.module}, time={self.timestamp})>"

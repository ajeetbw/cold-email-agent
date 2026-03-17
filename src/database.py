"""
Database models for tracking leads, emails, and outreach history.
Using SQLite with SQLAlchemy ORM.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from typing import Optional
import os

Base = declarative_base()


class EmailStatus(str, Enum):
    """Email status enumeration."""
    PENDING = "pending"  # Not sent yet
    SENDING = "sending"  # Currently being sent
    SENT = "sent"  # Successfully sent
    FAILED = "failed"  # Failed to send
    BOUNCED = "bounced"  # Email bounced
    OPENED = "opened"  # Email was opened
    CLICKED = "clicked"  # Link was clicked
    REPLIED = "replied"  # User replied


class Lead(Base):
    """Lead information model."""
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    company = Column(String(255), nullable=False, index=True)
    role = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Enrichment data
    company_summary = Column(Text, nullable=True)
    enriched_at = Column(DateTime, nullable=True)
    
    # Metadata
    source = Column(String(50), default="csv")  # csv, manual, api
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Relationships
    emails = relationship("Email", back_populates="lead", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Lead {self.name} ({self.email})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'company': self.company,
            'role': self.role,
            'website': self.website,
            'company_summary': self.company_summary,
            'added_at': self.added_at.isoformat() if self.added_at else None,
        }


class Email(Base):
    """Sent email tracking model."""
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    
    # Email content
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(50), default=EmailStatus.PENDING.value, index=True)  # pending, sent, failed, bounced, opened, replied
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True, index=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Campaign tracking
    campaign_id = Column(String(100), nullable=True, index=True)
    email_type = Column(String(50), default="initial")  # initial, follow_up_1, follow_up_2
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lead = relationship("Lead", back_populates="emails")
    
    def __repr__(self) -> str:
        return f"<Email {self.id} to {self.lead.email} - {self.status}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'subject': self.subject,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'email_type': self.email_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EmailTemplate(Base):
    """Email template model for personalized content."""
    __tablename__ = 'email_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    
    # Placeholder variables supported: {name}, {company}, {role}, {company_summary}, {sender_name}
    variables = Column(String(500), nullable=True)  # JSON list of variable names
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name}>"


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, db_path: str = "data/email_agent.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_dir()
        
        # Create engine
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        self.create_tables()
    
    def _ensure_db_dir(self) -> None:
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: str = "data/email_agent.db") -> DatabaseManager:
    """Get or create global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager


def get_session():
    """Get a database session."""
    return get_db_manager().get_session()

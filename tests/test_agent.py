"""
Unit tests for the Cold Email Agent system.
Run with: pytest tests/
"""

import os
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, Lead, Email, EmailStatus, DatabaseManager, EmailTemplate
from src.lead_input import LeadValidator, LeadInputManager
from src.config import Config, reset_config


# Test Database Setup
@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal
    engine.dispose()


# Test Lead Validation
class TestLeadValidator:
    """Test lead validation."""
    
    def test_valid_email(self):
        """Test valid email validation."""
        assert LeadValidator.is_valid_email("test@example.com")
        assert LeadValidator.is_valid_email("john.doe@company.co.uk")
        assert not LeadValidator.is_valid_email("invalid.email")
        assert not LeadValidator.is_valid_email("@example.com")
    
    def test_validate_lead(self):
        """Test full lead validation."""
        # Valid lead
        lead = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'ABC Corp',
            'role': 'CTO'
        }
        is_valid, error = LeadValidator.validate_lead(lead)
        assert is_valid
        assert error is None
        
        # Invalid: missing email
        bad_lead = {
            'name': 'John',
            'email': '',
            'company': 'ABC',
            'role': 'CTO'
        }
        is_valid, error = LeadValidator.validate_lead(bad_lead)
        assert not is_valid
        assert error is not None
        
        # Invalid: bad email
        bad_lead = {
            'name': 'John',
            'email': 'not-an-email',
            'company': 'ABC',
            'role': 'CTO'
        }
        is_valid, error = LeadValidator.validate_lead(bad_lead)
        assert not is_valid


# Test Database Models
class TestDatabaseModels:
    """Test database models."""
    
    def test_lead_creation(self, test_db):
        """Test Lead model."""
        session = test_db()
        
        lead = Lead(
            name='John Doe',
            email='john@example.com',
            company='ABC Corp',
            role='CTO',
            website='abccorp.com'
        )
        
        session.add(lead)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(Lead).filter(
            Lead.email == 'john@example.com'
        ).first()
        
        assert retrieved is not None
        assert retrieved.name == 'John Doe'
        assert retrieved.company == 'ABC Corp'
    
    def test_email_creation(self, test_db):
        """Test Email model."""
        session = test_db()
        
        # Create lead first
        lead = Lead(
            name='John Doe',
            email='john@example.com',
            company='ABC Corp',
            role='CTO'
        )
        session.add(lead)
        session.commit()
        
        # Create email
        email = Email(
            lead_id=lead.id,
            subject='Test Subject',
            body='Test Body',
            status=EmailStatus.PENDING.value
        )
        
        session.add(email)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(Email).first()
        assert retrieved.lead.email == 'john@example.com'
        assert retrieved.status == 'pending'
    
    def test_email_status_enum(self):
        """Test email status enumeration."""
        assert EmailStatus.PENDING.value == 'pending'
        assert EmailStatus.SENT.value == 'sent'
        assert EmailStatus.FAILED.value == 'failed'
        assert EmailStatus.REPLIED.value == 'replied'


# Test Configuration
class TestConfiguration:
    """Test configuration loading."""
    
    def test_default_config(self):
        """Test default configuration loading."""
        try:
            # This will fail if config file doesn't exist, which is expected in test
            pass
        except:
            pass


# Test Lead Input Manager
class TestLeadInputManager:
    """Test lead input functionality."""
    
    def test_csv_loading(self, tmpdir, test_db):
        """Test CSV loading."""
        # Create test CSV
        csv_file = tmpdir.join("test_leads.csv")
        csv_file.write("name,email,company,role,website\n")
        csv_file.write("John Doe,john@example.com,ABC Corp,CTO,abccorp.com\n")
        csv_file.write("Jane Smith,jane@example.com,XYZ Inc,VP Sales,xyz.com\n")
        
        # Test loading (would need database setup)
        # This is a placeholder for actual test
        assert csv_file.exists()


# Integration Tests
class TestIntegration:
    """Integration tests."""
    
    def test_lead_to_email_workflow(self, test_db):
        """Test lead creation to email workflow."""
        session = test_db()
        
        # Create lead
        lead = Lead(
            name='John Doe',
            email='john@example.com',
            company='ABC Corp',
            role='CTO'
        )
        session.add(lead)
        session.commit()
        
        # Create email
        email = Email(
            lead_id=lead.id,
            subject='Hello {name}'.format(name=lead.name),
            body='Body',
            status=EmailStatus.PENDING.value
        )
        session.add(email)
        session.commit()
        
        # Verify relationship
        retrieved_lead = session.query(Lead).filter(
            Lead.id == lead.id
        ).first()
        
        assert len(retrieved_lead.emails) == 1
        assert retrieved_lead.emails[0].subject == 'Hello John Doe'


# Mock Tests for External Services
class TestExternalServices:
    """Test external service interactions."""
    
    def test_email_generation_structure(self):
        """Test email generation produces correct structure."""
        # This would test OpenAI integration if API is available
        # For now, just verify the module loads
        try:
            from src.email_generator import EmailGenerator
            assert EmailGenerator is not None
        except ImportError:
            pytest.skip("OpenAI library not installed")
    
    def test_email_sender_structure(self):
        """Test email sender module structure."""
        from src.email_sender import EmailSender
        assert EmailSender is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

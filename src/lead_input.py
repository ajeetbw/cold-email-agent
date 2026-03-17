"""
Lead input module - handles CSV loading and manual lead entry.
"""

import csv
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
from sqlalchemy.orm import Session

from src.logger import logger
from src.database import Lead, get_session
from src.config import get_config


class LeadValidator:
    """Validates lead data."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Validate email format.
        
        RFC 5322 simplified validation - checks:
        - Local part not empty and doesn't start with dot
        - No consecutive dots
        - @ symbol exists
        - Domain has TLD
        """
        if not email or not isinstance(email, str):
            return False
        
        # More robust regex pattern
        # Allows alphanumeric, dots, hyphens, underscores, plus
        # But avoids double dots and leading/trailing dots
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%-]*[a-zA-Z0-9]@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.([a-zA-Z]{2,})$'
        
        if not re.match(pattern, email):
            return False
        
        # Additional checks for invalid patterns
        if '..' in email:
            return False
        if email.startswith('.') or email.endswith('.'):
            return False
        if '@.' in email or '.@' in email:
            return False
        
        return True
    
    @staticmethod
    def validate_lead(lead: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate lead data.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ['name', 'email', 'company', 'role']
        
        # Check required fields
        for field in required_fields:
            if field not in lead or not lead[field].strip():
                return False, f"Missing required field: {field}"
        
        # Validate email
        if not LeadValidator.is_valid_email(lead['email']):
            return False, f"Invalid email format: {lead['email']}"
        
        # Validate name
        if len(lead['name'].strip()) < 2:
            return False, "Name must be at least 2 characters"
        
        # Validate company
        if len(lead['company'].strip()) < 2:
            return False, "Company name must be at least 2 characters"
        
        return True, None


class LeadInputManager:
    """Manages lead input from CSV and manual entry."""
    
    def __init__(self):
        """Initialize lead input manager."""
        self.validator = LeadValidator()
        self.config = get_config()
    
    def load_from_csv(self, csv_file: str) -> Tuple[List[Lead], List[Dict[str, str]]]:
        """
        Load leads from CSV file.
        
        Args:
            csv_file: Path to CSV file
        
        Returns:
            Tuple of (loaded_leads, failed_leads)
        """
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return [], []
        
        loaded_leads = []
        failed_leads = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    logger.error("CSV file is empty or has no headers")
                    return [], []
                
                # Validate required columns exist and normalize to lowercase
                reader.fieldnames = [f.lower().strip() for f in reader.fieldnames] if reader.fieldnames else []
                required_cols = {'name', 'email', 'company', 'role'}
                existing_cols = set(reader.fieldnames or [])
                missing_cols = required_cols - existing_cols
                
                if missing_cols:
                    logger.error(f"CSV missing required columns: {missing_cols}. Found: {existing_cols}")
                    return [], []
                
                # Pre-load existing emails to avoid N+1 queries
                session = get_session()
                try:
                    existing_emails_set = {lead.email.lower() for lead in session.query(Lead.email).all()}
                finally:
                    session.close()
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    # Normalize row keys to lowercase
                    row = {k.lower().strip(): v for k, v in row.items()}
                    
                    # Validate lead
                    is_valid, error = self.validator.validate_lead(row)
                    
                    if not is_valid:
                        logger.warning(f"Row {row_num}: {error}")
                        failed_leads.append({**row, '_error': error, '_row': row_num})
                        continue
                    
                    # Check if lead already exists (using pre-loaded set)
                    email_lower = row['email'].lower().strip()
                    
                    if email_lower in existing_emails_set:
                        logger.warning(f"Row {row_num}: Lead already exists with email {row['email']}")
                        failed_leads.append({**row, '_error': 'Lead already exists', '_row': row_num})
                        continue
                    
                    # Add to set to prevent duplicates within same CSV
                    existing_emails_set.add(email_lower)
                    
                    # Create lead
                    lead = Lead(
                        name=row['name'].strip(),
                        email=row['email'].lower().strip(),
                        company=row['company'].strip(),
                        role=row['role'].strip(),
                        website=row.get('website', '').strip() or None,
                        source='csv'
                    )
                    loaded_leads.append(lead)
            
            logger.info(f"Loaded {len(loaded_leads)} leads from {csv_file}, {len(failed_leads)} failed")
            
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            return [], []
        
        return loaded_leads, failed_leads
    
    def add_manual_lead(
        self,
        name: str,
        email: str,
        company: str,
        role: str,
        website: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Add a lead manually.
        
        Args:
            name: Lead name
            email: Lead email
            company: Company name
            role: Job role
            website: Company website (optional)
            notes: Additional notes (optional)
        
        Returns:
            Tuple of (success, message)
        """
        # Validate
        lead_data = {
            'name': name,
            'email': email,
            'company': company,
            'role': role
        }
        
        is_valid, error = self.validator.validate_lead(lead_data)
        if not is_valid:
            return False, error
        
        # Check if already exists
        session = get_session()
        existing = session.query(Lead).filter(
            Lead.email == email.lower().strip()
        ).first()
        session.close()
        
        if existing:
            return False, f"Lead already exists: {email}"
        
        # Add to database
        session = get_session()
        try:
            lead = Lead(
                name=name.strip(),
                email=email.lower().strip(),
                company=company.strip(),
                role=role.strip(),
                website=website.strip() if website else None,
                notes=notes,
                source='manual'
            )
            session.add(lead)
            session.commit()
            logger.info(f"Added lead: {name} ({email})")
            return True, f"Lead added successfully: {name}"
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding lead: {str(e)}")
            return False, f"Error adding lead: {str(e)}"
        finally:
            session.close()
    
    def save_leads_to_db(self, leads: List[Lead]) -> Tuple[int, int]:
        """
        Save leads to database.
        
        Args:
            leads: List of Lead objects to save
        
        Returns:
            Tuple of (saved_count, failed_count)
        """
        session = get_session()
        saved_count = 0
        failed_count = 0
        
        try:
            for lead in leads:
                try:
                    session.add(lead)
                    session.commit()
                    saved_count += 1
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Failed to save lead {lead.email}: {str(e)}")
                    failed_count += 1
        finally:
            session.close()
        
        logger.info(f"Saved {saved_count} leads to database, {failed_count} failed")
        return saved_count, failed_count
    
    def get_leads(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Lead]:
        """
        Get leads from database.
        
        Args:
            status: Filter by lead status (pending, contacted, replied, etc.)
            limit: Maximum number of leads to return
        
        Returns:
            List of Lead objects
        """
        session = get_session()
        try:
            query = session.query(Lead)
            
            if limit:
                query = query.limit(limit)
            
            leads = query.all()
            
            # Detach from session to avoid lazy loading issues
            for lead in leads:
                # Access relationships to load them
                _ = len(lead.emails)
            
            return leads
        finally:
            session.close()
    
    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get a lead by email address."""
        session = get_session()
        try:
            return session.query(Lead).filter(
                Lead.email == email.lower().strip()
            ).first()
        finally:
            session.close()
    
    def export_leads_to_csv(self, output_file: str) -> bool:
        """
        Export leads to CSV file.
        
        Args:
            output_file: Path to output CSV file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            leads = self.get_leads()
            
            if not leads:
                logger.warning("No leads to export")
                return False
            
            fieldnames = ['name', 'email', 'company', 'role', 'website', 'company_summary', 'added_at']
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for lead in leads:
                    writer.writerow({
                        'name': lead.name,
                        'email': lead.email,
                        'company': lead.company,
                        'role': lead.role,
                        'website': lead.website or '',
                        'company_summary': lead.company_summary or '',
                        'added_at': lead.added_at.isoformat() if lead.added_at else '',
                    })
            
            logger.info(f"Exported {len(leads)} leads to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting leads: {str(e)}")
            return False

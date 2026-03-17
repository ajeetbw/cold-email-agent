"""
Scheduler module - handles follow-up scheduling and automated tasks.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from src.logger import logger
from src.config import get_config
from src.database import Email, Lead, EmailStatus, get_session


class FollowUpScheduler:
    """Manages follow-up email scheduling."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.config = get_config()
        self.followup_enabled = self.config.get('follow_up.enabled', True)
        self.first_followup_days = self.config.get('follow_up.first_followup_days', 3)
        self.second_followup_days = self.config.get('follow_up.second_followup_days', 7)
    
    def get_followups_due(self) -> Dict[str, List[Email]]:
        """
        Get emails that are due for follow-up.
        
        Returns:
            Dictionary with keys 'first_followup' and 'second_followup'
        """
        if not self.followup_enabled:
            return {'first_followup': [], 'second_followup': []}
        
        session = get_session()
        now = datetime.utcnow()
        
        try:
            # Find initial emails that should have follow-up
            initial_emails = session.query(Email).filter(
                Email.status == EmailStatus.SENT.value,
                Email.email_type == 'initial'
            ).all()
            
            first_followup = []
            second_followup = []
            
            for email in initial_emails:
                # Skip if no sent timestamp (should not happen but be safe)
                if not email.sent_at:
                    logger.warning(f"Email {email.id} has no sent_at timestamp, skipping")
                    continue
                
                days_since_sent = (now - email.sent_at).days
                
                # Check if lead has already replied - if so, skip follow-ups
                reply_exists = session.query(Email).filter(
                    Email.lead_id == email.lead_id,
                    Email.status == EmailStatus.REPLIED.value
                ).first()
                
                if reply_exists:
                    logger.info(f"Skipping follow-up for lead {email.lead.email} - already replied")
                    continue
                
                # Check if first follow-up is due
                if days_since_sent >= self.first_followup_days:
                    # Check if first follow-up already exists
                    existing_followup = session.query(Email).filter(
                        Email.lead_id == email.lead_id,
                        Email.email_type == 'follow_up_1'
                    ).first()
                    
                    if not existing_followup:
                        first_followup.append(email)
                
                    # Check if second follow-up is due
                    if days_since_sent >= self.second_followup_days:
                        # Check if second follow-up already exists
                        existing_followup = session.query(Email).filter(
                            Email.lead_id == email.lead_id,
                            Email.email_type == 'follow_up_2'
                        ).first()
                        
                        if not existing_followup:
                            second_followup.append(email)
            
            logger.info(f"Found {len(first_followup)} leads for first follow-up, {len(second_followup)} for second")
            
            return {
                'first_followup': first_followup,
                'second_followup': second_followup
            }
        
        finally:
            session.close()
    
    def create_followup_email(
        self,
        original_email: Email,
        followup_number: int,
        subject: str,
        body: str
    ) -> Tuple[bool, str]:
        """
        Create a follow-up email record.
        
        Args:
            original_email: The original Email object
            followup_number: 1 for first follow-up, 2 for second
            subject: Follow-up email subject
            body: Follow-up email body
        
        Returns:
            Tuple of (success, message)
        """
        session = get_session()
        try:
            email_type = f"follow_up_{followup_number}"
            
            # Check if follow-up already exists
            existing = session.query(Email).filter(
                Email.lead_id == original_email.lead_id,
                Email.email_type == email_type
            ).first()
            
            if existing:
                return False, f"{email_type} already exists for this lead"
            
            # Create new follow-up email
            followup = Email(
                lead_id=original_email.lead_id,
                subject=subject,
                body=body,
                status=EmailStatus.PENDING.value,
                email_type=email_type,
                campaign_id=original_email.campaign_id
            )
            
            session.add(followup)
            session.commit()
            
            logger.info(f"Created {email_type} for lead {original_email.lead.email}")
            return True, f"{email_type} created"
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating follow-up: {str(e)}")
            return False, str(e)
        
        finally:
            session.close()
    
    def schedule_batch_followups(
        self,
        emails: List[Email],
        followup_number: int,
        subject_template: str,
        body_template: str
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Schedule follow-ups for a batch of emails.
        
        Args:
            emails: List of Email objects to create follow-ups for
            followup_number: Follow-up number (1 or 2)
            subject_template: Subject template with {name}, {company} placeholders
            body_template: Body template with {name}, {company} placeholders
        
        Returns:
            Dictionary of results
        """
        results = {}
        
        for email in emails:
            try:
                lead = email.lead
                
                # Replace placeholders
                subject = subject_template.format(
                    name=lead.name,
                    company=lead.company,
                    role=lead.role
                )
                body = body_template.format(
                    name=lead.name,
                    company=lead.company,
                    role=lead.role
                )
                
                success, message = self.create_followup_email(
                    original_email=email,
                    followup_number=followup_number,
                    subject=subject,
                    body=body
                )
                
                results[lead.email] = (success, message)
            
            except Exception as e:
                logger.error(f"Error processing follow-up for {email.lead.email}: {str(e)}")
                results[email.lead.email] = (False, str(e))
        
        successful = sum(1 for s, _ in results.values() if s)
        logger.info(f"Scheduled {successful}/{len(results)} follow-ups")
        return results
    
    def get_followup_stats(self) -> Dict:
        """Get follow-up statistics."""
        session = get_session()
        try:
            initial_count = session.query(Email).filter(
                Email.email_type == 'initial',
                Email.status == EmailStatus.SENT.value
            ).count()
            
            first_followup_count = session.query(Email).filter(
                Email.email_type == 'follow_up_1'
            ).count()
            
            second_followup_count = session.query(Email).filter(
                Email.email_type == 'follow_up_2'
            ).count()
            
            replied_count = session.query(Email).filter(
                Email.status == EmailStatus.REPLIED.value
            ).count()
            
            return {
                'initial_emails_sent': initial_count,
                'first_followups_created': first_followup_count,
                'second_followups_created': second_followup_count,
                'replies_received': replied_count,
                'reply_rate': (replied_count / initial_count * 100) if initial_count > 0 else 0
            }
        finally:
            session.close()


class CampaignManager:
    """Manages email campaigns."""
    
    @staticmethod
    def create_campaign(
        campaign_id: str,
        lead_ids: List[int],
        email_subjects: Dict[int, str],
        email_bodies: Dict[int, str]
    ) -> Tuple[bool, str]:
        """
        Create a campaign with emails for multiple leads.
        
        Args:
            campaign_id: Unique campaign identifier
            lead_ids: List of lead IDs to include
            email_subjects: Dict of {lead_id: subject}
            email_bodies: Dict of {lead_id: body}
        
        Returns:
            Tuple of (success, message)
        """
        session = get_session()
        try:
            emails_created = 0
            
            for lead_id in lead_ids:
                subject = email_subjects.get(lead_id, "Follow up")
                body = email_bodies.get(lead_id, "")
                
                email = Email(
                    lead_id=lead_id,
                    subject=subject,
                    body=body,
                    status=EmailStatus.PENDING.value,
                    email_type='initial',
                    campaign_id=campaign_id
                )
                
                session.add(email)
                emails_created += 1
            
            session.commit()
            logger.info(f"Created campaign {campaign_id} with {emails_created} emails")
            return True, f"Campaign created with {emails_created} emails"
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating campaign: {str(e)}")
            return False, str(e)
        
        finally:
            session.close()
    
    @staticmethod
    def get_campaign_stats(campaign_id: str) -> Dict:
        """Get statistics for a campaign."""
        session = get_session()
        try:
            total = session.query(Email).filter(
                Email.campaign_id == campaign_id
            ).count()
            
            sent = session.query(Email).filter(
                Email.campaign_id == campaign_id,
                Email.status == EmailStatus.SENT.value
            ).count()
            
            failed = session.query(Email).filter(
                Email.campaign_id == campaign_id,
                Email.status == EmailStatus.FAILED.value
            ).count()
            
            replied = session.query(Email).filter(
                Email.campaign_id == campaign_id,
                Email.status == EmailStatus.REPLIED.value
            ).count()
            
            return {
                'campaign_id': campaign_id,
                'total_emails': total,
                'sent': sent,
                'failed': failed,
                'pending': total - sent - failed,
                'replied': replied,
                'send_rate': (sent / total * 100) if total > 0 else 0,
                'reply_rate': (replied / sent * 100) if sent > 0 else 0
            }
        finally:
            session.close()

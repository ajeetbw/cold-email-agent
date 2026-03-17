"""
Main Cold Email Agent Orchestrator - coordinates all modules.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime

from src.logger import logger
from src.config import get_config
from src.lead_input import LeadInputManager
from src.email_generator import EmailGenerator, TemplateEmailGenerator
from src.email_sender import EmailSender
from src.lead_enrichment import LeadEnricher
from src.scheduler import FollowUpScheduler, CampaignManager
from src.database import Lead, Email, get_session, EmailStatus


class ColdEmailAgent:
    """
    Main orchestrator for the cold email outreach system.
    
    Features:
    - Load leads from CSV or manual entry
    - Enrich leads with company information
    - Generate personalized emails
    - Send emails with rate limiting
    - Schedule follow-ups
    - Track metrics and results
    """
    
    def __init__(self):
        """Initialize the cold email agent."""
        logger.info("Initializing Cold Email Agent...")
        
        self.config = get_config()
        self.lead_manager = LeadInputManager()
        self.email_generator = EmailGenerator()
        self.email_sender = EmailSender()
        self.lead_enricher = LeadEnricher()
        self.scheduler = FollowUpScheduler()
        self.campaign_manager = CampaignManager()
        
        # Validate configuration
        if not self._validate_config():
            logger.error("Configuration validation failed!")
        else:
            logger.info("Configuration validated successfully")
    
    def _validate_config(self) -> bool:
        """Validate required configuration."""
        # Configuration should have been validated by Config class
        return True
    
    def load_leads_from_csv(self, csv_file: str) -> Tuple[int, int]:
        """
        Load leads from CSV file and save to database.
        
        Args:
            csv_file: Path to CSV file
        
        Returns:
            Tuple of (saved_count, failed_count)
        """
        logger.info(f"Loading leads from {csv_file}...")
        
        # Load from CSV
        leads, failed = self.lead_manager.load_from_csv(csv_file)
        
        if not leads:
            logger.warning("No valid leads found in CSV")
            return 0, len(failed)
        
        # Save to database
        saved, failed_save = self.lead_manager.save_leads_to_db(leads)
        
        return saved, failed_save + len(failed)
    
    def add_lead(
        self,
        name: str,
        email: str,
        company: str,
        role: str,
        website: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Add a single lead manually."""
        success, message = self.lead_manager.add_manual_lead(
            name=name,
            email=email,
            company=company,
            role=role,
            website=website,
            notes=notes
        )
        
        if success:
            logger.info(message)
        else:
            logger.warning(message)
        
        return success
    
    def enrich_leads(self, limit: Optional[int] = None) -> Dict:
        """
        Enrich leads with company information.
        
        Args:
            limit: Maximum leads to enrich
        
        Returns:
            Dictionary with enrichment results
        """
        logger.info("Starting lead enrichment...")
        
        # Get unenriched leads
        session = get_session()
        try:
            query = session.query(Lead).filter(Lead.enriched_at.isnull())
            if limit:
                query = query.limit(limit)
            
            leads = query.all()
        finally:
            session.close()
        
        if not leads:
            logger.info("No unenriched leads found")
            return {'enriched': 0, 'failed': 0}
        
        logger.info(f"Enriching {len(leads)} leads...")
        results = self.lead_enricher.enrich_batch(leads)
        
        successful = sum(1 for s, _ in results.values() if s)
        return {
            'enriched': successful,
            'failed': len(results) - successful,
            'total': len(results)
        }
    
    def generate_and_save_emails(
        self,
        limit: Optional[int] = None,
        email_type: str = "initial"
    ) -> Dict:
        """
        Generate personalized emails for leads without pending emails.
        
        Args:
            limit: Maximum leads to process
            email_type: Type of email ('initial', 'follow_up_1', 'follow_up_2')
        
        Returns:
            Dictionary with generation results
        """
        logger.info(f"Generating {email_type} emails...")
        
        # Get leads without pending emails of this type
        session = get_session()
        try:
            query = session.query(Lead).filter(
                ~Lead.emails.any(
                    (Email.status == EmailStatus.PENDING.value) & 
                    (Email.email_type == email_type)
                )
            )
            
            if limit:
                query = query.limit(limit)
            
            leads = query.all()
        finally:
            session.close()
        
        if not leads:
            logger.info(f"No leads found for {email_type} generation")
            return {'generated': 0, 'failed': 0}
        
        logger.info(f"Generating emails for {len(leads)} leads...")
        
        generated = 0
        failed = 0
        
        for lead in leads:
            try:
                success, subject, body = self.email_generator.generate_email(
                    lead=lead,
                    email_type=email_type
                )
                
                if success:
                    # Validate email content is not empty
                    if not subject.strip() or not body.strip():
                        logger.warning(f"Generated email is empty for {lead.email} ({email_type})")
                        failed += 1
                        continue
                    
                    # Save to database
                    new_email = Email(
                        lead_id=lead.id,
                        subject=subject,
                        body=body,
                        email_type=email_type,
                        status=EmailStatus.PENDING.value
                    )
                    
                    email_session = get_session()
                    try:
                        email_session.add(new_email)
                        email_session.commit()
                        generated += 1
                        logger.info(f"Generated {email_type} for {lead.email}")
                    except Exception as e:
                        email_session.rollback()
                        logger.error(f"Error saving email for {lead.email}: {str(e)}")
                        failed += 1
                    finally:
                        email_session.close()
                else:
                    failed += 1
            
            except Exception as e:
                logger.error(f"Error generating email for {lead.email}: {str(e)}")
                failed += 1
        
        return {'generated': generated, 'failed': failed, 'total': len(leads)}
    
    def send_pending_emails(self, max_to_send: Optional[int] = None) -> Dict:
        """
        Send pending emails respecting rate limits.
        
        Args:
            max_to_send: Maximum emails to send in this batch
        
        Returns:
            Dictionary with sending results
        """
        logger.info("Sending pending emails...")
        
        # Get pending emails
        session = get_session()
        try:
            query = session.query(Email).filter(
                Email.status == EmailStatus.PENDING.value
            )
            
            if max_to_send:
                query = query.limit(max_to_send)
            
            emails = query.all()
            
            # Prepare for batch sending
            emails_to_send = []
            for email in emails:
                emails_to_send.append({
                    'id': email.id,
                    'to_email': email.lead.email,
                    'to_name': email.lead.name,
                    'subject': email.subject,
                    'body': email.body
                })
        finally:
            session.close()
        
        if not emails_to_send:
            logger.info("No pending emails to send")
            return {'sent': 0, 'failed': 0, 'total': 0}
        
        # Send emails
        results = self.email_sender.send_batch(emails_to_send)
        
        sent = sum(1 for s, _ in results.values() if s)
        failed = len(results) - sent
        
        logger.info(f"Sent {sent}/{len(results)} emails")
        
        return {
            'sent': sent,
            'failed': failed,
            'total': len(results)
        }
    
    def retry_failed_emails(self, limit: int = 5) -> Dict:
        """
        Retry previously failed emails.
        
        Args:
            limit: Maximum failed emails to retry
        
        Returns:
            Dictionary with retry results
        """
        logger.info("Retrying failed emails...")
        
        results = self.email_sender.retry_failed_emails(limit=limit)
        
        sent = sum(1 for s, _ in results.values() if s)
        
        return {
            'retried': len(results),
            'successful': sent,
            'failed': len(results) - sent
        }
    
    def schedule_followups(self, email_type: str = "follow_up_1") -> Dict:
        """
        Create and schedule follow-up emails.
        
        Args:
            email_type: 'follow_up_1' or 'follow_up_2'
        
        Returns:
            Dictionary with scheduling results
        """
        logger.info(f"Scheduling {email_type}s...")
        
        # Get followups due
        followups = self.scheduler.get_followups_due()
        
        if email_type == "follow_up_1":
            emails_due = followups['first_followup']
        else:
            emails_due = followups['second_followup']
        
        if not emails_due:
            logger.info(f"No leads due for {email_type}")
            return {'scheduled': 0}
        
        # Generate follow-ups
        generated = 0
        
        for email in emails_due:
            lead = email.lead
            followup_num = 1 if email_type == "follow_up_1" else 2
            
            try:
                success, subject, body = self.email_generator.generate_email(
                    lead=lead,
                    email_type=email_type
                )
                
                if success:
                    success, msg = self.scheduler.create_followup_email(
                        original_email=email,
                        followup_number=followup_num,
                        subject=subject,
                        body=body
                    )
                    
                    if success:
                        generated += 1
            
            except Exception as e:
                logger.error(f"Error creating {email_type}: {str(e)}")
        
        logger.info(f"Scheduled {generated} {email_type}s")
        return {'scheduled': generated, 'total_due': len(emails_due)}
    
    def get_status(self) -> Dict:
        """Get comprehensive status of the system."""
        
        # Sending stats
        sending_stats = self.email_sender.get_sending_stats()
        
        # Follow-up stats
        followup_stats = self.scheduler.get_followup_stats()
        
        # Lead stats
        session = get_session()
        try:
            total_leads = session.query(Lead).count()
            enriched_leads = session.query(Lead).filter(Lead.enriched_at.isnot(None)).count()
            
            lead_stats = {
                'total': total_leads,
                'enriched': enriched_leads,
                'pending_enrichment': total_leads - enriched_leads
            }
        finally:
            session.close()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'leads': lead_stats,
            'emails': sending_stats,
            'follow_ups': followup_stats
        }
    
    def get_detailed_report(self) -> str:
        """Generate a detailed status report."""
        status = self.get_status()
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          COLD EMAIL AGENT - DETAILED STATUS REPORT          ║
╚══════════════════════════════════════════════════════════════╝

[LEADS]
  Total Leads:             {status['leads']['total']}
  Enriched:                {status['leads']['enriched']}
  Pending Enrichment:      {status['leads']['pending_enrichment']}

[EMAIL SENDING]
  Total Sent:              {status['emails']['total_sent']}
  Sent Today:              {status['emails']['today_sent']}/{status['emails']['daily_limit']}
  Remaining Today:         {status['emails']['remaining_today']}
  Failed:                  {status['emails']['failed']}
  Pending:                 {status['emails']['pending']}

[FOLLOW-UPS]
  Initial Emails Sent:     {status['follow_ups']['initial_emails_sent']}
  First Follow-ups:        {status['follow_ups']['first_followups_created']}
  Second Follow-ups:       {status['follow_ups']['second_followups_created']}
  Replies Received:        {status['follow_ups']['replies_received']}
  Reply Rate:              {status['follow_ups']['reply_rate']:.1f}%

[TIMESTAMP]
  {status['timestamp']}

╔══════════════════════════════════════════════════════════════╗
"""
        return report
    
    def export_results(self, output_file: str) -> bool:
        """Export results to CSV."""
        return self.lead_manager.export_leads_to_csv(output_file)


def main():
    """Example usage of the Cold Email Agent."""
    
    # Initialize agent
    agent = ColdEmailAgent()
    
    print(agent.get_detailed_report())
    
    # Example workflow:
    # 1. Load leads from CSV
    # saved, failed = agent.load_leads_from_csv('leads/leads.csv')
    # print(f"Loaded {saved} leads, {failed} failed")
    
    # 2. Enrich leads
    # enrich_result = agent.enrich_leads(limit=10)
    # print(f"Enriched {enrich_result['enriched']} leads")
    
    # 3. Generate emails
    # gen_result = agent.generate_and_save_emails(limit=10)
    # print(f"Generated {gen_result['generated']} emails")
    
    # 4. Send emails
    # send_result = agent.send_pending_emails(max_to_send=5)
    # print(f"Sent {send_result['sent']}/{send_result['total']} emails")
    
    # 5. Check status
    # print(agent.get_detailed_report())


if __name__ == "__main__":
    main()

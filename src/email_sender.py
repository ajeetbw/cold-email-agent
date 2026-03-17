"""
Email sending module - handles SMTP sending with batching, delays, and retry logic.
"""

import smtplib
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.logger import logger
from src.config import get_config
from src.database import Email, EmailStatus, Lead, get_session


class EmailSender:
    """Sends emails via SMTP with batching and rate limiting."""
    
    def __init__(self):
        """Initialize email sender."""
        self.config = get_config()
        self.sender_email = self.config.get('smtp.sender_email')
        self.sender_name = self.config.get('smtp.sender_name', '')
        self.app_password = self.config.get('smtp.app_password')
        self.smtp_server = self.config.get('smtp.smtp_server', 'smtp.gmail.com')
        self.smtp_port = self.config.get('smtp.smtp_port', 587)
        self.timeout = self.config.get('sending.timeout_seconds', 30)
        
        # Rate limiting settings
        self.max_emails_per_day = self.config.get('sending.max_emails_per_day', 30)
        self.emails_per_hour = self.config.get('sending.emails_per_hour', 5)
        self.delay_min = self.config.get('sending.delay_between_emails_seconds_min', 45)
        self.delay_max = self.config.get('sending.delay_between_emails_seconds_max', 120)
        
        self._validate_config()
    
    def _validate_config(self) -> bool:
        """Validate SMTP configuration."""
        if not self.sender_email:
            logger.error("SMTP sender_email not configured")
            return False
        
        if not self.app_password:
            logger.error("SMTP app_password not configured")
            return False
        
        logger.info(f"SMTP configured: {self.smtp_server}:{self.smtp_port}")
        return True
    
    def _get_connection(self):
        """Create SMTP connection."""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout)
            server.starttls()
            server.login(self.sender_email, self.app_password)
            return server
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to SMTP: {str(e)}")
            raise
    
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Send a single email.
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            body: Email body (plain text)
            html_body: HTML version of body (optional)
        
        Returns:
            Tuple of (success, message/error)
        """
        # Validate inputs
        if not subject or not subject.strip():
            logger.error(f"Cannot send email to {to_email}: Empty subject")
            return False, "Subject line cannot be empty"
        
        if not body or not body.strip():
            logger.error(f"Cannot send email to {to_email}: Empty body")
            return False, "Email body cannot be empty"
        
        if not to_email or not to_email.strip():
            logger.error("Cannot send email: Empty recipient email")
            return False, "Recipient email cannot be empty"
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            
            # Add plain text
            msg.attach(MIMEText(body, 'plain'))
            
            # Add HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Send
            server = self._get_connection()
            try:
                server.send_message(msg)
                logger.info(f"Email sent successfully to {to_email}")
                return True, "Sent"
            finally:
                server.quit()
        
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient refused: {str(e)}"
            logger.warning(f"Error sending to {to_email}: {error_msg}")
            return False, error_msg
        except smtplib.SMTPSenderRefused as e:
            error_msg = f"Sender refused: {str(e)}"
            logger.error(f"SMTP configuration error: {error_msg}")
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.warning(f"Error sending to {to_email}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error sending to {to_email}: {error_msg}")
            return False, error_msg
    
    def _get_random_delay(self) -> float:
        """Get random delay between emails."""
        return random.uniform(self.delay_min, self.delay_max)
    
    def _check_rate_limits(self) -> Tuple[bool, str]:
        """
        Check if we can send emails based on daily/hourly limits.
        
        Returns:
            Tuple of (can_send, message)
        """
        session = get_session()
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_start = now - timedelta(hours=1)
            
            # Check daily limit
            today_sent = session.query(Email).filter(
                Email.status == EmailStatus.SENT.value,
                Email.sent_at >= today_start
            ).count()
            
            if today_sent >= self.max_emails_per_day:
                return False, f"Daily limit reached ({self.max_emails_per_day} emails/day). Send more tomorrow."
            
            # Check hourly limit
            hour_sent = session.query(Email).filter(
                Email.status == EmailStatus.SENT.value,
                Email.sent_at >= hour_start
            ).count()
            
            if hour_sent >= self.emails_per_hour:
                return False, f"Hourly limit reached ({self.emails_per_hour} emails/hour). Wait a bit."
            
            return True, "OK"
        finally:
            session.close()
    
    def send_batch(
        self,
        emails: List[Dict],
        max_send: Optional[int] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Send a batch of emails with rate limiting and delays.
        
        Args:
            emails: List of dicts with keys: {id, to_email, to_name, subject, body}
            max_send: Maximum emails to send in this batch
        
        Returns:
            Dictionary of {email_address: (success, message)}
        """
        if not emails:
            logger.warning("No emails to send")
            return {}
        
        # Check rate limits first
        can_send, msg = self._check_rate_limits()
        if not can_send:
            logger.warning(f"Rate limit: {msg}")
            return {}
        
        results = {}
        
        # Apply max_send limit to emails list
        emails_to_process = emails[:max_send] if max_send else emails
        
        for i, email_data in enumerate(emails_to_process):
            # Check rate limits before each email
            can_send, msg = self._check_rate_limits()
            if not can_send:
                logger.warning(f"Stopping batch: {msg}")
                break
            
            # Validate email data has required keys
            required_keys = {'id', 'to_email', 'to_name', 'subject', 'body'}
            if not all(k in email_data for k in required_keys):
                logger.error(f"Email data missing required keys. Found: {email_data.keys()}")
                results['unknown'] = (False, "Invalid email data structure")
                continue
            
            to_email = email_data['to_email']
            
            # Validate subject and body are not empty
            if not email_data['subject'].strip() or not email_data['body'].strip():
                logger.error(f"Refusing to send blank email to {to_email}")
                results[to_email] = (False, "Email content is empty (subject or body)")
                continue
            
            try:
                # Send email
                success, message = self.send_email(
                    to_email=to_email,
                    to_name=email_data['to_name'],
                    subject=email_data['subject'],
                    body=email_data['body']
                )
                
                results[to_email] = (success, message)
                
                # Update database
                session = get_session()
                try:
                    email_record = session.query(Email).filter(
                        Email.id == email_data['id']
                    ).first()
                    
                    if email_record:
                        if success:
                            email_record.status = EmailStatus.SENT.value
                            email_record.sent_at = datetime.utcnow()
                        else:
                            email_record.status = EmailStatus.FAILED.value
                            email_record.error_message = message
                        
                        email_record.attempt_count += 1
                        email_record.last_attempt_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"Updated email record {email_data['id']}: {email_record.status}")
                finally:
                    session.close()
                
                # Add delay before next email (except for last one)
                if i < len(emails_to_process) - 1:
                    delay = self._get_random_delay()
                    logger.info(f"Waiting {delay:.1f}s before next email...")
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"Error processing email {to_email}: {str(e)}")
                results[to_email] = (False, str(e))
        
        logger.info(f"Sent {sum(1 for s, _ in results.values() if s)}/{len(results)} emails")
        return results
    
    def retry_failed_emails(self, limit: int = 5) -> Dict[str, Tuple[bool, str]]:
        """
        Retry previously failed emails.
        
        Args:
            limit: Maximum failed emails to retry
        
        Returns:
            Dictionary of retry results
        """
        session = get_session()
        try:
            failed_emails = session.query(Email).filter(
                Email.status == EmailStatus.FAILED.value,
                Email.attempt_count < 3  # Max 3 attempts
            ).limit(limit).all()
            
            if not failed_emails:
                logger.info("No failed emails to retry")
                return {}
            
            logger.info(f"Retrying {len(failed_emails)} failed emails...")
            
            # Prepare emails for batch sending
            emails_to_send = []
            for email in failed_emails:
                emails_to_send.append({
                    'id': email.id,
                    'to_email': email.lead.email,
                    'to_name': email.lead.name,
                    'subject': email.subject,
                    'body': email.body
                })
            
            return self.send_batch(emails_to_send)
        finally:
            session.close()
    
    def get_sending_stats(self) -> Dict:
        """Get statistics about sent emails."""
        session = get_session()
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            total_sent = session.query(Email).filter(
                Email.status == EmailStatus.SENT.value
            ).count()
            
            today_sent = session.query(Email).filter(
                Email.status == EmailStatus.SENT.value,
                Email.sent_at >= today_start
            ).count()
            
            failed = session.query(Email).filter(
                Email.status == EmailStatus.FAILED.value
            ).count()
            
            pending = session.query(Email).filter(
                Email.status == EmailStatus.PENDING.value
            ).count()
            
            return {
                'total_sent': total_sent,
                'today_sent': today_sent,
                'failed': failed,
                'pending': pending,
                'daily_limit': self.max_emails_per_day,
                'remaining_today': max(0, self.max_emails_per_day - today_sent)
            }
        finally:
            session.close()


# Retry decorator for transient failures
def retry_on_error(max_attempts: int = 3, delay_seconds: int = 5):
    """Decorator to retry a function on transient errors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay_seconds}s...")
                    time.sleep(delay_seconds)
        return wrapper
    return decorator

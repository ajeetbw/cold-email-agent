"""
Email generation module - creates personalized emails using OpenAI.
"""

import os
from typing import Dict, Optional, Tuple
from datetime import datetime
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.logger import logger
from src.config import get_config
from src.database import Lead, EmailTemplate, get_session


class EmailGenerator:
    """Generates personalized emails using AI."""
    
    def __init__(self):
        """Initialize email generator."""
        self.config = get_config()
        self.client = None
        self.model = self.config.get('ai.model', 'gpt-3.5-turbo')
        self.temperature = self.config.get('ai.temperature', 0.7)
        
        # Initialize OpenAI client
        api_key = self.config.get('ai.api_key')
        if api_key and OpenAI:
            self.client = OpenAI(api_key=api_key)
        elif not api_key:
            logger.warning("OpenAI API key not configured in config.yaml")
        elif not OpenAI:
            logger.warning("OpenAI library not installed. Install with: pip install openai")
    
    def _is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return self.client is not None
    
    def generate_email(
        self,
        lead: Lead,
        sender_name: Optional[str] = None,
        company_context: Optional[str] = None,
        email_type: str = "initial"
    ) -> Tuple[bool, str, str]:
        """
        Generate a personalized email for a lead.
        
        Args:
            lead: Lead object
            sender_name: Name of the sender (from config if not provided)
            company_context: Context about the lead's company (enrichment data)
            email_type: Type of email ('initial', 'follow_up_1', 'follow_up_2')
        
        Returns:
            Tuple of (success, subject, body)
        """
        if not self._is_configured():
            logger.error("OpenAI not configured")
            return False, "", ""
        
        sender_name = sender_name or self.config.get('smtp.sender_name', 'Team')
        company_context = company_context or lead.company_summary or f"{lead.company} company"
        
        # Create prompt
        if email_type == "initial":
            prompt = self._create_initial_email_prompt(
                lead=lead,
                sender_name=sender_name,
                company_context=company_context
            )
        elif email_type == "follow_up_1":
            prompt = self._create_followup_email_prompt(
                lead=lead,
                sender_name=sender_name,
                followup_number=1
            )
        else:  # follow_up_2
            prompt = self._create_followup_email_prompt(
                lead=lead,
                sender_name=sender_name,
                followup_number=2
            )
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cold email copywriter. Create short, personalized, non-spammy emails that are human and conversational."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=500
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract subject and body
            if "Subject:" in content and "Body:" in content:
                parts = content.split("Body:", 1)
                subject_part = parts[0].split("Subject:", 1)[1].strip()
                subject = subject_part.split("\n")[0].strip()
                body = parts[1].strip()
            else:
                # Fallback: assume first line is subject
                lines = content.split("\n", 1)
                subject = lines[0].strip()[:100]  # Limit to 100 chars
                body = lines[1].strip() if len(lines) > 1 else content
            
            logger.info(f"Generated email for {lead.email} ({email_type})")
            return True, subject, body
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            return False, "", ""
    
    def _create_initial_email_prompt(
        self,
        lead: Lead,
        sender_name: str,
        company_context: str
    ) -> str:
        """Create prompt for initial email."""
        return f"""Create a short, personalized cold email for the following person:

Name: {lead.name}
Email: {lead.email}
Company: {lead.company}
Job Role: {lead.role}
Company Info: {company_context}

IMPORTANT RULES:
1. Keep it SHORT (3-4 sentences max)
2. Make it PERSONAL and HUMAN (not templated)
3. NO SPAM - don't use salesy language
4. NO ALL-CAPS except for emphasis
5. Include a specific reason why you're reaching out
6. End with a single, clear call to action
7. The email should feel like it's from a real person

Format your response as:
Subject: [Your subject line]

Body:
[Your email body]

Remember: This person gets hundreds of emails. Make it interesting."""
    
    def _create_followup_email_prompt(
        self,
        lead: Lead,
        sender_name: str,
        followup_number: int
    ) -> str:
        """Create prompt for follow-up email."""
        if followup_number == 1:
            context = "This is the first follow-up (3 days after initial email). Keep it short and reference your first email."
        else:
            context = "This is the final follow-up (7 days after initial email). Make it brief and acknowledge if they're not interested."
        
        return f"""Create a short follow-up email for:

Name: {lead.name}
Email: {lead.email}
Company: {lead.company}
Job Role: {lead.role}

{context}

IMPORTANT RULES:
1. Keep it SHORT (2-3 sentences)
2. Respect their time and inbox
3. Don't be pushy
4. If it's the final follow-up, make it easy for them to say no
5. Add value or reason for reaching out again

Format your response as:
Subject: [Your subject line]

Body:
[Your email body]"""
    
    def generate_batch_emails(
        self,
        leads: list,
        email_type: str = "initial"
    ) -> Dict[str, Tuple[str, str]]:
        """
        Generate emails for multiple leads.
        
        Args:
            leads: List of Lead objects
            email_type: Type of email to generate
        
        Returns:
            Dictionary of {email: (subject, body)}
        """
        results = {}
        
        for i, lead in enumerate(leads, start=1):
            logger.info(f"Generating email {i}/{len(leads)} for {lead.email}")
            
            success, subject, body = self.generate_email(
                lead=lead,
                email_type=email_type
            )
            
            if success:
                results[lead.email] = (subject, body)
            
            # Rate limiting: OpenAI has rate limits
            if i < len(leads):
                import time
                time.sleep(1)  # 1 second between requests
        
        logger.info(f"Generated {len(results)} emails successfully")
        return results
    
    def preview_email(
        self,
        lead: Lead,
        subject: str,
        body: str
    ) -> str:
        """Generate a preview of the email."""
        return f"""
=== EMAIL PREVIEW ===
To: {lead.email}
To Name: {lead.name}
Company: {lead.company}

Subject: {subject}

{body}

========================
"""


class TemplateEmailGenerator:
    """Generate emails using pre-defined templates."""
    
    @staticmethod
    def generate_from_template(
        lead: Lead,
        template_name: str,
        sender_name: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Generate email from a template.
        
        Args:
            lead: Lead object
            template_name: Name of the template to use
            sender_name: Sender name for personalization
        
        Returns:
            Tuple of (success, subject, body)
        """
        sender_name = sender_name or ""
        
        session = get_session()
        try:
            template = session.query(EmailTemplate).filter(
                EmailTemplate.name == template_name
            ).first()
            
            if not template:
                logger.error(f"Template not found: {template_name}")
                return False, "", ""
            
            # Prepare replacement variables
            replacements = {
                '{name}': lead.name,
                '{company}': lead.company,
                '{role}': lead.role,
                '{company_summary}': lead.company_summary or lead.company,
                '{sender_name}': sender_name,
            }
            
            # Replace in subject
            subject = template.subject_template
            for placeholder, value in replacements.items():
                subject = subject.replace(placeholder, value)
            
            # Replace in body
            body = template.body_template
            for placeholder, value in replacements.items():
                body = body.replace(placeholder, value)
            
            logger.info(f"Generated email from template '{template_name}' for {lead.email}")
            return True, subject, body
            
        except Exception as e:
            logger.error(f"Error generating from template: {str(e)}")
            return False, "", ""
        finally:
            session.close()
    
    @staticmethod
    def create_template(
        name: str,
        subject_template: str,
        body_template: str
    ) -> bool:
        """Create a new email template."""
        session = get_session()
        try:
            template = EmailTemplate(
                name=name,
                subject_template=subject_template,
                body_template=body_template,
                updated_at=datetime.utcnow()
            )
            session.add(template)
            session.commit()
            logger.info(f"Created email template: {name}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating template: {str(e)}")
            return False
        finally:
            session.close()
    
    @staticmethod
    def list_templates() -> list:
        """List all available templates."""
        session = get_session()
        try:
            templates = session.query(EmailTemplate).all()
            return [(t.name, t.subject_template[:50] + "..." if len(t.subject_template) > 50 else t.subject_template) for t in templates]
        finally:
            session.close()

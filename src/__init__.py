"""
Cold Email Outreach Agent - Production-ready system
"""

from src.config import get_config, Config
from src.logger import logger
from src.database import get_db_manager, get_session, Lead, Email, EmailTemplate
from src.lead_input import LeadInputManager
from src.email_generator import EmailGenerator, TemplateEmailGenerator
from src.email_sender import EmailSender
from src.lead_enrichment import LeadEnricher
from src.scheduler import FollowUpScheduler, CampaignManager

__version__ = "1.0.0"
__all__ = [
    'get_config',
    'Config',
    'logger',
    'get_db_manager',
    'get_session',
    'Lead',
    'Email',
    'EmailTemplate',
    'LeadInputManager',
    'EmailGenerator',
    'TemplateEmailGenerator',
    'EmailSender',
    'LeadEnricher',
    'FollowUpScheduler',
    'CampaignManager'
]

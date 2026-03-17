"""
Lead enrichment module - fetches company information and enriches lead data.
"""

import requests
from typing import Optional, Dict, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.logger import logger
from src.config import get_config
from src.database import Lead, get_session


class LeadEnricher:
    """Enriches lead data with company information."""
    
    def __init__(self):
        """Initialize lead enricher."""
        self.config = get_config()
        self.timeout = self.config.get('enrichment.website_timeout_seconds', 10)
        self.fetch_website = self.config.get('enrichment.fetch_website_content', True)
        self.user_agent = self.config.get('enrichment.user_agent')
    
    def enrich_lead(
        self,
        lead: Lead,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Enrich a lead with company information.
        
        Args:
            lead: Lead object to enrich
            force: Force re-enrichment even if already enriched
        
        Returns:
            Tuple of (success, message)
        """
        if lead.enriched_at and not force:
            logger.info(f"Lead {lead.email} already enriched on {lead.enriched_at}")
            return True, "Already enriched"
        
        enrichment_source = "none"
        
        # Fetch website content if available
        if self.fetch_website and lead.website:
            company_info = self._fetch_website_content(lead.website)
            if company_info:
                lead.company_summary = company_info
                enrichment_source = "website"
                logger.info(f"Successfully enriched {lead.email} from website")
            else:
                logger.warning(f"Failed to fetch content from {lead.website} for {lead.email}")
        
        # If no website or fetch failed, create basic summary
        if not lead.company_summary:
            lead.company_summary = self._create_basic_summary(lead)
            if enrichment_source == "none":
                enrichment_source = "fallback"
                logger.info(f"Using fallback summary for {lead.email} (no website available)")
        
        # Update enrichment timestamp
        lead.enriched_at = datetime.utcnow()
        
        # Save to database
        session = get_session()
        try:
            session.merge(lead)
            session.commit()
            logger.info(f"Enriched lead {lead.email} via {enrichment_source}")
            return True, f"Enrichment completed via {enrichment_source}"
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving enriched lead: {str(e)}")
            return False, str(e)
        finally:
            session.close()
    
    def _fetch_website_content(self, website_url: str) -> Optional[str]:
        """
        Fetch and parse website content.
        
        Args:
            website_url: Website URL
        
        Returns:
            Extracted text or None if failed
        """
        if not website_url:
            return None
        
        # Ensure URL has protocol
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        try:
            headers = {
                'User-Agent': self.user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            
            response = requests.get(
                website_url,
                timeout=self.timeout,
                headers=headers,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {website_url}: HTTP {response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract relevant content
            text = self._extract_relevant_content(soup)
            
            if text:
                logger.info(f"Fetched content from {website_url}")
                return text[:500]  # Limit to 500 chars
            
            return None
        
        except requests.Timeout:
            logger.warning(f"Timeout fetching {website_url}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Error fetching {website_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing website content: {str(e)}")
            return None
    
    def _extract_relevant_content(self, soup: BeautifulSoup) -> str:
        """
        Extract relevant content from parsed HTML.
        
        Strategy:
        1. Look for meta descriptions
        2. Extract text from main content areas
        3. Clean up and summarize
        """
        text_parts = []
        
        # Try to get meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            text_parts.append(meta_desc['content'])
        
        # Extract from common content areas
        for tag in ['main', 'article', '[role="main"]']:
            content = soup.find(tag)
            if content:
                # Remove script and style elements
                for script in content(['script', 'style']):
                    script.decompose()
                
                text = content.get_text(separator=' ', strip=True)
                if text:
                    text_parts.append(text[:300])
                break
        
        # Fallback: first meaningful paragraph
        if not text_parts:
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 50:
                    text_parts.append(text)
                    break
        
        # If still empty, get first 200 chars of body
        if not text_parts:
            body = soup.find('body')
            if body:
                for script in body(['script', 'style']):
                    script.decompose()
                text = body.get_text(separator=' ', strip=True)
                if text:
                    text_parts.append(text[:300])
        
        return ' '.join(text_parts)
    
    def _create_basic_summary(self, lead: Lead) -> str:
        """Create a basic summary when website data is unavailable."""
        return f"{lead.company} is a company where {lead.name} works as a {lead.role}."
    
    def enrich_batch(self, leads: list, max_errors: int = 5) -> Dict[str, Tuple[bool, str]]:
        """
        Enrich multiple leads.
        
        Args:
            leads: List of Lead objects
            max_errors: Stop after this many errors
        
        Returns:
            Dictionary of {email: (success, message)}
        """
        results = {}
        error_count = 0
        
        for i, lead in enumerate(leads, start=1):
            try:
                success, message = self.enrich_lead(lead)
                results[lead.email] = (success, message)
                
                if not success:
                    error_count += 1
                    if error_count >= max_errors:
                        logger.warning(f"Reached error limit ({max_errors}), stopping enrichment")
                        break
            
            except Exception as e:
                logger.error(f"Error enriching {lead.email}: {str(e)}")
                results[lead.email] = (False, str(e))
                error_count += 1
        
        successful = sum(1 for s, _ in results.values() if s)
        logger.info(f"Enriched {successful}/{len(results)} leads")
        return results
    
    def get_enrichment_status(self, lead: Lead) -> Dict:
        """Get enrichment status for a lead."""
        return {
            'email': lead.email,
            'enriched': lead.enriched_at is not None,
            'enriched_at': lead.enriched_at.isoformat() if lead.enriched_at else None,
            'has_summary': bool(lead.company_summary),
            'summary_preview': lead.company_summary[:100] + "..." if lead.company_summary and len(lead.company_summary) > 100 else lead.company_summary
        }


# Standard enrichment data sources (for future expansion)
class DataEnrichedDatabase:
    """
    Interface for third-party enrichment databases.
    
    Ideas:
    - Company House API (UK)
    - Crunchbase API
    - Hunter.io (email validation and domain data)
    - RocketReach
    
    NOTE: This is for future expansion. Keep it ethical and respect Terms of Service.
    """
    pass

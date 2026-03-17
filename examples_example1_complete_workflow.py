#!/usr/bin/env python3
"""
Example 1: Complete Workflow
Demonstrates the full workflow from loading to sending.
"""

from src.agent import ColdEmailAgent
from src.logger import logger


def main():
    """Run complete workflow example."""
    
    # Initialize agent
    print("=" * 60)
    print("EXAMPLE 1: Complete Workflow")
    print("=" * 60)
    
    agent = ColdEmailAgent()
    
    # Step 1: Load leads from CSV
    print("\n[Step 1] Loading leads from CSV...")
    saved, failed = agent.load_leads_from_csv('leads/example_leads.csv')
    print(f"✓ Loaded {saved} leads ({failed} failed)")
    
    # Step 2: Enrich leads with company data
    print("\n[Step 2] Enriching leads...")
    result = agent.enrich_leads(limit=3)
    print(f"✓ Enriched {result['enriched']} leads")
    
    # Step 3: Generate personalized emails
    print("\n[Step 3] Generating personalized emails...")
    result = agent.generate_and_save_emails(limit=3)
    print(f"✓ Generated {result['generated']} emails")
    
    # Step 4: Preview emails before sending
    print("\n[Step 4] Email preview:")
    from src.database import get_session, Email, EmailStatus
    session = get_session()
    try:
        pending = session.query(Email).filter(
            Email.status == EmailStatus.PENDING.value
        ).limit(1).first()
        
        if pending:
            print(f"\nTo: {pending.lead.email}")
            print(f"Name: {pending.lead.name}")
            print(f"Company: {pending.lead.company}")
            print(f"\nSubject: {pending.subject}")
            print(f"\nBody:\n{pending.body}")
    finally:
        session.close()
    
    # Step 5: Send emails
    print("\n[Step 5] Sending emails (respects rate limits)...")
    result = agent.send_pending_emails(max_to_send=2)
    print(f"✓ Sent {result['sent']} emails ({result['failed']} failed)")
    
    # Step 6: Show status
    print("\n[Step 6] Final Status:")
    print(agent.get_detailed_report())


if __name__ == '__main__':
    main()

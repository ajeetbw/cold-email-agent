#!/usr/bin/env python3
"""
Example 3: Follow-ups and Scheduling
Demonstrates follow-up automation and campaign tracking.
"""

from src.agent import ColdEmailAgent
from src.scheduler import CampaignManager
from src.database import get_session, Lead, Email, EmailStatus


def main():
    """Follow-ups and scheduling example."""
    
    print("=" * 60)
    print("EXAMPLE 3: Follow-ups and Campaign Tracking")
    print("=" * 60)
    
    agent = ColdEmailAgent()
    
    # Step 1: Load and process leads
    print("\n[Step 1] Loading leads...")
    saved, _ = agent.load_leads_from_csv('leads/example_leads.csv')
    print(f"✓ Loaded {saved} leads")
    
    # Step 2: Enrich and generate
    print("\n[Step 2] Enriching and generating initial emails...")
    agent.enrich_leads(limit=5)
    agent.generate_and_save_emails(limit=5, email_type='initial')
    
    # Step 3: Create a campaign
    print("\n[Step 3] Creating campaign...")
    session = get_session()
    try:
        leads = session.query(Lead).limit(3).all()
        campaign_id = 'campaign_001'
        
        email_subjects = {lead.id: f'Quick question for {lead.name}' for lead in leads}
        email_bodies = {lead.id: f'Hi {lead.name}, would love to connect...' for lead in leads}
        
        success, msg = CampaignManager.create_campaign(
            campaign_id=campaign_id,
            lead_ids=[l.id for l in leads],
            email_subjects=email_subjects,
            email_bodies=email_bodies
        )
        print(f"✓ {msg}")
    finally:
        session.close()
    
    # Step 4: Send initial emails
    print("\n[Step 4] Sending initial emails...")
    result = agent.send_pending_emails(max_to_send=2)
    print(f"✓ Sent {result['sent']} emails")
    
    # Step 5: Check follow-up status
    print("\n[Step 5] Follow-up Status:")
    followup_status = agent.scheduler.get_followup_stats()
    print(f"  Initial emails sent: {followup_status['initial_emails_sent']}")
    print(f"  First follow-ups created: {followup_status['first_followups_created']}")
    print(f"  Second follow-ups created: {followup_status['second_followups_created']}")
    print(f"  Replies received: {followup_status['replies_received']}")
    
    # Step 6: Campaign statistics
    print("\n[Step 6] Campaign Statistics:")
    stats = CampaignManager.get_campaign_stats(campaign_id)
    print(f"  Campaign ID: {stats['campaign_id']}")
    print(f"  Total emails: {stats['total_emails']}")
    print(f"  Sent: {stats['sent']}")
    print(f"  Send rate: {stats['send_rate']:.1f}%")
    
    print("\n[Note] In production:")
    print("  - Wait 3 days, then run: agent.schedule_followups('follow_up_1')")
    print("  - This will generate first follow-up emails")
    print("  - Send them with: agent.send_pending_emails()")
    print("  - Wait 7 days total, then schedule follow_up_2")


if __name__ == '__main__':
    main()

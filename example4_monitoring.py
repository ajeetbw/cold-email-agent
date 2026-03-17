#!/usr/bin/env python3
"""
Example 4: Monitoring and Analytics
Demonstrates how to monitor system health and performance.
"""

from src.agent import ColdEmailAgent
from src.database import get_session, Email, Lead, EmailStatus


def main():
    """Monitoring and analytics example."""
    
    print("=" * 60)
    print("EXAMPLE 4: Monitoring and Analytics")
    print("=" * 60)
    
    agent = ColdEmailAgent()
    
    # Get comprehensive status
    print("\n[System Status]")
    status = agent.get_status()
    
    print("\nLead Statistics:")
    print(f"  Total leads: {status['leads']['total']}")
    print(f"  Enriched: {status['leads']['enriched']}")
    print(f"  Pending enrichment: {status['leads']['pending_enrichment']}")
    
    print("\nEmail Sending Statistics:")
    print(f"  Total sent: {status['emails']['total_sent']}")
    print(f"  Sent today: {status['emails']['today_sent']}")
    print(f"  Daily limit: {status['emails']['daily_limit']}")
    print(f"  Remaining today: {status['emails']['remaining_today']}")
    print(f"  Failed emails: {status['emails']['failed']}")
    print(f"  Pending emails: {status['emails']['pending']}")
    
    print("\nFollow-up Statistics:")
    print(f"  Initial emails sent: {status['follow_ups']['initial_emails_sent']}")
    print(f"  First follow-ups: {status['follow_ups']['first_followups_created']}")
    print(f"  Second follow-ups: {status['follow_ups']['second_followups_created']}")
    print(f"  Replies received: {status['follow_ups']['replies_received']}")
    if status['follow_ups']['initial_emails_sent'] > 0:
        print(f"  Reply rate: {status['follow_ups']['reply_rate']:.1f}%")
    
    # Detailed report
    print(agent.get_detailed_report())
    
    # Database query examples
    print("\n[Email Status Breakdown]")
    session = get_session()
    try:
        for email_status in EmailStatus:
            count = session.query(Email).filter(
                Email.status == email_status.value
            ).count()
            print(f"  {email_status.value.capitalize()}: {count}")
        
        # Top recipients
        print("\n[Recent Emails]")
        recent = session.query(Email).order_by(Email.created_at.desc()).limit(5).all()
        for email in recent:
            status_emoji = {
                'sent': '✓',
                'pending': '⏳',
                'failed': '✗',
                'replied': '↩'
            }.get(email.status, '?')
            
            print(f"  {status_emoji} {email.lead.email} - {email.status}")
    
    finally:
        session.close()
    
    # Failed emails investigation
    print("\n[Failed Emails Investigation]")
    session = get_session()
    try:
        failed = session.query(Email).filter(
            Email.status == EmailStatus.FAILED.value
        ).limit(5).all()
        
        if not failed:
            print("  No failed emails (Great!)")
        else:
            for email in failed:
                print(f"\n  Email to: {email.lead.email}")
                print(f"  Error: {email.error_message}")
                print(f"  Attempts: {email.attempt_count}")
    
    finally:
        session.close()


if __name__ == '__main__':
    main()

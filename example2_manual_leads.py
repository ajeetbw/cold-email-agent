#!/usr/bin/env python3
"""
Example 2: Adding Leads Manually
Demonstrates how to add leads programmatically.
"""

from src.agent import ColdEmailAgent


def main():
    """Add leads manually example."""
    
    print("=" * 60)
    print("EXAMPLE 2: Adding Leads Manually")
    print("=" * 60)
    
    agent = ColdEmailAgent()
    
    # Example leads to add
    leads_to_add = [
        {
            'name': 'Alice Johnson',
            'email': 'alice.j@startup.io',
            'company': 'StartupAI',
            'role': 'Head of Marketing',
            'website': 'startupai.io'
        },
        {
            'name': 'Bob Wilson',
            'email': 'bob.wilson@enterprise.com',
            'company': 'Enterprise Corp',
            'role': 'Director of Technology',
            'website': 'enterprise.com'
        },
        {
            'name': 'Carol Davis',
            'email': 'carol.d@tech.company',
            'company': 'Tech Company',
            'role': 'Engineering Manager',
            'website': 'techcompany.com'
        }
    ]
    
    # Add each lead
    print("\n[Adding Leads]")
    for lead_data in leads_to_add:
        success = agent.add_lead(**lead_data)
        status = "✓" if success else "✗"
        print(f"{status} {lead_data['name']} ({lead_data['email']})")
    
    # Enrich them
    print("\n[Enriching Leads]")
    result = agent.enrich_leads(limit=10)
    print(f"✓ Enriched {result['enriched']} leads")
    
    # Generate emails
    print("\n[Generating Emails]")
    result = agent.generate_and_save_emails(limit=10, email_type='initial')
    print(f"✓ Generated {result['generated']} emails")
    
    # Send emails
    print("\n[Sending Emails]")
    result = agent.send_pending_emails(max_to_send=3)
    print(f"✓ Sent {result['sent']} emails")
    
    # Show results
    print(agent.get_detailed_report())


if __name__ == '__main__':
    main()

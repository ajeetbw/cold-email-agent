#!/usr/bin/env python3
"""
Cold Email Agent - Main CLI Interface
Run with: python main.py
"""

import sys
import argparse
from typing import Optional

from src.agent import ColdEmailAgent
from src.logger import logger


def print_header():
    """Print application header."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         COLD EMAIL OUTREACH AGENT v1.0                  ║
║      Production-Ready | Ethical | Anti-Spam            ║
╚═══════════════════════════════════════════════════════════╝
    """)


def cmd_status(agent: ColdEmailAgent, _args) -> None:
    """Show system status."""
    print(agent.get_detailed_report())


def cmd_load_csv(agent: ColdEmailAgent, args) -> None:
    """Load leads from CSV."""
    csv_file = args.csv or 'leads/example_leads.csv'
    print(f"\n📂 Loading leads from: {csv_file}")
    
    saved, failed = agent.load_leads_from_csv(csv_file)
    
    print(f"\n✅ Loaded {saved} leads")
    if failed:
        print(f"⚠️  {failed} leads failed validation")


def cmd_enrich(agent: ColdEmailAgent, args) -> None:
    """Enrich leads with company data."""
    limit = args.limit or 10
    print(f"\n🔍 Enriching up to {limit} leads...")
    
    result = agent.enrich_leads(limit=limit)
    
    print(f"✅ Enriched {result['enriched']} leads")
    if result['failed']:
        print(f"⚠️  {result['failed']} enrichment failures")


def cmd_generate(agent: ColdEmailAgent, args) -> None:
    """Generate emails."""
    limit = args.limit or 10
    email_type = args.type or 'initial'
    
    print(f"\n✍️  Generating {email_type} emails for up to {limit} leads...")
    
    result = agent.generate_and_save_emails(limit=limit, email_type=email_type)
    
    print(f"✅ Generated {result['generated']} emails")
    if result['failed']:
        print(f"⚠️  {result['failed']} generation failures")


def cmd_send(agent: ColdEmailAgent, args) -> None:
    """Send pending emails."""
    max_to_send = args.max or 5
    
    # Show current limits
    status = agent.get_status()
    remaining = status['emails']['remaining_today']
    
    if remaining <= 0:
        print("\n⏹️  Daily sending limit reached!")
        print(f"   Sent {status['emails']['today_sent']} emails today")
        return
    
    max_to_send = min(max_to_send, remaining)
    
    print(f"\n📧 Sending up to {max_to_send} pending emails...")
    print(f"   (Daily limit: {status['emails']['remaining_today']} remaining)")
    
    result = agent.send_pending_emails(max_to_send=max_to_send)
    
    print(f"✅ Sent {result['sent']} emails successfully")
    if result['failed']:
        print(f"⚠️  {result['failed']} emails failed")


def cmd_retry(agent: ColdEmailAgent, args) -> None:
    """Retry failed emails."""
    limit = args.limit or 5
    
    print(f"\n🔄 Retrying up to {limit} failed emails...")
    
    result = agent.retry_failed_emails(limit=limit)
    
    print(f"✅ Retried {result['retried']} emails")
    print(f"   Successful: {result['successful']}")
    print(f"   Failed: {result['failed']}")


def cmd_followup(agent: ColdEmailAgent, args) -> None:
    """Schedule follow-ups."""
    followup_type = args.type or 'follow_up_1'
    
    print(f"\n📬 Scheduling {followup_type}s...")
    
    result = agent.schedule_followups(followup_type)
    
    print(f"✅ Scheduled {result['scheduled']} follow-ups")
    print(f"   Total due: {result['total_due']}")


def cmd_add_lead(agent: ColdEmailAgent, args) -> None:
    """Add a single lead manually."""
    print(f"\n➕ Adding lead manually...")
    
    name = args.name
    email = args.email
    company = args.company
    role = args.role
    website = args.website or None
    
    success = agent.add_lead(
        name=name,
        email=email,
        company=company,
        role=role,
        website=website
    )
    
    if success:
        print(f"✅ Lead added: {name} ({email})")
    else:
        print(f"❌ Failed to add lead")


def cmd_export(agent: ColdEmailAgent, args) -> None:
    """Export leads to CSV."""
    output_file = args.output or 'leads/export.csv'
    
    print(f"\n💾 Exporting leads to: {output_file}")
    
    success = agent.export_results(output_file)
    
    if success:
        print(f"✅ Exported successfully")
    else:
        print(f"❌ Export failed")


def main():
    """Main CLI entry point."""
    print_header()
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Cold Email Agent - Production-Ready Outreach System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py status                               # Show current status
  python main.py load-csv --csv leads/my_leads.csv   # Load from CSV
  python main.py enrich --limit 20                    # Enrich leads
  python main.py generate --limit 10 --type initial  # Generate emails
  python main.py send --max 5                        # Send emails
  python main.py retry --limit 5                     # Retry failures
  python main.py followup --type follow_up_1         # Schedule follow-ups
  python main.py add-lead --name "John" --email "j@ex.com" --company "ABC" --role "CTO"
  python main.py export --output leads/results.csv   # Export results
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Status command
    subparsers.add_parser('status', help='Show system status and stats')
    
    # Load CSV command
    load_parser = subparsers.add_parser('load-csv', help='Load leads from CSV')
    load_parser.add_argument('--csv', help='Path to CSV file', default='leads/example_leads.csv')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich leads with company data')
    enrich_parser.add_argument('--limit', type=int, help='Max leads to enrich', default=10)
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate personalized emails')
    gen_parser.add_argument('--limit', type=int, help='Max leads to process', default=10)
    gen_parser.add_argument('--type', help='Email type (initial, follow_up_1, follow_up_2)', 
                           default='initial')
    
    # Send command
    send_parser = subparsers.add_parser('send', help='Send pending emails')
    send_parser.add_argument('--max', type=int, help='Max emails to send', default=5)
    
    # Retry command
    retry_parser = subparsers.add_parser('retry', help='Retry failed emails')
    retry_parser.add_argument('--limit', type=int, help='Max emails to retry', default=5)
    
    # Follow-up command
    followup_parser = subparsers.add_parser('followup', help='Schedule follow-ups')
    followup_parser.add_argument('--type', help='Follow-up type (follow_up_1, follow_up_2)',
                                default='follow_up_1')
    
    # Add lead command
    add_parser = subparsers.add_parser('add-lead', help='Add a lead manually')
    add_parser.add_argument('--name', required=True, help='Lead name')
    add_parser.add_argument('--email', required=True, help='Lead email')
    add_parser.add_argument('--company', required=True, help='Company name')
    add_parser.add_argument('--role', required=True, help='Job role')
    add_parser.add_argument('--website', help='Company website (optional)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export leads to CSV')
    export_parser.add_argument('--output', help='Output file path', default='leads/export.csv')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command, show help
    if not args.command:
        parser.print_help()
        return
    
    # Initialize agent
    try:
        logger.info(f"Initializing agent for command: {args.command}")
        agent = ColdEmailAgent()
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    
    # Command dispatch
    commands = {
        'status': cmd_status,
        'load-csv': cmd_load_csv,
        'enrich': cmd_enrich,
        'generate': cmd_generate,
        'send': cmd_send,
        'retry': cmd_retry,
        'followup': cmd_followup,
        'add-lead': cmd_add_lead,
        'export': cmd_export,
    }
    
    # Execute command
    try:
        if args.command in commands:
            commands[args.command](agent, args)
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

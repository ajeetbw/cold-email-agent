# QUICK START GUIDE

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Get Your Credentials

#### Gmail API Password:
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer"
3. Copy the 16-character password
4. Paste in `.env` file as `APP_PASSWORD`

#### OpenAI API Key:
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy it to `.env` file as `OPENAI_API_KEY`

### Step 3: Configure

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
APP_PASSWORD=xxxx xxxx xxxx xxxx
OPENAI_API_KEY=sk-...your-key...
```

Edit `config/config.yaml` - update your email:
```yaml
smtp:
  sender_email: 'YOUR_EMAIL@gmail.com'
  sender_name: 'Your Name'
```

### Step 4: Try It Out

Open Python:
```bash
python
```

```python
from src.agent import ColdEmailAgent

# Initialize
agent = ColdEmailAgent()

# Check status
print(agent.get_detailed_report())
```

## Common Workflows

### Load CSV and Send Emails

```python
from src.agent import ColdEmailAgent

agent = ColdEmailAgent()

# 1. Load leads
print("Loading leads...")
saved, failed = agent.load_leads_from_csv('leads/example_leads.csv')
print(f"✓ Loaded {saved} leads")

# 2. Enrich with company data
print("\nEnriching leads...")
result = agent.enrich_leads(limit=3)
print(f"✓ Enriched {result['enriched']} leads")

# 3. Generate personalized emails
print("\nGenerating emails...")
result = agent.generate_and_save_emails(limit=3)
print(f"✓ Generated {result['generated']} emails")

# 4. Send emails (safe rate-limited)
print("\nSending emails...")
result = agent.send_pending_emails(max_to_send=2)
print(f"✓ Sent {result['sent']} emails")

# 5. Check status
print(agent.get_detailed_report())
```

### Add Single Lead

```python
from src.agent import ColdEmailAgent

agent = ColdEmailAgent()

# Add lead
agent.add_lead(
    name="Jane Doe",
    email="jane@company.com",
    company="Tech Corp",
    role="Engineering Manager",
    website="techcorp.com"
)

# Process it
agent.enrich_leads()
agent.generate_and_save_emails(limit=1)
agent.send_pending_emails(max_to_send=1)
```

### Schedule Follow-ups

```python
from src.agent import ColdEmailAgent

agent = ColdEmailAgent()

# Create first follow-ups (3 days after initial)
print("Scheduling first follow-ups...")
result = agent.schedule_followups('follow_up_1')
print(f"Scheduled {result['scheduled']} follow-ups")

# Send them
print("\nSending follow-ups...")
agent.send_pending_emails(max_to_send=5)
```

### Retry Failed Emails

```python
from src.agent import ColdEmailAgent

agent = ColdEmailAgent()

# Retry failed emails
result = agent.retry_failed_emails(limit=5)
print(f"Retried {result['successful']}/{result['retried']} emails")
```

## Monitoring

### View Current Status
```python
from src.agent import ColdEmailAgent

agent = ColdEmailAgent()
print(agent.get_detailed_report())
```

### Check Logs
```bash
tail -f logs/agent.log
```

### Database Queries
```python
from src.database import get_session, Lead, Email, EmailStatus

session = get_session()

# Count sent emails
sent = session.query(Email).filter(
    Email.status == EmailStatus.SENT.value
).count()

print(f"Total sent: {sent}")

# Get failed emails
failed = session.query(Email).filter(
    Email.status == EmailStatus.FAILED.value
).all()

for email in failed:
    print(f"Failed: {email.lead.email} - {email.error_message}")

session.close()
```

## CSV Format

Your CSV file should have these columns:

```
name,email,company,role,website
John Doe,john@example.com,ABC Corp,CTO,abccorp.com
Jane Smith,jane@example.com,XYZ Inc,VP Sales,xyz.com
```

**Required**: name, email, company, role
**Optional**: website

## Troubleshooting

### "Invalid credentials" Error
- Check your Gmail app password is correct
- Verify you're using the 16-character password (without spaces)
- If issues persist, generate a new app password

### "No module named 'openai'"
- Run: `pip install -r requirements.txt`
- Verify with: `pip list | grep openai`

### Emails not sending
- Check logs: `tail -f logs/agent.log`
- Verify SMTP settings in config.yaml
- Test with a single email first

### Rate limit errors
- This is normal - the system respects sending limits
- Wait a bit and try again
- Or check stats with `agent.get_status()`

## Rate Limits (Built-in Safety)

The system has built-in safeguards:
- **30 emails/day** maximum
- **5 emails/hour** maximum
- **45-120 seconds** delay between emails (randomized)

These protect you from spam filters and ensure decent delivery.

## Next Steps

1. ✅ Get credentials and configure
2. ✅ Load test leads with example CSV
3. ✅ Send a few test emails
4. ✅ Check delivery and open rates
5. ✅ Gradually scale up
6. ✅ Monitor and optimize

---

**Questions?** Check the README.md for full documentation

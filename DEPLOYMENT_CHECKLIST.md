# ✅ DEPLOYMENT CHECKLIST - Quick Reference

Use this checklist to prepare for production deployment.

---

## PRE-DEPLOYMENT VERIFICATION

### Code Quality
- [ ] All 9 bugs fixed (review BUG_FIXES_DETAILED.md)
- [ ] Run `python -m pytest tests/test_agent.py -v`
- [ ] All unit tests pass
- [ ] No syntax errors: `python -m py_compile src/*.py`
- [ ] Logging configured correctly (check `logs/agent.log`)

### Configuration
- [ ] `config/config.yaml` created with actual values
- [ ] `.env` file created with secrets:
  ```
  OPENAI_API_KEY=sk-...
  SMTP_USER=your-email@gmail.com
  SMTP_PASSWORD=app-specific-password
  ```
- [ ] SMTP credentials tested and working
- [ ] OpenAI API key valid and has quota

### Security
- [ ] No hardcoded secrets in code
- [ ] `.env` file is in `.gitignore`
- [ ] Database file location is safe
- [ ] Logs don't contain sensitive data
- [ ] TLS enabled for SMTP (port 587)
- [ ] Database backups automated

### Database
- [ ] SQLite database initialized
- [ ] All tables created (run `python -c "from src.database import init_db; init_db()"`)
- [ ] Backup strategy in place
- [ ] Can connect from production environment

---

## TESTING & VALIDATION

### Unit Tests
- [ ] Run: `python -m pytest tests/test_agent.py -v`
- [ ] All tests pass ✅
- [ ] No warnings or deprecations

### Manual Tests (Use TESTING_GUIDE.md)
- [ ] **TEST 1**: CSV with different header cases
  ```bash
  python -c "
  from src.lead_input import LeadInputManager
  m = LeadInputManager()
  leads, dupes = m.load_from_csv('test_capitalized_headers.csv')
  print(f'✅ Loaded {len(leads)} leads')
  "
  ```

- [ ] **TEST 2**: Empty email validation
  ```bash
  python -c "
  from src.email_sender import EmailSender
  s = EmailSender()
  success, msg = s.send_email('test@example.com', 'Test', '', 'body')
  print(f'❌ {msg}' if not success else '✅ Sent')
  "
  ```

- [ ] **TEST 3**: Rate limit delays (visual inspection of logs)

- [ ] **TEST 4**: CSV case sensitivity (see TEST 1)

- [ ] **TEST 5**: Large CSV performance
  ```bash
  python -c "
  import time
  from src.lead_input import LeadInputManager
  m = LeadInputManager()
  
  # Create 1000-row test CSV first
  start = time.time()
  leads, dupes = m.load_from_csv('large_test_1000_rows.csv')
  elapsed = time.time() - start
  
  print(f'⏱️ Loaded {len(leads)} leads in {elapsed:.2f}s')
  assert elapsed < 2, 'Performance issue detected'
  print('✅ Fast enough')
  "
  ```

- [ ] **TEST 6**: Follow-up reply detection (database inspection)

- [ ] **TEST 7**: Dict validation in send_batch (error logging check)

- [ ] **TEST 8**: Email validation regex
  ```bash
  python -c "
  from src.lead_input import LeadValidator
  v = LeadValidator()
  
  valid = v.is_valid_email('test@example.com')
  invalid = v.is_valid_email('test..test@example.com')
  
  assert valid, 'Should accept valid'
  assert not invalid, 'Should reject double dots'
  print('✅ Regex validation works')
  "
  ```

- [ ] **TEST 9**: Enrichment logging (check logs)

### Integration Test
- [ ] Load CSV → Enrich → Generate → Send workflow
  ```bash
  python main.py load test_leads.csv
  python main.py enrich
  python main.py generate
  python main.py send --max 1
  ```
  All commands succeed without errors ✅

---

## PRODUCTION ENVIRONMENT SETUP

### Infrastructure
- [ ] Server/VM ready with Python 3.8+
- [ ] Required ports open (SMTP 587, API ports if needed)
- [ ] Disk space available (20GB+ recommended for SQLite)
- [ ] Network connectivity tested

### Dependencies
- [ ] Install: `pip install -r requirements.txt`
- [ ] Verify: `python -c "import sqlalchemy, openai, requests; print('✅ All imports OK')"`

### Directories
- [ ] Create: `logs/` directory (writable)
- [ ] Create: `data/` directory (for database)
- [ ] Create: `config/` directory (for YAML)
- [ ] Permissions: Correct ownership

### Logging
- [ ] Log directory writable by application user
- [ ] Verify: `touch data/agent.log && rm data/agent.log`
- [ ] Rotation configured (see logger.py)
- [ ] Monitoring set up (e.g., `tail -f logs/agent.log`)

---

## RATE LIMITING CONFIGURATION

### IMPORTANT for First Deployment
Set conservative limits to test safely:

**config/config.yaml**:
```yaml
email_sending:
  max_emails_per_day: 10      # NOT 30 yet
  max_emails_per_hour: 2      # NOT 5 yet
  delay_between_emails_min: 45
  delay_between_emails_max: 120
```

Increase after monitoring for 1 week. Only increase if:
- Bounce rate < 2%
- Complaint rate < 0.1%
- No IP blacklisting

---

## MONITORING & ALERTING

### Metrics to Track Daily
- [ ] Email send success rate (target >98%)
- [ ] Bounce rate (target <2%)
- [ ] Complaint rate (target <0.1%)
- [ ] API response times (target <2s)
- [ ] Database query times (target <100ms)

### Log Analysis
```bash
# Check for errors
tail -50 logs/agent.log | grep -E "ERROR|CRITICAL"

# Check rate limit enforcement
grep "rate limit reached" logs/agent.log

# Check bounce tracking
grep "BOUNCED" logs/agent.log

# Monitor API usage
grep -c "OpenAI API" logs/agent.log
```

### Automated Alerts
- [ ] Email provider bounce/complaint notifications enabled
- [ ] Log aggregation tool configured (e.g., tail logs to monitoring service)
- [ ] Backup failures alerted
- [ ] Disk space warnings set up

---

## EMAIL PROVIDER SETUP

### If Using Gmail (Free)
- [ ] Gmail account created
- [ ] 2FA enabled
- [ ] App password generated (not regular password!)
- [ ] Test SMTP connection before deploying

### If Using SendGrid/Mailgun (Recommended for Production)
- [ ] Account created
- [ ] Domain verified
- [ ] SMTP credentials obtained
- [ ] Sender reputation monitoring enabled

### Verification Configuration
- [ ] SPF record added to DNS
- [ ] DKIM record added to DNS
- [ ] DMARC policy configured
- [ ] Domain reputation monitored

**Check records**:
```bash
# SPF
nslookup -type=TXT yourdomain.com

# DKIM
nslookup -type=TXT default._domainkey.yourdomain.com

# DMARC
nslookup -type=TXT _dmarc.yourdomain.com
```

---

## BACKUP & DISASTER RECOVERY

### Database Backups
- [ ] Backup script created (`backup_db.sh`)
- [ ] Runs daily: `0 2 * * * /path/to/backup_db.sh`
- [ ] Stored off-server (cloud storage, etc.)
- [ ] Retention policy defined (30 days minimum)

### Backup Verification
```bash
# Test restore from backup
cp data/agent.db data/agent.db.backup
sqlite3 data/agent.db "SELECT COUNT(*) FROM lead;"
```

### Testing
- [ ] Restore from backup tested
- [ ] Restore time documented (<1 minute target)
- [ ] Data integrity verified after restore

---

## FINAL CHECKS BEFORE GO-LIVE

### 24 Hours Before
- [ ] Review all logs for 24-hour period
- [ ] Verify no pending errors or warnings
- [ ] Confirm all configurations correct
- [ ] Test full workflow one final time

### 1 Hour Before
- [ ] Database backed up fresh
- [ ] Logs cleared (or rotated to archive)
- [ ] Monitor dashboard ready
- [ ] On-call support briefed

### After Deployment
- [ ] Monitor for 1 hour continuously
- [ ] Check every 4 hours for first 24 hours
- [ ] Daily reviews for first week
- [ ] Weekly reviews after that

---

## ROLLBACK PROCEDURE (If Issues)

If problems occur within first hour:

1. **Stop sending**: `pkill -f cold-email-agent`
2. **Restore database**: `cp data/agent.db.backup data/agent.db`
3. **Restore config**: Check last working version
4. **Verify**: Test on staging before resume
5. **Review logs**: Identify root cause

Document:
- [ ] Time of rollback
- [ ] Reason for rollback
- [ ] Emails affected
- [ ] How to prevent next time

---

## POST-DEPLOYMENT OPTIMIZATION (Week 2+)

Only after 1 week of stable operation:

- [ ] Increase `max_emails_per_day` to 20 (if metrics good)
- [ ] Increase `max_emails_per_hour` to 3 (if metrics good)
- [ ] Monitor closely again for 1 week
- [ ] Then increase to full limits if still good

Conservative approach = fewer issues.

---

## DOCUMENTATION HANDOFF

Provide ops team with:
- [ ] EXECUTIVE_SUMMARY.md (overview)
- [ ] TESTING_GUIDE.md (how to run tests)
- [ ] BUG_FIXES_DETAILED.md (known issues fixed)
- [ ] PERFORMANCE_ROADMAP.md (optimization plans)
- [ ] config.yaml template (with descriptions)
- [ ] .env.example (template, not actual secrets)
- [ ] Architecture diagram
- [ ] Runbook (standard operations)
- [ ] Troubleshooting guide
- [ ] Contact list for issues

---

## OPERATIONAL RUNBOOK

### Daily Operations
```bash
# Daily health check
tail -20 logs/agent.log | grep "ERROR\|CRITICAL"

# Weekly backup verification
sqlite3 data/agent.db "SELECT COUNT(*) FROM email WHERE status='SENT';"

# Monthly deep analysis
python main.py report > monthly_report.txt
```

### Common Issues & Quick Fixes

**Issue**: Low send success rate (<95%)
- Check SMTP credentials
- Check network connectivity
- Check rate limits (might be blocking)

**Issue**: High bounce rate (>3%)
- Check email validation regex
- Review sender reputation
- Check if on spam blacklist

**Issue**: Slow performance
- Check database size: `ls -lh data/agent.db`
- Check logs for slow queries
- Consider PostgreSQL migration

---

## SUCCESS CRITERIA

Deployment is successful if, after 1 week:

✅ All tests pass  
✅ No error logs  
✅ Bounce rate < 2%  
✅ Complaint rate < 0.1%  
✅ No performance issues  
✅ APIs responding < 2s  
✅ Emails delivered within 1 hour  
✅ Database integrity verified  
✅ Backups working  
✅ On-call support confident  

---

## SIGN-OFF

- [ ] QA: All tests passed
- [ ] Ops: Infrastructure ready
- [ ] Security: No vulnerabilities
- [ ] Manager: Approved for production

**Deployment Date**: ___________  
**Deployed By**: ___________  
**Status**: ___________

---

**Next Review**: 1 week post-deployment

For detailed info, see:
- QA_VALIDATION_REPORT.md
- BUG_FIXES_DETAILED.md
- TESTING_GUIDE.md
- PERFORMANCE_ROADMAP.md

---

**READY TO DEPLOY?** ✅ YES - Everything checks out!

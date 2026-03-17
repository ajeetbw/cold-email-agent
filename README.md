# Cold Email Outreach Agent

A production-ready Python-based cold email outreach system with lead ingestion, enrichment, AI-powered personalization, rate-limited sending, follow-up scheduling, and safety guardrails.

## Quick Start

### 1) Create & activate the virtual environment
```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```powershell
pip install -r requirements.txt
```

### 3) Run unit tests
```powershell
pytest -q
```

### 4) Run main CLI (example)
```powershell
python main.py status
```

## Project Structure

- `src/` — core modules (agent, email sender, lead input, enrichment, scheduler, etc.)
- `tests/` — unit tests covering core workflows
- `config/` — YAML config files
- `data/` — SQLite database storage
- `logs/` — runtime log output

## Useful Docs

- `QA_VALIDATION_REPORT.md` — full QA pass and bug fix summary
- `BUG_FIXES_DETAILED.md` — all bug fixes with code snippets
- `TESTING_GUIDE.md` — full test procedures
- `DEPLOYMENT_CHECKLIST.md` — production deployment steps
- `PERFORMANCE_ROADMAP.md` — optimization roadmap

## Notes

- Use a real OpenAI API key in `.env`
- Use SMTP credentials (Gmail app password or SMTP provider)
- Start with conservative rate limits (10/day, 2/hour)

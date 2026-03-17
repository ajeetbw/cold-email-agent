# System Architecture

## Overview

The Cold Email Outreach Agent is built with a **modular, layered architecture** that separates concerns and enables easy testing, maintenance, and extension.

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│  (CLI: main.py, API: examples, or direct imports)           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              ORCHESTRATION LAYER                            │
│         ColdEmailAgent (src/agent.py)                       │
│  - Coordinates all modules                                  │
│  - Provides unified API                                     │
│  - Manages workflows                                        │
└────────┬──────────┬──────────┬──────────┬──────────┬────────┘
         │          │          │          │          │
    ┌────▼──┐  ┌───▼──┐  ┌───▼──┐  ┌──▼───┐  ┌───▼──┐
    │ Lead  │  │Email │  │Email │  │Lead  │  │Follow│
    │ Input │  │Gen  │  │Send  │  │Enrich│  │ Up   │
    │Manager│  │erator│  │er    │  │      │  │Sched │
    └────┬──┘  └───┬──┘  └───┬──┘  └──┬───┘  └───┬──┘
         │         │         │        │           │
         └─────────┼─────────┼────────┼───────────┘
                   │
        ┌──────────▼──────────────────┐
        │   DATABASE LAYER            │
        │   (src/database.py)          │
        │                              │
        │  Models:                     │
        │  - Lead                      │
        │  - Email                     │
        │  - EmailTemplate             │
        │                              │
        │  ORM: SQLAlchemy             │
        │  DB: SQLite (default)        │
        └──────────┬───────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  SUPPORTING SERVICES        │
        │                              │
        │  - Config (config.py)        │
        │  - Logger (logger.py)        │
        └──────────────────────────────┘
```

## Layer Details

### 1. **User Interface Layer**
- **CLI**: `main.py` - Command-line interface
- **Programmatic**: Direct imports and method calls
- **Examples**: Demo scripts showing different workflows

### 2. **Orchestration Layer** 
- **ColdEmailAgent** (`src/agent.py`)
  - Top-level API for the system
  - Coordinates all modules
  - Provides simple, unified interface
  - Handles workflow orchestration
  - Manages error handling at workflow level

### 3. **Module Layer**

#### 3a. Lead Input Management
- **File**: `src/lead_input.py`
- **Classes**:
  - `LeadValidator`: Email and data validation
  - `LeadInputManager`: CSV loading, manual entry, persistence
- **Responsibilities**:
  - Load leads from CSV
  - Validate lead data
  - Manage lead persistence
  - Handle duplicates
  - Export functionality

#### 3b. Email Generation
- **File**: `src/email_generator.py`
- **Classes**:
  - `EmailGenerator`: AI-powered generation using OpenAI
  - `TemplateEmailGenerator`: Template-based generation
- **Responsibilities**:
  - Generate personalized emails via AI
  - Create multiple email types (initial, follow-ups)
  - Template-based fallback generation
  - Prompt engineering and optimization

#### 3c. Email Sending
- **File**: `src/email_sender.py`
- **Classes**:
  - `EmailSender`: SMTP sending with rate limiting
- **Responsibilities**:
  - Send emails via SMTP
  - Rate limiting (daily/hourly)
  - Randomized delays between sends
  - Retry logic for failed emails
  - Error tracking and reporting
  - Status database updates

#### 3d. Lead Enrichment
- **File**: `src/lead_enrichment.py`
- **Classes**:
  - `LeadEnricher`: Fetch and enrich company data
  - `DataEnrichedDatabase`: Placeholder for third-party APIs
- **Responsibilities**:
  - Fetch website content
  - Extract company information
  - Generate summaries
  - Support future enrichment sources
  - Track enrichment status

#### 3e. Scheduling & Follow-ups
- **File**: `src/scheduler.py`
- **Classes**:
  - `FollowUpScheduler`: Manage follow-up scheduling
  - `CampaignManager`: Campaign tracking and analytics
- **Responsibilities**:
  - Identify leads due for follow-ups
  - Create follow-up email records
  - Schedule multiple follow-up waves
  - Campaign management
  - Analytics and reporting

### 4. **Database Layer**
- **File**: `src/database.py`
- **ORM**: SQLAlchemy
- **Database**: SQLite (configurable)
- **Models**:
  - `Lead`: Recipient information
  - `Email`: Sent emails and status
  - `EmailTemplate`: Reusable email templates
- **Enums**:
  - `EmailStatus`: sent, pending, failed, bounced, opened, replied
- **Manager**:
  - `DatabaseManager`: Connection pooling, session management

### 5. **Support Services Layer**

#### 5a. Configuration Management
- **File**: `src/config.py`
- **Class**: `Config`
- **Features**:
  - YAML-based configuration
  - Environment variable substitution
  - Validation
  - Singleton pattern

#### 5b. Logging
- **File**: `src/logger.py`
- **Features**:
  - File and console logging
  - Configurable levels
  - Structured formatting
  - Global logger instance

## Data Flow

### Typical Workflow
```
1. Load Leads (CSV or Manual)
   └─> LeadInputManager.load_from_csv()
       └─> Validate each lead
       └─> Check for duplicates
       └─> Save to database

2. Enrich Leads
   └─> LeadEnricher.enrich_lead()
       └─> Fetch website content
       └─> Extract information
       └─> Generate summary
       └─> Update database

3. Generate Emails
   └─> EmailGenerator.generate_email()
       └─> Query OpenAI API
       └─> Extract subject & body
       └─> Create Email record
       └─> Save to database

4. Send Emails
   └─> EmailSender.send_batch()
       └─> Check rate limits
       └─> Send via SMTP
       └─> Add delay
       └─> Update status
       └─> Log result

5. Schedule Follow-ups
   └─> FollowUpScheduler.get_followups_due()
       └─> Find leads by age
       └─> Generate follow-up emails
       └─> Save to database

6. Repeat Steps 3-4 for follow-ups
```

## Design Patterns Used

### 1. **Singleton Pattern**
- Global config instance (`get_config()`)
- Global database manager (`get_db_manager()`)
- Global logger (`logger`)

### 2. **Session per Request**
- Database sessions created per operation
- Automatically closed to prevent leaks
- Safe for concurrent use

### 3. **Composition**
- ColdEmailAgent composes all modules
- Modules don't depend on each other
- Loose coupling, high cohesion

### 4. **Separation of Concerns**
- Each module has single responsibility
- Clear interfaces between modules
- Easy to test in isolation

### 5. **Configuration Management**
- Centralized configuration
- Environment variable support
- Runtime customization

### 6. **Error Handling**
- Try-catch at module level
- Logging at each step
- Graceful degradation
- Retry mechanisms

## Extensions & Future Improvements

### 1. **Database Support**
Current: SQLite
- Add PostgreSQL support
- Add MySQL support
- Add cloud databases (Firebase, DynamoDB)

### 2. **Email Providers**
Current: Gmail SMTP
- Sendgrid API
- Mailgun API
- AWS SES
- Multi-account support

### 3. **AI Models**
Current: OpenAI GPT-3.5-turbo
- Claude (Anthropic)
- Gemini (Google)
- Local LLMs (Ollama)
- Custom fine-tuned models

### 4. **Enrichment Sources**
Current: Website scraping
- Hunter.io API
- Clearbit API
- Apollo.io API
- Custom APIs

### 5. **Features**
- IMAP integration for reply tracking
- Unsubscribe list management
- A/B testing framework
- Lead scoring system
- Web dashboard/API server
- Webhook integration
- Multi-language support

### 6. **Infrastructure**
- Docker containerization
- Kubernetes deployment
- Message queues (for async operations)
- Cache layer (Redis)
- Monitoring/observability

## Performance Considerations

### Rate Limiting
- Daily: 30 emails max
- Hourly: 5 emails max
- Delay: 45-120 seconds between emails
- Respects provider limits

### Database
- Uses indices on frequently queried fields
- Proper foreign keys and relationships
- Automatic connection pooling
- Configurable for scale

### API Calls
- Batched when possible
- Rate limit awareness
- Retry with exponential backoff
- Timeout handling

## Security Best Practices

### Credentials
- Use `.env` files for secrets
- Never commit passwords
- Environment variable substitution
- App passwords instead of main credentials

### Database
- SQLite is single-threaded
- Lock timeout on conflicts
- Can be upgraded to PostgreSQL
- No SQL injection (ORM protected)

### Email Sending
- Validates email addresses
- Respects SMTP TLS
- Proper authentication
- SPF/DKIM compatible

## Testing Strategy

### Unit Tests
- Database models
- Lead validation
- Configuration loading
- Helper functions

### Integration Tests
- Lead-to-email workflow
- Database transactions
- Configuration with database

### Manual Testing
- Example scripts demonstrate features
- CLI provides interactive testing
- Logging shows all operations

### Test Database
- In-memory SQLite for speed
- Isolated from production
- Full clean slate per test

## Module Dependencies

```
config.py
logger.py
    ↓
database.py (depends on config, logger)
    ↓
lead_input.py (depends on database, logger)
email_generator.py (depends on database, config, logger)
email_sender.py (depends on database, config, logger)
lead_enrichment.py (depends on database, logger, config)
scheduler.py (depends on database, logger)
    ↓
agent.py (depends on all modules)
    ↓
main.py (CLI interface)
examples/ (demonstrates usage)
```

## Scalability Notes

### Current Limitations
- SQLite: Single-threaded, ~1000s of records
- OpenAI API: Rate limits and costs
- SMTP: Email provider rate limits
- Memory: Python process memory

### Scaling Up
1. **Database**: Replace SQLite with PostgreSQL
2. **Async Processing**: Add Celery + Redis
3. **API Gateway**: Add FastAPI server
4. **Multiple Providers**: Implement provider switching
5. **Caching**: Add Redis for enrichment cache
6. **Queuing**: Message queue for long operations

---

**Architecture Version**: 1.0
**Last Updated**: 2026-03-17
**Maintainers**: Backend Team

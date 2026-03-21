---
type: guide
title: Setting Up Periodic Balance Snapshots
created: 2026-02-05
tags:
  - net-worth
  - automation
  - snapshots
related:
  - "[[Net Worth Feature]]"
---

# Periodic Balance Snapshots Setup Guide

Balance snapshots are essential for tracking your net worth over time. This guide explains how to set up automatic snapshots to build a historical record of your financial position.

## Why Use Periodic Snapshots?

- **Track Financial Progress**: Monitor how your net worth grows or declines over time
- **Trend Analysis**: Identify spending patterns and financial health trends
- **Goal Setting**: Set and track progress toward financial goals
- **Retrospective Analysis**: Review how your finances changed over different periods

## API Endpoint

The `/api/v1/networth/auto-snapshot` endpoint automatically records current balances for all active accounts to the `balance_history` table.

**Request:**
```bash
POST /api/v1/networth/auto-snapshot
```

**Response:**
```json
{
  "message": "Balance snapshots created",
  "total_snapshots": 5,
  "errors": 0
}
```

## Setup Options

### Option 1: Cron Job (Recommended for Servers)

Set up a cron job to run snapshots daily or weekly at a consistent time.

**Daily Snapshot (9:00 AM):**
```bash
0 9 * * * curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot
```

**Weekly Snapshot (Sunday 6:00 AM):**
```bash
0 6 * * 0 curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot
```

**Daily at Midnight:**
```bash
0 0 * * * curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot
```

**With Authentication (requires API key):**
```bash
0 9 * * * curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Option 2: Background Task (Docker/Production)

Use a cron system running inside your Docker container.

**Edit docker-compose.yml:**
```yaml
services:
  api:
    # ... existing config
    command: >
      sh -c "
        python -m app.seed &&
        alembic upgrade head &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      "
    environment:
      - AUTO_SNAPSHOT_SCHEDULE=0 9 * * *
```

**Create a startup script** that triggers the snapshot:

```python
# backend/app/scripts/auto_snapshot.py
import requests
import os
import time

API_URL = os.getenv("API_URL", "http://localhost:8000")
SNAPSHOT_URL = f"{API_URL}/api/v1/networth/auto-snapshot"

def trigger_snapshot():
    try:
        response = requests.post(SNAPSHOT_URL)
        response.raise_for_status()
        print(f"Snapshot created: {response.json()}")
    except Exception as e:
        print(f"Failed to create snapshot: {e}")

if __name__ == "__main__":
    # Run once on startup
    trigger_snapshot()

    # Wait for database to be ready
    time.sleep(5)

    # Poll for next scheduled time
    import schedule
    import datetime

    schedule.every().day.at("09:00").do(trigger_snapshot)

    while True:
        schedule.run_pending()
        time.sleep(60)
```

**Update main.py to include the script:**
```python
# backend/app/main.py
import uvicorn
from app.config import settings

if __name__ == "__main__":
    if settings.auto_snapshot_enabled:
        # Run snapshot worker
        from app.scripts.auto_snapshot import main
        import multiprocessing

        # Start API server
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    else:
        # Normal startup
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
```

### Option 3: Trigger on Events

Automatically trigger snapshots at key events:

**On Import Completion:**
```python
# backend/app/services/import_service.py
# After successful import
result = auto_snapshot_all_balances(db)
logger.info(f"Auto-snapshot triggered on import: {result}")
```

**On Manual Balance Update:**
```python
# backend/app/api/v1/networth.py
# After updating balance
snapshot = record_balance_snapshot(db, str(account_id), current_balance, date.today())
logger.info(f"Balance snapshot created on manual update: {account_id}")
```

**On Dashboard View:**
```python
# Add rate limiting to prevent spamming
last_snapshot = db.query(BalanceHistory.recorded_at).order_by(BalanceHistory.recorded_at.desc()).first()

if not last_snapshot or (datetime.now() - last_snapshot) > timedelta(days=1):
    result = auto_snapshot_all_balances(db)
    logger.info(f"Auto-snapshot triggered on dashboard view: {result}")
```

## Best Practices

### Timing
- **Best Time**: Choose a consistent time when your accounts are likely stable
- **Avoid**: Times around major transactions (payday, bill due dates)
- **Frequency**:
  - Daily: Best for detailed tracking
  - Weekly: Good balance between detail and frequency
  - Monthly: Sufficient for most users

### Security
- Use authentication with API keys
- Run snapshots on a private network
- Monitor for failed snapshots
- Rotate API keys periodically

### Data Retention
- Balance history grows over time
- Consider archiving old data
- Keep at least 1-2 years of snapshots for most users
- Longer retention for detailed financial planning

## Monitoring

Check your snapshot schedule:

```bash
# Check last snapshot date
curl http://localhost:8000/api/v1/networth/breakdown | jq '.accounts[0].last_snapshot_date'

# Count total snapshots
curl http://localhost:8000/api/v1/networth/history?start_date=2025-01-01 | jq 'length'
```

## Troubleshooting

**Snapshots failing?**
1. Check database connection
2. Verify API endpoint is accessible
3. Review error logs
4. Ensure accounts are active

**Too many snapshots?**
1. Adjust cron schedule
2. Implement rate limiting
3. Remove duplicate snapshots

**Missing data?**
1. Manually trigger snapshot
2. Check account is active
3. Verify balance is not None

## Example: Complete Setup

**Docker Compose with Cron:**

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/db.sqlite
      - AUTO_SNAPSHOT_SCHEDULE=0 9 * * *
    volumes:
      - ./data:/app/data
    command: >
      sh -c "
        python -m app.seed &&
        alembic upgrade head &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000
      "
    depends_on:
      - db
```

**Cron Setup:**
```bash
# Add to crontab
crontab -e

# Daily snapshot at 9 AM
0 9 * * * cd /path/to/spendah && docker-compose exec api curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot
```

## Further Reading

- [[Net Worth Feature]] - Overview of net worth functionality
- [[Balance History Model]] - Database schema for snapshots
- [[API Reference]] - Full API documentation

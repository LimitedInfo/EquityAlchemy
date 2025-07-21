# Fly.io PostgreSQL Deployment Guide

This guide explains how to use the CombinedFinancialStatements persistence layer with your Fly.io PostgreSQL database.

## Database Connection

Your Fly.io PostgreSQL instance is configured as:
- **App Name**: twilight-river-6306
- **Internal Host**: twilight-river-6306.flycast
- **Ports**: 5432 (primary), 5433 (secondary)
- **Region**: mia

## Environment Variables

The application automatically detects Fly.io deployment through the `FLY_APP_NAME` environment variable.

flyctl deploy --config fly.listener.toml

### Required Secrets

Set these secrets in your Fly.io app:

```bash
# Get your database password from Fly.io
fly secrets list -a twilight-river-6306

# Set the database password (use the OPERATOR_PASSWORD from above)
fly secrets set DATABASE_PASSWORD=your_operator_password -a twilight-river-6306

# Optional: Override default values
fly secrets set DATABASE_USER=postgres -a twilight-river-6306
fly secrets set DATABASE_NAME=postgres -a twilight-river-6306
fly secrets set DATABASE_HOST=twilight-river-6306.flycast -a twilight-river-6306
fly secrets set DATABASE_PORT=5432 -a twilight-river-6306
```

## Initialize Database Tables

### Option 1: SSH into the app and run initialization

```bash
# SSH into your Fly app
fly ssh console -a twilight-river-6306

# Once inside, run the initialization
cd /app
python -m backend.init_db
```

### Option 2: Run initialization script locally with Fly proxy

```bash
# Create a proxy to your Fly PostgreSQL
fly proxy 5432:5432 -a twilight-river-6306

# Set local environment variables
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_PASSWORD=your_operator_password
export DATABASE_USER=postgres
export DATABASE_NAME=postgres

# Run initialization
python -m backend.init_db
```

## Connecting from Your Application

When deployed on Fly.io, the configuration automatically uses:
```postgresql://postgres:$DATABASE_PASSWORD@twilight-river-6306.flycast:5432/postgres
```

For external connections (development), use:
```bash
# Create a WireGuard tunnel
fly wireguard create

# Or use fly proxy
fly proxy 5432:5432 -a twilight-river-6306

# Then connect to localhost:5432
```

## Example Usage in Production

```python
# The configuration automatically detects Fly.io environment
from backend.adapters.orm import get_session_factory
from backend.service_layer.uow import SqlAlchemyUnitOfWork
from backend.service_layer import financial_statements_service
from backend.config import get_postgres_uri

# This will use Fly.io database when FLY_APP_NAME is set
session_factory = get_session_factory(get_postgres_uri())
uow = SqlAlchemyUnitOfWork(session_factory)

# Use as normal
stmt = financial_statements_service.fetch_statement('AAPL', '10-K', uow)
```

## Monitoring Database

Check database health:
```bash
fly status -a twilight-river-6306
fly checks list -a twilight-river-6306
```

View logs:
```bash
fly logs -a twilight-river-6306
```

## Backup Considerations

For production use, consider setting up regular backups:
```bash
# Create a snapshot
fly postgres backup create -a twilight-river-6306

# List backups
fly postgres backup list -a twilight-river-6306
```

## Performance Notes

- The JSONB storage is efficient for DataFrames
- The ticker index ensures fast lookups
- For very large datasets, consider pagination in your queries
- Fly.io PostgreSQL includes automatic daily backups in most plans

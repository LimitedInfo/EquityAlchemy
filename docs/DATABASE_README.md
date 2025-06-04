# Database Persistence for CombinedFinancialStatements

This implementation provides a clean, layered approach to persisting `CombinedFinancialStatements` to PostgreSQL.

Postgres cluster small-night-2462 created
  Username:    postgres
  Password:
  Hostname:    small-night-2462.internal
  Flycast:     fdaa:10:71fc:0:1::9
  Proxy port:  5432
  Postgres port:  5433


## Architecture Overview

Following the layered architecture pattern:

1. **Domain Layer** (`domain/repository.py`)
   - Defines the abstract `CombinedFinancialStatementsRepository` interface
   - No dependencies on infrastructure

2. **Infrastructure Layer** (`adapters/`)
   - `orm.py`: SQLAlchemy ORM models using JSONB for DataFrame storage
   - `repository.py`: Concrete PostgreSQL repository implementation
   - `unit_of_work.py`: Transaction management

3. **Service Layer** (`service_layer/financial_statements_service.py`)
   - Orchestrates domain logic and infrastructure
   - Provides simple functions for CRUD operations

## Database Schema

Single table approach with JSONB storage:

```sql
CREATE TABLE combined_financial_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR NOT NULL,
    form_type VARCHAR,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ticker ON combined_financial_statements(ticker);
```

## Setup

1. **Environment Variables**
   Add to your `.env` file:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_NAME=financial_statements
   ```

2. **Create Database**
   ```powershell
   # Using psql
   psql -U postgres -c "CREATE DATABASE financial_statements;"
   ```

3. **Initialize Tables**
   ```powershell
   python -m backend.init_db
   ```

## Usage Examples

### Persist a Single Statement
```python
from backend.domain.model import CombinedFinancialStatements
from backend.adapters.orm import get_session_factory
from backend.adapters.unit_of_work import SqlAlchemyUnitOfWork
from backend.service_layer import financial_statements_service
from backend.config import get_postgres_uri

# Create UoW
session_factory = get_session_factory(get_postgres_uri())
uow = SqlAlchemyUnitOfWork(session_factory)

# Persist
financial_statements_service.persist_single_statement(stmt, uow)

# Retrieve
stmt = financial_statements_service.fetch_statement('AAPL', '10-K', uow)
```

### Bulk Operations
```python
# Persist many
statements = [stmt1, stmt2, stmt3]
financial_statements_service.persist_statements(statements, uow)

# Get all for a ticker
all_stmts = financial_statements_service.fetch_statements_by_ticker('AAPL', uow)
```

## Data Serialization

- DataFrames are serialized using Pandas' `orient="split"` format
- Preserves index, columns, and data separately
- Handles NaN, dates, and numeric types correctly
- Round-trip fidelity guaranteed by Pandas

## Performance Considerations

1. **Bulk Inserts**: Use `add_many()` for multiple statements
2. **Indexing**: Ticker column is indexed for fast lookups
3. **JSONB**: Allows querying into the data if needed later
4. **Transaction Scope**: UoW ensures proper transaction boundaries

## Future Extensions

If you need cell-level queries later, you can add a second table:
```sql
CREATE TABLE financial_statement_cells (
    id UUID PRIMARY KEY,
    statement_id UUID REFERENCES combined_financial_statements(id),
    period VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,
    value NUMERIC,
    INDEX idx_lookup (statement_id, period, metric)
);
```

But start with the simple JSONB approach first!

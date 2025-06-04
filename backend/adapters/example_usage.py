from backend.domain.model import CombinedFinancialStatements, Filing
from backend.adapters.orm import get_session_factory
from backend.service_layer.uow import SqlAlchemyUnitOfWork
from backend.service_layer import financial_statements_service
from backend.adapters.config import get_postgres_uri
import pandas as pd


def example_persist_and_retrieve():
    session_factory = get_session_factory(get_postgres_uri())
    uow = SqlAlchemyUnitOfWork(session_factory)

    sample_df = pd.DataFrame({
        '2023-01-01:2023-03-31': [1000, 500, 300],
        '2023-04-01:2023-06-30': [1100, 550, 330],
        '2023-07-01:2023-09-30': [1200, 600, 360]
    }, index=['Revenue', 'Costs', 'Net Income'])

    stmt = CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='AAPL',
        form_type='10-Q'
    )
    stmt.df = sample_df

    financial_statements_service.persist_single_statement(stmt, uow)
    print("Statement persisted successfully!")

    retrieved_stmt = financial_statements_service.fetch_statement('AAPL', '10-Q', uow)
    if retrieved_stmt:
        print(f"\nRetrieved statement for {retrieved_stmt.ticker} ({retrieved_stmt.form_type}):")
        print(retrieved_stmt.df)

    all_aapl_stmts = financial_statements_service.fetch_statements_by_ticker('AAPL', uow)
    print(f"\nFound {len(all_aapl_stmts)} statements for AAPL")


def example_bulk_persist():
    session_factory = get_session_factory(get_postgres_uri())
    uow = SqlAlchemyUnitOfWork(session_factory)

    statements = []

    for ticker in ['MSFT', 'GOOG', 'AMZN']:
        for form_type in ['10-K', '10-Q']:
            sample_df = pd.DataFrame({
                '2023-01-01:2023-12-31': [1000, 500, 300],
            }, index=['Revenue', 'Costs', 'Net Income'])

            stmt = CombinedFinancialStatements(
                financial_statements=[],
                source_filings=[],
                ticker=ticker,
                form_type=form_type
            )
            stmt.df = sample_df
            statements.append(stmt)

    financial_statements_service.persist_statements(statements, uow)
    print(f"Bulk persisted {len(statements)} statements!")


if __name__ == "__main__":
    print("Example 1: Persist and retrieve a single statement")
    example_persist_and_retrieve()

    print("\n" + "="*50 + "\n")

    print("Example 2: Bulk persist multiple statements")
    example_bulk_persist()

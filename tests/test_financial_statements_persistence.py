import pytest
import pandas as pd
from backend.domain.model import CombinedFinancialStatements
from backend.adapters.orm import Base, get_session_factory, create_tables
from backend.service_layer.uow import SqlAlchemyUnitOfWork
from backend.service_layer import financial_statements_service
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture
def uow(session_factory):
    return SqlAlchemyUnitOfWork(session_factory)


def test_can_persist_and_retrieve_statement(uow):
    sample_df = pd.DataFrame({
        '2023-01-01:2023-03-31': [1000.5, 500.25, 300.75],
        '2023-04-01:2023-06-30': [1100.0, 550.50, 330.25]
    }, index=['Revenue', 'Costs', 'Net Income'])

    stmt = CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='TEST',
        form_type='10-Q'
    )
    stmt.df = sample_df

    financial_statements_service.persist_single_statement(stmt, uow)

    retrieved = financial_statements_service.fetch_statement('TEST', '10-Q', uow)

    assert retrieved is not None
    assert retrieved.ticker == 'TEST'
    assert retrieved.form_type == '10-Q'
    assert retrieved.df.shape == sample_df.shape
    assert retrieved.df.loc['Revenue', '2023-01-01:2023-03-31'] == 1000.5


def test_can_persist_multiple_statements(uow):
    statements = []

    for i, ticker in enumerate(['AAPL', 'MSFT', 'GOOG']):
        df = pd.DataFrame({
            '2023-01-01:2023-12-31': [1000 * (i+1), 500 * (i+1), 300 * (i+1)]
        }, index=['Revenue', 'Costs', 'Net Income'])

        stmt = CombinedFinancialStatements(
            financial_statements=[],
            source_filings=[],
            ticker=ticker,
            form_type='10-K'
        )
        stmt.df = df
        statements.append(stmt)

    financial_statements_service.persist_statements(statements, uow)

    for i, ticker in enumerate(['AAPL', 'MSFT', 'GOOG']):
        retrieved = financial_statements_service.fetch_statement(ticker, '10-K', uow)
        assert retrieved is not None
        assert retrieved.df.loc['Revenue', '2023-01-01:2023-12-31'] == 1000 * (i+1)


def test_can_get_all_statements_for_ticker(uow):
    for form_type in ['10-K', '10-Q', '8-K']:
        df = pd.DataFrame({
            '2023-01-01:2023-12-31': [1000, 500, 300]
        }, index=['Revenue', 'Costs', 'Net Income'])

        stmt = CombinedFinancialStatements(
            financial_statements=[],
            source_filings=[],
            ticker='AAPL',
            form_type=form_type
        )
        stmt.df = df
        financial_statements_service.persist_single_statement(stmt, uow)

    all_statements = financial_statements_service.fetch_statements_by_ticker('AAPL', uow)

    assert len(all_statements) == 3
    form_types = {stmt.form_type for stmt in all_statements}
    assert form_types == {'10-K', '10-Q', '8-K'}


def test_can_delete_statement(uow):
    df = pd.DataFrame({
        '2023-01-01:2023-12-31': [1000, 500, 300]
    }, index=['Revenue', 'Costs', 'Net Income'])

    stmt = CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='DELETE_ME',
        form_type='10-K'
    )
    stmt.df = df

    financial_statements_service.persist_single_statement(stmt, uow)

    retrieved = financial_statements_service.fetch_statement('DELETE_ME', '10-K', uow)
    assert retrieved is not None

    financial_statements_service.delete_statement('DELETE_ME', '10-K', uow)

    retrieved_after_delete = financial_statements_service.fetch_statement('DELETE_ME', '10-K', uow)
    assert retrieved_after_delete is None


def test_handles_nan_values(uow):
    df = pd.DataFrame({
        '2023-01-01:2023-03-31': [1000, float('nan'), 300],
        '2023-04-01:2023-06-30': [1100, 550, float('nan')]
    }, index=['Revenue', 'Costs', 'Net Income'])

    stmt = CombinedFinancialStatements(
        financial_statements=[],
        source_filings=[],
        ticker='NAN_TEST',
        form_type='10-Q'
    )
    stmt.df = df

    financial_statements_service.persist_single_statement(stmt, uow)

    retrieved = financial_statements_service.fetch_statement('NAN_TEST', '10-Q', uow)

    assert retrieved is not None
    assert pd.isna(retrieved.df.loc['Costs', '2023-01-01:2023-03-31'])
    assert pd.isna(retrieved.df.loc['Net Income', '2023-04-01:2023-06-30'])

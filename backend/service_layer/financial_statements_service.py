from typing import Sequence, Optional
from backend.domain.model import CombinedFinancialStatements
from backend.service_layer.uow import AbstractUnitOfWork


def persist_statements(
    statements: Sequence[CombinedFinancialStatements],
    uow: AbstractUnitOfWork
) -> None:
    with uow:
        uow.stmts.add_many(statements)
        uow.commit()


def persist_single_statement(
    statement: CombinedFinancialStatements,
    uow: AbstractUnitOfWork
) -> None:
    with uow:
        uow.stmts.add(statement)
        uow.commit()


def fetch_statement(
    ticker: str,
    form_type: str,
    uow: AbstractUnitOfWork
) -> Optional[CombinedFinancialStatements]:
    with uow:
        return uow.stmts.get(ticker, form_type)


def fetch_statements_by_ticker(
    ticker: str,
    uow: AbstractUnitOfWork
) -> list[CombinedFinancialStatements]:
    with uow:
        return uow.stmts.get_by_ticker(ticker)


def delete_statement(
    ticker: str,
    form_type: str,
    uow: AbstractUnitOfWork
) -> None:
    with uow:
        uow.stmts.delete(ticker, form_type)
        uow.commit()


def update_statement(
    statement: CombinedFinancialStatements,
    uow: AbstractUnitOfWork
) -> None:
    with uow:
        uow.stmts.delete(statement.ticker, statement.form_type)
        uow.stmts.add(statement)
        uow.commit()

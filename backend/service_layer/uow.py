from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from adapters import repository
from adapters.config import get_postgres_uri

DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        get_postgres_uri(),
    )
)


class AbstractUnitOfWork(ABC):
    sec_filings: repository.SECFilingRepository
    llm: repository.LLMRepository
    stmts: repository.PostgresCombinedFinancialStatementsRepository

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.rollback()

    @abstractmethod
    def commit(self):
        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        raise NotImplementedError


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.sec_filings = repository.FakeSECFilingRepository()
        self.llm = None
        self.stmts = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.sec_filings = repository.SECFilingRepository()
        self.llm = repository.LLMRepository()
        self.stmts = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker = DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> 'SqlAlchemyUnitOfWork':
        self.session = self.session_factory()
        self.stmts = repository.PostgresCombinedFinancialStatementsRepository(self.session)
        self.sec_filings = repository.SECFilingRepository()
        self.llm = repository.LLMRepository()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.session.close()

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()

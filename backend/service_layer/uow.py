from abc import ABC, abstractmethod
import backend.adapters.repository as repository


class AbstractUnitOfWork(ABC):
    sec_filings: repository.SECFilingRepository
    llm: repository.LLMRepository

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

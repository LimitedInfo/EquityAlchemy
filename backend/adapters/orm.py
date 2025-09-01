import uuid
from datetime import datetime
from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Date,
    MetaData,
    ForeignKey,
    DateTime,
    Boolean,
    BigInteger,
    Text,
    Numeric,
    Index,
    func,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as pgUUID


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(pgUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class JSONType(TypeDecorator):
    """Platform-independent JSON type.

    Uses PostgreSQL's JSONB type, otherwise uses Text.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB)
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            return json.loads(value)


Base = declarative_base()


class CombinedFinancialStatementsORM(Base):
    __tablename__ = "combined_financial_statements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    form_type = Column(String, nullable=True)
    data = Column(JSONType, nullable=False)
    balance_sheet_data = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    has_more_than_one_continuous_period = Column(Boolean, nullable=True)
    sec_filings_url = Column(String, nullable=True)

    __table_args__ = (
        {"schema": None},  # Don't use schema for SQLite compatibility
    )


class CompanyORM(Base):
    __tablename__ = 'companies'

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    ticker = Column(String, unique=True, index=True, nullable=False)
    shares_outstanding = Column(BigInteger, nullable=True)
    cik = Column(String, unique=True, index=True, nullable=True)
    cusip = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    is_delisted = Column(Boolean, nullable=True)
    category = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    sic = Column(String, nullable=True)
    sic_sector = Column(String, nullable=True)
    sic_industry = Column(String, nullable=True)
    fama_sector = Column(String, nullable=True)
    fama_industry = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    location = Column(String, nullable=True)
    sec_api_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        {"schema": None},
    )


def get_session_factory(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine)


def create_tables(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)

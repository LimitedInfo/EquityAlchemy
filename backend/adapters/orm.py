import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, create_engine, Text, Numeric, Index, Boolean
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
    form_type = Column(String, nullable=True)
    data = Column(JSONType, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    has_more_than_one_continuous_period = Column(Boolean, nullable=True)
    sec_filings_url = Column(String, nullable=True)

    __table_args__ = (
        {"schema": None},  # Don't use schema for SQLite compatibility
    )


class StockPriceORM(Base):
    __tablename__ = "stock_prices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    market_reference_price = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_stock_prices_ticker_date', 'ticker', 'date'),
        {"schema": None},
    )


class SignificantMoveORM(Base):
    __tablename__ = "significant_moves"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    pct_change = Column(Numeric(precision=8, scale=4), nullable=False)
    catalyst = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_significant_moves_ticker_date', 'ticker', 'occurred_at'),
        {"schema": None},
    )


def get_session_factory(database_url: str):
    engine = create_engine(database_url)
    return sessionmaker(bind=engine)


def create_tables(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

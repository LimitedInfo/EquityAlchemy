import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

from backend.domain import StockTicker, PricePoint, SignificantMove
from backend.adapters.repository import FakePriceRepository, FakeSignificantMoveRepository
from backend.adapters.market_data import FakeMarketDataProvider


class TestFakePriceRepository:
    def test_add_and_get_series(self):
        repo = FakePriceRepository()
        ticker = StockTicker("AAPL")

        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00'))
        ]

        repo.add_many(points, ticker)

        series = repo.get_series(ticker, date(2024, 1, 1), date(2024, 1, 3))

        assert series is not None
        assert series.ticker == ticker
        assert len(series.points) == 3
        assert series.points[0].price == Decimal('150.00')

    def test_get_series_date_filtering(self):
        repo = FakePriceRepository()
        ticker = StockTicker("AAPL")

        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00'))
        ]

        repo.add_many(points, ticker)

        series = repo.get_series(ticker, date(2024, 1, 2), date(2024, 1, 2))

        assert series is not None
        assert len(series.points) == 1
        assert series.points[0].price == Decimal('155.00')

    def test_get_latest_date(self):
        repo = FakePriceRepository()
        ticker = StockTicker("AAPL")

        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00'))
        ]

        repo.add_many(points, ticker)

        latest_date = repo.get_latest_date(ticker)

        assert latest_date == date(2024, 1, 3)

    def test_no_duplicate_dates(self):
        repo = FakePriceRepository()
        ticker = StockTicker("AAPL")

        points1 = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00'))
        ]

        points2 = [
            PricePoint(datetime(2024, 1, 2), Decimal('156.00'), Decimal('4512.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00'))
        ]

        repo.add_many(points1, ticker)
        repo.add_many(points2, ticker)

        series = repo.get_series(ticker, date(2024, 1, 1), date(2024, 1, 3))

        assert len(series.points) == 3
        date_list = [point.date.date() for point in series.points]
        assert len(set(date_list)) == 3


class TestFakeSignificantMoveRepository:
    def test_add_and_list_moves(self):
        repo = FakeSignificantMoveRepository()
        ticker = StockTicker("AAPL")

        move = SignificantMove(
            id=None,
            ticker=ticker,
            occurred_at=datetime(2024, 1, 2),
            pct_change=Decimal('8.50'),
            catalyst="Earnings beat"
        )

        repo.add(move)

        assert move.id is not None

        moves = repo.list_between(ticker, date(2024, 1, 1), date(2024, 1, 3))

        assert len(moves) == 1
        assert moves[0].pct_change == Decimal('8.50')
        assert moves[0].catalyst == "Earnings beat"

    def test_add_many_no_duplicates(self):
        repo = FakeSignificantMoveRepository()
        ticker = StockTicker("AAPL")

        moves = [
            SignificantMove(None, ticker, datetime(2024, 1, 2), Decimal('8.50'), "Earnings beat"),
            SignificantMove(None, ticker, datetime(2024, 1, 2), Decimal('8.60'), "Different catalyst"),
            SignificantMove(None, ticker, datetime(2024, 1, 3), Decimal('5.20'), "News")
        ]

        repo.add_many(moves)

        result_moves = repo.list_between(ticker, date(2024, 1, 1), date(2024, 1, 5))

        assert len(result_moves) == 2

    def test_update_catalyst(self):
        repo = FakeSignificantMoveRepository()
        ticker = StockTicker("AAPL")

        move = SignificantMove(
            id=None,
            ticker=ticker,
            occurred_at=datetime(2024, 1, 2),
            pct_change=Decimal('8.50'),
            catalyst="Initial catalyst"
        )

        repo.add(move)
        move_id = move.id

        repo.update_catalyst(move_id, "Updated catalyst")

        moves = repo.list_between(ticker, date(2024, 1, 1), date(2024, 1, 3))

        assert len(moves) == 1
        assert moves[0].catalyst == "Updated catalyst"


class TestFakeMarketDataProvider:
    def test_fetch_prices_with_fake_data(self):
        provider = FakeMarketDataProvider()

        fake_points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00'))
        ]

        provider.add_fake_data("AAPL", fake_points)

        result = provider.fetch_prices("AAPL", date(2024, 1, 1), date(2024, 1, 3))

        assert len(result) == 3
        assert result[0].price == Decimal('150.00')
        assert result[1].price == Decimal('155.00')

    def test_fetch_prices_date_filtering(self):
        provider = FakeMarketDataProvider()

        fake_points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('152.00'), Decimal('4505.00'))
        ]

        provider.add_fake_data("AAPL", fake_points)

        result = provider.fetch_prices("AAPL", date(2024, 1, 2), date(2024, 1, 2))

        assert len(result) == 1
        assert result[0].price == Decimal('155.00')

    def test_fetch_empty_ticker(self):
        provider = FakeMarketDataProvider()

        result = provider.fetch_prices("NONEXISTENT", date(2024, 1, 1), date(2024, 1, 3))

        assert len(result) == 0

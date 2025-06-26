import pytest
from datetime import datetime
from decimal import Decimal

from backend.domain import StockTicker, PricePoint, SignificantMove, StockPriceSeries


class TestStockTicker:
    def test_valid_ticker_creation(self):
        ticker = StockTicker("AAPL")
        assert ticker.symbol == "AAPL"
        assert str(ticker) == "AAPL"

    def test_ticker_normalization(self):
        ticker = StockTicker("  aapl  ")
        assert ticker.symbol == "AAPL"

    def test_invalid_ticker_empty(self):
        with pytest.raises(ValueError, match="Stock ticker must be a non-empty string"):
            StockTicker("")

    def test_invalid_ticker_too_long(self):
        with pytest.raises(ValueError, match="Stock ticker must be alphanumeric and max 10 characters"):
            StockTicker("VERYLONGTICKER")

    def test_ticker_equality(self):
        ticker1 = StockTicker("AAPL")
        ticker2 = StockTicker("AAPL")
        ticker3 = StockTicker("MSFT")

        assert ticker1 == ticker2
        assert ticker1 != ticker3
        assert hash(ticker1) == hash(ticker2)


class TestPricePoint:
    def test_valid_price_point(self):
        point = PricePoint(
            date=datetime(2024, 1, 1),
            price=Decimal('150.00'),
            market_reference_price=Decimal('4500.00')
        )
        assert point.price == Decimal('150.00')
        assert point.market_reference_price == Decimal('4500.00')

    def test_invalid_negative_price(self):
        with pytest.raises(ValueError, match="Price must be positive"):
            PricePoint(
                date=datetime(2024, 1, 1),
                price=Decimal('-10.00'),
                market_reference_price=Decimal('4500.00')
            )

    def test_invalid_zero_market_price(self):
        with pytest.raises(ValueError, match="Market reference price must be positive"):
            PricePoint(
                date=datetime(2024, 1, 1),
                price=Decimal('150.00'),
                market_reference_price=Decimal('0.00')
            )


class TestSignificantMove:
    def test_valid_significant_move(self):
        ticker = StockTicker("AAPL")
        move = SignificantMove(
            id="test-id",
            ticker=ticker,
            occurred_at=datetime(2024, 1, 1),
            pct_change=Decimal('5.50'),
            catalyst="Earnings beat"
        )
        assert move.pct_change == Decimal('5.50')
        assert move.catalyst == "Earnings beat"

    def test_invalid_small_move(self):
        ticker = StockTicker("AAPL")
        with pytest.raises(ValueError, match="Significant move must have at least 1% change"):
            SignificantMove(
                id="test-id",
                ticker=ticker,
                occurred_at=datetime(2024, 1, 1),
                pct_change=Decimal('0.5')
            )


class TestStockPriceSeries:
    def test_valid_price_series(self):
        ticker = StockTicker("AAPL")
        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('150.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('155.00'), Decimal('4510.00'))
        ]
        series = StockPriceSeries(ticker, points)

        assert series.ticker == ticker
        assert len(series.points) == 2

    def test_empty_points_raises_error(self):
        ticker = StockTicker("AAPL")
        with pytest.raises(ValueError, match="Stock price series must have at least one price point"):
            StockPriceSeries(ticker, [])

    def test_detect_significant_moves(self):
        ticker = StockTicker("AAPL")
        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('100.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('110.00'), Decimal('4505.00')),
            PricePoint(datetime(2024, 1, 3), Decimal('108.00'), Decimal('4510.00'))
        ]
        series = StockPriceSeries(ticker, points)

        moves = series.detect_significant_moves(Decimal('5.0'))

        assert len(moves) == 1
        assert moves[0].ticker == ticker
        assert moves[0].occurred_at == datetime(2024, 1, 2)
        assert abs(moves[0].pct_change - Decimal('10.0')) < Decimal('0.01')

    def test_no_significant_moves_below_threshold(self):
        ticker = StockTicker("AAPL")
        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('100.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('101.00'), Decimal('4501.00'))
        ]
        series = StockPriceSeries(ticker, points)

        moves = series.detect_significant_moves(Decimal('5.0'))

        assert len(moves) == 0

    def test_get_price_at_date(self):
        ticker = StockTicker("AAPL")
        target_date = datetime(2024, 1, 2)
        points = [
            PricePoint(datetime(2024, 1, 1), Decimal('100.00'), Decimal('4500.00')),
            PricePoint(target_date, Decimal('105.00'), Decimal('4505.00'))
        ]
        series = StockPriceSeries(ticker, points)

        found_point = series.get_price_at_date(target_date)

        assert found_point is not None
        assert found_point.price == Decimal('105.00')

    def test_get_date_range(self):
        ticker = StockTicker("AAPL")
        points = [
            PricePoint(datetime(2024, 1, 3), Decimal('100.00'), Decimal('4500.00')),
            PricePoint(datetime(2024, 1, 1), Decimal('105.00'), Decimal('4505.00')),
            PricePoint(datetime(2024, 1, 2), Decimal('103.00'), Decimal('4502.00'))
        ]
        series = StockPriceSeries(ticker, points)

        start_date, end_date = series.get_date_range()

        assert start_date == datetime(2024, 1, 1)
        assert end_date == datetime(2024, 1, 3)

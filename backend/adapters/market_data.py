import yfinance as yf
from datetime import datetime, date
from decimal import Decimal
from typing import List
import pandas as pd

from backend.domain import PricePoint, MarketDataProvider


class YFinanceMarketDataProvider(MarketDataProvider):
    def __init__(self, market_index: str = "^GSPC"):
        self.market_index = market_index

    def fetch_prices(self, ticker: str, start_date: date, end_date: date) -> List[PricePoint]:
        try:
            stock = yf.Ticker(ticker)
            stock_data = stock.history(start=start_date, end=end_date)

            market = yf.Ticker(self.market_index)
            market_data = market.history(start=start_date, end=end_date)

            if stock_data.empty or market_data.empty:
                return []

            stock_data = stock_data.reset_index()
            market_data = market_data.reset_index()

            merged_data = pd.merge(
                stock_data[['Date', 'Close']],
                market_data[['Date', 'Close']],
                on='Date',
                suffixes=('_stock', '_market'),
                how='inner'
            )

            price_points = []
            for _, row in merged_data.iterrows():
                price_point = PricePoint(
                    date=pd.to_datetime(row['Date']).to_pydatetime(),
                    price=Decimal(str(round(row['Close_stock'], 2))),
                    market_reference_price=Decimal(str(round(row['Close_market'], 2)))
                )
                price_points.append(price_point)

            return price_points

        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return []

    def fetch_index_prices(self, index_symbol: str, start_date: date, end_date: date) -> List[PricePoint]:
        try:
            index = yf.Ticker(index_symbol)
            index_data = index.history(start=start_date, end=end_date)

            if index_data.empty:
                return []

            index_data = index_data.reset_index()

            price_points = []
            for _, row in index_data.iterrows():
                price_point = PricePoint(
                    date=pd.to_datetime(row['Date']).to_pydatetime(),
                    price=Decimal(str(round(row['Close'], 2))),
                    market_reference_price=Decimal(str(round(row['Close'], 2)))
                )
                price_points.append(price_point)

            return price_points

        except Exception as e:
            print(f"Error fetching index data for {index_symbol}: {e}")
            return []


class FakeMarketDataProvider(MarketDataProvider):
    def __init__(self):
        self.fake_data = {}

    def add_fake_data(self, ticker: str, price_points: List[PricePoint]):
        self.fake_data[ticker.upper()] = price_points

    def fetch_prices(self, ticker: str, start_date: date, end_date: date) -> List[PricePoint]:
        ticker_data = self.fake_data.get(ticker.upper(), [])

        filtered_data = [
            point for point in ticker_data
            if start_date <= point.date.date() <= end_date
        ]

        return filtered_data

    def fetch_index_prices(self, index_symbol: str, start_date: date, end_date: date) -> List[PricePoint]:
        return self.fetch_prices(index_symbol, start_date, end_date)

import pandas as pd
import numpy as np
import re
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    from prophet import Prophet
except ImportError:
    print("Warning: Facebook Prophet not installed. Install with: pip install prophet")
    Prophet = None


@dataclass
class ForecastResult:
    forecasted_data: pd.DataFrame
    lower_bound_data: pd.DataFrame
    upper_bound_data: pd.DataFrame
    forecast_periods: List[str]
    is_quarterly: bool
    metadata: Dict[str, any]


class ForecastService:

    def __init__(self):
        if Prophet is None:
            raise ImportError("Facebook Prophet is required for forecasting. Install with: pip install prophet")

    def forecast_dataframe(self, df: pd.DataFrame, forecast_years: int = 10) -> ForecastResult:
        if df.empty:
            raise ValueError("Cannot forecast empty DataFrame")

        forecasted_df = df.copy()
        lower_bound_df = df.copy()
        upper_bound_df = df.copy()

        date_columns = self._identify_date_columns(df)
        if not date_columns:
            raise ValueError("No valid date columns found in the dataframe")

        sorted_columns = sorted(date_columns.keys(), key=lambda x: date_columns[x])

        if len(sorted_columns) < 2:
            raise ValueError("Need at least 2 date points for forecasting")

        is_quarterly = self._detect_quarterly_data(date_columns, sorted_columns)
        future_dates = self._generate_future_dates(
            date_columns, sorted_columns, forecast_years, is_quarterly
        )

        for date_str in future_dates:
            forecasted_df[date_str] = np.nan
            lower_bound_df[date_str] = np.nan
            upper_bound_df[date_str] = np.nan

        successful_forecasts = 0
        failed_forecasts = 0

        for idx in df.index:
            try:
                historical_data = self._prepare_historical_data(df, idx, sorted_columns, date_columns)

                if len(historical_data) < 2:
                    failed_forecasts += 1
                    continue

                predictions = self._forecast_metric(historical_data, future_dates, is_quarterly)

                if predictions is not None:
                    for i, date_str in enumerate(future_dates):
                        forecasted_df.loc[idx, date_str] = round(predictions['yhat'].iloc[i], 2)
                        lower_bound_df.loc[idx, date_str] = round(predictions['yhat_lower'].iloc[i], 2)
                        upper_bound_df.loc[idx, date_str] = round(predictions['yhat_upper'].iloc[i], 2)
                    successful_forecasts += 1
                else:
                    failed_forecasts += 1

            except Exception as e:
                print(f"Prophet forecasting failed for {idx}: {str(e)}")
                failed_forecasts += 1
                continue

        metadata = {
            'successful_forecasts': successful_forecasts,
            'failed_forecasts': failed_forecasts,
            'total_metrics': len(df.index),
            'forecast_years': forecast_years,
            'is_quarterly': is_quarterly,
            'original_columns': len(sorted_columns),
            'forecast_columns': len(future_dates)
        }

        return ForecastResult(
            forecasted_data=forecasted_df,
            lower_bound_data=lower_bound_df,
            upper_bound_data=upper_bound_df,
            forecast_periods=future_dates,
            is_quarterly=is_quarterly,
            metadata=metadata
        )

    def _identify_date_columns(self, df: pd.DataFrame) -> Dict[str, date]:
        date_pattern = re.compile(r'^(\d{4})[-/](\d{2})[-/](\d{2})$')
        date_columns = {}

        for col in df.columns:
            parsed_date = self._parse_column_to_date(col, date_pattern)
            if parsed_date is not None:
                date_columns[col] = parsed_date

        return date_columns

    def _parse_column_to_date(self, col, date_pattern) -> Optional[date]:
        if isinstance(col, (date, datetime)):
            return col if isinstance(col, date) else col.date()

        if isinstance(col, str):
            match = date_pattern.match(col)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)

            if col.isdigit():
                return date(int(col), 1, 1)

        if isinstance(col, (int, float)) and not math.isnan(col):
            return date(int(col), 1, 1)

        return None

    def _detect_quarterly_data(self, date_columns: Dict[str, date], sorted_columns: List[str]) -> bool:
        if len(sorted_columns) < 2:
            return False

        date_differences = []
        for i in range(1, len(sorted_columns)):
            previous_date = date_columns[sorted_columns[i-1]]
            current_date = date_columns[sorted_columns[i]]
            difference_days = (current_date - previous_date).days
            date_differences.append(difference_days)

        median_interval_days = int(np.median(date_differences))
        return 70 <= median_interval_days <= 110

    def _generate_future_dates(
        self,
        date_columns: Dict[str, date],
        sorted_columns: List[str],
        forecast_years: int,
        is_quarterly: bool
    ) -> List[str]:

        last_date = date_columns[sorted_columns[-1]]
        future_dates = []
        current_date = last_date

        periods = forecast_years * 4 if is_quarterly else forecast_years

        date_pattern = re.compile(r'^(\d{4})[-/](\d{2})[-/](\d{2})$')
        uses_date_format = date_pattern.match(str(sorted_columns[0]))

        for i in range(periods):
            if is_quarterly:
                year = current_date.year + ((current_date.month + 3) // 12)
                month = ((current_date.month + 3 - 1) % 12) + 1
                days_in_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                day = min(current_date.day, days_in_month[month-1])
                current_date = date(year, month, day)
            else:
                current_date = date(current_date.year + 1, current_date.month, current_date.day)

            if uses_date_format:
                date_str = current_date.strftime('%Y-%m-%d')
            else:
                date_str = str(current_date.year)

            future_dates.append(date_str)

        return future_dates

    def _prepare_historical_data(
        self,
        df: pd.DataFrame,
        metric_idx: str,
        sorted_columns: List[str],
        date_columns: Dict[str, date]
    ) -> List[Dict]:

        historical_data = []

        for col in sorted_columns:
            value = df.loc[metric_idx, col]
            if pd.isna(value) or not isinstance(value, (int, float)):
                continue
            historical_data.append({'ds': date_columns[col], 'y': float(value)})

        return historical_data

    def _forecast_metric(
        self,
        historical_data: List[Dict],
        future_dates: List[str],
        is_quarterly: bool
    ) -> Optional[pd.DataFrame]:

        try:
            historical_df = pd.DataFrame(historical_data)

            if is_quarterly:
                model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=False,
                    daily_seasonality=False
                )
            else:
                model = Prophet(
                    yearly_seasonality=False,
                    weekly_seasonality=False,
                    daily_seasonality=False
                )

            model.fit(historical_df)

            date_pattern = re.compile(r'^(\d{4})[-/](\d{2})[-/](\d{2})$')

            if date_pattern.match(str(future_dates[0])):
                future = pd.DataFrame([
                    {'ds': datetime.strptime(date_str, '%Y-%m-%d')}
                    for date_str in future_dates
                ])
            else:
                future = pd.DataFrame([
                    {'ds': datetime(int(date_str), 1, 1)}
                    for date_str in future_dates
                ])

            forecast = model.predict(future)
            return forecast[['yhat', 'yhat_lower', 'yhat_upper']]

        except Exception as e:
            print(f"Prophet model failed: {str(e)}")
            return None


def forecast_financial_data(df: pd.DataFrame, forecast_years: int = 10) -> ForecastResult:
    service = ForecastService()
    return service.forecast_dataframe(df, forecast_years)


def get_forecast_summary(result: ForecastResult) -> Dict[str, any]:
    return {
        'total_metrics_processed': result.metadata['total_metrics'],
        'successful_forecasts': result.metadata['successful_forecasts'],
        'failed_forecasts': result.metadata['failed_forecasts'],
        'success_rate': result.metadata['successful_forecasts'] / result.metadata['total_metrics'] * 100,
        'forecast_years': result.metadata['forecast_years'],
        'is_quarterly_data': result.metadata['is_quarterly'],
        'forecast_periods_generated': len(result.forecast_periods),
        'original_periods': result.metadata['original_columns']
    }

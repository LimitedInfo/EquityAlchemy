import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Union

np.float_ = np.float64

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except (ImportError, AttributeError) as e:
    print(f"Warning: Prophet import failed ({e}). Prophet forecasting will not be available.")
    PROPHET_AVAILABLE = False


DEFAULT_FORECASTING_METHODS = {
    "Revenue": {"method": "prophet"},
    "Sales": {"method": "prophet"},
    "Cost of Goods Sold": {"method": "ratio", "base": "Revenue"},
    "R&D Expense": {"method": "ratio", "base": "Revenue"},
    "SG&A Expense": {"method": "ratio", "base": "Revenue"},
    "Operating Expenses": {"method": "ratio", "base": "Revenue"},
    "Operating Income": {"method": "ratio", "base": "Revenue"},
    "Net Income": {"method": "ratio", "base": "Revenue"},
    "Shares Outstanding": {"method": "growth_rate"},
    "Diluted Shares Outstanding": {"method": "growth_rate"},
    "Operating Cash Flow": {"method": "ratio", "base": "Revenue"},
    "Capital Expenditures": {"method": "ratio", "base": "Operating Cash Flow"},
}

DEFAULT_CALCULATED_METHODS = {
    "Gross Profit": {"method": "calc", "formula": ["Revenue", "minus", "Cost of Goods Sold"]},
    "Basic EPS": {"method": "calc", "formula": ["Net Income", "divided by", "Shares Outstanding"]},
    "Diluted EPS": {"method": "calc", "formula": ["Net Income", "divided by", "Diluted Shares Outstanding"]},
    "Free Cash Flow": {"method": "calc", "formula": ["Operating Cash Flow", "minus", "Capital Expenditures"]},
}


def _fallback_growth_forecast(df: pd.DataFrame, key: str, periods: int = 5, default_growth: float = 0.05) -> List[float]:
    if key not in df.index:
        return [np.nan] * periods
    
    values = []
    for col in df.columns:
        try:
            value = df.loc[key, col]
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            if not pd.isna(value):
                values.append(value)
        except (ValueError, AttributeError):
            continue
    
    if len(values) < 2:
        return [np.nan] * periods
    
    growth_rates = []
    for i in range(1, len(values)):
        if values[i-1] != 0:
            growth_rates.append((values[i] - values[i-1]) / values[i-1])
    
    if growth_rates:
        avg_growth = np.mean(growth_rates[-3:]) if len(growth_rates) >= 3 else np.mean(growth_rates)
    else:
        avg_growth = default_growth
    
    last_value = values[-1]
    forecasts = []
    for i in range(1, periods + 1):
        forecasts.append(last_value * ((1 + avg_growth) ** i))
    
    return forecasts


def forecast_prophet(df: pd.DataFrame, key: str, periods: int = 5) -> List[float]:
    if not PROPHET_AVAILABLE:
        print(f"Prophet not available. Using growth rate forecasting for {key} instead.")
        return _fallback_growth_forecast(df, key, periods)
    
    if key not in df.index:
        return [np.nan] * periods
    
    historical_data = []
    for col in df.columns:
        try:
            year = int(col.split(':')[1].split('-')[0])
            value = df.loc[key, col]
            
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            
            if not pd.isna(value):
                historical_data.append({
                    'ds': datetime(year, 12, 31),
                    'y': value
                })
        except (ValueError, IndexError, AttributeError):
            continue
    
    if len(historical_data) < 2:
        return [np.nan] * periods
    
    prophet_df = pd.DataFrame(historical_data)
    prophet_df = prophet_df.sort_values('ds')
    
    model = Prophet(yearly_seasonality=False, 
                    weekly_seasonality=False,
                    daily_seasonality=False,
                    changepoint_prior_scale=0.05)
    
    model.fit(prophet_df)
    
    last_year = prophet_df['ds'].max().year
    future_dates = pd.DataFrame({
        'ds': [datetime(last_year + i + 1, 12, 31) for i in range(periods)]
    })
    
    forecast = model.predict(future_dates)
    
    return forecast['yhat'].tolist()


def forecast_ratio(df: pd.DataFrame, key: str, base: str, base_forecast: Union[pd.Series, List[float]], 
                  periods: int = 5) -> List[float]:
    if key not in df.index or base not in df.index:
        return [np.nan] * periods
    
    ratios = []
    for col in df.columns:
        try:
            key_value = df.loc[key, col]
            base_value = df.loc[base, col]
            
            if isinstance(key_value, str):
                key_value = float(key_value.replace(',', ''))
            if isinstance(base_value, str):
                base_value = float(base_value.replace(',', ''))
            
            if not pd.isna(key_value) and not pd.isna(base_value) and base_value != 0:
                ratios.append(key_value / base_value)
        except (ValueError, AttributeError):
            continue
    
    if not ratios:
        return [np.nan] * periods
    
    avg_ratio = np.mean(ratios[-3:]) if len(ratios) >= 3 else np.mean(ratios)
    
    if all(pd.isna(base_forecast)):
        last_base_value = None
        for col in reversed(df.columns):
            try:
                value = df.loc[base, col]
                if isinstance(value, str):
                    value = float(value.replace(',', ''))
                if not pd.isna(value):
                    last_base_value = value
                    break
            except (ValueError, AttributeError):
                continue
        
        if last_base_value is None:
            return [np.nan] * periods
        
        base_forecast = [last_base_value * (1.05 ** i) for i in range(1, periods + 1)]
    
    return [base_val * avg_ratio for base_val in base_forecast]


def forecast_growth_rate(df: pd.DataFrame, key: str, periods: int = 5, 
                        default_growth: float = 0.02) -> List[float]:
    if key not in df.index:
        return [np.nan] * periods
    
    values = []
    for col in df.columns:
        try:
            value = df.loc[key, col]
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            if not pd.isna(value):
                values.append(value)
        except (ValueError, AttributeError):
            continue
    
    if len(values) < 2:
        return [np.nan] * periods
    
    growth_rates = []
    for i in range(1, len(values)):
        if values[i-1] != 0:
            growth_rates.append((values[i] - values[i-1]) / values[i-1])
    
    if growth_rates:
        avg_growth = np.mean(growth_rates[-3:]) if len(growth_rates) >= 3 else np.mean(growth_rates)
    else:
        avg_growth = default_growth
    
    last_value = values[-1]
    forecasts = []
    for i in range(1, periods + 1):
        forecasts.append(last_value * ((1 + avg_growth) ** i))
    
    return forecasts


def create_forecast_columns(df: pd.DataFrame, 
                           defaults: Optional[Dict[str, Dict[str, Any]]] = None,
                           defaults_calculated: Optional[Dict[str, Dict[str, Any]]] = None,
                           periods: int = 5,
                           verbose: bool = False) -> pd.DataFrame:
    if defaults is None:
        defaults = DEFAULT_FORECASTING_METHODS
    
    if defaults_calculated is None:
        defaults_calculated = DEFAULT_CALCULATED_METHODS
    
    forecast_df = df.copy()
    
    last_year = max([int(col.split(':')[0].split('-')[0]) for col in df.columns 
                     if ':' in col and col.split(':')[0].split('-')[0].isdigit()])
    last_col = df.columns[-1]
    last_date = last_col.split(':')[1]
    last_date_obj = datetime.strptime(last_date, '%Y-%m-%d')
    last_year = last_date_obj.year
    
    forecast_columns = []
    for i in range(1, periods + 1):
        year = last_year + i
        col_name = f"{year}:{last_date_obj.strftime('%m-%d')}:Forecast"
        forecast_columns.append(col_name)
        forecast_df[col_name] = np.nan
    
    for key, config in defaults.items():
        if key not in forecast_df.index:
            continue
        
        if config["method"] == "prophet":
            forecasts = forecast_prophet(forecast_df, key, periods)
        elif config["method"] == "ratio":
            if verbose:
                print(f"Forecasting {key} as a ratio of {config['base']}")
            base_forecast = forecast_df.loc[config["base"], :][-periods:]
            forecasts = forecast_ratio(forecast_df, key, config["base"], base_forecast, periods)
        elif config["method"] == "growth_rate":
            forecasts = forecast_growth_rate(forecast_df, key, periods)
        else:
            continue
        
        for i, col in enumerate(forecast_columns):
            if i < len(forecasts):
                forecast_df.loc[key, col] = forecasts[i]
    
    for key in forecast_df.index:
        if key not in defaults.keys():
            if verbose:
                print(f"Forecasting {key} as a ratio of Revenue")

            base_forecast = forecast_df.loc["Revenue", :][-periods:]
            forecasts = forecast_ratio(forecast_df, key, "Revenue", base_forecast, periods)
            for i, col in enumerate(forecast_columns):
                if i < len(forecasts):
                    forecast_df.loc[key, col] = forecasts[i]
    
    for key, config in defaults_calculated.items():
        if config["method"] == "calc":
            formula = config["formula"]
            
            for col in forecast_columns:
                if len(formula) == 3:
                    operand1_key = formula[0]
                    operator = formula[1]
                    operand2_key = formula[2]
                    
                    val1 = forecast_df.loc[operand1_key, col] if operand1_key in forecast_df.index else np.nan
                    val2 = forecast_df.loc[operand2_key, col] if operand2_key in forecast_df.index else np.nan
                    
                    if not pd.isna(val1) and not pd.isna(val2):
                        if operator == "minus":
                            forecast_df.loc[key, col] = val1 - val2
                        elif operator == "plus":
                            forecast_df.loc[key, col] = val1 + val2
                        elif operator == "divided by" and val2 != 0:
                            forecast_df.loc[key, col] = val1 / val2
                        elif operator == "times":
                            forecast_df.loc[key, col] = val1 * val2
    
    for col in forecast_columns:
        forecast_df[col] = forecast_df[col].apply(
            lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and not pd.isna(x) and abs(x) >= 1000 else x
        )
    
    return forecast_df


def plot_forecast(df: pd.DataFrame, metric_name: str, figsize: tuple = (12, 6)) -> None:
    if metric_name not in df.index:
        print(f"Metric '{metric_name}' not found in dataframe")
        return
    
    historical_years = []
    historical_values = []
    forecast_years = []
    forecast_values = []
    
    for col in df.columns:
        try:
            year = int(col.split(':')[0].split('-')[0])
            value = df.loc[metric_name, col]
            
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            
            if not pd.isna(value):
                if 'Forecast' in col:
                    forecast_years.append(year)
                    forecast_values.append(value)
                else:
                    historical_years.append(year)
                    historical_values.append(value)
        except (ValueError, IndexError, AttributeError):
            continue
    
    if not historical_years and not forecast_years:
        print(f"No data available for '{metric_name}'")
        return
    
    plt.figure(figsize=figsize)
    
    if historical_years:
        plt.plot(historical_years, historical_values, 'bo-', label='Historical', linewidth=2, markersize=8)
    
    if forecast_years:
        plt.plot(forecast_years, forecast_values, 'rs--', label='Forecast', linewidth=2, markersize=8)
        
        if historical_years and forecast_years:
            plt.plot([historical_years[-1], forecast_years[0]], 
                    [historical_values[-1], forecast_values[0]], 
                    'g--', alpha=0.5, linewidth=1)
    
    plt.title(f'{metric_name} - Historical vs Forecast', fontsize=14, fontweight='bold')
    plt.xlabel('Year', fontsize=12)
    plt.ylabel('Value (in millions)', fontsize=12)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:,.0f}M' if x >= 1e6 else f'${x:,.0f}'))
    
    plt.tight_layout()
    plt.show()


def display_forecast_sample(forecasted_df: pd.DataFrame, 
                           sample_metrics: Optional[List[str]] = None,
                           historical_periods: int = 3) -> pd.DataFrame:
    if sample_metrics is None:
        sample_metrics = ["Revenue", "Cost of Goods Sold", "Operating Income", 
                         "Net Income", "Operating Cash Flow"]
    
    available_metrics = [m for m in sample_metrics if m in forecasted_df.index]
    
    if not available_metrics:
        print("No sample metrics found in the dataframe")
        return pd.DataFrame()
    
    print("Sample of forecasted financial metrics:")
    print("=" * 80)
    
    historical_cols = [col for col in forecasted_df.columns if 'Forecast' not in col][-historical_periods:]
    forecast_cols = [col for col in forecasted_df.columns if 'Forecast' in col]
    display_cols = historical_cols + forecast_cols
    
    display_df = forecasted_df.loc[available_metrics, display_cols]
    print(display_df)
    
    return display_df

import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
from service_layer import service
from service_layer import uow
from service_layer import forecasting
# from service_layer import forecast
import pandas as pd
import numpy as np
import traceback

free_query_usage: Dict[str, int] = {}

class FinancialMetric(BaseModel):
    name: str
    values: Dict[str, float]

class FinancialStatements(BaseModel):
    ticker: str
    form_type: Optional[str] = None
    metrics: List[FinancialMetric]
    periods: List[str]

class ForecastRequest(BaseModel):
    forecast_years: int = 10

class ForecastResponse(BaseModel):
    ticker: str
    form_type: str
    forecasted_data: List[Dict]
    lower_bound_data: List[Dict]
    upper_bound_data: List[Dict]
    forecast_periods: List[str]
    metadata: Dict

class CompanyResponse(BaseModel):
    name: str
    ticker: str
    cik: Optional[str] = None
    cusip: Optional[str] = None
    exchange: Optional[str] = None
    is_delisted: Optional[bool] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    sic: Optional[str] = None
    sic_sector: Optional[str] = None
    sic_industry: Optional[str] = None
    fama_sector: Optional[str] = None
    fama_industry: Optional[str] = None
    currency: Optional[str] = None
    location: Optional[str] = None
    sec_api_id: Optional[str] = None

class PriceDataResponse(BaseModel):
    ticker: str
    dates: List[str]
    prices: List[float]
    price_changes: List[Optional[float]]

app = FastAPI()

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print("--- Unhandled Exception Traceback ---")
    traceback.print_exc()
    print("-----------------------------------")
    return JSONResponse(
        status_code=500,
        content={
            "message": "An internal server error occurred.",
            "error_type": type(exc).__name__,
            "details": str(exc),
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://equityalchemy.ai",
        "https://www.equityalchemy.ai",
        "https://api.equityalchemy.ai",
        "https://www.api.equityalchemy.ai",
        "https://basic-sparkling-thunder-7964.fly.dev",  # deployed frontend
        "http://localhost:3000",  # for local development
        "http://localhost:8000"   # for local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

def check_free_query_limit(request: Request) -> bool:
    client_ip = get_client_ip(request)
    usage_count = free_query_usage.get(client_ip, 0)
    return usage_count < 1

def increment_free_query_usage(request: Request):
    client_ip = get_client_ip(request)
    free_query_usage[client_ip] = free_query_usage.get(client_ip, 0) + 1

def is_authenticated(request: Request) -> bool:
    """Simple check for authentication - look for auth headers or session cookies"""
    # Check for Authorization header (from Clerk frontend)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return True

    # Check for Clerk session cookies
    if hasattr(request, 'cookies'):
        clerk_session = request.cookies.get("__session")
        if clerk_session:
            return True

    return False

@app.get("/")
async def root():
    return {"message": "Financial Data API powered by Clerk Authentication"}

@app.get("/api/debug/db-info")
async def debug_db_info():
    """Debug endpoint to check database connection info."""
    try:
        from sqlalchemy import text
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            # Get database name
            result = uow_instance.session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            
            # Get current schema
            result = uow_instance.session.execute(text("SELECT current_schema()"))
            schema = result.scalar()
            
            # Get search path
            result = uow_instance.session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            
            # Check if table exists
            result = uow_instance.session.execute(
                text("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE tablename = 'combined_financial_statements'
                """)
            )
            table_info = result.fetchall()
            
            # Get all tables in public schema
            result = uow_instance.session.execute(
                text("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                    LIMIT 10
                """)
            )
            public_tables = [row[0] for row in result.fetchall()]
            
            return {
                "database": db_name,
                "current_schema": schema,
                "search_path": search_path,
                "combined_financial_statements_found_in": [
                    {"schema": row[0], "table": row[1]} for row in table_info
                ],
                "sample_public_tables": public_tables
            }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/api/free-query-status")
async def get_free_query_status(request: Request):
    client_ip = get_client_ip(request)
    usage_count = free_query_usage.get(client_ip, 0)
    return {
        "free_queries_used": usage_count,
        "free_queries_remaining": max(0, 1 - usage_count),
        "has_free_queries": usage_count < 1
    }

@app.get("/api/tickers/search")
async def search_tickers_endpoint(term: str):
    if not term:
        return []
    try:
        companies = service.search_companies_from_csv(term)
        return companies
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error searching for companies.")


@app.post("/api/company/update-shares")
async def update_shares_endpoint():
    try:
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            service.update_shares_outstanding(uow_instance)
        return {"message": "Shares outstanding updated successfully."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error updating shares outstanding.")


@app.post("/api/company/supplement/{ticker}", response_model=CompanyResponse)
async def supplement_company_data_endpoint(ticker: str):
    """
    Supplements company data from an external API and stores it.
    """
    try:
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            company = service.supplement_company_data(ticker, uow_instance)
        return company
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/financial/income/{ticker}")
async def get_income_statements(ticker: str, request: Request, form_type: Optional[str] = None):
    # Validate that the company exists in our CSV
    if not service.validate_company_exists(ticker):
        raise HTTPException(
            status_code=422,
            detail=f"Company '{ticker}' not found. Please select a valid company from the suggestions."
        )

    # Convert company name to ticker if needed
    validated_ticker = service.get_ticker_from_name_or_ticker(ticker)

    # Check if user is authenticated
    user_authenticated = is_authenticated(request)

    # If not authenticated and no free queries left, reject request
    if not user_authenticated and not check_free_query_limit(request):
        raise HTTPException(
            status_code=401,
            detail="Free query limit exceeded. Please sign in to continue accessing financial data.",
            headers={"X-Free-Limit-Exceeded": "true"}
        )

    try:
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            combined_financial_statements = service.get_consolidated_income_statements(validated_ticker, uow_instance, form_type=form_type, retrieve_from_database=True, overwrite_database=False)

        metrics = []
        metric_names = combined_financial_statements.get_all_metrics()
        sorted_periods = sorted(combined_financial_statements.get_all_periods(), key=lambda x: x.split(':')[0])

        for metric_name in metric_names:
            metric_series = combined_financial_statements.get_metric(metric_name)

            if metric_series is not None:
                values = {}

                for period in sorted_periods:
                    value = metric_series.get(period)
                    try:
                        if isinstance(value, pd.Series):
                            if not value.empty and pd.notna(value.iloc[0]):
                                values[period] = float(value.iloc[0])
                        else:
                            if pd.notna(value):
                                values[period] = float(value)
                    except (ValueError, TypeError, IndexError) as e:
                        continue

                metrics.append(FinancialMetric(
                    name=metric_name,
                    values=values
                ))

        # Track free query usage for non-authenticated users
        if not user_authenticated:
            increment_free_query_usage(request)

        response_data = FinancialStatements(
            ticker=combined_financial_statements.ticker,
            form_type=combined_financial_statements.form_type,
            metrics=metrics,
            periods=sorted_periods
        )

        response = JSONResponse(content=response_data.dict())
        if not user_authenticated:
            response.headers["X-Free-Query-Used"] = "true"
            response.headers["X-Remaining-Free-Queries"] = "0"

        return response

    except Exception as e:
        print(f"--- Exception in /api/financial/income/{ticker} ---")
        traceback.print_exc()
        print("--------------------------------------------------")
        raise HTTPException(status_code=500, detail=f"Error fetching financial data for {ticker}: {str(e)}")

@app.get("/api/financial/prices/{ticker}")
async def get_price_data(ticker: str, days: int = 30):
    try:
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            price_series = service.get_price_time_series(ticker, days, uow_instance)

        df = price_series.table()
        if df.empty:
            return PriceDataResponse(ticker=ticker, dates=[], prices=[], price_changes=[])

        dates = [str(date) for date in df.index]
        prices = [float(price) if pd.notna(price) and np.isfinite(price) else 0.0 for price in df['Price']]

        price_changes = []
        if 'Price_Change_Pct' in df.columns:
            price_changes = [float(change) if pd.notna(change) and np.isfinite(change) else None
                           for change in df['Price_Change_Pct']]

        return PriceDataResponse(
            ticker=ticker,
            dates=dates,
            prices=prices,
            price_changes=price_changes
        )
    except Exception as e:
        print(f"--- Exception in /api/financial/prices/{ticker} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching price data: {str(e)}")

@app.post("/api/financial/forecast/{ticker}")
async def forecast_financial_data(ticker: str, request: Request, forecast_request: ForecastRequest, form_type: Optional[str] = None):
    if not is_authenticated(request):
        raise HTTPException(
            status_code=401,
            detail="Authentication required for forecasting features. Please sign in.",
            headers={"X-Auth-Required": "true"}
        )

    try:
        # Debug logging
        print(f"=== FORECAST REQUEST DEBUG ===")
        print(f"Ticker: {ticker}")
        print(f"Form Type (query param): {form_type}")
        print(f"Forecast Years: {forecast_request.forecast_years}")

        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            combined_financial_statements = service.get_consolidated_income_statements(
                ticker, uow_instance, form_type=form_type
            )

        if not combined_financial_statements:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data found for {ticker} with form type {form_type}. Please load the financial data first."
            )

        metrics = combined_financial_statements.get_all_metrics()
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"No financial metrics found for {ticker}. The data may be empty or malformed."
            )

        df = combined_financial_statements.df
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data table available for forecasting for {ticker}."
            )

        forecasted_df = forecasting.create_forecast_columns(
            df,
            forecasting.DEFAULT_FORECASTING_METHODS,
            forecasting.DEFAULT_CALCULATED_METHODS,
            periods=forecast_request.forecast_years,
            verbose=False
        )

        def parse_numeric(v):
            if v is None:
                return None
            try:
                if isinstance(v, str):
                    vv = v.replace(",", "").replace("$", "")
                    return float(vv)
                if isinstance(v, (int, float, np.floating)):
                    return float(v)
                if isinstance(v, pd.Series):
                    if not v.empty and pd.notna(v.iloc[0]):
                        return float(v.iloc[0])
                return None
            except Exception:
                return None

        all_periods = list(forecasted_df.columns)
        sorted_periods = sorted(all_periods, key=lambda x: x.split(":")[0])

        response_metrics = []
        for metric_name in forecasted_df.index:
            series = forecasted_df.loc[metric_name]
            values = {}
            for period in sorted_periods:
                val = series.get(period) if isinstance(series, pd.Series) else None
                num = parse_numeric(val)
                if num is not None and not (isinstance(num, float) and (np.isnan(num) or np.isinf(num))):
                    values[period] = num
            response_metrics.append({
                "name": metric_name,
                "values": values
            })

        response_data = FinancialStatements(
            ticker=combined_financial_statements.ticker,
            form_type=combined_financial_statements.form_type,
            metrics=response_metrics,
            periods=sorted_periods
        )

        return JSONResponse(content=response_data.dict())

    except HTTPException:
        raise
    except ImportError as e:
        print(f"--- Import Error in forecast endpoint ---")
        traceback.print_exc()
        print("----------------------------------------")
        raise HTTPException(
            status_code=500,
            detail="Forecasting service unavailable. Please ensure Facebook Prophet is installed."
        )
    except Exception as e:
        print(f"--- Exception in /api/financial/forecast/{ticker} ---")
        traceback.print_exc()
        print("-----------------------------------------------------")
        raise HTTPException(status_code=500, detail=f"Error generating forecast for {ticker}: {str(e)}")

@app.get("/api/financial/sec-filings-url/{ticker}")
async def get_sec_filings_url(ticker: str, form_type: Optional[str] = "10-K"):
    try:
        with uow.SqlAlchemyUnitOfWork() as uow_instance:
            sec_url = service.get_sec_filings_url(ticker=ticker, form_type=form_type, uow_instance=uow_instance)

        return {"ticker": ticker, "form_type": form_type, "sec_filings_url": sec_url}

    except Exception as e:
        print(f"--- Exception in /api/financial/sec-filings-url/{ticker} ---")
        traceback.print_exc()
        print("-------------------------------------------------------")
        raise HTTPException(status_code=500, detail=f"Error getting SEC filings URL for {ticker}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

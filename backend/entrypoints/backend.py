import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
from service_layer import service
from service_layer import uow
# from service_layer import forecast
import pandas as pd
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
        "https://api.equityalchemy.ai",
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

@app.get("/api/free-query-status")
async def get_free_query_status(request: Request):
    client_ip = get_client_ip(request)
    usage_count = free_query_usage.get(client_ip, 0)
    return {
        "free_queries_used": usage_count,
        "free_queries_remaining": max(0, 1 - usage_count),
        "has_free_queries": usage_count < 1
    }

@app.get("/api/financial/income/{ticker}")
async def get_income_statements(ticker: str, request: Request, form_type: Optional[str] = None):
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
            combined_financial_statements = service.get_consolidated_income_statements(ticker, uow_instance, form_type=form_type)

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
            print(f"Loading financial data for {ticker}...")
            combined_financial_statements = service.get_consolidated_income_statements(
                ticker, uow_instance, form_type=form_type
            )

            print(f"Financial statements loaded: {combined_financial_statements is not None}")
            if combined_financial_statements:
                metrics = combined_financial_statements.get_all_metrics()
                periods = combined_financial_statements.get_all_periods()
                print(f"Metrics found: {len(metrics) if metrics else 0}")
                print(f"Periods found: {len(periods) if periods else 0}")
                print(f"First few metrics: {metrics[:3] if metrics else 'None'}")
                print(f"First few periods: {periods[:3] if periods else 'None'}")

        if not combined_financial_statements:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data found for {ticker} with form type {form_type}. Please load the financial data first."
            )

        metrics = combined_financial_statements.get_all_metrics()
        if not metrics:
            print(f"ERROR: No metrics found in financial statements")
            raise HTTPException(
                status_code=404,
                detail=f"No financial metrics found for {ticker}. The data may be empty or malformed."
            )

        df = combined_financial_statements.table
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame empty: {df.empty}")
        print(f"DataFrame columns: {list(df.columns)}")

        if df.empty:
            print(f"ERROR: DataFrame is empty")
            raise HTTPException(
                status_code=404,
                detail=f"No financial data table available for forecasting for {ticker}."
            )

        forecast_result = forecast.forecast_financial_data(df, forecast_request.forecast_years)

        forecasted_data_dict = forecast_result.forecasted_data.reset_index().to_dict('records')
        lower_bound_dict = forecast_result.lower_bound_data.reset_index().to_dict('records')
        upper_bound_dict = forecast_result.upper_bound_data.reset_index().to_dict('records')

        response_data = ForecastResponse(
            ticker=ticker,
            form_type=form_type,
            forecasted_data=forecasted_data_dict,
            lower_bound_data=lower_bound_dict,
            upper_bound_data=upper_bound_dict,
            forecast_periods=forecast_result.forecast_periods,
            metadata=forecast_result.metadata
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

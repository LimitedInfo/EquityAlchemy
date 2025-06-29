import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
from service_layer import service
from service_layer import uow
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

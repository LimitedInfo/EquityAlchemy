from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
from typing import Dict, Optional, List
import backend.service_layer.service as service
import backend.service_layer.uow as uow
import backend.adapters.repository as repository
import pandas as pd
import traceback
from typing import List, Optional


sessions: Dict[str, dict] = {}

class User(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    username: str

class FinancialMetric(BaseModel):
    name: str
    values: Dict[str, float]

class FinancialStatements(BaseModel):
    ticker: str
    form_type: Optional[str] = None
    metrics: List[FinancialMetric]
    periods: List[str]

class CORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app = FastAPI()
app.add_middleware(CORSHeaderMiddleware)

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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicitly list methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],  # Expose all headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

def get_current_user(session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[session_id]

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/login")
async def login(user: User, response: Response):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"username": user.username}

    response.set_cookie(key="session_id", value=session_id, httponly=True)

    return {"status": "success", "message": "Login successful"}

@app.get("/user/profile")
async def get_profile(user_data: dict = Depends(get_current_user)):
    return UserProfile(username=user_data["username"])

@app.post("/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id and session_id in sessions:
        del sessions[session_id]

    response.delete_cookie(key="session_id")

    return {"status": "success", "message": "Logout successful"}



@app.get("/api/financial/income/{ticker}")
async def get_income_statements(ticker: str, form_type: Optional[str] = None):
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

        return FinancialStatements(
            ticker=combined_financial_statements.ticker,
            form_type=combined_financial_statements.form_type,
            metrics=metrics,
            periods=sorted_periods
        )
    except Exception as e:
        print(f"--- Exception in /api/financial/income/{ticker} ---")
        traceback.print_exc()
        print("--------------------------------------------------")
        raise HTTPException(status_code=500, detail=f"Error fetching financial data for {ticker}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

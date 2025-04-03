from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
from typing import Dict, Optional, List
import service
import repository
import pandas as pd

# Session storage (in-memory for simplicity)
# In a real app, you'd use Redis, a database, or another persistent store
sessions: Dict[str, dict] = {}

class User(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    username: str

class CORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app = FastAPI()

# Add custom CORS middleware
app.add_middleware(CORSHeaderMiddleware)

# Keep existing CORS middleware as well
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
    # In a real app, validate credentials against a database
    # For test purposes, accept any login

    # Create a session
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"username": user.username}

    # Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    return {"status": "success", "message": "Login successful"}

@app.get("/user/profile")
async def get_profile(user_data: dict = Depends(get_current_user)):
    return UserProfile(username=user_data["username"])

@app.post("/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    # Clear the session
    if session_id and session_id in sessions:
        del sessions[session_id]

    # Clear the cookie - use expires instead of max_age for better compatibility
    response.delete_cookie(key="session_id")

    return {"status": "success", "message": "Logout successful"}

# Add new models for financial data
class FinancialMetric(BaseModel):
    name: str
    values: Dict[str, float]

class FinancialStatements(BaseModel):
    ticker: str
    form_type: Optional[str] = None
    metrics: List[FinancialMetric]
    periods: List[str]

@app.get("/api/financial/income/{ticker}")
async def get_income_statements(ticker: str, form_type: Optional[str] = None):
    """
    Get combined income statements for a company.

    Args:
        ticker: Company ticker symbol
        form_type: Optional form type to filter by (e.g., '10-K', '10-Q')

    Returns:
        FinancialStatements: Combined income statements
    """
    try:
        # Initialize repositories
        sec_repository = repository.SECFilingRepository()
        llm_repository = repository.LLMRepository()

        # Call the service function
        combined_statements = service.get_combined_income_statements(
            ticker,
            sec_repository,
            llm_repository=llm_repository,
            form_type=form_type
        )

        # Convert to response model
        metrics = []
        for metric_name in combined_statements.get_all_metrics():
            metric_series = combined_statements.get_metric(metric_name)
            metrics.append(FinancialMetric(
                name=metric_name,
                values={period: float(value) for period, value in metric_series.items() if pd.notna(value)}
            ))

        return FinancialStatements(
            ticker=combined_statements.ticker,
            form_type=combined_statements.form_type,
            metrics=metrics,
            periods=combined_statements.get_all_periods()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching financial data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

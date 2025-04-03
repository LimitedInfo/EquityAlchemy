from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend import app
import model
import service
from repository import FakeSECFilingRepository

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_cors_headers():
    response = client.get("/", headers={"Origin": "http://localhost"})
    assert response.status_code == 200

    # Check for exact header names with proper case
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers

def test_session_management():
    # Create a fresh test client for this test to avoid cookie persistence issues
    test_client = TestClient(app)

    # First request - should create a session
    response1 = test_client.post("/login", json={"username": "testuser", "password": "password123"})
    assert response1.status_code == 200
    assert "session_id" in response1.cookies

    # Save the session cookie
    session_cookie = response1.cookies.get("session_id")
    assert session_cookie is not None

    # Set the cookie on the client instance
    test_client.cookies.set("session_id", session_cookie)

    # Second request - should maintain session state
    response2 = test_client.get("/user/profile")
    assert response2.status_code == 200
    assert response2.json().get("username") == "testuser"

    # Test logout - should clear the session
    response3 = test_client.post("/logout")
    assert response3.status_code == 200
    assert response3.json() == {"status": "success", "message": "Logout successful"}

    # Verify session was actually cleared by attempting to access the profile endpoint
    response4 = test_client.get("/user/profile")
    assert response4.status_code == 401  # Should get Unauthorized since session is invalid

def test_get_income_statements():
    # Create fake repositories for testing
    fake_sec_repo = FakeSECFilingRepository()
    fake_llm_repo = MagicMock()

    # Prepare a fake filing with fake income statement data
    test_data = pd.DataFrame({
        '2023-12-31': [100, 50, 50],
        '2024-12-31': [120, 60, 60]
    }, index=['Revenue', 'Cost of Revenue', 'Gross Profit'])

    # Patch the relevant model/repository methods to return our test data
    with patch('model.Company.filter_filings') as mock_filter_filings, \
         patch('model.Filing.income_statement') as mock_income_statement, \
         patch('backend.repository.SECFilingRepository', return_value=fake_sec_repo), \
         patch('backend.repository.LLMRepository', return_value=fake_llm_repo):

        # Set up the mocks to return appropriate test data
        mock_filing = MagicMock()
        mock_statement = MagicMock()
        mock_statement.table = test_data

        mock_filing.income_statement = mock_statement
        mock_filter_filings.return_value = [mock_filing]

        # Make the actual service call with our fake repositories
        # This defines what should be returned when the backend calls the service
        actual_result = service.get_combined_income_statements(
            'AAPL',
            fake_sec_repo,
            llm_repository=fake_llm_repo,
            form_type='10-K'
        )

        # Now test the API endpoint that will use this service
        with patch('backend.service.get_combined_income_statements', return_value=actual_result):
            response = client.get("/api/financial/income/AAPL?form_type=10-K")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["form_type"] == "10-K"

            # We need to get metrics from the actual result to know what to expect
            expected_metrics = actual_result.get_all_metrics()
            assert len(data["metrics"]) == len(expected_metrics)

            # Verify periods
            assert set(data["periods"]) == set(actual_result.get_all_periods())

            # Verify metric values if metrics are available
            if expected_metrics and 'Revenue' in expected_metrics:
                revenue_metric = next((m for m in data["metrics"] if m["name"] == "Revenue"), None)
                if revenue_metric:
                    revenue_series = actual_result.get_metric('Revenue')
                    for period in revenue_series.index:
                        assert revenue_metric["values"][period] == float(revenue_series[period])

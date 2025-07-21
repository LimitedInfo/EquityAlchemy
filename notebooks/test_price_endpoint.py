import requests

# Test the price endpoint
response = requests.get("http://localhost:8000/api/financial/prices/AAPL?days=30")
print("Status Code:", response.status_code)
print("Response:", response.json())

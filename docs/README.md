


## Financial Data App

- Provide COMBINED financials for free as opposed to other apps that either limit the years provided or require payment for download of data.
- Provide quick at a glance valuation estimates so you can benchmark vs. current market price/expectations.
- Work backward from what market expects to baseline what you need to happen for the price to be fair.




### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.



# FastAPI Backend

A minimal FastAPI backend.

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the server:
```
python -m uvicorn backend.entrypoints.backend:app --reload
```

The server will start at http://localhost:8000

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run the tests with:
```
pytest
```

This will execute the test suite and verify that the backend is working correctly.

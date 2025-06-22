errrror with hims

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


# Central Index Key, unique identifier for a company or individual.
# A 20-character string that uniquely identifies a specific filing in the EDGAR system.
# The main document file within the filing submission.

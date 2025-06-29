# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements_prod.txt .

# Install dependencies
RUN pip install -r requirements_prod.txt

# Copy the rest of the application
COPY . .

# Expose port 8080
EXPOSE 8080

# Simplest possible command for testing
CMD ["uvicorn", "entrypoints.backend:app", "--host", "0.0.0.0", "--port", "8080"]

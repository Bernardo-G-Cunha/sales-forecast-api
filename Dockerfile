# Base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python logs directly to stdout/stderr
ENV PYTHONUNBUFFERED=1

# Working directory inside the container
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY requirements-api.txt .
COPY pyproject.toml .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy the application source
COPY app app
COPY common common

# Expose the API port
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden in deployment configs)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
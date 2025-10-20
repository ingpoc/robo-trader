FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/portfolio/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY services/portfolio/ ./
COPY services/ /shared/services/

# Create directories
RUN mkdir -p /app/logs

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/shared

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8001}/health || exit 1

# Run service
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8001}

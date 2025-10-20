FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl gcc && rm -rf /var/lib/apt/lists/*

COPY services/risk_management/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/risk_management/ ./
COPY services/ /shared/services/

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/shared

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8002}/health || exit 1

CMD python -m uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8002}

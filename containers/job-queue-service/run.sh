#!/bin/bash

# Job Queue Service Runner for Apple Container
# Runs Celery workers for distributed task processing

set -e

echo "Starting Job Queue Service (Celery) in container..."

# Set container-specific environment
export CONTAINER_MODE=true
export SERVICE_NAME=job-queue-service

# Create necessary directories
mkdir -p /app/logs

# Copy shared config if available
if [ -f /shared/config/config.json ]; then
    cp /shared/config/config.json /app/config/
fi

# Wait for Redis to be ready
echo "Waiting for Redis cache service..."
until redis-cli -h redis-cache ping > /dev/null 2>&1; do
    echo "Redis not ready, waiting..."
    sleep 2
done
echo "Redis is ready!"

# Start Celery worker
echo "Starting Celery worker..."
cd /app

# Start worker with all queues
exec celery -A tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --hostname=job-queue@%h \
    --queues=portfolio,risk,analytics,market_data,critical \
    --logfile=/app/logs/celery.log \
    --pidfile=/app/celery.pid
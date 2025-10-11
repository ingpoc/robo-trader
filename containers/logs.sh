#!/bin/bash

# View Logs for Robo Trader Services

SERVICE_NAME=$1

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    echo "Available services:"
    echo "  event-bus"
    echo "  portfolio-service"
    echo "  risk-service"
    echo "  execution-service"
    echo "  analytics-service"
    echo "  learning-service"
    echo "  safety-layer"
    exit 1
fi

CONTAINER_NAME="robo-trader-$SERVICE_NAME"

echo "📋 Showing logs for $SERVICE_NAME..."

# Check if container exists
if ! container ps --all --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container $CONTAINER_NAME not found"
    echo "💡 Make sure the service is running: ./containers/start-all.sh"
    exit 1
fi

# Show logs
container logs --follow "$CONTAINER_NAME"
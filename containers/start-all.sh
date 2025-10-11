#!/bin/bash

# Start All Robo Trader Services using Apple Container
# This script starts all services in the correct dependency order

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINERS_DIR="$PROJECT_ROOT/containers"
SHARED_DIR="$PROJECT_ROOT/shared"

echo "🚀 Starting Robo Trader Services with Apple Container..."

# Create shared directories
mkdir -p "$SHARED_DIR/db" "$SHARED_DIR/logs" "$SHARED_DIR/config"

# Copy base config to shared
cp "$PROJECT_ROOT/config/config.json" "$SHARED_DIR/config/" 2>/dev/null || true

# Function to start a service
start_service() {
    local service_name=$1
    local containerfile="$CONTAINERS_DIR/$service_name/Containerfile"

    if [ ! -f "$containerfile" ]; then
        echo "❌ Containerfile not found for $service_name"
        return 1
    fi

    echo "🏗️  Building $service_name container..."
    container build --tag "robo-trader-$service_name:latest" --file "$containerfile" "$PROJECT_ROOT"

    echo "🚀 Starting $service_name service..."
    container run --name "robo-trader-$service_name" \
                  --detach \
                  --volume "$SHARED_DIR/db:/shared/db" \
                  --volume "$SHARED_DIR/logs:/shared/logs" \
                  --volume "$SHARED_DIR/config:/shared/config" \
                  --network robo-trader-network \
                  "robo-trader-$service_name:latest"

    echo "✅ $service_name started"
}

# Create network if it doesn't exist
container network create robo-trader-network 2>/dev/null || true

# Start services in dependency order
echo "📋 Starting services in dependency order..."

# 1. Infrastructure services (Databases and Cache)
start_service "redis-cache"
start_service "timescale-db"

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure services to be ready..."
sleep 10

# 2. Observability stack
start_service "prometheus"
start_service "grafana"

# 3. Event Bus (fundamental service)
start_service "event-bus"

# Wait for event bus to be ready
echo "⏳ Waiting for event bus to be ready..."
sleep 10

# 4. Job Queue (distributed task processing)
start_service "job-queue-service"

# Wait for job queue to be ready
echo "⏳ Waiting for job queue to be ready..."
sleep 5

# 5. Core services
start_service "portfolio-service"
start_service "risk-service"
start_service "execution-service"
start_service "analytics-service"
start_service "learning-service"

# 6. Safety layer
start_service "safety-layer"

echo ""
echo "🎉 All Robo Trader services started!"
echo ""
echo "📊 Service Status:"
container ps --filter "name=robo-trader-"

echo ""
echo "🔍 Health Checks:"
echo "Redis Cache:   redis-cli -h localhost ping"
echo "TimescaleDB:   pg_isready -h localhost -p 5432 -U robo_trader"
echo "Prometheus:    http://localhost:9090/-/healthy"
echo "Grafana:       http://localhost:3000/api/health"
echo "Event Bus:     http://localhost:8000/health"
echo "Job Queue:     celery -A tasks inspect active"
echo "Portfolio:     http://localhost:8001/health"
echo "Risk:          http://localhost:8002/health"
echo "Execution:     http://localhost:8003/health"
echo "Analytics:     http://localhost:8004/health"
echo "Learning:      http://localhost:8005/health"
echo "Safety:        http://localhost:8006/health"

echo ""
echo "📝 View logs with: ./containers/logs.sh <service-name>"
echo "🛑 Stop all with: ./containers/stop-all.sh"
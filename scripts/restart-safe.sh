#!/bin/bash

# Safe Restart Script for Docker Compose
# Ensures no stale cache and verifies builds
# Usage: ./scripts/restart-safe.sh [service] [--rebuild]

set -e

SERVICE=${1:-all}
REBUILD=${2:-false}

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔄 Safe Restart for Robo Trader"
echo "================================="
echo ""

# Check if rebuilding is needed
if [ "$REBUILD" = "--rebuild" ] || [ "$REBUILD" = "--force" ]; then
    echo "🔨 REBUILD MODE: Rebuilding services..."
    echo ""

    if [ "$SERVICE" = "all" ]; then
        echo "Step 1: Removing old containers and images..."
        docker-compose down --remove-orphans

        echo "Step 2: Rebuilding all services (no cache)..."
        DOCKER_BUILDKIT=0 docker-compose build --no-cache
    else
        echo "Step 1: Stopping $SERVICE..."
        docker-compose stop $SERVICE 2>/dev/null || true

        echo "Step 2: Removing $SERVICE image..."
        docker rmi "robo-trader-$SERVICE:latest" 2>/dev/null || true

        echo "Step 3: Rebuilding $SERVICE (no cache)..."
        DOCKER_BUILDKIT=0 docker-compose build --no-cache $SERVICE
    fi

    echo ""
fi

echo "🚀 Starting services..."

if [ "$SERVICE" = "all" ]; then
    docker-compose up -d
else
    docker-compose up -d $SERVICE
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

echo ""
echo "📊 Service status:"
docker-compose ps

echo ""
echo "🔍 Verifying builds (checking for stale cache)..."

verify_service() {
    local svc=$1
    local container="robo-trader-$svc"

    if ! docker ps | grep -q "$container"; then
        echo "  ⏭️  $svc not running"
        return 0
    fi

    case $svc in
        paper-trading)
            # Check that routes DON'T have /api/paper-trading prefix
            if docker exec "$container" grep "@app.get.*overview" /app/main.py | grep -q "/api/paper-trading"; then
                echo "  ❌ STALE CACHE: paper-trading has old routes!"
                return 1
            else
                echo "  ✅ paper-trading: routes are correct"
                return 0
            fi
            ;;
        api-gateway)
            # Check that service URLs use container names
            if docker exec "$container" grep "robo-trader-paper-trading" /app/main.py > /dev/null; then
                echo "  ✅ api-gateway: using container names"
                return 0
            else
                echo "  ⚠️  api-gateway: check service URLs"
                return 0
            fi
            ;;
        *)
            # Basic health check
            if docker exec "$container" curl -s http://localhost:$(docker-compose ps $svc | tail -1 | awk '{print $NF}' | cut -d: -f2) > /dev/null 2>&1; then
                echo "  ✅ $svc: responding to requests"
            else
                echo "  ⏳ $svc: still starting up"
            fi
            return 0
            ;;
    esac
}

if [ "$SERVICE" = "all" ]; then
    for svc in paper-trading api-gateway; do
        verify_service "$svc" || true
    done
else
    verify_service "$SERVICE" || true
fi

echo ""
echo "✅ Restart complete!"
echo ""
echo "Next steps:"
echo "  Test API Gateway: curl http://localhost:8000/health"
echo "  Test Paper Trading: curl http://localhost:8008/health"
echo "  Verify integration: curl http://localhost:8000/api/paper-trading/accounts/paper_swing_main/overview"
echo ""
echo "If anything looks wrong, run:"
echo "  ./scripts/rebuild-all.sh"

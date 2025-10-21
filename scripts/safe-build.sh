#!/bin/bash

# Safe Build Script for Robo Trader
# Prevents stale Docker build cache issues
# Usage: ./scripts/safe-build.sh [service] [force]
#        ./scripts/safe-build.sh paper-trading force

set -e

SERVICE=${1:-all}
FORCE_REBUILD=${2:-false}

echo "🔨 Building ${SERVICE}..."
echo ""

if [ "$FORCE_REBUILD" = "force" ]; then
    echo "🧹 FORCE MODE: Cleaning cache and rebuilding..."
    DOCKER_BUILDKIT=0 docker-compose build --no-cache $SERVICE
else
    echo "⚠️  Using cache. For clean rebuild, add 'force':"
    echo "   ./scripts/safe-build.sh $SERVICE force"
    echo ""
    DOCKER_BUILDKIT=0 docker-compose build $SERVICE
fi

echo ""
echo "✅ Build complete"
echo ""
echo "🔍 IMPORTANT: Verify the build is not stale:"

case $SERVICE in
    paper-trading)
        echo ""
        echo "Check 1: Routes should NOT have /api/paper-trading prefix:"
        echo "   docker exec robo-trader-paper-trading grep '@app.get' /app/main.py | head -3"
        echo ""
        echo "Check 2: File hash should match local:"
        LOCAL_HASH=$(md5 services/paper_trading/main.py 2>/dev/null | awk '{print $NF}' || md5sum services/paper_trading/main.py | awk '{print $1}')
        CONTAINER_HASH=$(docker exec robo-trader-paper-trading md5sum /app/main.py 2>/dev/null | awk '{print $1}' || echo "N/A")
        if [ "$LOCAL_HASH" = "$CONTAINER_HASH" ]; then
            echo "   ✅ Hashes match: $LOCAL_HASH"
        else
            echo "   ❌ HASHES DON'T MATCH - STALE CACHE!"
            echo "      Local:     $LOCAL_HASH"
            echo "      Container: $CONTAINER_HASH"
            echo "      Fix: ./scripts/safe-build.sh $SERVICE force"
        fi
        ;;
    api-gateway)
        echo ""
        echo "Check: Service URLs should use container names (robo-trader-*):"
        docker exec robo-trader-api-gateway grep "robo-trader-" /app/main.py | head -3 || echo "Not found"
        echo ""
        echo "Should NOT have .orb.local DNS names"
        ;;
    *)
        echo ""
        echo "Check 1: Service is running:"
        docker-compose ps $SERVICE 2>/dev/null || echo "Not running yet"
        echo ""
        echo "Check 2: Container is healthy:"
        echo "   docker exec robo-trader-$SERVICE cat /app/main.py | head -20"
        ;;
esac

echo ""

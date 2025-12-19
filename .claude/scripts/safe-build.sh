#!/bin/bash

# Safe Build Script for Robo Trader
# Prevents stale Docker build cache issues
# Usage: ./scripts/safe-build.sh [service] [force]
#        ./scripts/safe-build.sh web force

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
    web)
        echo ""
        echo "Check 1: Paper trading routes should have /api/paper-trading prefix:"
        echo "   docker exec robo-trader-web grep 'paper-trading' /app/src/web/app.py | head -3"
        echo ""
        echo "Check 2: File hash should match local:"
        LOCAL_HASH=$(md5 src/web/app.py 2>/dev/null | awk '{print $NF}' || md5sum src/web/app.py | awk '{print $1}')
        CONTAINER_HASH=$(docker exec robo-trader-web md5sum /app/src/web/app.py 2>/dev/null | awk '{print $1}' || echo "N/A")
        if [ "$LOCAL_HASH" = "$CONTAINER_HASH" ]; then
            echo "   ✅ Hashes match: $LOCAL_HASH"
        else
            echo "   ❌ HASHES DON'T MATCH - STALE CACHE!"
            echo "      Local:     $LOCAL_HASH"
            echo "      Container: $CONTAINER_HASH"
            echo "      Fix: ./scripts/safe-build.sh $SERVICE force"
        fi
        ;;
    frontend)
        echo ""
        echo "Frontend uses volume mount - cache not applicable"
        echo "Check: Vite dev server should be running:"
        docker exec robo-trader-frontend ps aux | grep vite || echo "Not running yet"
        ;;
    *)
        echo ""
        echo "Check 1: Service is running:"
        docker-compose ps $SERVICE 2>/dev/null || echo "Not running yet"
        echo ""
        echo "Check 2: Container is healthy:"
        if [ "$SERVICE" = "all" ]; then
            echo "   docker-compose ps"
        else
            echo "   docker exec robo-trader-$SERVICE cat /proc/1/comm 2>/dev/null || echo 'Container not accessible'"
        fi
        ;;
esac

echo ""
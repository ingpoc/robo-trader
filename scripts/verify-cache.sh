#!/bin/bash

# Verify Cache Script - Check if Docker images have stale code
# Run after rebuilding to ensure code is fresh
# Usage: ./scripts/verify-cache.sh [service]

SERVICE=${1:-all}

echo "🔍 Cache Verification Script"
echo ""

verify_service() {
    local svc=$1
    local container="robo-trader-$svc"

    echo "Checking $svc..."

    if ! docker ps | grep -q "$container"; then
        echo "  ❌ Container not running: $container"
        return 1
    fi

    # Get file hash
    local local_file=""
    local app_file=""

    case $svc in
        paper-trading)
            local_file="services/paper_trading/main.py"
            app_file="/app/main.py"
            ;;
        api-gateway)
            local_file="services/api_gateway/main.py"
            app_file="/app/main.py"
            ;;
        market-data)
            local_file="services/market_data/main.py"
            app_file="/app/main.py"
            ;;
        *)
            echo "  ⏭️  Unknown service - skipping"
            return 0
            ;;
    esac

    if [ ! -f "$local_file" ]; then
        echo "  ⏭️  Local file not found: $local_file"
        return 0
    fi

    # Calculate hashes
    if command -v md5 &> /dev/null; then
        LOCAL_HASH=$(md5 "$local_file" | awk '{print $NF}')
    else
        LOCAL_HASH=$(md5sum "$local_file" | awk '{print $1}')
    fi

    CONTAINER_HASH=$(docker exec "$container" md5sum "$app_file" 2>/dev/null | awk '{print $1}')

    if [ -z "$CONTAINER_HASH" ]; then
        echo "  ❌ Could not get hash from container"
        return 1
    fi

    if [ "$LOCAL_HASH" = "$CONTAINER_HASH" ]; then
        echo "  ✅ Hashes match: $LOCAL_HASH"
        return 0
    else
        echo "  ❌ STALE CACHE DETECTED!"
        echo "     Local:     $LOCAL_HASH"
        echo "     Container: $CONTAINER_HASH"
        echo ""
        echo "     Fix this with:"
        echo "     ./scripts/safe-build.sh $svc force"
        return 1
    fi
}

case $SERVICE in
    all)
        echo "Verifying all services..."
        echo ""

        FAILED=0
        for svc in paper-trading api-gateway market-data portfolio risk execution analytics recommendation task-scheduler; do
            verify_service "$svc" || FAILED=$((FAILED + 1))
            echo ""
        done

        if [ $FAILED -eq 0 ]; then
            echo "✅ All services have fresh code!"
            exit 0
        else
            echo "❌ $FAILED service(s) have stale cache"
            exit 1
        fi
        ;;
    *)
        verify_service "$SERVICE"
        ;;
esac

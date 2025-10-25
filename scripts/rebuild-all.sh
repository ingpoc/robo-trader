#!/bin/bash

# Aggressive Rebuild Script - Use when everything is broken
# Removes ALL old containers and images, rebuilds from scratch
# Use this if you suspect stale cache issues

set -e

echo "🔥 AGGRESSIVE REBUILD"
echo "   This will REMOVE all robo-trader containers and images"
echo "   and rebuild everything from scratch"
echo ""
read -p "Continue? (type 'yes' to proceed): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cancelled"
    exit 1
fi

echo ""
echo "Step 1/5: Stopping all containers..."
docker-compose down --remove-orphans

echo ""
echo "Step 2/5: Removing all robo-trader images..."
IMAGES=$(docker images | grep robo-trader | awk '{print $3}' | sort -u)
if [ -n "$IMAGES" ]; then
    echo "$IMAGES" | xargs docker rmi -f 2>/dev/null || true
    echo "Removed old images"
else
    echo "No old images found"
fi

echo ""
echo "Step 3/5: Removing dangling layers..."
docker system prune -f

echo ""
echo "Step 4/5: Building everything without cache (this will take time)..."
DOCKER_BUILDKIT=0 docker-compose build --no-cache

echo ""
echo "Step 5/5: Starting all services..."
docker-compose up -d

echo ""
echo "✅ Rebuild complete!"
echo ""
echo "Service status:"
docker-compose ps

echo ""
echo "🔍 Verify builds are fresh:"
echo "   Paper Trading:"
echo "   docker exec robo-trader-paper-trading md5sum /app/main.py"
echo ""
echo "   API Gateway:"
echo "   docker exec robo-trader-api-gateway md5sum /app/main.py"
echo ""
echo "   Compare hashes to your local files"

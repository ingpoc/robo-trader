#!/bin/bash

# Stop All Robo Trader Services using Apple Container

set -e

echo "🛑 Stopping all Robo Trader services..."

# Stop all robo-trader containers
container ps --filter "name=robo-trader-" --format "{{.Names}}" | while read -r container_name; do
    if [ -n "$container_name" ]; then
        echo "Stopping $container_name..."
        container stop "$container_name"
        container rm "$container_name"
    fi
done

# Remove network (optional - will be recreated on next start)
# container network rm robo-trader-network 2>/dev/null || true

echo "✅ All Robo Trader services stopped"

# Show remaining containers
echo ""
echo "📊 Remaining containers:"
container ps --filter "name=robo-trader-"
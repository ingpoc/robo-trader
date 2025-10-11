#!/bin/bash

# Portfolio Service Runner for Apple Container
# Runs the portfolio service in isolated container environment

set -e

echo "Starting Portfolio Service in container..."

# Set container-specific environment
export CONTAINER_MODE=true
export SERVICE_NAME=portfolio-service
export SERVICE_PORT=8001

# Mount points for shared data
export SHARED_DB_PATH=/shared/db
export SHARED_LOGS_PATH=/shared/logs

# Create necessary directories
mkdir -p /app/data /app/logs

# Copy shared config if available
if [ -f /shared/config/config.json ]; then
    cp /shared/config/config.json /app/config/
fi

# Run the portfolio service
cd /app
exec python -c "
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from src.config import Config
from src.services.portfolio_service import PortfolioService
from src.core.event_bus import initialize_event_bus

async def run_portfolio_service():
    print('Initializing Portfolio Service...')

    # Load configuration
    config = Config()

    # Initialize event bus
    event_bus = await initialize_event_bus(config)

    # Create and initialize portfolio service
    portfolio_service = PortfolioService(config, event_bus)
    await portfolio_service.initialize()

    print('Portfolio Service started successfully')
    print(f'Service running on port {os.getenv(\"SERVICE_PORT\", \"8001\")}')

    # Keep service running
    try:
        while True:
            await asyncio.sleep(60)
            print('Portfolio Service heartbeat')
    except KeyboardInterrupt:
        print('Shutting down Portfolio Service...')
        await portfolio_service.close()
        await event_bus.close()

if __name__ == '__main__':
    asyncio.run(run_portfolio_service())
"
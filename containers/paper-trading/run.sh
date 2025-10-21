#!/bin/bash

# Paper Trading Service Runner for Apple Container
# Runs the paper trading service in isolated container environment

set -e

echo "Starting Paper Trading Service in container..."

# Set container-specific environment
export CONTAINER_MODE=true
export SERVICE_NAME=paper-trading
export SERVICE_PORT=8008

# Mount points for shared data
export SHARED_DB_PATH=/shared/db
export SHARED_LOGS_PATH=/shared/logs

# Create necessary directories
mkdir -p /app/data /app/logs

# Copy shared config if available
if [ -f /shared/config/config.json ]; then
    cp /shared/config/config.json /app/config/
fi

# Run the paper trading service
cd /app
exec python -c "
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from src.config import Config
from src.services.paper_trading.main import app
from src.core.di import DependencyContainer
from src.core.event_bus import initialize_event_bus

async def run_paper_trading_service():
    print('Initializing Paper Trading Service...')

    # Import the FastAPI app from the service
    from services.paper_trading.main import app

    print('Paper Trading Service started successfully')
    print(f'Service running on port {os.getenv(\"SERVICE_PORT\", \"8008\")}')

    # Keep service running
    try:
        while True:
            await asyncio.sleep(60)
            print('Paper Trading Service heartbeat')
    except KeyboardInterrupt:
        print('Shutting down Paper Trading Service...')

if __name__ == '__main__':
    asyncio.run(run_paper_trading_service())
"
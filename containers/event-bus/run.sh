#!/bin/bash

# Event Bus Service Runner for Apple Container
# Runs the centralized event routing service

set -e

echo "Starting Event Bus Service in container..."

# Set container-specific environment
export CONTAINER_MODE=true
export SERVICE_NAME=event-bus
export SERVICE_PORT=8000

# Mount points for shared data
export SHARED_DB_PATH=/shared/db
export SHARED_LOGS_PATH=/shared/logs

# Create necessary directories
mkdir -p /app/data /app/logs

# Copy shared config if available
if [ -f /shared/config/config.json ]; then
    cp /shared/config/config.json /app/config/
fi

# Run the event bus service
cd /app
exec python -c "
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from src.config import Config
from src.core.event_bus import EventBus, initialize_event_bus

async def run_event_bus():
    print('Initializing Event Bus Service...')

    # Load configuration
    config = Config()

    # Initialize event bus
    event_bus = await initialize_event_bus(config)

    print('Event Bus Service started successfully')
    print(f'Service running on port {os.getenv(\"SERVICE_PORT\", \"8000\")}')

    # Keep service running and processing events
    try:
        while True:
            # Process any pending events
            pending_events = await event_bus.get_pending_events()
            if pending_events:
                print(f'Processing {len(pending_events)} pending events')

            await asyncio.sleep(30)  # Check every 30 seconds
            print('Event Bus heartbeat')

    except KeyboardInterrupt:
        print('Shutting down Event Bus Service...')
        await event_bus.close()

if __name__ == '__main__':
    asyncio.run(run_event_bus())
"
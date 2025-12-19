#!/bin/bash

# Start backend and frontend servers with error logging
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend.log"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

echo "Starting Robo Trader servers..."
echo "Project root: $PROJECT_ROOT"

# Kill existing processes first
./scripts/kill_servers.sh

# Start backend
echo "Starting backend server..."
cd "$PROJECT_ROOT"
PYTHONUNBUFFERED=1 \
ROBO_TRADER_PROJECT_ROOT="$PROJECT_ROOT" \
ROBO_TRADER_API="http://localhost:8000" \
ROBO_TRADER_DB="$PROJECT_ROOT/state/robo_trader.db" \
LOG_DIR="$PROJECT_ROOT/logs" \
./venv/bin/python -m src.server > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to initialize
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s -m 2 http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start after 60 seconds"
        echo "Last 10 lines of backend log:"
        tail -10 "$BACKEND_LOG"
        exit 1
    fi
    sleep 2
done

# Start frontend
echo "Starting frontend server..."
cd "$PROJECT_ROOT/ui"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to initialize
echo "Waiting for frontend to initialize..."
for i in {1..60}; do
    if curl -s -m 2 http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is healthy!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "⚠️  Frontend may still be starting (this is normal)"
        echo "Last 10 lines of frontend log:"
        tail -10 "$FRONTEND_LOG"
    fi
    sleep 1
done

echo ""
echo "🚀 Servers started successfully!"
echo "Backend PID: $BACKEND_PID (http://localhost:8000)"
echo "Frontend PID: $FRONTEND_PID (http://localhost:3000)"
echo ""
echo "View logs:"
echo "  Backend: tail -f $BACKEND_LOG"
echo "  Frontend: tail -f $FRONTEND_LOG"
echo ""
echo "Stop servers: ./scripts/kill_servers.sh"

# Save PIDs to file for later use
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend_pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend_pid"
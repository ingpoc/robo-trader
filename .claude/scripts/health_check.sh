#!/bin/bash
# System Health Manager for Robo Trader
# Kills old servers, starts fresh, checks health, analyzes logs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="/Users/gurusharan/Documents/remote-claude/robo-trader"
cd "$PROJECT_ROOT"

echo "=== Robo Trader System Health Manager ==="

# Step 1: Kill existing processes
echo ""
echo "Step 1: Killing existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "  Port 8000 cleared" || echo "  Port 8000 already free"
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "  Port 3000 cleared" || echo "  Port 3000 already free"

# Step 2: Start servers
echo ""
echo "Step 2: Starting servers..."
mkdir -p logs

# Start backend
PYTHONUNBUFFERED=1 \
ROBO_TRADER_PROJECT_ROOT="$PROJECT_ROOT" \
ROBO_TRADER_API="http://localhost:8000" \
ROBO_TRADER_DB="$PROJECT_ROOT/state/robo_trader.db" \
LOG_DIR="$PROJECT_ROOT/logs" \
./venv/bin/python -m src.main --command web > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend starting (PID: $BACKEND_PID)"

# Start frontend
cd ui
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "  Frontend starting (PID: $FRONTEND_PID)"

# Step 3: Wait for startup with readiness check
echo ""
echo "Step 3: Waiting for servers to be ready..."

MAX_WAIT=60
ELAPSED=0
BACKEND_READY=false
FRONTEND_READY=false

while [ $ELAPSED -lt $MAX_WAIT ]; do
  # Check backend
  BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 2 http://localhost:8000/api/health 2>/dev/null || echo "000")
  if [ "$BACKEND_STATUS" = "200" ]; then
    BACKEND_READY=true
  fi

  # Check frontend
  FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 2 http://localhost:3000 2>/dev/null || echo "000")
  if [ "$FRONTEND_STATUS" = "200" ]; then
    FRONTEND_READY=true
  fi

  # Show progress
  if [ "$BACKEND_READY" = true ] && [ "$FRONTEND_READY" = true ]; then
    echo "  ✓ Both servers ready (${ELAPSED}s)"
    break
  elif [ "$BACKEND_READY" = true ]; then
    echo -n "  Backend ready, frontend starting... ($((MAX_WAIT - ELAPSED))s remaining) "
  elif [ "$FRONTEND_READY" = true ]; then
    echo -n "  Frontend ready, backend starting... ($((MAX_WAIT - ELAPSED))s remaining) "
  else
    echo -n "."
  fi

  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

echo ""

# Timeout check
if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo -e "${YELLOW}  Warning: Reached ${MAX_WAIT}s timeout${NC}"
fi

# Step 4: Health check (using readiness results)
echo ""
echo "Step 4: Health check..."

# Final status check
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://localhost:8000/api/health 2>/dev/null || echo "000")
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://localhost:3000 2>/dev/null || echo "000")

echo "  Backend: $BACKEND_STATUS"
echo "  Frontend: $FRONTEND_STATUS"

# Step 5: Server status
echo ""
echo "Step 5: Server Status..."
echo ""
echo "✓ Backend server started (PID: $BACKEND_PID)"
echo "✓ Frontend server started (PID: $FRONTEND_PID)"
echo ""
echo "Logs: logs/backend.log, logs/frontend.log"

# Final status
echo ""
echo "=== Status Summary ==="
if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_STATUS" = "200" ]; then
  echo -e "${GREEN}HEALTH: OK${NC}"
  exit 0
elif [ "$BACKEND_STATUS" = "200" ]; then
  echo -e "${YELLOW}HEALTH: PARTIAL (backend ok, frontend down)${NC}"
  exit 1
else
  echo -e "${RED}HEALTH: FAILED${NC}"
  exit 2
fi

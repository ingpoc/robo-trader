#!/bin/bash
# Startup Script for Robo Trader
# Kills processes, clears logs, starts services, checks health, runs API tests
# Exit codes: 0=success, 1=backend failure, 2=log errors, 3=API test failure

set -e

PROJECT_ROOT="/Users/gurusharan/Documents/remote-claude/robo-trader"
cd "$PROJECT_ROOT"

echo "========================================="
echo "🚀 Starting Robo Trader Verification"
echo "========================================="

# Step 1: Kill existing processes
echo "🔪 Killing processes on ports 3000 and 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 2

# Step 2: Clear logs
echo "🧹 Clearing logs..."
mkdir -p logs
> logs/backend.log
> logs/errors.log
> logs/critical.log

# Step 3: Set environment variables
echo "⚙️  Setting environment variables..."
export ROBO_TRADER_PROJECT_ROOT="$PROJECT_ROOT"
export ROBO_TRADER_API="http://localhost:8000"
export ROBO_TRADER_DB="$PROJECT_ROOT/state/robo_trader.db"
export LOG_DIR="$PROJECT_ROOT/logs"

# Step 4: Start backend
echo "🖥️  Starting backend server..."
nohup "$PROJECT_ROOT/venv/bin/python" -m src.main --command web > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Step 5: Wait for backend health (max 30s)
echo "⏳ Waiting for backend health check..."
HEALTHY=false
for i in {1..10}; do
    sleep 3
    HEALTH=$(curl -s -m 2 http://localhost:8000/api/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "")
    if [ "$HEALTH" = "healthy" ]; then
        HEALTHY=true
        echo "✅ Backend is healthy"
        break
    fi
    echo "   Attempt $i/10..."
done

if [ "$HEALTHY" = "false" ]; then
    echo "❌ Backend failed to start within 30 seconds"
    echo "   Check logs/backend.log for details"
    exit 1
fi

# Step 6: Start frontend
echo "🎨 Starting frontend server..."
cd ui
nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

# Wait a bit for frontend to start
sleep 5

# Step 7: Check logs for errors
echo "🔍 Checking logs for errors..."
if [ -f "logs/errors.log" ] && [ -f "logs/critical.log" ]; then
    ERROR_COUNT=$(grep -i -E "(ERROR|CRITICAL|Exception)" logs/errors.log logs/critical.log 2>/dev/null | wc -l)
    ERROR_COUNT=$(echo "$ERROR_COUNT" | tr -d ' ')

    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "❌ Found $ERROR_COUNT errors in logs"
        echo "   Check logs/errors.log and logs/critical.log"
        exit 2
    fi
    echo "✅ No errors found in logs"
else
    echo "⚠️  Log files not found, skipping error check"
fi

# Step 8: Run API tests
echo "🧪 Running API tests..."
if [ -d "tests/api" ]; then
    "$PROJECT_ROOT/venv/bin/pytest" tests/api/ -v --tb=short
    TEST_EXIT=$?

    if [ $TEST_EXIT -ne 0 ]; then
        echo "❌ API tests failed"
        exit 3
    fi
    echo "✅ All API tests passed"
else
    echo "⚠️  No API tests found, skipping"
fi

echo "========================================="
echo "✅ Startup verification completed successfully"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "========================================="

exit 0

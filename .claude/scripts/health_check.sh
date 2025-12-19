#!/bin/bash

# Quick health check for Robo Trader services
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend.log"

echo "🔍 Robo Trader Health Check"
echo "========================="

# Check if processes are running
echo ""
echo "1. Process Status:"
BACKEND_PID=$(cat "$PROJECT_ROOT/.backend_pid" 2>/dev/null || echo "")
FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend_pid" 2>/dev/null || echo "")

if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "✅ Backend process running (PID: $BACKEND_PID)"
else
    echo "❌ Backend process not running"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "✅ Frontend process running (PID: $FRONTEND_PID)"
else
    echo "❌ Frontend process not running"
fi

# Check API health
echo ""
echo "2. API Health:"
if curl -s -m 3 http://localhost:8000/api/health | grep -q "ok"; then
    echo "✅ Backend API responding"
    echo "   $(curl -s http://localhost:8000/api/health | jq -r '.status // "unknown status"')"
else
    echo "❌ Backend API not responding"
fi

if curl -s -m 3 http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend responding"
else
    echo "❌ Frontend not responding"
fi

# Check database
echo ""
echo "3. Database:"
DB_FILE="$PROJECT_ROOT/state/robo_trader.db"
if [ -f "$DB_FILE" ]; then
    echo "✅ Database file exists ($(du -h "$DB_FILE" | cut -f1))"
    TABLES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    echo "   Tables: $TABLES"
else
    echo "❌ Database file not found"
fi

# Check for recent errors
echo ""
echo "4. Recent Errors (last 5 minutes):"
if [ -f "$BACKEND_LOG" ]; then
    ERRORS=$(find "$BACKEND_LOG" -mmin -5 -exec grep -l "ERROR\|Exception\|Traceback" {} \; 2>/dev/null | wc -l)
    if [ $ERRORS -gt 0 ]; then
        echo "⚠️  Found $ERRORS error(s) in backend log"
        echo "   Latest error:"
        tail -50 "$BACKEND_LOG" | grep -E "ERROR|Exception|Traceback" | tail -3 | sed 's/^/     /'
    else
        echo "✅ No recent errors in backend log"
    fi
else
    echo "ℹ️  Backend log not found"
fi

# Summary
echo ""
echo "5. Quick Actions:"
if ! ps -p $BACKEND_PID > /dev/null 2>&1 || ! curl -s -m 3 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   → Run: ./scripts/start_servers.sh"
else
    echo "   → View logs: tail -f logs/backend.log"
    echo "   → Stop servers: ./scripts/kill_servers.sh"
fi
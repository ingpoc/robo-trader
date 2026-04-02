#!/bin/bash

# Start backend and frontend servers with error logging
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend.log"
CODEX_RUNTIME_LOG="$PROJECT_ROOT/logs/codex-runtime.log"
BACKEND_URL="http://localhost:8000/api/health"
FRONTEND_URL="http://localhost:3000"
BACKEND_BASE_URL="http://localhost:8000"
FRONTEND_PROXY_TARGET="${VITE_PROXY_TARGET:-$BACKEND_BASE_URL}"
FRONTEND_WS_TARGET="${VITE_WS_TARGET:-ws://localhost:8000}"
STARTUP_SOAK_SECONDS="${STARTUP_SOAK_SECONDS:-5}"
CODEX_RUNTIME_URL="${CODEX_RUNTIME_URL:-http://127.0.0.1:8765/health}"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

require_process_alive() {
    local pid="$1"
    local label="$2"
    local log_file="$3"

    if ! kill -0 "$pid" 2>/dev/null; then
        echo "❌ ${label} exited during startup validation"
        echo "Last 20 lines of ${label} log:"
        tail -20 "$log_file" || true
        exit 1
    fi
}

spawn_detached() {
    local log_file="$1"
    shift

    nohup "$@" > "$log_file" 2>&1 < /dev/null &
    echo $!
}

wait_for_http_ok() {
    local url="$1"
    local label="$2"
    local pid="$3"
    local log_file="$4"
    local attempts="$5"
    local sleep_seconds="$6"

    for ((i=1; i<=attempts; i++)); do
        require_process_alive "$pid" "$label" "$log_file"

        if curl -fsS -m 2 "$url" > /dev/null 2>&1; then
            echo "✅ ${label} responded successfully"
            return 0
        fi

        if [ "$i" -eq "$attempts" ]; then
            echo "❌ ${label} failed startup validation"
            echo "Last 20 lines of ${label} log:"
            tail -20 "$log_file" || true
            exit 1
        fi

        sleep "$sleep_seconds"
    done
}

soak_process() {
    local url="$1"
    local label="$2"
    local pid="$3"
    local log_file="$4"

    echo "Soaking ${label} for ${STARTUP_SOAK_SECONDS}s..."
    sleep "$STARTUP_SOAK_SECONDS"
    require_process_alive "$pid" "$label" "$log_file"

    if ! curl -fsS -m 2 "$url" > /dev/null 2>&1; then
        echo "❌ ${label} failed soak validation after initial success"
        echo "Last 20 lines of ${label} log:"
        tail -20 "$log_file" || true
        exit 1
    fi

    echo "✅ ${label} stayed healthy through soak window"
}

wait_for_runtime_ready() {
    local url="$1"
    local label="$2"
    local pid="$3"
    local log_file="$4"
    local attempts="$5"
    local sleep_seconds="$6"

    for ((i=1; i<=attempts; i++)); do
        require_process_alive "$pid" "$label" "$log_file"

        local payload
        payload="$(curl -fsS -m 3 "$url" 2>/dev/null || true)"
        if [[ "$payload" == *'"status":"ready"'* ]]; then
            echo "✅ ${label} reported ready"
            return 0
        fi

        if [ "$i" -eq "$attempts" ]; then
            echo "❌ ${label} failed readiness validation"
            echo "Last health payload:"
            echo "${payload:-<no response>}"
            echo "Last 20 lines of ${label} log:"
            tail -20 "$log_file" || true
            exit 1
        fi

        sleep "$sleep_seconds"
    done
}

echo "Starting Robo Trader servers..."
echo "Project root: $PROJECT_ROOT"
echo "Canonical lane contract:"
echo "  Backend: $BACKEND_BASE_URL"
echo "  Frontend: $FRONTEND_URL"
echo "  Codex runtime: ${CODEX_RUNTIME_URL%/health}"
echo "  OAuth callback listener: http://localhost:${ZERODHA_DEV_CALLBACK_PORT:-8010}"

if [ "$FRONTEND_PROXY_TARGET" != "$BACKEND_BASE_URL" ]; then
    echo "❌ Frontend proxy target ($FRONTEND_PROXY_TARGET) does not match canonical backend lane ($BACKEND_BASE_URL)"
    exit 1
fi

# Kill existing processes first
if [ -f "$PROJECT_ROOT/scripts/kill_servers.sh" ]; then
    "$PROJECT_ROOT/scripts/kill_servers.sh"
elif [ -f "$PROJECT_ROOT/.claude/scripts/kill_servers.sh" ]; then
    "$PROJECT_ROOT/.claude/scripts/kill_servers.sh"
fi

# Load .env.local if it exists
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    export $(cat "$PROJECT_ROOT/.env.local" | grep -v '^#' | xargs)
    echo "Loaded .env.local configuration"
fi

# Start backend
echo "Starting backend server..."
cd "$PROJECT_ROOT"
BACKEND_PID=$(spawn_detached "$BACKEND_LOG" env \
PYTHONUNBUFFERED=1 \
ROBO_TRADER_PROJECT_ROOT="$PROJECT_ROOT" \
ROBO_TRADER_API="http://localhost:8000" \
ROBO_TRADER_DB="$PROJECT_ROOT/state/robo_trader.db" \
LOG_DIR="$PROJECT_ROOT/logs" \
./venv/bin/python -m src.main --command web)
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to initialize
echo "Waiting for backend to initialize..."
wait_for_http_ok "$BACKEND_URL" "Backend" "$BACKEND_PID" "$BACKEND_LOG" 30 2
soak_process "$BACKEND_URL" "Backend" "$BACKEND_PID" "$BACKEND_LOG"

# Start Codex runtime sidecar
echo "Starting Codex runtime sidecar..."
cd "$PROJECT_ROOT"
CODEX_RUNTIME_PID=$(spawn_detached "$CODEX_RUNTIME_LOG" ./scripts/start_codex_runtime.sh)
echo "Codex runtime started with PID: $CODEX_RUNTIME_PID"

echo "Waiting for Codex runtime to become ready..."
wait_for_runtime_ready "$CODEX_RUNTIME_URL" "Codex runtime" "$CODEX_RUNTIME_PID" "$CODEX_RUNTIME_LOG" 45 1
soak_process "$CODEX_RUNTIME_URL" "Codex runtime" "$CODEX_RUNTIME_PID" "$CODEX_RUNTIME_LOG"

# Start frontend
echo "Starting frontend server..."
cd "$PROJECT_ROOT/ui"
FRONTEND_PID=$(spawn_detached "$FRONTEND_LOG" env \
VITE_PROXY_TARGET="$FRONTEND_PROXY_TARGET" \
VITE_WS_TARGET="$FRONTEND_WS_TARGET" \
npm run dev)
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to initialize
echo "Waiting for frontend to initialize..."
wait_for_http_ok "$FRONTEND_URL" "Frontend" "$FRONTEND_PID" "$FRONTEND_LOG" 60 1
soak_process "$FRONTEND_URL" "Frontend" "$FRONTEND_PID" "$FRONTEND_LOG"

echo ""
echo "🚀 Servers started successfully!"
echo "Backend PID: $BACKEND_PID ($BACKEND_BASE_URL)"
echo "Codex runtime PID: $CODEX_RUNTIME_PID (${CODEX_RUNTIME_URL%/health})"
echo "Frontend PID: $FRONTEND_PID ($FRONTEND_URL)"
echo "Frontend proxy target: $FRONTEND_PROXY_TARGET"
echo ""
echo "View logs:"
echo "  Backend: tail -f $BACKEND_LOG"
echo "  Codex runtime: tail -f $CODEX_RUNTIME_LOG"
echo "  Frontend: tail -f $FRONTEND_LOG"
echo ""
echo "Stop servers: ./scripts/kill_servers.sh"

# Save PIDs to file for later use
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend_pid"
echo "$CODEX_RUNTIME_PID" > "$PROJECT_ROOT/.codex_runtime_pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend_pid"

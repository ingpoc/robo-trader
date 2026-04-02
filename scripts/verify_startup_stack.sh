#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000
CODEX_RUNTIME_PORT=8765
POST_EXIT_SOAK_SECONDS="${POST_EXIT_SOAK_SECONDS:-2}"
KEEP_STACK_RUNNING="${KEEP_STACK_RUNNING:-0}"

cleanup() {
    if [ "$KEEP_STACK_RUNNING" != "1" ]; then
        "$PROJECT_ROOT/scripts/kill_servers.sh" >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT

require_listener() {
    local port="$1"
    local label="$2"

    if ! lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
        echo "❌ ${label} is not listening on port ${port}"
        return 1
    fi

    echo "✅ ${label} is listening on port ${port}"
}

echo "Verifying full startup stack from: $PROJECT_ROOT"
"$PROJECT_ROOT/scripts/kill_servers.sh" >/dev/null 2>&1 || true
"$PROJECT_ROOT/scripts/start_servers.sh"

echo "Waiting ${POST_EXIT_SOAK_SECONDS}s after launcher exit to catch false-success teardown..."
sleep "$POST_EXIT_SOAK_SECONDS"

require_listener "$BACKEND_PORT" "Backend"
require_listener "$CODEX_RUNTIME_PORT" "Codex runtime"
require_listener "$FRONTEND_PORT" "Frontend"

curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null
echo "✅ Backend /api/health responded"

curl -fsS "http://127.0.0.1:${CODEX_RUNTIME_PORT}/health" >/dev/null
echo "✅ Codex runtime /health responded"

curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null
echo "✅ Frontend / responded"

curl -fsS -X POST "http://127.0.0.1:${BACKEND_PORT}/api/paper-trading/runtime/validate-ai?account_id=paper_swing_main" >/dev/null
echo "✅ Paper-trading runtime validation responded"

echo "🎯 Startup stack survived launcher exit and health verification"

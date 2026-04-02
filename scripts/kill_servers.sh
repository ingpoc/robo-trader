#!/bin/bash

# Kill backend and frontend servers
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load PIDs from file if they exist
if [ -f "$PROJECT_ROOT/.backend_pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/.backend_pid")
    echo "Killing backend server (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || echo "Backend process not found"
    rm -f "$PROJECT_ROOT/.backend_pid"
fi

if [ -f "$PROJECT_ROOT/.frontend_pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend_pid")
    echo "Killing frontend server (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null || echo "Frontend process not found"
    rm -f "$PROJECT_ROOT/.frontend_pid"
fi

if [ -f "$PROJECT_ROOT/.codex_runtime_pid" ]; then
    CODEX_RUNTIME_PID=$(cat "$PROJECT_ROOT/.codex_runtime_pid")
    echo "Killing Codex runtime sidecar (PID: $CODEX_RUNTIME_PID)..."
    kill $CODEX_RUNTIME_PID 2>/dev/null || echo "Codex runtime process not found"
    rm -f "$PROJECT_ROOT/.codex_runtime_pid"
fi

# Kill any processes using ports 8000, 3000, and 8765
echo "Checking for processes on ports 8000, 3000, and 8765..."

# Port 8000 (backend)
BACKEND_PORT_PID=$(lsof -ti:8000 2>/dev/null || echo "")
if [ ! -z "$BACKEND_PORT_PID" ]; then
    echo "Killing process on port 8000 (PID: $BACKEND_PORT_PID)..."
    kill -9 $BACKEND_PORT_PID
fi

# Port 3000 (frontend)
FRONTEND_PORT_PID=$(lsof -ti:3000 2>/dev/null || echo "")
if [ ! -z "$FRONTEND_PORT_PID" ]; then
    echo "Killing process on port 3000 (PID: $FRONTEND_PORT_PID)..."
    kill -9 $FRONTEND_PORT_PID
fi

# Port 8765 (Codex runtime)
CODEX_RUNTIME_PORT_PID=$(lsof -ti:8765 2>/dev/null || echo "")
if [ ! -z "$CODEX_RUNTIME_PORT_PID" ]; then
    echo "Killing process on port 8765 (PID: $CODEX_RUNTIME_PORT_PID)..."
    kill -9 $CODEX_RUNTIME_PORT_PID
fi

echo "✅ All servers stopped"

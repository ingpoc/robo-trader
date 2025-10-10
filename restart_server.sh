#!/bin/bash
# Robo Trader - Start Backend + Frontend

echo "🚀 Starting Robo Trader (Backend + Frontend)..."
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    echo ""
    echo "${YELLOW}🛑 Shutting down Robo Trader...${NC}"

    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi

    pkill -f "python -m src.main --command web" 2>/dev/null
    pkill -f "vite" 2>/dev/null

    echo "✅ Shutdown complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Cleaning up existing processes..."
pkill -f "python -m src.main --command web" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Starting Backend (FastAPI)${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "URL: http://localhost:8000"
echo "WebSocket: ws://localhost:8000/ws"
echo "Mode: PAPER (Safe for testing)"
echo ""

python -m src.main --command web --host 0.0.0.0 --port 8000 2>&1 | tee logs/backend.log &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

echo "Waiting for backend to be ready..."
sleep 3

if ! ps -p $BACKEND_PID > /dev/null; then
    echo "❌ Backend failed to start! Check logs/backend.log"
    exit 1
fi
echo "✅ Backend is ready"

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Starting Frontend (React + Vite)${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "URL: http://localhost:3000"
echo "Design: Swiss Digital Minimalism"
echo ""

if [ ! -d "ui/node_modules" ]; then
    echo "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
    cd ui && npm install && cd ..
    if [ $? -ne 0 ]; then
        echo "❌ npm install failed!"
        cleanup
        exit 1
    fi
fi

cd ui
npm run dev 2>&1 | tee ../logs/frontend.log &
FRONTEND_PID=$!
cd ..
echo "Frontend started (PID: $FRONTEND_PID)"

echo "Waiting for frontend to be ready..."
sleep 3

if ! ps -p $FRONTEND_PID > /dev/null; then
    echo "❌ Frontend failed to start! Check logs/frontend.log"
    echo "Try running 'cd ui && npm install' manually"
    cleanup
    exit 1
fi
echo "✅ Frontend is ready"

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}✨ Robo Trader is Running!${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  📊 Dashboard:    ${GREEN}http://localhost:3000${NC}"
echo "  🔌 API:          ${BLUE}http://localhost:8000${NC}"
echo "  📡 WebSocket:    ${BLUE}ws://localhost:8000/ws${NC}"
echo "  📝 API Docs:     ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "  📁 Logs:"
echo "     Backend:  logs/backend.log"
echo "     Frontend: logs/frontend.log"
echo ""
echo "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

wait $BACKEND_PID $FRONTEND_PID

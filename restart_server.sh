#!/bin/bash
# Robo Trader - Complete Restart (Microservices + Frontend)
# Restarts all 13 Docker containers (backend services) + React frontend

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

echo "🚀 Starting Robo Trader (All Services + Frontend)..."
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    echo ""
    echo "${YELLOW}🛑 Shutting down Robo Trader...${NC}"

    # Kill all background processes created by this script
    echo "  Stopping log streams..."
    if [ ! -z "$BACKEND_LOG_PID" ]; then
        # Kill process group to ensure all children are killed
        kill -9 -$BACKEND_LOG_PID 2>/dev/null || kill -9 $BACKEND_LOG_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_LOG_PID" ]; then
        # Kill process group to ensure all children are killed
        kill -9 -$FRONTEND_LOG_PID 2>/dev/null || kill -9 $FRONTEND_LOG_PID 2>/dev/null || true
    fi

    # Stop frontend npm process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "  Stopping frontend server (PID: $FRONTEND_PID)..."
        kill -15 $FRONTEND_PID 2>/dev/null || true
        sleep 1
        kill -9 $FRONTEND_PID 2>/dev/null || true
    fi

    # Stop all vite processes (be more aggressive)
    echo "  Stopping Vite dev server..."
    pkill -15 -f "vite" 2>/dev/null || true
    pkill -15 -f "npm.*dev" 2>/dev/null || true
    sleep 1
    pkill -9 -f "vite" 2>/dev/null || true
    pkill -9 -f "npm.*dev" 2>/dev/null || true

    # Stop Docker containers
    echo "  Stopping Docker containers..."
    docker-compose down --remove-orphans 2>/dev/null || true
    sleep 2

    # Clean up any remaining processes on port 3000
    echo "  Cleaning up port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    # Kill any lingering docker-compose processes
    pkill -9 -f "docker-compose" 2>/dev/null || true

    # Kill any lingering tail processes (logs)
    pkill -9 -f "tail.*logs" 2>/dev/null || true
    pkill -9 -f "docker-compose logs" 2>/dev/null || true

    echo "✅ Shutdown complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Cleaning up existing processes..."
echo "  Stopping frontend processes..."
pkill -9 -f "vite" 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

echo "  Stopping Docker containers..."
docker-compose down 2>/dev/null || true
sleep 2

echo "✅ Cleanup complete"

echo ""
echo "${YELLOW}🔨 Building containers (preventing stale cache)...${NC}"
echo "   Using DOCKER_BUILDKIT=0 to ensure fresh code is used"
echo ""
DOCKER_BUILDKIT=0 docker-compose build --no-cache 2>&1 | tail -5
if [ $? -ne 0 ]; then
    echo "${RED}❌ Build failed!${NC}"
    exit 1
fi
echo "${GREEN}✅ Build complete${NC}"
echo ""

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Starting Backend Microservices (13 Containers via OrbStack)${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Services starting:"
echo "  ✓ API Gateway (8000)"
echo "  ✓ Portfolio Service (8001)"
echo "  ✓ Risk Management (8002)"
echo "  ✓ Execution Service (8003)"
echo "  ✓ Market Data (8004)"
echo "  ✓ Analytics (8005)"
echo "  ✓ Recommendation (8006)"
echo "  ✓ Task Scheduler (8007)"
echo "  ✓ PostgreSQL (5432)"
echo "  ✓ RabbitMQ (5672, 15672)"
echo "  ✓ Redis (6379)"
echo ""

docker-compose up -d
if [ $? -ne 0 ]; then
    echo "${RED}❌ Docker containers failed to start!${NC}"
    echo "Try running: docker-compose up -d"
    exit 1
fi

echo "Waiting for backend services to be healthy..."
sleep 5

# Check if API Gateway is healthy
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend services are healthy"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Starting Frontend (React + Vite on Port 3000)${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "ui/node_modules" ]; then
    echo "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
    cd ui && npm install && cd ..
    if [ $? -ne 0 ]; then
        echo "${RED}❌ npm install failed!${NC}"
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
sleep 4

if ! ps -p $FRONTEND_PID > /dev/null; then
    echo "${RED}❌ Frontend failed to start! Check logs/frontend.log${NC}"
    echo "Try running: cd ui && npm install"
    cleanup
    exit 1
fi
echo "✅ Frontend is ready"

echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}✨ Robo Trader is Running (All Services)! ✨${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📊 FRONTEND & DASHBOARD"
echo "   Dashboard:     ${GREEN}http://localhost:3000${NC}"
echo "   Design:        Swiss Digital Minimalism"
echo ""
echo "🔌 BACKEND SERVICES"
echo "   API Gateway:   ${BLUE}http://localhost:8000${NC}"
echo "   API Docs:      ${BLUE}http://localhost:8000/docs${NC}"
echo "   WebSocket:     ${BLUE}ws://localhost:8000/ws${NC}"
echo ""
echo "📊 INFRASTRUCTURE"
echo "   RabbitMQ:      ${BLUE}http://localhost:15672${NC} (guest/guest)"
echo ""
echo "📁 LOGS"
echo "   Frontend:      logs/frontend.log"
echo "   Backend:       docker-compose logs -f"
echo ""
echo "🐳 DOCKER STATUS"
echo "   View containers:  docker-compose ps"
echo "   View all logs:    docker-compose logs -f"
echo "   View service:     docker-compose logs -f <service-name>"
echo ""
echo "⚙️ ENVIRONMENT"
echo "   Runtime:       OrbStack (Apple Silicon optimized)"
echo "   Containers:    11 services"
echo "   Memory:        ~2.2 GB (optimized, no monitoring)"
echo ""
echo "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}📊 UNIFIED LOG STREAM (Backend + Frontend)${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to format backend logs
format_backend_logs() {
    docker-compose logs -f 2>&1 | while IFS= read -r line; do
        # Show ALL API Gateway logs (INFO, WARNING, ERROR with request details)
        if echo "$line" | grep -qi "api-gateway"; then
            if echo "$line" | grep -qi "📥\|📤"; then
                # API requests/responses
                echo -e "${GREEN}$line${NC}"
            elif echo "$line" | grep -qi "error\|failed\|critical"; then
                echo -e "${RED}[ERROR]${NC} $line"
            elif echo "$line" | grep -qi "warning"; then
                echo -e "${YELLOW}[WARNING]${NC} $line"
            fi
        # Show ERROR and WARNING logs from other services
        elif echo "$line" | grep -qi "error\|warning\|failed\|critical"; then
            # Skip known non-critical infrastructure logs
            if echo "$line" | grep -qi "grafana.*provisioning\|grafana.*dashboard\|Event bus health check failed\|GET /metrics.*404\|invalid length of startup packet\|no config file specified\|Classic peer discovery\|rebuilding indices\|deprecated features\|management_metrics_collection\|angular plugins\|Plugin validation failed\|attribute.*version.*obsolete"; then
                continue
            fi

            # Color code by level
            if echo "$line" | grep -qi "error\|failed\|critical"; then
                echo -e "${RED}[ERROR]${NC} $line"
            elif echo "$line" | grep -qi "warning"; then
                echo -e "${YELLOW}[WARNING]${NC} $line"
            fi
        fi
    done
}

# Function to format frontend logs
format_frontend_logs() {
    sleep 1
    # Use tail -F to follow frontend logs in real-time
    tail -F logs/frontend.log 2>/dev/null | while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue

        # Color code based on content type
        if echo "$line" | grep -qi "error\|failed"; then
            echo -e "${RED}[FRONTEND ERROR]${NC} $line"
        elif echo "$line" | grep -qi "warning"; then
            echo -e "${YELLOW}[FRONTEND WARNING]${NC} $line"
        elif echo "$line" | grep -qi "vite\|local:\|network:\|ready\|port\|expose\|press h"; then
            # Show VITE startup and status messages
            echo -e "${GREEN}[VITE]${NC} $line"
        else
            # Show all other frontend activity (HMR updates, requests, etc.)
            echo -e "${BLUE}[FRONTEND]${NC} $line"
        fi
    done
}

# Start both log streams in background
format_backend_logs &
BACKEND_LOG_PID=$!

format_frontend_logs &
FRONTEND_LOG_PID=$!

# Keep running and listen for signals
# Use wait with no arguments to wait for ALL background processes
# This ensures trap cleanup is called immediately when signal arrives
wait

FRONTEND_EXIT=$?

if [ $FRONTEND_EXIT -ne 143 ] && [ $FRONTEND_EXIT -ne 0 ]; then
    echo ""
    echo "${YELLOW}Frontend process ended unexpectedly${NC}"
fi

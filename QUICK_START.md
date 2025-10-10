# Robo Trader - Quick Start Guide

## Start the Application

```bash
./restart_server.sh
```

## Access Points

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/ws |

## Stop the Application

Press `Ctrl+C` in the terminal

## View Logs

```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

## Verify Setup

```bash
./verify_setup.sh
```

## First Run

On first run, the script will automatically:
1. Install npm dependencies (2-3 minutes)
2. Start both backend and frontend
3. Display access URLs

## Troubleshooting

### Kill Stuck Processes
```bash
pkill -f "python -m src.main --command web"
pkill -f "vite"
```

### Manual npm Install
```bash
cd ui && npm install && cd ..
```

### Check Logs
```bash
cat logs/backend.log
cat logs/frontend.log
```

## Architecture

```
Frontend (React) → Port 3000
Backend (FastAPI) → Port 8000
WebSocket → ws://localhost:8000/ws
```

## Key Features

- Real-time portfolio updates via WebSocket
- AI-powered trading recommendations
- Multi-agent system monitoring
- Risk management and alerts
- Performance analytics
- PAPER mode for safe testing

## Environment

Mode: PAPER (Safe for testing with real data)
No real trades will be executed

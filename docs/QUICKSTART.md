# Quick Start Guide

Get the Robo Trader UI running in 3 minutes.

## Prerequisites

- Node.js 18 or higher
- Running FastAPI backend at `localhost:8000`

## Installation

```bash
cd ui
npm install
```

## Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Default values work with local backend:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
```

## Start Development Server

```bash
npm run dev
```

Open browser to `http://localhost:3000`

## What You'll See

### Dashboard (/)
- 4 metric cards with rolling animations
- Portfolio performance chart
- Holdings table with virtualization
- AI insights panel
- Quick trade form

### Agents (/agents)
- Status of all 8 AI agents
- Task completion counts
- Uptime tracking

### Trading (/trading)
- Quick trade execution
- AI recommendations queue
- Approve/reject actions

### Settings (/config)
- System configuration
- Risk tolerance
- API limits

### Logs (/logs)
- Recent system activity
- Trade execution logs

## Common Issues

### "Cannot connect to backend"
- Ensure FastAPI server is running on port 8000
- Check `.env` has correct API URL

### "WebSocket disconnected"
- Verify WebSocket endpoint is accessible
- Check CORS settings on backend

### Build errors
```bash
rm -rf node_modules
npm install
```

## Next Steps

1. Explore the dashboard with live data
2. Execute a test trade
3. Review AI recommendations
4. Monitor agent activity
5. Customize configuration

For detailed documentation, see [README.md](./README.md)

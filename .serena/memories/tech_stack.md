# Robo Trader - Tech Stack

## Backend
- **Python 3.10+** with async/await throughout
- **Claude Agent SDK 0.1.6+** (MCP 1.21.0) - NEVER use anthropic directly
- **FastAPI** with uvicorn for web server
- **aiosqlite** for database (SQLite)
- **pydantic 2.12.4** for data validation
- **Celery + Redis** for distributed job queue
- **kiteconnect 4.3.0** for Zerodha broker integration

## Frontend
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **Radix UI** for components
- **Zustand** for state management
- **Socket.IO** for WebSocket
- **Recharts** for charts
- **React Router v6** for routing

## Infrastructure
- **Docker** with docker-compose for containerization
- **EventBus** for internal event-driven communication
- **Dependency Injection Container** for service lifecycle
- **Background scheduler** for scheduled tasks

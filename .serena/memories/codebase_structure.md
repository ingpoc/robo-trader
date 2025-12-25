# Robo Trader - Codebase Structure

## Root Level
```
robo-trader/
├── src/                    # Backend source code
├── ui/                     # Frontend (React + TypeScript)
├── tests/                  # Test files
├── config/                 # Configuration files
├── state/                  # Database files (SQLite)
├── logs/                   # Application logs
├── scripts/                # Utility scripts
├── migrations/             # Database migrations
├── .claude/                # Claude Code shared files (skills, agents, progress)
├── .mcp.json              # MCP server configuration
├── requirements.txt       # Python dependencies
├── pytest.ini            # Pytest configuration
└── docker-compose.yml    # Docker services
```

## Backend (src/)
```
src/
├── main.py               # Entry point
├── config.py             # Configuration loading
├── core/                 # Core infrastructure
│   ├── coordinators/    # Session coordinators (morning, evening)
│   ├── event_bus.py     # Event-driven communication
│   ├── background_scheduler.py
│   └── database_state/  # State management with locking
├── services/            # Business logic services
│   ├── paper_trading_service.py
│   ├── market_data_service.py
│   ├── queue_management.py
│   └── claude_agent_service.py
├── web/                 # Web layer
│   └── routes/          # API endpoints
├── models/              # Pydantic models
├── repositories/        # Data access layer
└── agents/              # Agent SDK agents
```

## Frontend (ui/)
```
ui/
├── src/
│   ├── main.tsx         # Entry point
│   ├── features/        # Feature-based modules
│   │   └── paper-trading/
│   ├── components/      # Reusable components
│   ├── lib/            # Utilities
│   └── hooks/          # Custom React hooks
├── package.json        # Dependencies
└── vite.config.ts      # Vite configuration
```

## Key Files
- `.claude/progress/feature-list.json` - Feature tracking
- `.claude/progress/session-state.json` - Session state recovery
- `.mcp.json` - MCP server configuration
- `CLAUDE.md` - Project memory (root level)
- `src/CLAUDE.md` - Backend layer patterns
- `.claude/CLAUDE.md` - Shared with Agent SDK

# Robo Trader - Code Style & Conventions

## Python Backend

### Naming
- **Services**: snake_case (e.g., `market_data_service`)
- **Classes**: PascalCase (e.g., `TaskCoordinator`)
- **Functions/variables**: snake_case (e.g., `fetch_portfolio_data`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_POSITION_SIZE`)
- **Private**: Single underscore prefix (e.g., `_internal_method`)

### Code Organization
| Layer | Max Size | Pattern |
|-------|----------|--------|
| core/ | 350 lines | DI, events, state |
| services/ | 400 lines | EventHandler + DI |
| web/ | 300 lines | FastAPI routes |
| models/ | 200 lines | Pydantic models |
| Coordinators | 150 lines | Single responsibility |

### Critical Rules
1. **SDK-only**: Use `ClaudeSDKClientManager.get_instance()` - NEVER import anthropic directly
2. **Locked state**: Use `config_state.store_*()` methods - NEVER direct DB connection (causes locks)
3. **Event loop**: Use `asyncio.get_running_loop()` - NEVER `get_event_loop()` (crashes in async context)
4. **Service names**: Use short names from DI registry (`"state_manager"` not `"database_state_manager"`)
5. **Async I/O**: Use `async with aiofiles.open()` for non-blocking file operations
6. **Services**: Extend `EventHandler` class for event-driven via EventBus
7. **Errors**: Use `TradingError(category=ErrorCategory.*)` for structured error handling

### Type Hints
- Always use type hints for function signatures
- Use `|` for union types (Python 3.10+)
- Use `typing` module for complex types

### Docstrings
- Google-style docstrings for public methods
- Keep concise - focus on what and why, not how

## Frontend (TypeScript/React)

### Naming
- **Components**: PascalCase (e.g., `PortfolioDashboard`)
- **Hooks**: camelCase with `use` prefix (e.g., `usePortfolioData`)
- **Functions/variables**: camelCase (e.g., `fetchMarketData`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_POSITION_SIZE`)
- **Types/Interfaces**: PascalCase (e.g., `PortfolioData`)

### Patterns
- Functional components with hooks
- Zustand for state management
- Radix UI for accessible components
- Tailwind utility classes for styling

## Git Conventions
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, etc.
- Feature branches: `claude/description-issueNumber`

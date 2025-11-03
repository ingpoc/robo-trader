# Core Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/core/` directory. Read `src/core/CLAUDE.md` for context.

## Overview

Core coordinators provide fundamental system functionality: Claude SDK session management, query processing, lifecycle management, and portfolio operations. These are foundational coordinators used throughout the system.

## Core Coordinators

### 1. SessionCoordinator

Manages Claude SDK session lifecycle.

**Responsibilities**:
- Authenticate Claude SDK
- Start/stop Claude SDK sessions
- Manage client lifecycle
- Track authentication status

**Key Methods**:
- `validate_authentication()` - Validate Claude SDK authentication
- `start_session()` - Start interactive session
- `end_session()` - End session and cleanup
- `get_claude_status()` - Get current Claude status

**Rules**:
- ✅ Use `ClaudeSDKClientManager` for client creation
- ✅ Handle auth failures gracefully (don't raise exceptions)
- ✅ Broadcast status updates via `BroadcastCoordinator`
- ✅ Max 200 lines

### 2. QueryCoordinator

Processes user queries and manages Claude SDK query/response flow.

**Responsibilities**:
- Process user queries
- Handle streaming responses
- Parse AI thinking, tool usage, and results
- Handle market alerts

**Key Methods**:
- `process_query()` - Process single query
- `process_query_enhanced()` - Process query with structured response
- `handle_market_alert()` - Handle real-time market alerts

**Rules**:
- ✅ Use timeout helpers (`query_only_with_timeout`, `receive_response_with_timeout`)
- ✅ Handle streaming responses properly
- ✅ Parse response blocks correctly
- ✅ Max 200 lines

### 3. LifecycleCoordinator

Manages system lifecycle and emergency operations.

**Responsibilities**:
- Start/stop background scheduler
- Emergency stop/resume operations
- Lifecycle event management

**Key Methods**:
- `start_scheduler()` - Start background scheduler
- `stop_scheduler()` - Stop background scheduler
- `emergency_stop()` - Emergency stop all operations
- `resume_operations()` - Resume after emergency stop

**Rules**:
- ✅ Emit lifecycle events
- ✅ Handle graceful shutdown
- ✅ Max 200 lines

### 4. PortfolioCoordinator

Manages portfolio operations and trading.

**Responsibilities**:
- Portfolio scans and analysis
- Trading operations
- Portfolio state management

**Key Methods**:
- `run_portfolio_scan()` - Scan portfolio for updates
- `analyze_portfolio()` - Analyze portfolio
- `execute_trade()` - Execute trade (delegates to service)

**Rules**:
- ✅ Delegate to portfolio services
- ✅ Emit portfolio events
- ✅ Max 200 lines

## Implementation Patterns

### Session Management

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager

class SessionCoordinator(BaseCoordinator):
    """Manages Claude SDK session lifecycle."""
    
    async def start_session(self) -> None:
        """Start Claude SDK session."""
        if not self.is_authenticated():
            self._log_warning("Skipping session start - authentication unavailable")
            return
        
        client_manager = await ClaudeSDKClientManager.get_instance()
        self.client = await client_manager.get_client("trading", self.options)
```

### Query Processing

```python
from src.core.sdk_helpers import query_only_with_timeout, receive_response_with_timeout

async def process_query(self, query: str) -> List[Any]:
    """Process user query."""
    await query_only_with_timeout(client, query, timeout=30.0)
    
    responses = []
    async for response in receive_response_with_timeout(client, timeout=60.0):
        responses.append(response)
    
    return responses
```

## Event Types

- `session_started` - Claude session started
- `session_ended` - Claude session ended
- `query_processed` - Query processed
- `portfolio_updated` - Portfolio updated
- `lifecycle_changed` - System lifecycle changed

## Dependencies

Core coordinators typically depend on:
- `ClaudeSDKClientManager` - For SDK client creation
- `BroadcastCoordinator` - For UI updates
- `BackgroundScheduler` - For lifecycle management
- `DatabaseStateManager` - For state management
- `EventBus` - For event emission

## Error Handling

- Handle authentication failures gracefully (don't raise)
- Use timeout protection for all SDK calls
- Log errors with full context
- Emit error events for monitoring


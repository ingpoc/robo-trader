# Queue Management Service

Advanced task scheduling and orchestration service for the Robo Trader platform.

## Overview

The Queue Management Service provides a sophisticated task scheduling and orchestration system that manages the execution flow of trading operations across multiple specialized queues. It ensures proper sequencing, dependency management, and monitoring of complex trading workflows.

## Architecture

### Core Components

1. **Queue Orchestration Layer** (`core/queue_orchestration_layer.py`)
   - Manages complex workflow orchestration
   - Handles event-driven triggers between queues
   - Supports sequential and parallel execution modes
   - Implements orchestration rules and dependencies

2. **Task Scheduling Engine** (`core/task_scheduling_engine.py`)
   - Advanced task scheduling with priority management
   - Dependency resolution and conflict handling
   - Resource allocation and concurrency control
   - Intelligent task queuing and execution

3. **Queue Monitoring** (`core/queue_monitoring.py`)
   - Comprehensive monitoring and alerting
   - Performance metrics collection
   - Health checks and system diagnostics
   - Real-time status tracking

### Queue Implementations

1. **Portfolio Queue** (`queues/portfolio_queue.py`)
   - Account balance synchronization
   - Position updates and tracking
   - P&L calculations and risk validation

2. **Data Fetcher Queue** (`queues/data_fetcher_queue.py`)
   - News monitoring and sentiment analysis
   - Earnings data collection and processing
   - Fundamental data updates
   - Options data fetching

3. **AI Analysis Queue** (`queues/ai_analysis_queue.py`)
   - Morning preparation analysis
   - Evening performance reviews
   - Trading recommendations generation
   - Strategy analysis and risk assessment

## Key Features

### Orchestration Modes
- **Sequential**: Strict ordering (Portfolio → Data Fetcher → AI Analysis)
- **Parallel**: Concurrent execution with controlled concurrency
- **Event-Driven**: Trigger-based execution from external events
- **Conditional**: Rule-based execution with prerequisites

### Task Management
- Priority-based scheduling (1-10 scale)
- Dependency management and resolution
- Retry logic with exponential backoff
- Timeout handling and cancellation
- Resource-aware execution

### Monitoring & Alerting
- Real-time health monitoring
- Performance metrics collection
- Configurable alert thresholds
- System resource tracking
- Comprehensive logging and diagnostics

### Integration Points
- Event Bus for inter-service communication
- Database for task persistence and state management
- External APIs for market data and AI services
- WebSocket for real-time status updates

## API Endpoints

### Orchestration
- `POST /api/v1/orchestrate/sequential` - Execute queues sequentially
- `POST /api/v1/orchestrate/parallel` - Execute queues in parallel

### Task Management
- `POST /api/v1/tasks` - Create new tasks
- `GET /api/v1/scheduling/status` - Get scheduling status

### AI Operations
- `POST /api/v1/ai/recommendations` - Generate AI recommendations
- `POST /api/v1/ai/morning-prep` - Trigger morning analysis
- `POST /api/v1/ai/evening-review` - Trigger evening review

### Monitoring
- `GET /api/v1/monitoring/status` - Get monitoring status
- `GET /api/v1/monitoring/alerts` - Get active alerts
- `GET /api/v1/monitoring/metrics` - Get metrics data

## Configuration

The service is configured via `config/service_config.py` with settings for:

- Execution parameters (timeouts, concurrency limits)
- Monitoring thresholds and intervals
- External service integrations
- Queue-specific configurations
- Alert and logging settings

## Usage Examples

### Sequential Workflow Execution
```python
from fastapi import BackgroundTasks
from .core.queue_orchestration_layer import QueueOrchestrationLayer

# Execute all queues in sequence
result = await orchestration_layer.execute_sequential_workflow([
    QueueName.PORTFOLIO_SYNC,
    QueueName.DATA_FETCHER,
    QueueName.AI_ANALYSIS
])
```

### Task Creation with Dependencies
```python
# Create dependent tasks
task1 = await scheduling_engine.schedule_task_with_dependencies(
    queue_name=QueueName.DATA_FETCHER,
    task_type=TaskType.NEWS_MONITORING,
    payload={"symbols": ["AAPL", "GOOGL"]}
)

task2 = await scheduling_engine.schedule_task_with_dependencies(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"trigger": "news_analysis"},
    dependencies=[task1.task_id]
)
```

### Monitoring Integration
```python
# Get comprehensive monitoring status
status = monitoring.get_monitoring_status()

# Check for active alerts
alerts = monitoring.get_alerts(severity="CRITICAL")
```

## Development

### Running the Service
```bash
# Start the queue management service
python -m src.services.queue_management.main

# Or with uvicorn
uvicorn src.services.queue_management.main:app --host 0.0.0.0 --port 8001
```

### Testing
```bash
# Run tests
pytest tests/test_queue_management/

# Run with coverage
pytest --cov=src.services.queue_management tests/
```

### Docker
```bash
# Build container
docker build -t robo-trader/queue-management .

# Run container
docker run -p 8001:8001 robo-trader/queue-management
```

## Dependencies

- FastAPI: Web framework and API
- Pydantic: Data validation
- AsyncIO: Asynchronous operations
- Loguru: Structured logging
- Psutil: System monitoring
- AIOHTTP: HTTP client for external APIs

## Security Considerations

- API authentication (when enabled)
- Rate limiting for API endpoints
- Input validation and sanitization
- Secure configuration management
- Audit logging for all operations

## Performance Characteristics

- Concurrent task execution with configurable limits
- Event-driven architecture for low latency
- Efficient resource utilization
- Scalable monitoring and metrics collection
- Optimized database queries and caching

## Future Enhancements

- Distributed execution across multiple nodes
- Advanced AI-driven scheduling optimization
- Real-time dashboard integration
- Enhanced alerting with notification channels
- Historical performance analytics
- Auto-scaling based on load patterns
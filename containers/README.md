# macOS Native Containerization for Robo Trader

This directory contains macOS native container configurations for distributed deployment of Robo Trader services using OrbStack.

## Architecture Overview

Each service runs in its own macOS native container with:
- Isolated processes and resources
- Inter-service communication via event bus
- Shared database access
- Independent scaling and fault isolation

## Services

### Core Services
- **portfolio-service**: Portfolio management and P&L calculations
- **risk-service**: Risk management and position sizing
- **execution-service**: Order execution and broker integration
- **analytics-service**: Technical analysis and screening
- **learning-service**: Pattern recognition and strategy optimization
- **event-bus**: Centralized event routing and persistence
- **safety-layer**: Compliance and safety monitoring

### Infrastructure Services
- **database**: SQLite database with shared volume mounts
- **redis-cache**: Optional caching layer (Phase 5)

## Prerequisites

1. **OrbStack** installed: `brew install orbstack`
2. **Python 3.9+** in containers
3. **Shared volumes** for database and logs

## Quick Start

```bash
# Start all services
./containers/start-all.sh

# Check service status
./containers/status.sh

# View logs
./containers/logs.sh portfolio-service

# Stop all services
./containers/stop-all.sh
```

## Service Communication

Services communicate through:
- **Event Bus**: Async event-driven messaging
- **gRPC**: Direct service-to-service calls (future)
- **Shared Database**: For state persistence
- **Health Checks**: Service discovery and monitoring

## Development

```bash
# Run single service in development mode
./containers/dev-run.sh portfolio-service

# Build service image
./containers/build.sh portfolio-service

# Test inter-service communication
./containers/test-integration.sh
```

## Configuration

Each service has its own configuration in `containers/<service>/`:
- `Containerfile`: Container build instructions
- `config.json`: Service-specific configuration
- `run.sh`: Service startup script

## Monitoring

- Health checks via `/health` endpoints
- Logs aggregated in shared volume
- Metrics collection (future Phase 8)
- Service discovery and load balancing

## Security

- Container isolation prevents service interference
- Network segmentation between services
- Audit logging through safety layer
- API authentication and authorization

## Scaling

Each service can be scaled independently:
```bash
# Scale analytics service to 3 instances
orbctl scale analytics-service=3

# Auto-scaling based on load (future)
./containers/autoscale.sh
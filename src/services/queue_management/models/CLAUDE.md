# Queue Management Models Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/models/` directory. Read `src/services/queue_management/CLAUDE.md` for context.

## Purpose

The `models/` directory contains data models for the Queue Management Service. It defines data structures for queue status, execution context, alerts, and monitoring metrics.

## Architecture Pattern

### Dataclass Model Pattern

Models use Python dataclasses and enums to define data structures. Models are immutable and type-safe.

### Directory Structure

```
models/
└── queue_models.py    # Queue management data models
```

## Rules

### ✅ DO

- ✅ Use dataclasses for models
- ✅ Use enums for status values
- ✅ Provide default values
- ✅ Document model fields
- ✅ Use type hints
- ✅ Implement validation methods

### ❌ DON'T

- ❌ Use mutable default values
- ❌ Skip type hints
- ❌ Mix business logic with models
- ❌ Skip validation
- ❌ Create circular dependencies

## Model Pattern

```python
from dataclasses import dataclass
from src.services.queue_management.models.queue_models import QueueStatus

# Create queue status
status = QueueStatus(
    queue_name="AI_ANALYSIS",
    is_running=True,
    current_task_id="task_123",
    pending_tasks_count=5,
    completed_tasks_count=10,
    failed_tasks_count=1,
    average_execution_time=150.5,
    last_execution_time=datetime.now(),
    registered_handlers=["RECOMMENDATION_GENERATION"]
)
```

## Model Structure

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

class ExecutionStatus(str, Enum):
    """Status of task/queue execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class QueueStatus:
    """Status information for a queue."""
    queue_name: str
    is_running: bool
    current_task_id: Optional[str]
    pending_tasks_count: int
    completed_tasks_count: int
    failed_tasks_count: int
    average_execution_time: float
    last_execution_time: Optional[datetime]
    registered_handlers: List[str]
    queue_specific_status: Dict[str, Any] = field(default_factory=dict)
```

## Enum Models

```python
from enum import Enum

class AlertSeverity(str, Enum):
    """Severity levels for monitoring alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

## Model Validation

```python
@dataclass
class QueueStatus:
    pending_tasks_count: int
    completed_tasks_count: int
    
    def __post_init__(self):
        """Validate model data."""
        if self.pending_tasks_count < 0:
            raise ValueError("pending_tasks_count must be >= 0")
        if self.completed_tasks_count < 0:
            raise ValueError("completed_tasks_count must be >= 0")
```

## Dependencies

Model components depend on:
- `dataclasses` - For model classes
- `enum` - For enum models
- `typing` - For type hints
- `datetime` - For timestamp fields

## Testing

Test models:

```python
import pytest
from src.services.queue_management.models.queue_models import QueueStatus, ExecutionStatus

def test_queue_status_model():
    """Test queue status model."""
    status = QueueStatus(
        queue_name="AI_ANALYSIS",
        is_running=True,
        current_task_id="task_123",
        pending_tasks_count=5,
        completed_tasks_count=10,
        failed_tasks_count=1,
        average_execution_time=150.5,
        last_execution_time=datetime.now(),
        registered_handlers=[]
    )
    
    assert status.queue_name == "AI_ANALYSIS"
    assert status.is_running is True
    assert status.pending_tasks_count == 5
```

## Maintenance

When adding new models:

1. Add dataclass model
2. Use type hints
3. Provide default values
4. Add validation if needed
5. Document model fields
6. Update this CLAUDE.md file


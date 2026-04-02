from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.coordinators.portfolio.portfolio_analysis_coordinator import PortfolioAnalysisCoordinator
from src.models.scheduler import QueueName, TaskType


@pytest.mark.asyncio
async def test_queue_analysis_tasks_uses_stock_analysis_task_type():
    task_service = SimpleNamespace(
        create_task=AsyncMock(return_value=SimpleNamespace(task_id="task-1"))
    )
    coordinator = PortfolioAnalysisCoordinator(
        config=SimpleNamespace(),
        state_manager=SimpleNamespace(),
        config_state=SimpleNamespace(),
        task_service=task_service,
    )

    stocks = [
        {"symbol": "TCS", "priority": 5, "reason": "stale_analysis"},
        {"symbol": "INFY", "priority": 10, "reason": "never_analyzed"},
    ]

    await coordinator._queue_analysis_tasks(stocks)

    task_service.create_task.assert_awaited_once()
    _, kwargs = task_service.create_task.await_args
    assert kwargs["queue_name"] == QueueName.AI_ANALYSIS
    assert kwargs["task_type"] == TaskType.STOCK_ANALYSIS
    assert kwargs["payload"] == {"symbols": ["INFY", "TCS"]}


@pytest.mark.asyncio
async def test_initialize_does_not_start_background_monitoring():
    coordinator = PortfolioAnalysisCoordinator(
        config=SimpleNamespace(),
        state_manager=SimpleNamespace(),
        config_state=SimpleNamespace(),
        task_service=SimpleNamespace(),
    )

    await coordinator.initialize()

    assert coordinator._initialization_complete is True
    assert coordinator._monitoring_task is None

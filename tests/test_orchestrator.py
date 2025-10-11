"""
Tests for Robo Trader Orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Config
from src.core.orchestrator import RoboTraderOrchestrator
from src.core.database_state import DatabaseStateManager


@pytest.fixture
def config():
    """Test configuration."""
    return Config(environment="dry-run")


@pytest.fixture
def state_manager(config):
    """Test state manager."""
    return DatabaseStateManager(config)


@pytest.mark.asyncio
async def test_orchestrator_initialization(config, state_manager):
    """Test orchestrator initialization."""
    orchestrator = RoboTraderOrchestrator(config)

    with patch('src.core.orchestrator.create_broker_mcp_server', new_callable=AsyncMock) as mock_broker, \
         patch('src.core.orchestrator.create_agents_mcp_server', new_callable=AsyncMock) as mock_agents, \
         patch('src.core.orchestrator.create_safety_hooks', return_value={}) as mock_hooks:

        broker_server = MagicMock()
        agent_server = MagicMock()
        mock_broker.return_value = broker_server
        mock_agents.return_value = agent_server

        await orchestrator.initialize()

        assert orchestrator.options is not None
        assert orchestrator.state_manager is not None
        mock_broker.assert_awaited_once()
        mock_agents.assert_awaited_once()
        mock_hooks.assert_called_once()


@pytest.mark.asyncio
async def test_portfolio_scan(config):
    """Test portfolio scan workflow."""
    orchestrator = RoboTraderOrchestrator(config)

    response = MagicMock()
    response.content = [MagicMock(text="Portfolio scan completed")]

    orchestrator.client = AsyncMock()
    orchestrator.client.query = AsyncMock()

    async def response_stream():
        yield response

    orchestrator.client.receive_response = MagicMock(return_value=response_stream())

    await orchestrator.run_portfolio_scan()

    orchestrator.client.query.assert_called_once()
    assert "portfolio scan" in orchestrator.client.query.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_market_screening(config):
    """Test market screening workflow."""
    orchestrator = RoboTraderOrchestrator(config)

    response = MagicMock()
    response.content = [MagicMock(text="Market screening completed")]

    orchestrator.client = AsyncMock()
    orchestrator.client.query = AsyncMock()

    async def response_stream():
        yield response

    orchestrator.client.receive_response = MagicMock(return_value=response_stream())

    await orchestrator.run_market_screening()

    orchestrator.client.query.assert_called_once()
    assert "market screening" in orchestrator.client.query.call_args[0][0].lower()
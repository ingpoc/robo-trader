from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.coordinators.paper_trading.morning_research_coordinator import MorningResearchCoordinator


@pytest.mark.asyncio
async def test_morning_research_uses_claude_batch_research():
    event_bus = AsyncMock()
    service = AsyncMock()
    service.collect_batch_symbol_research.return_value = {
        "INFY": {
            "research_timestamp": "2026-03-24T06:00:00+00:00",
            "summary": "Infosys remains constructive.",
            "financial_data": "Margins held steady.",
            "news": "A fresh contract win was disclosed.",
            "filings": "Exchange filing confirmed the client announcement.",
            "market_context": "Relative strength remains positive.",
            "evidence": ["Contract win disclosed."],
            "risks": ["Execution risk remains."],
            "source_summary": [{"source_type": "claude_web_news"}],
            "errors": [],
        }
    }

    container = MagicMock()
    container.get = AsyncMock(return_value=service)

    coordinator = MorningResearchCoordinator(config=MagicMock(), event_bus=event_bus, container=container)
    await coordinator.initialize()
    result = await coordinator.research_stocks([{"symbol": "INFY", "name": "Infosys", "price": 1500}])

    assert result[0]["symbol"] == "INFY"
    assert result[0]["research"]["fundamentals"] == "Margins held steady."
    assert result[0]["research"]["news"] == "A fresh contract win was disclosed."
    service.collect_batch_symbol_research.assert_awaited_once()

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.prompt_optimization_service import PromptOptimizationService


@pytest.mark.asyncio
async def test_prompt_optimization_fetches_claude_research_payload():
    market_research_service = AsyncMock()
    market_research_service.collect_batch_symbol_research.return_value = {
        "INFY": {
            "summary": "Infosys remains constructive.",
            "news": "A large deal win was announced.",
            "financial_data": "Margins held steady and cash flow remained strong.",
            "filings": "Exchange filing confirmed the announcement.",
            "market_context": "Relative strength remains positive.",
            "sources": ["https://example.com/news"],
            "errors": [],
        }
    }
    service = PromptOptimizationService(
        config={},
        event_bus=AsyncMock(),
        container=MagicMock(),
        market_research_service=market_research_service,
    )

    payload = await service._fetch_data_with_prompt(
        "Focus on fresh company news and supporting evidence.",
        "news",
        ["INFY"],
    )

    assert "INFY: A large deal win was announced." in payload
    assert "Sources: https://example.com/news" in payload
    market_research_service.collect_batch_symbol_research.assert_awaited_once()

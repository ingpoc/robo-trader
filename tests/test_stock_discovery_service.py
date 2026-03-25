from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.paper_trading.stock_discovery import StockDiscoveryService


@pytest.mark.asyncio
async def test_analyze_candidates_uses_claude_web_research_not_perplexity():
    state_manager = AsyncMock()
    event_bus = AsyncMock()
    market_research_service = AsyncMock()
    market_research_service.collect_symbol_research.return_value = {
        "research_timestamp": "2026-03-24T06:00:00+00:00",
        "research_summary": "Fresh web research summary.",
        "financial_data": "Margins stable.",
        "filings": "Exchange filing confirms a contract win.",
        "market_context": "Relative strength remains positive.",
        "sources": ["https://example.com/news"],
        "source_summary": [],
        "evidence_citations": [],
        "evidence": ["Contract win disclosed."],
        "risks": ["Execution risk remains."],
        "errors": [],
    }
    feature_entry = SimpleNamespace(
        action="BUY",
        feature_confidence=0.76,
        score=0.81,
        id="ledger-1",
        to_flat_features=lambda: {"fin_revenue_growth_yoy_pct": 18.0},
    )
    feature_extractor = AsyncMock()
    feature_extractor.extract_features.return_value = feature_entry
    deterministic_scorer = SimpleNamespace(score=lambda entry: entry)

    service = StockDiscoveryService(
        state_manager=state_manager,
        market_research_service=market_research_service,
        event_bus=event_bus,
        config={},
        feature_extractor=feature_extractor,
        deterministic_scorer=deterministic_scorer,
    )

    result = await service._analyze_candidates(
        [{"symbol": "TCS", "name": "TCS", "sector": "Technology"}],
        {},
    )

    assert result[0]["external_research"]["research_summary"] == "Fresh web research summary."
    assert result[0]["claude_analysis"]["recommendation"] == "BUY"
    market_research_service.collect_symbol_research.assert_awaited_once_with("TCS", company_name="TCS")
    feature_extractor.extract_features.assert_awaited_once_with(
        "TCS",
        {
            "news": "Fresh web research summary.",
            "financials": "Margins stable.",
            "filings": "Exchange filing confirms a contract win.",
            "market_data": "Relative strength remains positive.",
        },
    )

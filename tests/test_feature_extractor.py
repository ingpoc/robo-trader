from unittest.mock import AsyncMock

import pytest

from src.services.recommendation_engine.feature_extractor import (
    FEATURE_EXTRACTION_SCHEMA,
    FeatureExtractor,
)


@pytest.mark.asyncio
async def test_feature_extractor_uses_single_structured_runtime_call():
    runtime_client = AsyncMock()
    runtime_client.run_structured.return_value = {
        "output": {
            "management": {"guidance_raised": True},
            "financial": {"revenue_growth_yoy_pct": 18.5},
            "catalyst": {"order_book_win": True},
            "market": {"base_breakout_setup": True},
            "sources": ["codex_research_news", "financial_statements"],
        }
    }
    extractor = FeatureExtractor(runtime_client=runtime_client)

    entry = await extractor.extract_features(
        "INFY",
        {
            "news": "Large deal win announced.",
            "financials": "Revenue grew 18.5% YoY.",
            "filings": "Exchange filing confirms order.",
            "market_data": "Price breaking out above base.",
        },
    )

    runtime_client.run_structured.assert_awaited_once()
    call = runtime_client.run_structured.await_args.kwargs
    assert call["output_schema"] == FEATURE_EXTRACTION_SCHEMA
    assert entry.management.guidance_raised is True
    assert entry.financial.revenue_growth_yoy_pct == 18.5
    assert entry.catalyst.order_book_win is True
    assert entry.market.base_breakout_setup is True
    assert entry.sources == ["codex_research_news", "financial_statements"]

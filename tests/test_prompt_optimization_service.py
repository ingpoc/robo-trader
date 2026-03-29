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


@pytest.mark.asyncio
async def test_prompt_optimization_uses_strict_quality_analysis_schema():
    runtime_client = AsyncMock()
    runtime_client.run_structured.return_value = {
        "output": {
            "quality_score": 8.2,
            "missing_elements": [
                {
                    "element": "insider_activity",
                    "description": "Need insider activity context",
                    "importance": "high",
                }
            ],
            "redundant_elements": ["company_history"],
            "feedback": "Useful, but missing insider activity.",
            "strengths": ["Fresh catalyst coverage"],
            "improvements_needed": ["Add insider activity"],
        }
    }
    service = PromptOptimizationService(
        config={},
        event_bus=AsyncMock(),
        container=MagicMock(),
        market_research_service=AsyncMock(),
        runtime_client=runtime_client,
    )

    result = await service._analyze_data_quality_with_claude(
        "news",
        "Fresh deal win coverage.",
        "Focus on fresh catalysts.",
        1,
    )

    call = runtime_client.run_structured.await_args.kwargs
    schema = call["output_schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "quality_score",
        "missing_elements",
        "redundant_elements",
        "feedback",
        "strengths",
        "improvements_needed",
    ]
    assert schema["properties"]["missing_elements"]["items"]["additionalProperties"] is False
    assert result["quality_score"] == 8.2
    assert result["missing_elements"][0]["element"] == "insider_activity"

from unittest.mock import AsyncMock

import pytest

from src.services.claude_agent.claude_market_research_service import ClaudeMarketResearchService


@pytest.mark.asyncio
async def test_collect_symbol_research_parses_sections_and_citations(monkeypatch):
    service = ClaudeMarketResearchService()
    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_with_timeout(client, prompt, timeout):
        return (
            "SUMMARY: Infosys has fresh company and sector signals.\n"
            "NEWS: Infosys announced a new strategic partnership this week.\n"
            "FINANCIALS: Latest quarter showed stable margins and cash generation.\n"
            "FILINGS: Recent exchange disclosure confirmed a board-approved initiative.\n"
            "MARKET: Relative strength versus NIFTY IT remains constructive.\n"
            "FACT 1: Partnership update was disclosed this week.\n"
            "URL 1: https://example.com/news\n"
            "FACT 2: Quarterly margins remained stable.\n"
            "URL 2: https://example.com/financials\n"
            "RISK 1: Deal ramp could take longer than expected.\n"
        )

    monkeypatch.setattr(
        "src.services.claude_agent.claude_market_research_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.claude_market_research_service.query_with_timeout",
        _query_with_timeout,
    )

    result = await service.collect_symbol_research("INFY", company_name="Infosys")

    assert result["summary"] == "Infosys has fresh company and sector signals."
    assert result["news"] == "Infosys announced a new strategic partnership this week."
    assert result["financial_data"] == "Latest quarter showed stable margins and cash generation."
    assert result["filings"] == "Recent exchange disclosure confirmed a board-approved initiative."
    assert result["market_context"] == "Relative strength versus NIFTY IT remains constructive."
    assert result["evidence"] == [
        "Partnership update was disclosed this week.",
        "Quarterly margins remained stable.",
    ]
    assert result["risks"] == ["Deal ramp could take longer than expected."]
    assert result["evidence_citations"][0]["reference"] == "https://example.com/news"
    assert any(item["source_type"] == "claude_web_fundamentals" for item in result["source_summary"])
    options = manager.get_client.await_args.args[1]
    assert "Task" in options.allowed_tools
    assert "news-researcher" in options.agents
    manager.cleanup_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_symbol_research_returns_error_when_usage_is_exhausted(monkeypatch):
    service = ClaudeMarketResearchService()
    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_with_timeout(client, prompt, timeout):
        return "You're out of extra usage · resets 6:30pm (Asia/Calcutta)"

    monkeypatch.setattr(
        "src.services.claude_agent.claude_market_research_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.claude_market_research_service.query_with_timeout",
        _query_with_timeout,
    )

    result = await service.collect_symbol_research("TCS", company_name="TCS")

    assert result["evidence"] == []
    assert result["errors"] == ["You're out of extra usage · resets 6:30pm (Asia/Calcutta)"]
    manager.cleanup_client.assert_awaited_once()


def test_extract_usage_limited_message_handles_spending_cap():
    message = ClaudeMarketResearchService._extract_usage_limited_message(
        "Spending cap reached resets 11:30pm"
    )

    assert message == "Spending cap reached resets 11:30pm"

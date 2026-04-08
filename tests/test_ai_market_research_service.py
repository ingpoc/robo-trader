from unittest.mock import AsyncMock

import pytest

from src.services.ai_market_research_service import AIMarketResearchService
from src.services.codex_runtime_client import CodexRuntimeError


@pytest.mark.asyncio
async def test_collect_symbol_research_normalizes_sidecar_payload():
    runtime_client = AsyncMock()
    runtime_client.collect_batch_research.return_value = {
        "results": {
            "INFY": {
                "symbol": "INFY",
                "research_timestamp": "2026-03-25T17:00:00Z",
                "summary": "Fresh company research.",
                "research_summary": "Fresh company research.",
                "news": "Deal win announced.",
                "financial_data": "Margins stable.",
                "filings": "Exchange filing confirms update.",
                "market_context": "Relative strength constructive.",
                "sources": ["https://example.com/news"],
                "source_summary": [],
                "evidence_citations": [],
                "evidence": ["Deal win announced."],
                "risks": ["Execution risk."],
                "errors": [],
                "external_evidence_status": "fresh",
            }
        },
        "provider_metadata": {"provider": "codex"},
    }
    service = AIMarketResearchService(runtime_client, timeout_seconds=45.0)

    result = await service.collect_symbol_research("INFY", company_name="Infosys")

    assert result["summary"] == "Fresh company research."
    assert result["provider_metadata"]["provider"] == "codex"
    payload = runtime_client.collect_batch_research.await_args.args[0]
    assert payload["timeout_seconds"] == 35.0
    assert payload["reasoning"] == "minimal"
    assert payload["symbols"] == ["INFY"]
    assert "freshest swing-trading evidence" in payload["research_brief"]
    assert "Infosys (INFY)" in payload["research_brief"]
    assert result["external_evidence_status"] == "fresh"


@pytest.mark.asyncio
async def test_collect_symbol_research_adds_source_tiers_and_partial_status():
    runtime_client = AsyncMock()
    runtime_client.collect_batch_research.return_value = {
        "results": {
            "TCS": {
                "symbol": "TCS",
                "research_timestamp": "2026-03-25T17:00:00Z",
                "summary": "Partial evidence returned.",
                "research_summary": "Partial evidence returned.",
                "news": "Press coverage notes a contract update.",
                "financial_data": "",
                "filings": "Exchange disclosure references management commentary.",
                "market_context": "",
                "sources": ["https://example.com/news", "https://example.com/filing"],
                "source_summary": [
                    {"source_type": "company_filing", "label": "BSE disclosure", "timestamp": "2026-03-25T16:00:00Z", "freshness": "fresh", "detail": "Management update"},
                    {"source_type": "reputable_financial_news", "label": "Financial daily", "timestamp": "2026-03-25T15:00:00Z", "freshness": "fresh", "detail": "Contract coverage"},
                ],
                "evidence_citations": [
                    {"source_type": "company_filing", "label": "BSE disclosure", "reference": "https://example.com/filing", "freshness": "fresh", "timestamp": "2026-03-25T16:00:00Z"},
                    {"source_type": "reputable_financial_news", "label": "Financial daily", "reference": "https://example.com/news", "freshness": "fresh", "timestamp": "2026-03-25T15:00:00Z"},
                ],
                "evidence": ["Management update.", "Contract coverage."],
                "risks": ["Guidance still needs confirmation."],
                "errors": ["optional_enrichment: timeout"],
            }
        },
        "provider_metadata": {"provider": "codex"},
    }
    service = AIMarketResearchService(runtime_client, timeout_seconds=35.0)

    result = await service.collect_symbol_research("TCS", company_name="TCS")

    assert result["external_evidence_status"] == "partial"
    assert result["source_summary"][0]["tier"] == "primary"
    assert result["source_summary"][1]["tier"] == "secondary"
    assert result["evidence_citations"][0]["tier"] == "primary"


@pytest.mark.asyncio
async def test_collect_symbol_research_records_usage_limit(monkeypatch):
    runtime_client = AsyncMock()
    runtime_client.collect_batch_research.side_effect = CodexRuntimeError(
        "Usage cap reached.",
        usage_limited=True,
    )
    service = AIMarketResearchService(runtime_client)
    recorded = {}

    monkeypatch.setattr(
        "src.services.ai_market_research_service.record_claude_runtime_limit",
        lambda message: recorded.setdefault("message", message),
    )

    result = await service.collect_symbol_research("TCS", company_name="TCS")

    assert "Usage cap reached." in result["errors"][0]
    assert recorded["message"] == "Usage cap reached."


@pytest.mark.asyncio
async def test_discovery_scout_uses_manual_timeout_budget():
    runtime_client = AsyncMock()
    runtime_client.discover_market_opportunities.return_value = {
        "market_state_summary": "Breadth is improving.",
        "favored_sectors": ["Capital Goods"],
        "caution_sectors": [],
        "key_insights": [],
        "candidates": [],
        "provider_metadata": {"provider": "codex"},
    }
    service = AIMarketResearchService(runtime_client, timeout_seconds=45.0)

    result = await service.discover_market_opportunities(account_id="paper_main", limit=5)

    assert result["provider_metadata"]["provider"] == "codex"
    payload = runtime_client.discover_market_opportunities.await_args.args[0]
    assert payload["timeout_seconds"] == 45.0
    assert payload["limit"] == 5

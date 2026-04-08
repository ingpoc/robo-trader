from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.paper_trading.stock_discovery import StockDiscoveryService


def _build_service(*, learning_service=None, account_manager=None):
    state_manager = SimpleNamespace(
        paper_trading=SimpleNamespace(
            get_discovery_watchlist=AsyncMock(return_value=[]),
            get_discovery_watchlist_by_symbol=AsyncMock(return_value=None),
            add_to_discovery_watchlist=AsyncMock(return_value=True),
            update_discovery_watchlist=AsyncMock(return_value=True),
            delete_discovery_watchlist_entry=AsyncMock(return_value=True),
            create_discovery_session=AsyncMock(return_value="session-1"),
            update_discovery_session=AsyncMock(return_value=True),
        )
    )
    event_bus = AsyncMock()
    market_research_service = AsyncMock()
    market_research_service.discover_market_opportunities.return_value = {
        "market_state_summary": "",
        "favored_sectors": [],
        "caution_sectors": [],
        "key_insights": [],
        "candidates": [],
        "provider_metadata": {},
        "error": "",
    }
    feature_extractor = AsyncMock()
    deterministic_scorer = SimpleNamespace(score=lambda entry: entry)

    service = StockDiscoveryService(
        state_manager=state_manager,
        market_research_service=market_research_service,
        event_bus=event_bus,
        config={},
        feature_extractor=feature_extractor,
        deterministic_scorer=deterministic_scorer,
        learning_service=learning_service,
        account_manager=account_manager,
    )
    return service, state_manager, market_research_service, feature_extractor


@pytest.mark.asyncio
async def test_screen_market_skips_recent_symbols_and_prioritizes_dark_horses():
    recent_research_timestamp = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(top_lessons=["Technology breakouts were crowded and late."])
    learning_service.get_discovery_memory.return_value = {
        "recent_research": [
            {
                "symbol": "TCS",
                "sector": "Technology",
                "generated_at": recent_research_timestamp,
                "actionability": "watch_only",
                "analysis_mode": "stale_evidence",
                "risks": ["Fresh evidence was missing."],
            }
        ],
        "recent_evaluations": [
            {"symbol": "TCS", "outcome": "loss"},
            {"symbol": "SUNPHARMA", "outcome": "win"},
        ],
    }
    account_manager = AsyncMock()
    account_manager.get_open_positions.return_value = [SimpleNamespace(symbol="HDFCBANK")]

    service, _, _, _ = _build_service(
        learning_service=learning_service,
        account_manager=account_manager,
    )

    market_stocks = [
        {"symbol": "TCS", "name": "TCS", "sector": "Technology", "cap": "large"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking", "cap": "large"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "Pharma", "cap": "large"},
        {"symbol": "LAURUSLABS", "name": "Laurus Labs", "sector": "Pharma", "cap": "mid"},
    ]
    memory_context = await service._build_discovery_memory("paper_main", market_stocks)

    shortlisted, market_conditions, key_insights = await service._screen_market({}, market_stocks, memory_context)

    assert [item["symbol"] for item in shortlisted] == ["LAURUSLABS", "SUNPHARMA"]
    assert market_conditions["favored_sectors"] == ["Pharma"]
    assert "Technology" in market_conditions["unfavored_sectors"]
    assert any("Skipped 1 recently researched symbols" in insight for insight in key_insights)


@pytest.mark.asyncio
async def test_analyze_candidates_uses_batched_research_brief():
    service, _, market_research_service, feature_extractor = _build_service()
    market_research_service.collect_batch_symbol_research.return_value = {
        "TCS": {
            "research_timestamp": "2026-03-24T06:00:00+00:00",
            "research_summary": "Fresh web research summary.",
            "financial_data": "Margins stable.",
            "filings": "Exchange filing confirms a contract win.",
            "market_context": "Relative strength remains positive.",
            "source_summary": [],
            "evidence_citations": [],
            "evidence": ["Contract win disclosed."],
            "risks": ["Execution risk remains."],
            "errors": [],
        }
    }
    feature_entry = SimpleNamespace(
        action="BUY",
        feature_confidence=0.76,
        score=81.0,
        id="ledger-1",
        to_flat_features=lambda: {"fin_revenue_growth_yoy_pct": 18.0},
    )
    feature_extractor.extract_features.return_value = feature_entry

    result = await service._analyze_candidates(
        [{"symbol": "TCS", "name": "TCS", "sector": "Technology", "discovery_reason": "Fresh dark-horse candidate."}],
        {},
        memory_context={"recent_symbols": {"INFY"}, "friction_notes": ["Fresh evidence was missing."]},
        market_conditions={"favored_sectors": ["Technology"]},
    )

    assert result[0]["external_research"]["research_summary"] == "Fresh web research summary."
    assert result[0]["claude_analysis"]["recommendation"] == "BUY"
    market_research_service.collect_batch_symbol_research.assert_awaited_once()
    call = market_research_service.collect_batch_symbol_research.await_args
    assert call.args[0] == ["TCS"]
    assert "dark-horse stock discovery pass" in call.kwargs["research_brief"]
    feature_extractor.extract_features.assert_awaited_once_with(
        "TCS",
        {
            "news": "Fresh web research summary.",
            "financials": "Margins stable.",
            "filings": "Exchange filing confirms a contract win.",
            "market_data": "Relative strength remains positive.",
        },
    )


@pytest.mark.asyncio
async def test_analyze_candidates_reuses_discovery_scout_research_without_extra_batch_fetch():
    service, _, market_research_service, feature_extractor = _build_service()
    feature_entry = SimpleNamespace(
        action="BUY",
        feature_confidence=0.76,
        score=81.0,
        id="ledger-1",
        to_flat_features=lambda: {"fin_revenue_growth_yoy_pct": 18.0},
    )
    feature_extractor.extract_features.return_value = feature_entry

    result = await service._analyze_candidates(
        [
            {
                "symbol": "TCS",
                "name": "TCS",
                "sector": "Technology",
                "discovery_reason": "Fresh dark-horse candidate.",
                "seed_research": {
                    "research_timestamp": "2026-03-24T06:00:00+00:00",
                    "research_summary": "Fresh web research summary.",
                    "financial_data": "Margins stable.",
                    "filings": "Exchange filing confirms a contract win.",
                    "market_context": "Relative strength remains positive.",
                    "source_summary": [],
                    "evidence_citations": [],
                    "evidence": ["Contract win disclosed."],
                    "risks": ["Execution risk remains."],
                    "errors": [],
                },
            }
        ],
        {},
        memory_context={},
        market_conditions={},
    )

    assert result[0]["external_research"]["research_summary"] == "Fresh web research summary."
    market_research_service.collect_batch_symbol_research.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_candidates_skips_feature_extraction_when_runtime_is_usage_limited():
    service, _, market_research_service, feature_extractor = _build_service()
    market_research_service.collect_batch_symbol_research.return_value = {
        "TCS": {
            "research_timestamp": "2026-03-24T06:00:00+00:00",
            "research_summary": "",
            "financial_data": "",
            "filings": "",
            "market_context": "",
            "source_summary": [],
            "evidence_citations": [],
            "evidence": [],
            "risks": [],
            "errors": [
                "You've hit your usage limit. Upgrade to Plus to continue using Codex, or try again later."
            ],
        }
    }

    result = await service._analyze_candidates(
        [{"symbol": "TCS", "name": "TCS", "sector": "Technology"}],
        {},
        memory_context={},
        market_conditions={},
    )

    assert result[0]["claude_analysis"]["analysis_type"] == "blocked"
    assert "usage limit" in result[0]["analysis_error"].lower()
    feature_extractor.extract_features.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_discovery_session_fails_fast_when_runtime_is_usage_limited(monkeypatch):
    service, _, market_research_service, _ = _build_service()
    service._build_discovery_memory = AsyncMock(return_value={})
    service._complete_discovery_session = AsyncMock()

    monkeypatch.setattr(
        "src.services.paper_trading.stock_discovery.get_ai_runtime_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                rate_limit_info={
                    "status": "exhausted",
                    "message": "You've hit your usage limit. Try again later.",
                },
                error=None,
            )
        ),
    )

    result = await service.run_discovery_session(account_id="paper_main")

    assert result["status"] == "blocked"
    assert "usage-limited" in result["blockers"][0]
    assert result["shortlisted"] == 0
    market_research_service.discover_market_opportunities.assert_not_awaited()
    market_research_service.collect_batch_symbol_research.assert_not_awaited()


@pytest.mark.asyncio
async def test_discovery_session_uses_market_scout_dark_horse_candidates(monkeypatch):
    service, state_manager, market_research_service, feature_extractor = _build_service()
    service._build_discovery_memory = AsyncMock(
        return_value={
            "recent_symbols": set(),
            "recently_blocked_symbols": set(),
            "held_symbols": set(),
            "watchlist_symbols": set(),
            "sector_scores": {},
            "sector_recent_counts": {},
            "friction_notes": [],
            "recent_lessons": [],
            "recent_research_by_symbol": {},
        }
    )
    feature_entry = SimpleNamespace(
        action="BUY",
        feature_confidence=0.81,
        score=84.0,
        id="ledger-1",
        to_flat_features=lambda: {"fin_revenue_growth_yoy_pct": 22.0},
    )
    feature_extractor.extract_features.return_value = feature_entry
    market_research_service.discover_market_opportunities.return_value = {
        "market_state_summary": "Breadth is improving outside crowded mega-cap leadership.",
        "favored_sectors": ["Capital Goods"],
        "caution_sectors": ["IT Services"],
        "key_insights": ["Discovery is leaning into industrial dark horses with fresh order-book support."],
        "candidates": [
            {
                "symbol": "KAYNES",
                "company_name": "Kaynes Technology",
                "sector": "Capital Goods",
                "discovery_reason": "Order-book momentum and sector tailwinds support a dark-horse setup.",
                "opportunity_score": 88,
                "research_timestamp": "2026-03-26T03:00:00+00:00",
                "summary": "Industrial electronics exposure is re-rating.",
                "research_summary": "Fresh order wins and manufacturing tailwinds support the setup.",
                "news": "Recent order wins point to momentum.",
                "financial_data": "Revenue growth and margins remain strong.",
                "filings": "Recent exchange updates confirm new business.",
                "market_context": "Sector breadth is improving.",
                "source_summary": [],
                "evidence_citations": [],
                "evidence": ["Order book growth remains strong."],
                "risks": ["Execution risk on rapid scale-up."],
                "errors": [],
            }
        ],
        "provider_metadata": {"provider": "codex"},
        "error": "",
    }

    monkeypatch.setattr(
        "src.services.paper_trading.stock_discovery.get_ai_runtime_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=False,
                error="Codex runtime sidecar is reachable, but no explicit AI request has validated auth/quota in this session yet.",
                rate_limit_info={},
            )
        ),
    )

    result = await service.run_discovery_session(account_id="paper_main")

    assert result["status"] == "completed"
    assert result["top_candidates"][0]["symbol"] == "KAYNES"
    assert result["market_conditions"]["discovery_style"] == "web_market_scout"
    market_research_service.discover_market_opportunities.assert_awaited_once()
    market_research_service.collect_batch_symbol_research.assert_not_awaited()
    state_manager.paper_trading.add_to_discovery_watchlist.assert_awaited()


@pytest.mark.asyncio
async def test_discovery_session_falls_back_to_deterministic_screen_when_web_scout_degrades(monkeypatch):
    service, state_manager, market_research_service, _ = _build_service()
    service._load_market_universe = AsyncMock(
        return_value=[
            {"symbol": "KAYNES", "name": "Kaynes", "sector": "Capital Goods", "cap": "mid"},
            {"symbol": "TANLA", "name": "Tanla", "sector": "Technology", "cap": "mid"},
        ]
    )
    service._build_discovery_memory = AsyncMock(
        return_value={
            "recent_symbols": set(),
            "recently_blocked_symbols": set(),
            "held_symbols": set(),
            "watchlist_symbols": set(),
            "stale_watchlist_symbols": set(),
            "sector_scores": {"Capital Goods": 1.0},
            "sector_recent_counts": {},
            "friction_notes": [],
            "recent_lessons": [],
            "recent_research_by_symbol": {},
        }
    )
    market_research_service.discover_market_opportunities.return_value = {
        "market_state_summary": "",
        "favored_sectors": [],
        "caution_sectors": [],
        "key_insights": [],
        "candidates": [],
        "provider_metadata": {},
        "error": "Codex runtime timed out after 45.0s.",
    }

    monkeypatch.setattr(
        "src.services.paper_trading.stock_discovery.get_ai_runtime_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                error=None,
                rate_limit_info={},
            )
        ),
    )

    result = await service.run_discovery_session(account_id="paper_main")

    assert result["status"] == "completed"
    assert result["market_conditions"]["discovery_style"] == "deterministic_fallback"
    assert result["top_candidates"][0]["symbol"] == "KAYNES"
    assert "Live web scout degraded" in result["top_candidates"][0]["discovery_reason"]
    assert result["blockers"] == ["AI runtime discovery scout failed. Codex runtime timed out after 45.0s."]
    market_research_service.collect_batch_symbol_research.assert_not_awaited()
    state_manager.paper_trading.add_to_discovery_watchlist.assert_awaited()


@pytest.mark.asyncio
async def test_update_watchlist_retires_symbols_that_drop_out_of_latest_discovery():
    service, state_manager, _, _ = _build_service()
    state_manager.paper_trading.get_discovery_watchlist.return_value = [
        {"id": 1, "symbol": "RELIANCE"},
        {"id": 2, "symbol": "INFY"},
    ]
    state_manager.paper_trading.get_discovery_watchlist_by_symbol.side_effect = [
        {"id": 2, "symbol": "INFY", "status": "ACTIVE"},
    ]

    updates = await service._update_watchlist(
        [
            {
                "symbol": "INFY",
                "name": "Infosys",
                "sector": "Technology",
                "recommendation": "BUY",
                "score": 72,
                "claude_analysis": {"features": {}},
            }
        ]
    )

    assert updates["removed"] == 1
    state_manager.paper_trading.delete_discovery_watchlist_entry.assert_awaited_once_with(1)

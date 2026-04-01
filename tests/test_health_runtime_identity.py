from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.trading_capabilities import CapabilityCheck, CapabilityStatus, TradingCapabilitySnapshot
from src.web.app import APP_BUILD_ID, APP_GIT_SHA, APP_GIT_SHORT_SHA, health_check


@pytest.mark.asyncio
async def test_health_check_exposes_runtime_identity():
    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="ai_runtime",
                label="AI Runtime",
                status=CapabilityStatus.READY,
                summary="AI runtime is ready.",
            ),
            CapabilityCheck(
                key="quote_stream",
                label="Quote Stream",
                status=CapabilityStatus.READY,
                summary="Quote stream is ready.",
            ),
            CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.READY,
                summary="Market data is ready.",
            ),
        ],
    )

    container = MagicMock()
    container.get = AsyncMock(return_value=capability_service)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=container)))

    payload = await health_check(request=request)

    assert payload["status"] == "healthy"
    assert payload["runtime_identity"] == {
        "runtime": "backend",
        "git_sha": APP_GIT_SHA,
        "git_short_sha": APP_GIT_SHORT_SHA,
        "build_id": APP_BUILD_ID,
        "started_at": payload["runtime_identity"]["started_at"],
        "workspace_path": "/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader",
    }
    assert payload["runtime_identity"]["started_at"]
    assert payload["readiness"]["ai_runtime"]["status"] == "ready"
    assert payload["readiness"]["quote_stream"]["status"] == "ready"
    assert payload["readiness"]["market_data"]["status"] == "ready"

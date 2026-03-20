"""Mission-first capability checks for paper-trading automation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.auth.claude_auth import get_claude_status_cached
from src.models.trading_capabilities import (
    CapabilityCheck,
    CapabilityStatus,
    TradingCapabilitySnapshot,
)

logger = logging.getLogger(__name__)


class TradingCapabilityService:
    """Build a truthful readiness snapshot for autonomous paper trading."""

    def __init__(self, container: "DependencyContainer"):
        self.container = container

    async def get_snapshot(self, account_id: Optional[str] = None) -> TradingCapabilitySnapshot:
        """Collect capability checks for the current operating mode."""
        checks = [
            await self._check_claude_runtime(),
            await self._check_quote_stream(),
            await self._check_market_data_pipeline(),
            await self._check_broker_auth(),
            await self._check_paper_trading_account(account_id),
        ]
        return TradingCapabilitySnapshot.build(
            mode="paper_only",
            checks=checks,
            account_id=account_id,
        )

    async def _check_claude_runtime(self) -> CapabilityCheck:
        """Verify Claude Agent SDK runtime/auth state."""
        status = await get_claude_status_cached()
        if status.is_valid:
            return CapabilityCheck(
                key="claude_runtime",
                label="Claude Runtime",
                status=CapabilityStatus.READY,
                summary="Claude Agent SDK authentication is valid.",
                metadata={
                    "checked_at": status.checked_at,
                    "auth_method": status.account_info.get("auth_method"),
                },
            )

        return CapabilityCheck(
            key="claude_runtime",
            label="Claude Runtime",
            status=CapabilityStatus.BLOCKED,
            summary="Claude Agent SDK authentication is invalid.",
            detail=status.error or "Claude runtime must authenticate before autonomous workflows can run.",
            metadata={"checked_at": status.checked_at},
        )

    async def _check_quote_stream(self) -> CapabilityCheck:
        """Verify the live quote stream that powers paper-mode mark-to-market updates."""
        market_data_service = await self.container.get("market_data_service")
        if market_data_service is None:
            return CapabilityCheck(
                key="quote_stream",
                label="Quote Stream",
                status=CapabilityStatus.BLOCKED,
                summary="No quote stream service is wired for paper-mode live marks.",
                detail="Configure a provider such as Upstox Market Data Feed V3 before relying on live paper P&L.",
            )

        stream_status = await market_data_service.get_quote_stream_status()
        metadata = stream_status.to_metadata()

        if not stream_status.configured:
            return CapabilityCheck(
                key="quote_stream",
                label="Quote Stream",
                status=CapabilityStatus.BLOCKED,
                summary="No quote stream provider is configured for live paper marks.",
                detail=stream_status.detail
                or "Set QUOTE_STREAM_PROVIDER and provider credentials to enable quote streaming.",
                metadata=metadata,
            )

        if stream_status.connected and stream_status.last_tick_at:
            return CapabilityCheck(
                key="quote_stream",
                label="Quote Stream",
                status=CapabilityStatus.READY,
                summary=f"{stream_status.provider.replace('_', ' ').title()} is streaming live quotes.",
                detail=stream_status.detail,
                metadata=metadata,
            )

        degraded_summary = (
            f"{stream_status.provider.replace('_', ' ').title()} is configured but not serving fresh ticks yet."
        )
        return CapabilityCheck(
            key="quote_stream",
            label="Quote Stream",
            status=CapabilityStatus.DEGRADED,
            summary=degraded_summary,
            detail=stream_status.detail or "Connect the quote stream and subscribe active paper-trading symbols.",
            metadata=metadata,
        )

    async def _check_market_data_pipeline(self) -> CapabilityCheck:
        """Verify live quote freshness from the active quote provider."""
        market_data_service = await self.container.get("market_data_service")
        if market_data_service is None:
            return CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.BLOCKED,
                summary="Market data service is unavailable.",
                detail="Paper-trading mark-to-market requires the shared market data service to initialize correctly.",
            )

        subscriptions = await market_data_service.get_active_subscriptions()
        market_data = getattr(market_data_service, "_market_data", {}) or {}

        if not subscriptions:
            return CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.DEGRADED,
                summary="No active quote subscriptions exist yet.",
                detail="Live paper marks will begin once positions or watched symbols are subscribed.",
                metadata={"active_subscriptions": 0, "cached_symbols": len(market_data)},
            )

        if not market_data:
            return CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.BLOCKED,
                summary="Quote subscriptions exist but no market data has been cached.",
                detail="The quote stream is not delivering usable ticks to the live paper-mark cache.",
                metadata={"active_subscriptions": len(subscriptions), "cached_symbols": 0},
            )

        freshest_age_seconds: Optional[float] = None
        for snapshot in market_data.values():
            try:
                age_seconds = (
                    datetime.now(timezone.utc) - datetime.fromisoformat(snapshot.timestamp)
                ).total_seconds()
            except ValueError:
                continue
            freshest_age_seconds = age_seconds if freshest_age_seconds is None else min(freshest_age_seconds, age_seconds)

        if freshest_age_seconds is None or freshest_age_seconds > 120:
            return CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.BLOCKED,
                summary="Market data cache is stale for active paper-trading symbols.",
                detail="Fresh live marks are required before autonomous position management can rely on unrealized P&L.",
                metadata={
                    "active_subscriptions": len(subscriptions),
                    "cached_symbols": len(market_data),
                    "freshest_age_seconds": round(freshest_age_seconds or 0.0, 2),
                },
            )

        providers = sorted({snapshot.provider for snapshot in market_data.values() if snapshot.provider})
        provider_label = ", ".join(providers) if providers else "configured provider"
        return CapabilityCheck(
            key="market_data",
            label="Market Data",
            status=CapabilityStatus.READY,
            summary=f"Live quote cache is fresh from {provider_label}.",
            metadata={
                "active_subscriptions": len(subscriptions),
                "cached_symbols": len(market_data),
                "freshest_age_seconds": round(freshest_age_seconds or 0.0, 2),
                "providers": providers,
            },
        )

    async def _check_broker_auth(self) -> CapabilityCheck:
        """Verify future broker execution readiness without blocking paper-mode quotes."""
        config = getattr(self.container.config, "integration", None)
        api_key = getattr(config, "zerodha_api_key", None) if config else None
        api_secret = getattr(config, "zerodha_api_secret", None) if config else None

        if not api_key or not api_secret:
            return CapabilityCheck(
                key="broker_auth",
                label="Broker",
                status=CapabilityStatus.DEGRADED,
                blocking=False,
                summary="Zerodha broker credentials are not configured.",
                detail="Paper mode can still run on a separate quote provider. Zerodha is only required for broker-backed execution or reconciliation.",
            )

        kite_service = await self.container.get("kite_connect_service")
        if kite_service is None:
            return CapabilityCheck(
                key="broker_auth",
                label="Broker",
                status=CapabilityStatus.DEGRADED,
                blocking=False,
                summary="Zerodha broker service is unavailable.",
                detail="Paper mode can continue without broker auth, but broker-backed execution is unavailable.",
            )

        if getattr(kite_service, "is_mock", False):
            return CapabilityCheck(
                key="broker_auth",
                label="Broker",
                status=CapabilityStatus.DEGRADED,
                blocking=False,
                summary="Broker is still running in mock mode.",
                detail="Mock broker sessions are ignored for mission-critical paper-mode readiness.",
            )

        try:
            authenticated = await kite_service.is_authenticated()
        except Exception as exc:  # pragma: no cover - defensive service check
            logger.warning("Broker authentication probe failed: %s", exc)
            authenticated = False

        if not authenticated:
            return CapabilityCheck(
                key="broker_auth",
                label="Broker",
                status=CapabilityStatus.DEGRADED,
                blocking=False,
                summary="Zerodha broker session is not authenticated.",
                detail="Paper mode can still use a separate live quote provider. Authenticate Zerodha only when broker-backed features are needed.",
            )

        return CapabilityCheck(
            key="broker_auth",
            label="Broker",
            status=CapabilityStatus.READY,
            blocking=False,
            summary="Zerodha broker session is authenticated.",
            detail="Broker-backed execution and reconciliation can use the live Zerodha session.",
        )

    async def _check_paper_trading_account(self, account_id: Optional[str]) -> CapabilityCheck:
        """Verify there is an explicit paper-trading account for automation."""
        account_manager = await self.container.get("paper_trading_account_manager")
        accounts = await account_manager.get_all_accounts()

        if not accounts:
            return CapabilityCheck(
                key="paper_account",
                label="Paper Account",
                status=CapabilityStatus.BLOCKED,
                summary="No paper trading account exists.",
                detail="Create a paper trading account before running autonomous swing-trading workflows.",
            )

        if account_id:
            account = await account_manager.get_account(account_id)
            if account is None:
                return CapabilityCheck(
                    key="paper_account",
                    label="Paper Account",
                    status=CapabilityStatus.BLOCKED,
                    summary=f"Selected paper trading account '{account_id}' was not found.",
                    detail="Choose an existing account instead of relying on an implicit default.",
                    metadata={"available_accounts": [acct.account_id for acct in accounts]},
                )

            return CapabilityCheck(
                key="paper_account",
                label="Paper Account",
                status=CapabilityStatus.READY,
                summary=f"Paper trading account '{account_id}' is available.",
                metadata={"available_accounts": len(accounts)},
            )

        if len(accounts) == 1:
            return CapabilityCheck(
                key="paper_account",
                label="Paper Account",
                status=CapabilityStatus.DEGRADED,
                summary=f"One paper account exists but no account was explicitly selected ({accounts[0].account_id}).",
                detail="Select the account explicitly so the operator workflow remains unambiguous.",
                metadata={"available_accounts": [accounts[0].account_id]},
            )

        return CapabilityCheck(
            key="paper_account",
            label="Paper Account",
            status=CapabilityStatus.BLOCKED,
            summary="Multiple paper accounts exist but none is selected.",
            detail="Automation should not infer which account to trade.",
            metadata={"available_accounts": [account.account_id for account in accounts]},
        )

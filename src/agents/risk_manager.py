"""
Risk Manager Agent

Assesses risk for trading intents and enforces position limits.
"""

import json
import math
from typing import Dict, List, Any, Optional

from claude_agent_sdk import tool
from loguru import logger

from ..config import Config
from ..core.state import StateManager, RiskDecision, Intent, PortfolioState, Signal


def create_risk_manager_tool(config: Config, state_manager: StateManager):
    """Create risk manager tool with dependencies via closure."""
    
    @tool("risk_assessment", "Assess risk for trading intent", {"intent_id": str})
    async def risk_assessment_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk for a trading intent."""
        try:
            intent_id = args["intent_id"]
            intent = await state_manager.get_intent(intent_id)

            if not intent:
                return {
                    "content": [{"type": "text", "text": f"Intent {intent_id} not found"}],
                    "is_error": True
                }

            # Perform risk assessment
            decision = await _assess_risk(intent, config, state_manager)

            # Update intent
            intent.risk_decision = decision
            await state_manager.update_intent(intent)

            return {
                "content": [
                    {"type": "text", "text": f"Risk assessment completed for intent {intent_id}"},
                    {"type": "text", "text": json.dumps(decision.to_dict(), indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return risk_assessment_tool


async def _assess_risk(intent: Intent, config: Config, state_manager: StateManager) -> RiskDecision:
    """Perform risk assessment."""
    symbol = intent.symbol
    signal = intent.signal

    if not signal:
        return RiskDecision(
            symbol=symbol,
            decision="deny",
            reasons=["No signal data available"]
        )

    portfolio = await state_manager.get_portfolio()
    portfolio_value = _estimate_portfolio_value(portfolio, config)

    max_position_value = portfolio_value * (config.risk.max_position_size_percent / 100)
    risk_per_trade = portfolio_value * (config.risk.max_single_symbol_exposure_percent / 100)

    entry_price = signal.entry.get("price", 0) if signal.entry else 0
    if entry_price <= 0:
        entry_price = _fallback_price(symbol, portfolio)

    if entry_price <= 0:
        reason = "Entry price unavailable; cannot size position"
        return RiskDecision(
            symbol=symbol,
            decision="deny",
            constraints=[reason],
            reasons=[reason]
        )

    qty = _size_position(entry_price, signal, config, max_position_value, risk_per_trade)

    if qty <= 0:
        reason = "Unable to size position within risk limits"
        return RiskDecision(
            symbol=symbol,
            decision="deny",
            constraints=[reason],
            reasons=[reason]
        )

    constraints: List[str] = []
    position_value = qty * entry_price

    if position_value > max_position_value:
        constraints.append(
            f"Position size {position_value:.2f} exceeds limit {max_position_value:.2f}"
        )

    current_exposure = 0.0
    if portfolio:
        for holding in portfolio.holdings:
            if holding["symbol"] == symbol:
                current_exposure = float(holding.get("exposure", 0))
                break

    new_exposure = current_exposure + position_value
    max_symbol_exposure = portfolio_value * (config.risk.max_single_symbol_exposure_percent / 100)
    if new_exposure > max_symbol_exposure:
        constraints.append(
            f"Symbol exposure {new_exposure:.2f} exceeds limit {max_symbol_exposure:.2f}"
        )

    stop_price = signal.stop.get("price") if signal.stop else None
    if stop_price is not None:
        per_share_loss = abs(entry_price - stop_price)
        potential_loss = per_share_loss * qty
        if portfolio_value > 0:
            potential_loss_percent = (potential_loss / portfolio_value) * 100
            if potential_loss_percent > config.risk.max_portfolio_risk_percent:
                constraints.append(
                    f"Projected loss {potential_loss_percent:.2f}% exceeds portfolio risk limit {config.risk.max_portfolio_risk_percent}%"
                )

    if constraints:
        return RiskDecision(
            symbol=symbol,
            decision="deny",
            size_qty=None,
            max_risk_inr=int(risk_per_trade),
            stop=signal.stop,
            targets=signal.targets,
            constraints=constraints,
            reasons=constraints,
        )

    return RiskDecision(
        symbol=symbol,
        decision="approve",
        size_qty=qty,
        max_risk_inr=int(risk_per_trade),
        stop=signal.stop,
        targets=signal.targets,
        constraints=[],
        reasons=["Within all risk limits"],
    )

def _estimate_portfolio_value(portfolio: Optional[PortfolioState], config: Config) -> float:
    """Estimate total portfolio value with sensible fallbacks."""
    if portfolio:
        cash_free = float(portfolio.cash.get("free", 0))
        exposure_total = float(portfolio.exposure_total or 0)
        if exposure_total <= 0 and portfolio.holdings:
            exposure_total = sum(float(h.get("exposure", 0)) for h in portfolio.holdings)
        total = cash_free + exposure_total
        if total > 0:
            return total

    # Fallback to conservative baseline derived from configuration limits
    baseline_capital = max(
        config.risk.max_daily_trades * 10000,
        (config.risk.max_notional_per_order if hasattr(config.risk, "max_notional_per_order") else 100000),
    )
    return float(max(baseline_capital, 1.0))


def _fallback_price(symbol: str, portfolio: Optional[PortfolioState]) -> float:
    """Fallback to last known price from portfolio holdings."""
    if portfolio:
        for holding in portfolio.holdings:
            if holding["symbol"] == symbol:
                last_price = holding.get("last_price")
                avg_price = holding.get("avg_price")
                if last_price:
                    return float(last_price)
                if avg_price:
                    return float(avg_price)
    return 0.0


def _size_position(
    entry_price: float,
    signal: Signal,
    config: Config,
    max_position_value: float,
    risk_per_trade: float,
) -> int:
    """Determine optimal quantity respecting notional and risk budgets."""
    if entry_price <= 0:
        return 0

    notional_qty = max_position_value / entry_price if entry_price else 0

    per_share_risk_candidates: List[float] = []

    stop_price = signal.stop.get("price") if signal.stop else None
    if stop_price is not None:
        per_share_risk_candidates.append(abs(entry_price - stop_price))

    if signal.indicators and signal.indicators.get("atr"):
        atr_value = float(signal.indicators["atr"])
        if atr_value > 0:
            per_share_risk_candidates.append(atr_value)

    per_share_risk_candidates.append(entry_price * (config.risk.stop_loss_percent / 100))
    per_share_risk = max(per_share_risk_candidates) if per_share_risk_candidates else entry_price * 0.02
    per_share_risk = max(per_share_risk, entry_price * 0.005)

    risk_qty = risk_per_trade / per_share_risk if per_share_risk > 0 else 0
    qty = math.floor(max(0, min(notional_qty, risk_qty)))
    return qty
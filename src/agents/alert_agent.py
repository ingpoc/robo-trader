"""
Smart Alert Agent

Provides customizable alerts for market conditions, portfolio changes, and trading opportunities.
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from claude_agent_sdk import tool
from loguru import logger

from ..config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import PortfolioState


@dataclass
class AlertRule:
    """Customizable alert rule."""
    id: str
    name: str
    condition_type: str  # "price", "volume", "technical", "portfolio"
    symbol: str
    condition: Dict[str, Any]  # Flexible condition parameters
    notification_type: str  # "toast", "email", "sms"
    is_active: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def create_alert_tools(config: Config, state_manager: DatabaseStateManager) -> List:
    """Create alert tools with dependencies via closure."""
    
    @tool("create_alert_rule", "Create a custom alert rule", {
        "name": str,
        "condition_type": str,
        "symbol": str,
        "condition": Dict[str, Any],
        "notification_type": str
    })
    async def create_alert_rule_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a customizable alert rule for market conditions."""
        try:
            rule = AlertRule(
                id=f"alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                name=args["name"],
                condition_type=args["condition_type"],
                symbol=args["symbol"],
                condition=args["condition"],
                notification_type=args["notification_type"]
            )

            # Store the alert rule (in a real implementation, this would be persisted)
            await _store_alert_rule(rule)

            return {
                "content": [
                    {"type": "text", "text": f"Alert rule '{rule.name}' created successfully"},
                    {"type": "text", "text": json.dumps(asdict(rule), indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Alert rule creation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error creating alert rule: {str(e)}"}],
                "is_error": True
            }

    @tool("list_alert_rules", "List all active alert rules", {})
    async def list_alert_rules_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all configured alert rules."""
        try:
            rules = await _get_alert_rules()

            return {
                "content": [
                    {"type": "text", "text": f"Found {len(rules)} active alert rules"},
                    {"type": "text", "text": json.dumps([asdict(rule) for rule in rules], indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Failed to list alert rules: {e}")
            return {
                "content": [{"type": "text", "text": f"Error listing alert rules: {str(e)}"}],
                "is_error": True
            }

    @tool("check_alerts", "Check all alert conditions and trigger notifications", {})
    async def check_alerts_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all alert conditions and send notifications for triggered alerts."""
        try:
            rules = await _get_alert_rules()
            triggered_alerts = []

            for rule in rules:
                if rule.is_active:
                    triggered = await _evaluate_alert_rule(rule, state_manager)
                    if triggered:
                        triggered_alerts.append(rule)
                        await _send_alert_notification(rule, triggered)

            return {
                "content": [
                    {"type": "text", "text": f"Checked {len(rules)} alert rules, {len(triggered_alerts)} triggered"},
                    {"type": "text", "text": json.dumps({
                        "total_rules": len(rules),
                        "triggered_alerts": len(triggered_alerts),
                        "alerts": [asdict(rule) for rule in triggered_alerts]
                    }, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Alert check failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error checking alerts: {str(e)}"}],
                "is_error": True
            }

    @tool("delete_alert_rule", "Delete an alert rule", {"rule_id": str})
    async def delete_alert_rule_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a specific alert rule."""
        try:
            rule_id = args["rule_id"]
            await _delete_alert_rule(rule_id)

            return {
                "content": [
                    {"type": "text", "text": f"Alert rule {rule_id} deleted successfully"}
                ]
            }

        except Exception as e:
            logger.error(f"Alert rule deletion failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error deleting alert rule: {str(e)}"}],
                "is_error": True
            }
    
    return [create_alert_rule_tool, list_alert_rules_tool, check_alerts_tool, delete_alert_rule_tool]


async def _evaluate_alert_rule(rule: AlertRule, state_manager: DatabaseStateManager) -> bool:
    """Evaluate if an alert rule condition is met."""

    try:
        if rule.condition_type == "price":
            return await _check_price_alert(rule, state_manager)
        elif rule.condition_type == "portfolio":
            return await _check_portfolio_alert(rule, state_manager)
        elif rule.condition_type == "technical":
            return await _check_technical_alert(rule, state_manager)
        else:
            logger.warning(f"Unknown alert condition type: {rule.condition_type}")
            return False

    except Exception as e:
        logger.error(f"Error evaluating alert rule {rule.id}: {e}")
        return False


async def _check_price_alert(rule: AlertRule, state_manager: DatabaseStateManager) -> bool:
    """Check price-based alert conditions."""

    symbol = rule.symbol
    condition = rule.condition

    # Get current price (in a real implementation, this would fetch from broker)
    # For now, we'll simulate price data
    current_price = await _get_current_price(symbol)

    if condition.get("operator") == "above" and current_price > condition.get("price", 0):
        return True
    elif condition.get("operator") == "below" and current_price < condition.get("price", 0):
        return True
    elif condition.get("operator") == "crosses_above" and current_price > condition.get("price", 0):
        return True
    elif condition.get("operator") == "crosses_below" and current_price < condition.get("price", 0):
        return True

    return False


async def _check_portfolio_alert(rule: AlertRule, state_manager: DatabaseStateManager) -> bool:
    """Check portfolio-based alert conditions."""

    portfolio = await state_manager.get_portfolio()
    if not portfolio:
        return False

    condition = rule.condition

    if condition.get("metric") == "concentration_risk":
        current_risk = portfolio.risk_aggregates.portfolio.concentration_risk
        threshold = condition.get("threshold", 20)
        return current_risk > threshold

    elif condition.get("metric") == "total_exposure":
        current_exposure = portfolio.exposure_total
        threshold = condition.get("threshold", 0)
        return current_exposure > threshold

    return False


async def _check_technical_alert(rule: AlertRule, state_manager: DatabaseStateManager) -> bool:
    """Check technical indicator-based alert conditions."""

    # This would check technical indicators against thresholds
    # For now, return a simulated result
    symbol = rule.symbol
    condition = rule.condition

    # Simulate technical indicator check
    indicator_value = await _get_technical_indicator(symbol, condition.get("indicator", "rsi"))

    if condition.get("operator") == "above" and indicator_value > condition.get("threshold", 0):
        return True
    elif condition.get("operator") == "below" and indicator_value < condition.get("threshold", 0):
        return True

    return False


async def _send_alert_notification(rule: AlertRule, trigger_data: Dict[str, Any]) -> None:
    """Send alert notification through specified channel."""

    message = f"🚨 Alert: {rule.name}\nSymbol: {rule.symbol}\nCondition: {rule.condition_type}\nTime: {datetime.now().strftime('%H:%M:%S')}"

    if rule.notification_type == "toast":
        # Send to web interface via WebSocket
        await _send_websocket_notification(message, "warning")
    elif rule.notification_type == "email":
        # Send email notification (implement with email service)
        logger.info(f"Email alert: {message}")
    elif rule.notification_type == "sms":
        # Send SMS notification (implement with SMS service)
        logger.info(f"SMS alert: {message}")

    logger.info(f"Alert triggered: {rule.name} for {rule.symbol}")


async def _send_websocket_notification(message: str, type: str) -> None:
    """Send notification to connected WebSocket clients."""
    # This would integrate with the WebSocket system to send real-time notifications
    logger.info(f"WebSocket notification: {message}")


# Helper functions (in a real implementation, these would connect to actual data sources)

async def _get_current_price(symbol: str) -> float:
    """Get current market price for symbol."""
    # Simulate price data - in reality, this would fetch from broker API
    import random
    base_prices = {
        "RELIANCE": 2685.40,
        "TCS": 4185.80,
        "HDFCBANK": 1720.90,
        "ICICIBANK": 1158.60,
        "INFY": 1925.75
    }
    base_price = base_prices.get(symbol, 1000)
    # Add some random variation
    variation = random.uniform(-0.02, 0.02)  # ±2%
    return base_price * (1 + variation)


async def _get_technical_indicator(symbol: str, indicator: str) -> float:
    """Get technical indicator value for symbol."""
    # Simulate technical indicator data
    import random

    indicators = {
        "rsi": random.uniform(30, 70),
        "macd": random.uniform(-50, 50),
        "volume": random.uniform(100000, 1000000),
        "ema_20": random.uniform(100, 200)
    }

    return indicators.get(indicator, 50)


async def _store_alert_rule(rule: AlertRule) -> None:
    """Store alert rule in persistent storage."""
    # In a real implementation, this would save to database
    logger.info(f"Stored alert rule: {rule.id}")


async def _get_alert_rules() -> List[AlertRule]:
    """Get all alert rules from storage."""
    # In a real implementation, this would load from database
    # For now, return some default rules
    return [
        AlertRule(
            id="default_price_alert",
            name="RELIANCE Price Alert",
            condition_type="price",
            symbol="RELIANCE",
            condition={"operator": "above", "price": 2700},
            notification_type="toast"
        ),
        AlertRule(
            id="default_risk_alert",
            name="High Concentration Risk",
            condition_type="portfolio",
            symbol="PORTFOLIO",
            condition={"metric": "concentration_risk", "threshold": 25},
            notification_type="toast"
        )
    ]


async def _delete_alert_rule(rule_id: str) -> None:
    """Delete alert rule from storage."""
    logger.info(f"Deleted alert rule: {rule_id}")
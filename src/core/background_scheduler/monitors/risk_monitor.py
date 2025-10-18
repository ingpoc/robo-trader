"""
Risk monitoring service.

Tracks stop loss levels and alerts on position risks.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from loguru import logger


class RiskMonitor:
    """Monitors portfolio risk and stop loss levels."""

    def __init__(self, state_manager=None, alert_manager=None):
        """Initialize risk monitor.

        Args:
            state_manager: State manager for portfolio access
            alert_manager: Alert manager for creating alerts
        """
        self.state_manager = state_manager
        self.alert_manager = alert_manager

    async def check_stop_loss(
        self,
        portfolio: Dict[str, Any],
        stop_loss_percent: float = 5.0
    ) -> Dict[str, Any]:
        """Check portfolio for stop loss breaches.

        Args:
            portfolio: Portfolio data with holdings
            stop_loss_percent: Stop loss percentage threshold

        Returns:
            Dictionary with breach information
        """
        result = {
            "breaches": [],
            "alerts_created": 0,
            "positions_checked": 0
        }

        if not portfolio or not portfolio.get('holdings'):
            return result

        for holding in portfolio.get('holdings', []):
            try:
                result['positions_checked'] += 1
                symbol = holding.get('tradingsymbol', '')
                if not symbol:
                    continue

                avg_price = float(holding.get('average_price', 0))
                last_price = float(holding.get('last_price', 0))
                quantity = float(holding.get('quantity', 0))
                pnl_percent = float(holding.get('pnl_percent', 0))

                if avg_price <= 0 or last_price <= 0:
                    continue

                stop_loss_price = avg_price * (1 - stop_loss_percent / 100)
                stop_loss_breached = last_price <= stop_loss_price

                if stop_loss_breached and pnl_percent < 0:
                    potential_loss = abs(pnl_percent)
                    breach_data = {
                        "symbol": symbol,
                        "current_price": last_price,
                        "stop_loss_price": stop_loss_price,
                        "avg_price": avg_price,
                        "quantity": quantity,
                        "pnl_percent": pnl_percent,
                        "potential_loss": potential_loss,
                        "severity": "high" if potential_loss > 5 else "medium",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    result["breaches"].append(breach_data)

                    if self.alert_manager:
                        try:
                            await self.alert_manager.create_alert(
                                alert_type="stop_loss",
                                severity=breach_data["severity"],
                                title=f"Stop Loss Alert: {symbol}",
                                message=f"Price ₹{last_price:.2f} breached stop loss at ₹{stop_loss_price:.2f}. Loss: {pnl_percent:.2f}%",
                                symbol=symbol
                            )
                            result["alerts_created"] += 1
                        except Exception as e:
                            logger.error(f"Failed to create alert for {symbol}: {e}")

                    logger.warning(f"Stop loss breached for {symbol}: {last_price:.2f} <= {stop_loss_price:.2f}")

            except Exception as e:
                logger.error(f"Error checking stop loss for {symbol}: {e}")

        if result["alerts_created"] > 0:
            logger.info(f"Risk monitor: created {result['alerts_created']} stop loss alerts")

        return result

    @staticmethod
    def calculate_position_risk(holding: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics for a position.

        Args:
            holding: Holding data

        Returns:
            Risk analysis for the position
        """
        try:
            avg_price = float(holding.get('average_price', 0))
            last_price = float(holding.get('last_price', 0))
            quantity = float(holding.get('quantity', 0))
            pnl_percent = float(holding.get('pnl_percent', 0))
            pnl_value = float(holding.get('pnl', 0))

            if avg_price <= 0:
                return {}

            position_value = quantity * last_price
            max_loss = quantity * avg_price
            loss_per_1pct_drop = quantity * (avg_price * 0.01)

            return {
                "position_value": position_value,
                "max_loss": max_loss,
                "current_loss": abs(pnl_value),
                "loss_per_1pct_drop": loss_per_1pct_drop,
                "pnl_percent": pnl_percent,
                "risk_level": "high" if pnl_percent < -10 else "medium" if pnl_percent < -5 else "low",
                "break_even_price": avg_price,
                "distance_from_breakeven": ((last_price - avg_price) / avg_price * 100) if avg_price else 0
            }
        except Exception as e:
            logger.error(f"Error calculating position risk: {e}")
            return {}

    @staticmethod
    def calculate_portfolio_risk(portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics.

        Args:
            portfolio: Portfolio data

        Returns:
            Portfolio risk analysis
        """
        try:
            holdings = portfolio.get('holdings', [])
            if not holdings:
                return {}

            total_value = 0
            total_loss = 0
            losing_positions = 0
            gain_positions = 0

            for holding in holdings:
                try:
                    pnl_value = float(holding.get('pnl', 0))
                    total_value += float(holding.get('average_price', 0)) * float(holding.get('quantity', 0))
                    total_loss += abs(pnl_value) if pnl_value < 0 else 0

                    pnl_percent = float(holding.get('pnl_percent', 0))
                    if pnl_percent < 0:
                        losing_positions += 1
                    else:
                        gain_positions += 1
                except Exception as e:
                    logger.debug(f"Error processing holding in risk calculation: {e}")

            portfolio_loss_pct = (total_loss / total_value * 100) if total_value > 0 else 0

            return {
                "total_value": total_value,
                "total_loss": total_loss,
                "portfolio_loss_pct": portfolio_loss_pct,
                "losing_positions": losing_positions,
                "gain_positions": gain_positions,
                "risk_level": "high" if portfolio_loss_pct > 5 else "medium" if portfolio_loss_pct > 2 else "low"
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {}

    async def check_concentration_risk(
        self,
        portfolio: Dict[str, Any],
        max_position_percent: float = 15.0
    ) -> Dict[str, Any]:
        """Check for portfolio concentration risk.

        Args:
            portfolio: Portfolio data
            max_position_percent: Maximum allowed position percentage

        Returns:
            Concentration risk analysis
        """
        result = {
            "high_concentration_positions": [],
            "total_portfolio_value": 0,
            "max_position_size": 0
        }

        try:
            holdings = portfolio.get('holdings', [])
            if not holdings:
                return result

            total_value = 0
            for holding in holdings:
                position_value = float(holding.get('average_price', 0)) * float(holding.get('quantity', 0))
                total_value += position_value

            result['total_portfolio_value'] = total_value

            if total_value == 0:
                return result

            for holding in holdings:
                position_value = float(holding.get('average_price', 0)) * float(holding.get('quantity', 0))
                position_percent = (position_value / total_value) * 100

                if position_percent > max_position_percent:
                    result["high_concentration_positions"].append({
                        "symbol": holding.get('tradingsymbol', ''),
                        "position_value": position_value,
                        "position_percent": position_percent,
                        "concentration_level": "very_high" if position_percent > 30 else "high"
                    })

                result['max_position_size'] = max(result['max_position_size'], position_percent)

        except Exception as e:
            logger.error(f"Error checking concentration risk: {e}")

        return result

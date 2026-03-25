"""Morning Pre-Market Coordinator

Scans pre-market data for trading opportunities using stock discovery
and Kite Connect services.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus
from src.services.kite_connect_service import KiteConnectService
from src.services.paper_trading.stock_discovery import StockDiscoveryService

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


class MorningPremarketCoordinator(BaseCoordinator):
    """Scans pre-market data for stock opportunities. Max 150 lines."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container
        self.kite_service: Optional[KiteConnectService] = None
        self.stock_discovery: Optional[StockDiscoveryService] = None

    async def initialize(self) -> None:
        """Initialize with required services from DI container."""
        self.stock_discovery = await self.container.get("stock_discovery_service")

        try:
            self._log_debug("Attempting to get kite_connect_service from container...")
            self.kite_service = await self.container.get("kite_connect_service")
            self._log_debug(f"kite_connect_service obtained: {self.kite_service}")
        except ValueError:
            self._log_warning("kite_connect_service not registered - using market_data_service")
            self.kite_service = await self.container.get("market_data_service")

        self._initialized = True

    async def scan_pre_market_data(self) -> List[Dict[str, Any]]:
        """
        Scan pre-market data for opportunities.

        Returns:
            List of stock dicts with symbol, price, change, volume, risk_score.
        """
        try:
            watchlist = await self.stock_discovery.get_watchlist(limit=20)
            pre_market_data = []

            for stock in watchlist:
                try:
                    if self.kite_service and hasattr(self.kite_service, 'get_pre_market_data'):
                        data = await self.kite_service.get_pre_market_data(stock["symbol"])
                    else:
                        data = {"last_price": 0, "change": 0, "volume": 0}

                    if stock.get("symbol"):
                        pre_market_data.append({
                            "symbol": stock["symbol"],
                            "price": data.get("last_price", 0),
                            "change": data.get("change", 0),
                            "volume": data.get("volume", 0),
                            "risk_score": stock.get("risk_score", 0.5)
                        })
                except Exception as e:
                    self._log_warning(
                        f"Failed to get pre-market data for {stock.get('symbol', 'unknown')}: {e}"
                    )
                    if stock.get("symbol"):
                        pre_market_data.append({
                            "symbol": stock["symbol"],
                            "price": 0,
                            "change": 0,
                            "volume": 0,
                            "risk_score": stock.get("risk_score", 0.5)
                        })

            # Sort by risk_score (lower is better), then volume, then change magnitude
            pre_market_data.sort(
                key=lambda x: (-x.get("risk_score", 0.5), x["volume"], abs(x["change"])),
                reverse=True
            )

            return pre_market_data[:10]

        except Exception as e:
            self._log_error(f"Pre-market scan failed: {e}")
            return []

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("MorningPremarketCoordinator cleanup complete")

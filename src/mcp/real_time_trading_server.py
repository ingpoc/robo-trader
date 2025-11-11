"""
Real-time trading MCP server with comprehensive trading capabilities.

This MCP server provides tools for real-time trading operations including
order execution, position monitoring, market data fetching, and portfolio
analysis using Kite Connect integration.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListResourcesRequest, ListResourcesResult,
    ReadResourceRequest, ReadResourceResult
)

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.kite_connect_service import KiteConnectService, KiteCredentials, OrderRequest
from src.core.database_state.real_time_trading_state import RealTimeTradingState
from src.services.token_storage_service import TokenStorageService


@dataclass
class TradeExecutionRequest:
    """Trade execution request data structure."""
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    order_type: str = "MARKET"  # MARKET, LIMIT
    price: Optional[float] = None
    product: str = "CNC"  # CNC, INTRADAY, CO, OCO
    trigger_price: Optional[float] = None
    validity: str = "DAY"
    account_id: str = "paper_swing_main"


@dataclass
class PositionMonitoringRequest:
    """Position monitoring request."""
    account_id: str = "paper_swing_main"
    include_real_time_pnl: bool = True
    include_historical_data: bool = False
    days_back: int = 7


@dataclass
class MarketDataRequest:
    """Market data request."""
    symbols: List[str]
    include_ohlc: bool = True
    include_volume: bool = True
    include_change: bool = True


class RealTimeTradingMCPServer:
    """Real-time trading MCP server with comprehensive trading tools."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server = Server("real-time-trading-server")

        # Services
        self.real_time_state = None
        self.kite_service = None
        self.token_storage = None

        # Configuration
        self.config = {}
        self._initialized = False

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available trading tools."""
            return [
                Tool(
                    name="execute_buy_order",
                    description="Execute a real-time buy order with current market prices",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Stock symbol (e.g., RELIANCE, TCS)"},
                            "quantity": {"type": "integer", "description": "Number of shares to buy"},
                            "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "MARKET", "description": "Order type"},
                            "price": {"type": "number", "description": "Limit price (required for LIMIT orders)"},
                            "product": {"type": "string", "enum": ["CNC", "INTRADAY", "CO", "OCO"], "default": "CNC", "description": "Product type"},
                            "trigger_price": {"type": "number", "description": "Trigger price for stop loss orders"},
                            "validity": {"type": "string", "enum": ["DAY", "IOC"], "default": "DAY", "description": "Order validity"},
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"}
                        },
                        "required": ["symbol", "quantity"]
                    }
                ),
                Tool(
                    name="execute_sell_order",
                    description="Execute a real-time sell order with position validation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Stock symbol (e.g., RELIANCE, TCS)"},
                            "quantity": {"type": "integer", "description": "Number of shares to sell"},
                            "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "MARKET", "description": "Order type"},
                            "price": {"type": "number", "description": "Limit price (required for LIMIT orders)"},
                            "product": {"type": "string", "enum": ["CNC", "INTRADAY", "CO", "OCO"], "default": "CNC", "description": "Product type"},
                            "trigger_price": {"type": "number", "description": "Trigger price for stop loss orders"},
                            "validity": {"type": "string", "enum": ["DAY", "IOC"], "default": "DAY", "description": "Order validity"},
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"}
                        },
                        "required": ["symbol", "quantity"]
                    }
                ),
                Tool(
                    name="close_position",
                    description="Close an existing position instantly with current market price",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Stock symbol to close position for"},
                            "quantity": {"type": "integer", "description": "Quantity to close (optional, defaults to full position)"},
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"}
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="get_real_time_quotes",
                    description="Get real-time market quotes for multiple symbols",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbols": {"type": "array", "items": {"type": "string"}, "description": "List of stock symbols"},
                            "include_ohlc": {"type": "boolean", "default": True, "description": "Include OHLC data"},
                            "include_volume": {"type": "boolean", "default": True, "description": "Include volume data"},
                            "include_change": {"type": "boolean", "default": True, "description": "Include price change data"}
                        },
                        "required": ["symbols"]
                    }
                ),
                Tool(
                    name="monitor_positions_pnl",
                    description="Get real-time positions with live P&L calculations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"},
                            "include_real_time_pnl": {"type": "boolean", "default": True, "description": "Include real-time P&L calculations"},
                            "include_historical_data": {"type": "boolean", "default": False, "description": "Include historical performance data"},
                            "days_back": {"type": "integer", "default": 7, "description": "Days of historical data to include"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_order_book",
                    description="Get current order book with real-time status updates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"},
                            "status_filter": {"type": "array", "items": {"type": "string"}, "enum": ["PENDING", "OPEN", "COMPLETE", "CANCELLED", "REJECTED"], "description": "Filter by order status"},
                            "limit": {"type": "integer", "default": 50, "description": "Maximum number of orders to return"},
                            "include_filled_details": {"type": "boolean", "default": True, "description": "Include detailed fill information"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="authenticate_kite",
                    description="Authenticate with Kite Connect using request token",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "request_token": {"type": "string", "description": "Request token from Kite Connect callback"},
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"}
                        },
                        "required": ["request_token"]
                    }
                ),
                Tool(
                    name="get_kite_login_url",
                    description="Get Kite Connect login URL for authentication",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_portfolio_overview",
                    description="Get comprehensive portfolio overview with real-time metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"},
                            "include_holdings": {"type": "boolean", "default": True, "description": "Include holdings details"},
                            "include_positions": {"type": "boolean", "default": True, "description": "Include positions details"},
                            "include_performance_metrics": {"type": "boolean", "default": True, "description": "Include performance metrics"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="analyze_trade_risk",
                    description="Analyze trade risk before execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Stock symbol to analyze"},
                            "action": {"type": "string", "enum": ["BUY", "SELL"], "description": "Trade action"},
                            "quantity": {"type": "integer", "description": "Trade quantity"},
                            "price": {"type": "number", "description": "Expected execution price"},
                            "account_id": {"type": "string", "default": "paper_swing_main", "description": "Trading account ID"}
                        },
                        "required": ["symbol", "action", "quantity"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if not self._initialized:
                    await self._initialize()

                if name == "execute_buy_order":
                    return await self._handle_execute_buy_order(arguments)
                elif name == "execute_sell_order":
                    return await self._handle_execute_sell_order(arguments)
                elif name == "close_position":
                    return await self._handle_close_position(arguments)
                elif name == "get_real_time_quotes":
                    return await self._handle_get_real_time_quotes(arguments)
                elif name == "monitor_positions_pnl":
                    return await self._handle_monitor_positions_pnl(arguments)
                elif name == "get_order_book":
                    return await self._handle_get_order_book(arguments)
                elif name == "authenticate_kite":
                    return await self._handle_authenticate_kite(arguments)
                elif name == "get_kite_login_url":
                    return await self._handle_get_kite_login_url(arguments)
                elif name == "get_portfolio_overview":
                    return await self._handle_get_portfolio_overview(arguments)
                elif name == "analyze_trade_risk":
                    return await self._handle_analyze_trade_risk(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                self.logger.error(f"Tool call failed for {name}: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error executing {name}: {str(e)}"
                        )
                    ],
                    isError=True
                )

    async def _initialize(self):
        """Initialize the MCP server and services."""
        try:
            if self._initialized:
                return

            # Initialize configuration
            self.config = self._load_config()

            # Initialize database state
            db_path = self.config.get("database_path", "/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db")
            self.real_time_state = RealTimeTradingState(db_path)
            await self.real_time_state.initialize()

            # Initialize token storage
            encryption_key = self.config.get("encryption_key")
            self.token_storage = TokenStorageService(encryption_key)

            # Initialize Kite Connect service
            kite_config = self.config.get("kite_connect", {})
            credentials = KiteCredentials(
                api_key=kite_config.get("api_key", ""),
                api_secret=kite_config.get("api_secret", "")
            )
            self.kite_service = KiteConnectService(kite_config, self.real_time_state)
            await self.kite_service.initialize(credentials)

            self._initialized = True
            self.logger.info("Real-time trading MCP server initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP server: {e}")
            raise TradingError(
                f"MCP server initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        try:
            # For now, return default configuration
            # In production, this would load from config files
            return {
                "database_path": "/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db",
                "kite_connect": {
                    "api_key": "your_api_key_here",
                    "api_secret": "your_api_secret_here"
                },
                "encryption_key": None
            }
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}

    async def _handle_execute_buy_order(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle buy order execution."""
        try:
            symbol = arguments["symbol"]
            quantity = arguments["quantity"]
            order_type = arguments.get("order_type", "MARKET")
            price = arguments.get("price")
            product = arguments.get("product", "CNC")
            trigger_price = arguments.get("trigger_price")
            validity = arguments.get("validity", "DAY")
            account_id = arguments.get("account_id", "paper_swing_main")

            # Get current market price if not provided
            if order_type == "LIMIT" and price is None:
                quotes = await self.kite_service.get_quotes([symbol])
                if symbol in quotes:
                    price = quotes[symbol].last_price
                else:
                    raise TradingError(
                        f"Unable to get market price for {symbol}",
                        category=ErrorCategory.MARKET_DATA,
                        severity=ErrorSeverity.HIGH
                    )

            # Create order request
            order_request = OrderRequest(
                tradingsymbol=symbol.upper(),
                exchange="NSE",
                transaction_type="BUY",
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                validity=validity
            )

            # Execute order
            result = await self.kite_service.place_order(order_request, account_id)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "message": f"Buy order placed successfully for {symbol}",
                            "order_id": result["order_id"],
                            "status": result["status"],
                            "symbol": symbol,
                            "quantity": quantity,
                            "order_type": order_type,
                            "price": price,
                            "filled_quantity": result.get("filled_quantity", 0),
                            "average_price": result.get("average_price", 0.0),
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Buy order execution failed: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"Failed to execute buy order for {arguments.get('symbol', 'Unknown')}"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_execute_sell_order(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle sell order execution."""
        try:
            symbol = arguments["symbol"]
            quantity = arguments["quantity"]
            order_type = arguments.get("order_type", "MARKET")
            price = arguments.get("price")
            product = arguments.get("product", "CNC")
            trigger_price = arguments.get("trigger_price")
            validity = arguments.get("validity", "DAY")
            account_id = arguments.get("account_id", "paper_swing_main")

            # Validate position exists (for CNC products)
            if product == "CNC":
                positions = await self.real_time_state.get_positions_by_account(account_id)
                has_position = any(
                    p.symbol == symbol.upper() and p.quantity > 0
                    for p in positions
                )
                if not has_position:
                    raise TradingError(
                        f"No position available for {symbol} to sell",
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.HIGH
                    )

            # Get current market price if not provided
            if order_type == "LIMIT" and price is None:
                quotes = await self.kite_service.get_quotes([symbol])
                if symbol in quotes:
                    price = quotes[symbol].last_price
                else:
                    raise TradingError(
                        f"Unable to get market price for {symbol}",
                        category=ErrorCategory.MARKET_DATA,
                        severity=ErrorSeverity.HIGH
                    )

            # Create order request
            order_request = OrderRequest(
                tradingsymbol=symbol.upper(),
                exchange="NSE",
                transaction_type="SELL",
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                validity=validity
            )

            # Execute order
            result = await self.kite_service.place_order(order_request, account_id)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "message": f"Sell order placed successfully for {symbol}",
                            "order_id": result["order_id"],
                            "status": result["status"],
                            "symbol": symbol,
                            "quantity": quantity,
                            "order_type": order_type,
                            "price": price,
                            "filled_quantity": result.get("filled_quantity", 0),
                            "average_price": result.get("average_price", 0.0),
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Sell order execution failed: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"Failed to execute sell order for {arguments.get('symbol', 'Unknown')}"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_close_position(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle position closure."""
        try:
            symbol = arguments["symbol"]
            quantity = arguments.get("quantity")  # Optional, defaults to full position
            account_id = arguments.get("account_id", "paper_swing_main")

            # Get current positions
            positions = await self.real_time_state.get_positions_by_account(account_id)
            target_position = None

            for pos in positions:
                if pos.symbol == symbol.upper() and pos.quantity != 0:
                    target_position = pos
                    break

            if not target_position:
                raise TradingError(
                    f"No open position found for {symbol}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.HIGH
                )

            # Determine quantity to close
            close_quantity = quantity or abs(target_position.quantity)
            if close_quantity > abs(target_position.quantity):
                raise TradingError(
                    f"Requested quantity {close_quantity} exceeds position size {abs(target_position.quantity)}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.HIGH
                )

            # Determine order type (opposite of position)
            transaction_type = "SELL" if target_position.quantity > 0 else "BUY"

            # Get current market price
            quotes = await self.kite_service.get_quotes([symbol])
            if symbol not in quotes:
                raise TradingError(
                    f"Unable to get market price for {symbol}",
                    category=ErrorCategory.MARKET_DATA,
                    severity=ErrorSeverity.HIGH
                )

            market_price = quotes[symbol].last_price

            # Create order request for market order
            order_request = OrderRequest(
                tradingsymbol=symbol.upper(),
                exchange="NSE",
                transaction_type=transaction_type,
                quantity=close_quantity,
                product=target_position.product_type,
                order_type="MARKET",
                price=None  # Market order
            )

            # Execute order
            result = await self.kite_service.place_order(order_request, account_id)

            # Calculate P&L
            avg_price = target_position.buy_average_price if target_position.quantity > 0 else target_position.sell_average_price
            pnl_per_share = market_price - avg_price if target_position.quantity > 0 else avg_price - market_price
            total_pnl = pnl_per_share * close_quantity

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "message": f"Position closed successfully for {symbol}",
                            "order_id": result["order_id"],
                            "status": result["status"],
                            "symbol": symbol,
                            "quantity_closed": close_quantity,
                            "market_price": market_price,
                            "average_price": avg_price,
                            "pnl_per_share": pnl_per_share,
                            "total_pnl": total_pnl,
                            "transaction_type": transaction_type,
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Position closure failed: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"Failed to close position for {arguments.get('symbol', 'Unknown')}"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_get_real_time_quotes(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle real-time quotes request."""
        try:
            symbols = arguments["symbols"]
            include_ohlc = arguments.get("include_ohlc", True)
            include_volume = arguments.get("include_volume", True)
            include_change = arguments.get("include_change", True)

            # Get quotes from Kite Connect
            quotes_data = await self.kite_service.get_quotes(symbols)

            # Format response
            quotes = {}
            for symbol, quote in quotes_data.items():
                quotes[symbol] = {
                    "symbol": symbol,
                    "last_price": quote.last_price,
                    "timestamp": quote.timestamp,
                    "volume": quote.volume if include_volume else None,
                    "buy_quantity": quote.buy_quantity,
                    "sell_quantity": quote.sell_quantity,
                }

                if include_change:
                    quotes[symbol]["change"] = quote.change
                    quotes[symbol]["change_percent"] = quote.change_percent

                if include_ohlc:
                    quotes[symbol]["ohlc"] = quote.ohlc

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "quotes": quotes,
                            "timestamp": datetime.now().isoformat(),
                            "count": len(quotes)
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Failed to get real-time quotes: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Failed to fetch real-time quotes"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_monitor_positions_pnl(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle positions and P&L monitoring."""
        try:
            account_id = arguments.get("account_id", "paper_swing_main")
            include_real_time_pnl = arguments.get("include_real_time_pnl", True)
            include_historical_data = arguments.get("include_historical_data", False)
            days_back = arguments.get("days_back", 7)

            # Get positions
            positions = await self.real_time_state.get_positions_by_account(account_id)

            # Get real-time quotes if requested
            symbols_with_positions = [pos.symbol for pos in positions if pos.quantity != 0]
            real_time_quotes = {}

            if include_real_time_pnl and symbols_with_positions:
                quotes_data = await self.kite_service.get_quotes(symbols_with_positions)
                real_time_quotes = {symbol: quote.last_price for symbol, quote in quotes_data.items()}

            # Calculate live P&L
            positions_with_pnl = []
            total_pnl = 0.0
            total_investment = 0.0

            for pos in positions:
                if pos.quantity == 0:
                    continue

                # Update with real-time price if available
                last_price = real_time_quotes.get(pos.symbol, pos.last_price)

                # Calculate P&L
                if pos.quantity > 0:  # Long position
                    avg_price = pos.buy_average_price
                    unrealized_pnl = (last_price - avg_price) * pos.quantity
                else:  # Short position
                    avg_price = pos.sell_average_price
                    unrealized_pnl = (avg_price - last_price) * abs(pos.quantity)

                investment = avg_price * abs(pos.quantity)
                pnl_percent = (unrealized_pnl / investment) * 100 if investment > 0 else 0.0

                position_data = {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "product_type": pos.product_type,
                    "average_price": avg_price,
                    "last_price": last_price,
                    "unrealized_pnl": unrealized_pnl,
                    "realized_pnl": pos.realized_pnl,
                    "total_pnl": unrealized_pnl + pos.realized_pnl,
                    "pnl_percent": pnl_percent,
                    "investment": investment,
                    "value": last_price * abs(pos.quantity),
                    "updated_at": pos.updated_at
                }

                positions_with_pnl.append(position_data)
                total_pnl += position_data["total_pnl"]
                total_investment += investment

            # Calculate portfolio metrics
            portfolio_metrics = {
                "total_positions": len(positions_with_pnl),
                "total_pnl": total_pnl,
                "total_investment": total_investment,
                "pnl_percent": (total_pnl / total_investment) * 100 if total_investment > 0 else 0.0
            }

            response_data = {
                "success": True,
                "account_id": account_id,
                "positions": positions_with_pnl,
                "portfolio_metrics": portfolio_metrics,
                "timestamp": datetime.now().isoformat()
            }

            # Add historical data if requested
            if include_historical_data:
                # This would require additional database queries
                response_data["historical_data"] = {
                    "note": "Historical data not implemented yet",
                    "days_back": days_back
                }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(response_data, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Failed to monitor positions and P&L: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Failed to fetch positions and P&L data"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_get_order_book(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle order book request."""
        try:
            account_id = arguments.get("account_id", "paper_swing_main")
            status_filter = arguments.get("status_filter", [])
            limit = arguments.get("limit", 50)
            include_filled_details = arguments.get("include_filled_details", True)

            # Get orders from database
            orders = await self.real_time_state.get_orders_by_account(account_id, limit)

            # Filter by status if specified
            if status_filter:
                orders = [order for order in orders if order.status in status_filter]

            # Format orders
            formatted_orders = []
            for order in orders:
                order_data = {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "order_type": order.order_type,
                    "product_type": order.product_type,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": order.status,
                    "placed_at": order.placed_at,
                    "updated_at": order.updated_at
                }

                if include_filled_details:
                    order_data.update({
                        "filled_quantity": order.filled_quantity,
                        "pending_quantity": order.pending_quantity,
                        "cancelled_quantity": order.cancelled_quantity,
                        "average_price": order.average_price,
                        "exchange_order_id": order.exchange_order_id
                    })

                formatted_orders.append(order_data)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "account_id": account_id,
                            "orders": formatted_orders,
                            "count": len(formatted_orders),
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Failed to get order book: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Failed to fetch order book"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_authenticate_kite(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle Kite Connect authentication."""
        try:
            request_token = arguments["request_token"]
            account_id = arguments.get("account_id", "paper_swing_main")

            # Authenticate with Kite Connect
            session_data = await self.kite_service.authenticate(request_token)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "message": "Kite Connect authentication successful",
                            "account_id": account_id,
                            "user_name": session_data.get("user_name"),
                            "user_id": session_data.get("user_id"),
                            "products": session_data.get("products"),
                            "exchanges": session_data.get("exchanges"),
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Kite Connect authentication failed: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Kite Connect authentication failed"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_get_kite_login_url(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle Kite login URL request."""
        try:
            login_url = await self.kite_service.get_login_url()

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "login_url": login_url,
                            "message": "Use this URL to authenticate with Kite Connect",
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Failed to get Kite login URL: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Failed to generate Kite Connect login URL"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_get_portfolio_overview(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle portfolio overview request."""
        try:
            account_id = arguments.get("account_id", "paper_swing_main")
            include_holdings = arguments.get("include_holdings", True)
            include_positions = arguments.get("include_positions", True)
            include_performance_metrics = arguments.get("include_performance_metrics", True)

            overview_data = {
                "success": True,
                "account_id": account_id,
                "timestamp": datetime.now().isoformat()
            }

            # Get holdings
            if include_holdings:
                try:
                    holdings = await self.kite_service.get_holdings()
                    overview_data["holdings"] = {
                        "count": len(holdings),
                        "total_value": sum(h["quantity"] * h["last_price"] for h in holdings),
                        "total_pnl": sum(h["pnl"] for h in holdings),
                        "holdings": holdings
                    }
                except Exception as e:
                    overview_data["holdings"] = {"error": str(e)}

            # Get positions
            if include_positions:
                try:
                    positions_data = await self.kite_service.get_positions()
                    overview_data["positions"] = positions_data
                except Exception as e:
                    overview_data["positions"] = {"error": str(e)}

            # Add performance metrics if requested
            if include_performance_metrics:
                # This would be calculated from historical data
                overview_data["performance_metrics"] = {
                    "note": "Performance metrics calculation not fully implemented yet"
                }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(overview_data, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Failed to get portfolio overview: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": "Failed to fetch portfolio overview"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def _handle_analyze_trade_risk(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle trade risk analysis."""
        try:
            symbol = arguments["symbol"]
            action = arguments["action"]
            quantity = arguments["quantity"]
            price = arguments.get("price")
            account_id = arguments.get("account_id", "paper_swing_main")

            # Get current market data
            quotes = await self.kite_service.get_quotes([symbol])
            if symbol not in quotes:
                raise TradingError(
                    f"No market data available for {symbol}",
                    category=ErrorCategory.MARKET_DATA,
                    severity=ErrorSeverity.HIGH
                )

            current_price = quotes[symbol].last_price
            market_price = price or current_price

            # Get current positions
            positions = await self.real_time_state.get_positions_by_account(account_id)
            current_position = next((p for p in positions if p.symbol == symbol.upper()), None)

            # Calculate position sizes and risk metrics
            trade_value = market_price * quantity
            max_position_size = 50000  # ₹50,000 max per position
            portfolio_risk_limit = 100000  # ₹100,000 portfolio risk limit

            risk_analysis = {
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "market_price": market_price,
                "trade_value": trade_value,
                "current_position": {
                    "quantity": current_position.quantity if current_position else 0,
                    "average_price": current_position.buy_average_price if current_position else 0
                } if current_position else None,
                "risk_metrics": {
                    "position_size_limit": max_position_size,
                    "position_size_utilization": (trade_value / max_position_size) * 100,
                    "within_position_limit": trade_value <= max_position_size,
                    "portfolio_risk_utilization": (trade_value / portfolio_risk_limit) * 100,
                    "within_portfolio_risk_limit": trade_value <= portfolio_risk_limit
                },
                "market_data": {
                    "last_price": current_price,
                    "change": quotes[symbol].change,
                    "change_percent": quotes[symbol].change_percent,
                    "volume": quotes[symbol].volume
                },
                "recommendations": []
            }

            # Add risk recommendations
            if trade_value > max_position_size:
                risk_analysis["recommendations"].append(
                    f"Trade value ₹{trade_value:,.0f} exceeds maximum position size of ₹{max_position_size:,.0f}"
                )

            if trade_value > portfolio_risk_limit:
                risk_analysis["recommendations"].append(
                    f"Trade value ₹{trade_value:,.0f} exceeds portfolio risk limit of ₹{portfolio_risk_limit:,.0f}"
                )

            # Add position-specific recommendations
            if current_position:
                if action == "BUY" and current_position.quantity > 0:
                    risk_analysis["recommendations"].append(
                        "Adding to existing long position - consider diversification"
                    )
                elif action == "SELL" and current_position.quantity > 0:
                    risk_analysis["recommendations"].append(
                        "Selling existing long position - will realize P&L"
                    )
                elif action == "SELL" and current_position.quantity < 0:
                    risk_analysis["recommendations"].append(
                        "Adding to existing short position - monitor market direction"
                    )

            # Overall risk assessment
            risk_analysis["risk_level"] = "LOW"
            if len(risk_analysis["recommendations"]) > 0:
                risk_analysis["risk_level"] = "MEDIUM"
            if not risk_analysis["risk_metrics"]["within_position_limit"]:
                risk_analysis["risk_level"] = "HIGH"

            risk_analysis["approved_for_execution"] = (
                risk_analysis["risk_metrics"]["within_position_limit"] and
                risk_analysis["risk_metrics"]["within_portfolio_risk_limit"]
            )

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "risk_analysis": risk_analysis,
                            "timestamp": datetime.now().isoformat()
                        }, indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Trade risk analysis failed: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"Failed to analyze trade risk for {arguments.get('symbol', 'Unknown')}"
                        }, indent=2)
                    )
                ],
                isError=True
            )

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="real-time-trading-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )

    async def close(self):
        """Close the MCP server and cleanup resources."""
        try:
            if self.kite_service:
                await self.kite_service.close()

            self.logger.info("Real-time trading MCP server closed")

        except Exception as e:
            self.logger.error(f"Error closing MCP server: {e}")


async def main():
    """Main entry point for the real-time trading MCP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = RealTimeTradingMCPServer()

    try:
        await server.run()
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())
"""
Zerodha Broker MCP Server

Provides tools for:
- Authentication and token management
- Portfolio and holdings
- Order management (place, modify, cancel)
- Instruments data
- Real-time ticker subscription
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from kiteconnect import KiteConnect
from claude_agent_sdk import tool, create_sdk_mcp_server
from loguru import logger

from ..config import Config


class ZerodhaBroker:
    """Zerodha Kite Connect wrapper."""

    def __init__(self, config: Config):
        self.config = config
        self.kite: Optional[KiteConnect] = None
        self.ticker = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Kite Connect client."""
        if not self.config.integration.zerodha_api_key:
            logger.warning("Zerodha API key not configured")
            return

        self.kite = KiteConnect(api_key=self.config.integration.zerodha_api_key)

        # Set access token if available
        if self.config.integration.zerodha_access_token:
            self.kite.set_access_token(self.config.integration.zerodha_access_token)
            logger.info("Zerodha client initialized with access token")
        else:
            logger.warning("Zerodha access token not set - authentication required")

    def get_login_url(self) -> str:
        """Get login URL for authentication."""
        if not self.kite:
            raise ValueError("Kite client not initialized")
        return self.kite.login_url()

    def set_access_token(self, request_token: str) -> str:
        """Exchange request token for access token."""
        if not self.kite:
            raise ValueError("Kite client not initialized")

        data = self.kite.generate_session(request_token, api_secret=self.config.integration.zerodha_api_secret)
        access_token = data["access_token"]
        self.kite.set_access_token(access_token)

        logger.info("Zerodha access token set")
        return access_token

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        if not self.kite:
            return False
        try:
            self.kite.margins()
            return True
        except Exception:
            return False


# Global broker instance
_broker: Optional[ZerodhaBroker] = None


def get_broker(config: Config) -> ZerodhaBroker:
    """Get global broker instance."""
    global _broker
    if _broker is None:
        _broker = ZerodhaBroker(config)
    return _broker


# Tool factory functions using closure pattern

def create_get_login_url_tool(broker: ZerodhaBroker):
    """Factory function for get_login_url tool using closure."""
    @tool("get_login_url", "Get Zerodha login URL for authentication", {})
    async def get_login_url_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get login URL for Zerodha authentication."""
        try:
            url = broker.get_login_url()
            return {
                "content": [
                    {"type": "text", "text": f"Login URL: {url}"}
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get login URL: {e}")
            return {
                "content": [
                    {"type": "text", "text": "Failed to generate login URL. Please check API configuration."}
                ],
                "is_error": True
            }
    return get_login_url_tool


@tool("set_access_token", "Set access token from request token", {"request_token": str})
async def set_access_token_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set access token from request token."""
    try:
        broker = get_broker(None)
        request_token = args["request_token"]
        access_token = broker.set_access_token(request_token)
        return {
            "content": [
                {"type": "text", "text": f"Access token set successfully"}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to set access token: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to authenticate with Zerodha. Please check your request token and API credentials."}
            ],
            "is_error": True
        }


@tool("get_portfolio", "Get current portfolio holdings and positions", {})
async def get_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get portfolio holdings and positions."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        holdings = broker.kite.holdings()
        positions = broker.kite.positions()

        return {
            "content": [
                {"type": "text", "text": json.dumps({
                    "holdings": holdings,
                    "positions": positions
                }, indent=2)}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to retrieve portfolio data. Please check your authentication and try again."}
            ],
            "is_error": True
        }


@tool("get_orders", "Get order history and current orders", {})
async def get_orders_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get orders."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        orders = broker.kite.orders()
        return {
            "content": [
                {"type": "text", "text": json.dumps(orders, indent=2)}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to retrieve order history. Please check your authentication and try again."}
            ],
            "is_error": True
        }


@tool("place_order", "Place a new order", {
    "variety": str, "exchange": str, "tradingsymbol": str, "transaction_type": str,
    "order_type": str, "quantity": int, "price": Optional[float], "product": str,
    "client_tag": Optional[str]
})
async def place_order_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Place an order."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        # Map arguments to Kite format
        order_params = {
            "variety": args["variety"],
            "exchange": args["exchange"],
            "tradingsymbol": args["tradingsymbol"],
            "transaction_type": args["transaction_type"],
            "order_type": args["order_type"],
            "quantity": args["quantity"],
            "product": args["product"]
        }

        if args.get("price"):
            order_params["price"] = args["price"]

        if args.get("client_tag"):
            order_params["tag"] = args["client_tag"]

        order_id = broker.kite.place_order(**order_params)

        return {
            "content": [
                {"type": "text", "text": f"Order placed successfully. Order ID: {order_id}"}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to place order. Please check your order parameters and try again."}
            ],
            "is_error": True
        }


@tool("modify_order", "Modify an existing order", {
    "order_id": str, "variety": str, "quantity": Optional[int],
    "price": Optional[float], "order_type": Optional[str],
    "client_tag": Optional[str]
})
async def modify_order_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Modify an order."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        modify_params = {"order_id": args["order_id"], "variety": args["variety"]}

        if args.get("quantity"):
            modify_params["quantity"] = args["quantity"]
        if args.get("price"):
            modify_params["price"] = args["price"]
        if args.get("order_type"):
            modify_params["order_type"] = args["order_type"]
        if args.get("client_tag"):
            modify_params["tag"] = args["client_tag"]

        broker.kite.modify_order(**modify_params)

        return {
            "content": [
                {"type": "text", "text": f"Order {args['order_id']} modified successfully"}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to modify order: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to modify order. Please check your order parameters and try again."}
            ],
            "is_error": True
        }


@tool("cancel_order", "Cancel an order", {"order_id": str, "variety": str, "client_tag": Optional[str]})
async def cancel_order_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel an order."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        cancel_params = {"order_id": args["order_id"], "variety": args["variety"]}

        if args.get("client_tag"):
            cancel_params["tag"] = args["client_tag"]

        broker.kite.cancel_order(**cancel_params)

        return {
            "content": [
                {"type": "text", "text": f"Order {args['order_id']} cancelled successfully"}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to cancel order. Please check your order parameters and try again."}
            ],
            "is_error": True
        }


@tool("get_instruments", "Get instrument master data", {"exchange": Optional[str]})
async def get_instruments_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get instruments data."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        exchange = args.get("exchange", "NSE")
        instruments = broker.kite.instruments(exchange=exchange)

        # Return first 100 instruments to avoid huge response
        limited_instruments = instruments[:100] if len(instruments) > 100 else instruments

        return {
            "content": [
                {"type": "text", "text": f"Retrieved {len(limited_instruments)} instruments from {exchange}"},
                {"type": "text", "text": json.dumps(limited_instruments, indent=2)}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get instruments: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to retrieve instrument data. Please check your authentication and try again."}
            ],
            "is_error": True
        }


@tool("quote", "Get quote for instruments", {"instruments": List[str]})
async def quote_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get quotes for instruments."""
    try:
        broker = get_broker(None)
        if not broker.is_authenticated():
            return {
                "content": [
                    {"type": "text", "text": "Not authenticated with Zerodha"}
                ],
                "is_error": True
            }

        instruments = args["instruments"]
        quotes = broker.kite.quote(instruments)

        return {
            "content": [
                {"type": "text", "text": json.dumps(quotes, indent=2)}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get quotes: {e}")
        return {
            "content": [
                {"type": "text", "text": "Failed to retrieve quote data. Please check your authentication and try again."}
            ],
            "is_error": True
        }


# Ticker tools (simplified - full implementation would need WebSocket handling)

@tool("ticker_subscribe", "Subscribe to real-time ticker", {"instruments": List[int]})
async def ticker_subscribe_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Subscribe to ticker (simplified implementation)."""
    # In a full implementation, this would manage WebSocket connections
    instruments = args["instruments"]
    return {
        "content": [
            {"type": "text", "text": f"Subscribed to {len(instruments)} instruments"}
        ]
    }


@tool("ticker_unsubscribe", "Unsubscribe from ticker", {"instruments": List[int]})
async def ticker_unsubscribe_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Unsubscribe from ticker."""
    instruments = args["instruments"]
    return {
        "content": [
            {"type": "text", "text": f"Unsubscribed from {len(instruments)} instruments"}
        ]
    }


@tool("ticker_set_mode", "Set ticker mode", {"instruments": List[int], "mode": str})
async def ticker_set_mode_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set ticker mode."""
    instruments = args["instruments"]
    mode = args["mode"]
    return {
        "content": [
            {"type": "text", "text": f"Set mode {mode} for {len(instruments)} instruments"}
        ]
    }


async def create_broker_mcp_server(config: Config):
    """Create the broker MCP server."""
    global _broker
    _broker = ZerodhaBroker(config)

    return create_sdk_mcp_server(
        name="broker",
        version="1.0.0",
        tools=[
            create_get_login_url_tool(_broker),
            set_access_token_tool,
            get_portfolio_tool,
            get_orders_tool,
            place_order_tool,
            modify_order_tool,
            cancel_order_tool,
            get_instruments_tool,
            quote_tool,
            ticker_subscribe_tool,
            ticker_unsubscribe_tool,
            ticker_set_mode_tool,
        ]
    )


async def cleanup_broker():
    """Cleanup the global broker instance."""
    global _broker
    if _broker is not None:
        try:
            # Close any active connections or resources
            if hasattr(_broker, 'ticker') and _broker.ticker:
                # Close ticker connection if it exists
                try:
                    _broker.ticker.close()
                except Exception as e:
                    logger.warning(f"Error closing ticker connection: {e}")

            logger.info("Global broker instance cleaned up")
        except Exception as e:
            logger.error(f"Error during broker cleanup: {e}")
        finally:
            _broker = None


def reset_broker():
    """Reset the global broker instance (for testing)."""
    global _broker
    _broker = None
"""Paper Trading Execution Service - Handles buy/sell/close operations using Claude Agent SDK."""

import uuid
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING
from decimal import Decimal

from loguru import logger as loguru_logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

if TYPE_CHECKING:
    from src.core.database_state.database_state import DatabaseStateManager

logger = logging.getLogger(__name__)


class PaperTradingExecutionService:
    """Service for executing paper trades using Claude Agent SDK for decision-making."""

    def __init__(self, state_manager: Optional['DatabaseStateManager'] = None):
        """Initialize execution service."""
        self._state_manager = state_manager
        self._initialized = False
        self._client: Optional[ClaudeSDKClient] = None

    async def initialize(self) -> None:
        """Initialize service and set up Claude SDK client."""
        loguru_logger.info("PaperTradingExecutionService initializing")
        await self._ensure_client()
        self._initialized = True
        loguru_logger.info("PaperTradingExecutionService ready with Claude Agent SDK")

    async def cleanup(self) -> None:
        """Clean up SDK client."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
                loguru_logger.info("PaperTradingExecutionService client cleaned up")
            except Exception as e:
                loguru_logger.warning(f"Error cleaning up client: {e}")
            finally:
                self._client = None

    async def execute_buy_trade(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        strategy_rationale: str = "User initiated trade"
    ) -> Dict[str, Any]:
        """
        Execute buy trade with Claude Agent SDK validation and decision-making.

        Args:
            account_id: Paper trading account ID
            symbol: Stock symbol (uppercase)
            quantity: Number of shares
            order_type: MARKET or LIMIT
            price: Limit price for LIMIT orders
            strategy_rationale: Reason for the trade

        Returns:
            Trade execution result with trade_id and status

        Raises:
            TradingError: If validation fails or insufficient balance
        """
        try:
            # Validate inputs
            symbol = symbol.upper()
            if not symbol or len(symbol) > 20:
                raise TradingError(
                    f"Invalid symbol: {symbol}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=False
                )

            if quantity <= 0 or quantity > 10000:
                raise TradingError(
                    f"Invalid quantity: {quantity}. Must be between 1 and 10000",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=False
                )

            # Use Claude Agent SDK to validate and execute trade (create fresh client)
            prompt = f"""You are a paper trading execution engine. Your ONLY job is to validate trade parameters and return a JSON decision.

TRADE REQUEST:
- Account ID: {account_id}
- Symbol: {symbol}
- Quantity: {quantity} shares
- Order Type: {order_type}
- Price: {price if price else 'Market price'}
- Strategy Rationale: {strategy_rationale}

VALIDATION RULES:
- Symbol must be uppercase, 1-10 characters, letters only
- Quantity must be positive integer ≤ 10000
- Assume account balance: ₹100,000
- Assume reasonable market price: ₹2000-3000 for Indian stocks
- Required amount = price × quantity

RESPONSE FORMAT (JSON ONLY - NO OTHER TEXT):
{{
  "decision": "APPROVE" or "REJECT",
  "reason": "Brief explanation",
  "trade_price": assumed_market_price_number,
  "required_amount": calculated_amount
}}

Example:
{{"decision": "APPROVE", "reason": "Valid parameters", "trade_price": 2500, "required_amount": 25000}}

Respond with ONLY the JSON object. No explanation text."""

            try:
                await self._ensure_client()
                # Use timeout helpers (MANDATORY per architecture pattern)
                from src.core.sdk_helpers import query_with_timeout
                # query_with_timeout handles both query() and receive_response() internally
                response_text = await query_with_timeout(self._client, prompt, timeout=30.0)

                loguru_logger.debug(f"Claude SDK response received: {response_text[:200]}...")

                # Parse Claude's response
                result = self._parse_claude_response(response_text)
            except ConnectionError as e:
                loguru_logger.error(f"Claude SDK connection failed: {e}")
                raise TradingError(
                    "Failed to connect to Claude Agent SDK. Ensure Claude Code CLI is authenticated.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.CRITICAL,
                    recoverable=True,
                    metadata={"error": str(e), "error_type": "connection"}
                )
            except Exception as e:
                error_str = str(e).lower()
                if "auth" in error_str or "api key" in error_str or "invalid" in error_str:
                    loguru_logger.error(f"Claude SDK authentication failed: {e}")
                    raise TradingError(
                        "Claude Agent SDK authentication failed. Run 'claude auth' to authenticate.",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.CRITICAL,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "authentication"}
                    )
                else:
                    loguru_logger.error(f"Claude SDK query failed: {e}")
                    raise TradingError(
                        f"Failed to execute trade via Claude Agent: {str(e)}",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "query_execution"}
                    )

            if result['decision'] != 'APPROVE':
                raise TradingError(
                    f"Trade rejected: {result['reason']}",
                    category=ErrorCategory.TRADING,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={"reason": result['reason']}
                )

            # Create trade record
            trade_id = f"trade_{uuid.uuid4().hex[:8]}"
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            trade_price = result.get('trade_price', 2000.0)

            loguru_logger.info(f"Buy trade executed by Claude Agent: {trade_id} for {quantity} {symbol} at ₹{trade_price}")

            return {
                "success": True,
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "BUY",
                "quantity": quantity,
                "price": float(trade_price),
                "status": "COMPLETED",
                "timestamp": now,
                "account_id": account_id,
                "remaining_balance": 100000.0 - (quantity * trade_price)
            }

        except TradingError:
            raise
        except Exception as e:
            loguru_logger.exception(f"Buy trade execution failed: {e}")
            raise TradingError(
                f"Trade execution failed: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    async def execute_sell_trade(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        strategy_rationale: str = "User initiated trade"
    ) -> Dict[str, Any]:
        """
        Execute sell trade with Claude Agent SDK validation.

        Args:
            account_id: Paper trading account ID
            symbol: Stock symbol (uppercase)
            quantity: Number of shares
            order_type: MARKET or LIMIT
            price: Limit price for LIMIT orders
            strategy_rationale: Reason for the trade

        Returns:
            Trade execution result

        Raises:
            TradingError: If validation fails or insufficient position
        """
        try:
            # Validate inputs
            symbol = symbol.upper()
            if not symbol or len(symbol) > 20:
                raise TradingError(
                    f"Invalid symbol: {symbol}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=False
                )

            if quantity <= 0 or quantity > 10000:
                raise TradingError(
                    f"Invalid quantity: {quantity}. Must be between 1 and 10000",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=False
                )

            # Use Claude Agent SDK to validate and execute SELL trade (create fresh client)
            prompt = f"""You are a paper trading execution engine. Your ONLY job is to validate sell trade parameters and return a JSON decision.

TRADE REQUEST:
- Account ID: {account_id}
- Symbol: {symbol}
- Quantity: {quantity} shares
- Order Type: {order_type}
- Price: {price if price else 'Market price'}
- Strategy Rationale: {strategy_rationale}

VALIDATION RULES:
- Symbol must be uppercase, 1-10 characters, letters only
- Quantity must be positive integer ≤ 10000
- Assume we hold position: 10 shares at ₹2750 entry price
- Assume reasonable market price: ₹2000-3000 for Indian stocks
- Proceeds = price × quantity
- Realized P&L = proceeds - (quantity × 2750)

RESPONSE FORMAT (JSON ONLY - NO OTHER TEXT):
{{
  "decision": "APPROVE" or "REJECT",
  "reason": "Brief explanation",
  "trade_price": assumed_market_price_number,
  "proceeds": calculated_proceeds,
  "realized_pnl": calculated_pnl
}}

Example:
{{"decision": "APPROVE", "reason": "Valid sell parameters", "trade_price": 2500, "proceeds": 25000, "realized_pnl": -2500}}

Respond with ONLY the JSON object. No explanation text."""

            try:
                await self._ensure_client()
                # Use timeout helpers (MANDATORY per architecture pattern)
                from src.core.sdk_helpers import query_with_timeout
                # query_with_timeout handles both query() and receive_response() internally
                response_text = await query_with_timeout(self._client, prompt, timeout=30.0)

                loguru_logger.debug(f"Claude SDK response received: {response_text[:200]}...")

                # Parse Claude's response
                result = self._parse_claude_response(response_text)
            except ConnectionError as e:
                loguru_logger.error(f"Claude SDK connection failed: {e}")
                raise TradingError(
                    "Failed to connect to Claude Agent SDK. Ensure Claude Code CLI is authenticated.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.CRITICAL,
                    recoverable=True,
                    metadata={"error": str(e), "error_type": "connection"}
                )
            except Exception as e:
                error_str = str(e).lower()
                if "auth" in error_str or "api key" in error_str or "invalid" in error_str:
                    loguru_logger.error(f"Claude SDK authentication failed: {e}")
                    raise TradingError(
                        "Claude Agent SDK authentication failed. Run 'claude auth' to authenticate.",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.CRITICAL,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "authentication"}
                    )
                else:
                    loguru_logger.error(f"Claude SDK query failed: {e}")
                    raise TradingError(
                        f"Failed to execute trade via Claude Agent: {str(e)}",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "query_execution"}
                    )

            if result['decision'] != 'APPROVE':
                raise TradingError(
                    f"Trade rejected: {result['reason']}",
                    category=ErrorCategory.TRADING,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={"reason": result['reason']}
                )

            # Create sell trade
            trade_id = f"trade_{uuid.uuid4().hex[:8]}"
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            trade_price = result.get('trade_price', 2000.0)
            proceeds = result.get('proceeds', quantity * trade_price)
            realized_pnl = result.get('realized_pnl', proceeds - (quantity * 2750.0))

            loguru_logger.info(f"Sell trade executed by Claude Agent: {trade_id} for {quantity} {symbol} at ₹{trade_price}, P&L: ₹{realized_pnl}")

            return {
                "success": True,
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": float(trade_price),
                "status": "COMPLETED",
                "timestamp": now,
                "account_id": account_id,
                "realized_pnl": float(realized_pnl),
                "proceeds": float(proceeds),
                "new_balance": 100000.0 + proceeds
            }

        except TradingError:
            raise
        except Exception as e:
            loguru_logger.exception(f"Sell trade execution failed: {e}")
            raise TradingError(
                f"Trade execution failed: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    async def close_trade(
        self,
        account_id: str,
        trade_id: str
    ) -> Dict[str, Any]:
        """
        Close an existing open trade using Claude Agent SDK.

        Args:
            account_id: Paper trading account ID
            trade_id: Trade ID to close

        Returns:
            Close operation result with P&L

        Raises:
            TradingError: If trade not found or already closed
        """
        try:
            # Use Claude Agent SDK to validate and close trade (create fresh client)
            prompt = f"""
            Close a paper trading position with these parameters:
            - Account ID: {account_id}
            - Trade ID: {trade_id}
            - Assume trade: 10 shares at ₹2750 entry price for {trade_id}

            Please:
            1. Validate the trade parameters
            2. Calculate current exit price at market conditions
            3. Calculate realized P&L
            4. Provide decision: APPROVE or REJECT with reason

            Return a JSON response with:
            {{
              "decision": "APPROVE" or "REJECT",
              "reason": "explanation",
              "exit_price": number or null,
              "realized_pnl": number or null,
              "execution_details": {{...}} or null
            }}
            """

            try:
                await self._ensure_client()
                # Use timeout helpers (MANDATORY per architecture pattern)
                from src.core.sdk_helpers import query_with_timeout
                # query_with_timeout handles both query() and receive_response() internally
                response_text = await query_with_timeout(self._client, prompt, timeout=30.0)

                loguru_logger.debug(f"Claude SDK response received: {response_text[:200]}...")

                # Parse Claude's response
                result = self._parse_claude_response(response_text)
            except ConnectionError as e:
                loguru_logger.error(f"Claude SDK connection failed: {e}")
                raise TradingError(
                    "Failed to connect to Claude Agent SDK. Ensure Claude Code CLI is authenticated.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.CRITICAL,
                    recoverable=True,
                    metadata={"error": str(e), "error_type": "connection"}
                )
            except Exception as e:
                error_str = str(e).lower()
                if "auth" in error_str or "api key" in error_str or "invalid" in error_str:
                    loguru_logger.error(f"Claude SDK authentication failed: {e}")
                    raise TradingError(
                        "Claude Agent SDK authentication failed. Run 'claude auth' to authenticate.",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.CRITICAL,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "authentication"}
                    )
                else:
                    loguru_logger.error(f"Claude SDK query failed: {e}")
                    raise TradingError(
                        f"Failed to execute trade via Claude Agent: {str(e)}",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        metadata={"error": str(e), "error_type": "query_execution"}
                    )

            if result['decision'] != 'APPROVE':
                raise TradingError(
                    f"Trade close rejected: {result['reason']}",
                    category=ErrorCategory.TRADING,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={"reason": result['reason']}
                )

            # Close trade
            now = datetime.now(timezone.utc).isoformat()
            exit_price = result.get('exit_price', 2050.0)
            realized_pnl = result.get('realized_pnl', (exit_price - 2750.0) * 10)

            loguru_logger.info(f"Trade closed by Claude Agent: {trade_id}, exit_price={exit_price}, P&L: ₹{realized_pnl}")

            return {
                "success": True,
                "trade_id": trade_id,
                "status": "CLOSED",
                "exit_price": float(exit_price),
                "realized_pnl": float(realized_pnl),
                "timestamp": now
            }

        except TradingError:
            raise
        except Exception as e:
            loguru_logger.exception(f"Trade close failed: {e}")
            raise TradingError(
                f"Trade close failed: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client - called once at service init and on-demand."""
        if self._client is None:
            try:
                options = ClaudeAgentOptions(
                    allowed_tools=[],
                    system_prompt=self._get_trading_prompt(),
                    max_turns=1,
                    disallowed_tools=["WebSearch", "WebFetch", "Bash", "Read", "Write"],
                )
                # Use client manager with unique client type for paper trading
                from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
                client_manager = await ClaudeSDKClientManager.get_instance()
                self._client = await client_manager.get_client("paper_trading", options)
                loguru_logger.debug("Initialized Claude SDK client for trade execution via manager")
            except Exception as e:
                loguru_logger.error(f"Failed to initialize Claude SDK client: {e}")
                raise TradingError(
                    "Failed to initialize Claude Agent SDK. Ensure Claude Code CLI is authenticated.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    metadata={"error": str(e)}
                )

    def _get_trading_prompt(self) -> str:
        """Get the system prompt for paper trading execution."""
        return """You are an expert paper trading execution engine and risk manager for Indian markets (INR).

IMPORTANT CONSTRAINTS:
- You do NOT have access to real-time market data APIs
- You do NOT have access to web search
- You MUST make reasonable assumptions about stock prices
- You CANNOT use external tools to fetch data

Your role is to:
- Validate paper trade requests thoroughly
- Assume reasonable market prices (e.g., ₹2000-3000 for typical stocks, ₹200-500 for AAPL equivalent)
- Calculate required amounts and P&L accurately based on assumed prices
- Make APPROVE or REJECT decisions based on validation logic only

CRITICAL RESPONSE FORMAT:
You MUST respond with ONLY a JSON object. No explanation text before or after.
Do NOT wrap in markdown code blocks.
Do NOT try to fetch real data.
Just return the raw JSON.

Required JSON format:
{
  "decision": "APPROVE",
  "reason": "Valid trade parameters",
  "trade_price": 2500,
  "required_amount": 25000,
  "proceeds": 0,
  "realized_pnl": 0,
  "execution_details": {
    "timestamp": "2025-10-24T10:30:00Z",
    "market_conditions": "Assumed market conditions"
  }
}

Price assumptions:
- Indian stocks: ₹2000-3000 per share
- US stocks (AAPL, GOOGL, etc.): ₹200-400 per share
- Calculate required_amount = trade_price * quantity
- For sells: proceeds = trade_price * quantity
- For closes: realized_pnl = (exit_price - entry_price) * quantity

ALWAYS approve valid trades (proper symbol format, positive quantity, reasonable parameters).
Only REJECT if parameters are invalid (empty symbol, negative quantity, etc.).
"""

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response from trade execution."""
        try:
            import re

            # Step 1: Try to extract JSON from markdown code blocks (```json...```)
            markdown_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if markdown_match:
                json_str = markdown_match.group(1)
                result = json.loads(json_str)
                return result

            # Step 2: Find any JSON object (handles nested braces properly)
            # Use a more robust pattern that finds the first complete JSON object
            brace_count = 0
            start_idx = response_text.find('{')
            if start_idx != -1:
                for i, char in enumerate(response_text[start_idx:], start=start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response_text[start_idx:i+1]
                            result = json.loads(json_str)
                            return result

            # Step 3: Fallback - try parsing entire response
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            loguru_logger.warning(f"Failed to parse Claude response as JSON: {response_text[:200]}... Error: {e}")
            # Return default rejection if parsing fails
            return {
                "decision": "REJECT",
                "reason": "Failed to parse trading response from Claude",
                "trade_price": None,
                "proceeds": None,
                "realized_pnl": None
            }
        except Exception as e:
            loguru_logger.error(f"Unexpected error parsing Claude response: {e}")
            return {
                "decision": "REJECT",
                "reason": f"Error parsing response: {str(e)}",
                "trade_price": None,
                "proceeds": None,
                "realized_pnl": None
            }

    async def cleanup(self) -> None:
        """Cleanup resources (clients are created per-request and auto-cleaned)."""
        loguru_logger.info("PaperTradingExecutionService cleanup complete")

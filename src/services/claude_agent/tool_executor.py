"""Tool execution for Claude Agent SDK with validation and safety."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from ...core.errors import ErrorCategory, ErrorSeverity, TradingError

if TYPE_CHECKING:
    from ...core.di import DependencyContainer

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Prevent cascade failures from repeated tool execution errors."""

    def __init__(self, failure_threshold: int = 3, timeout_seconds: int = 300):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self._failures = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half_open

    def record_success(self) -> None:
        """Record successful execution."""
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failures += 1
        self._last_failure_time = datetime.utcnow()

        if self._failures >= self.failure_threshold:
            self._state = "open"
            logger.error(f"Circuit breaker opened after {self._failures} failures")

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self._state == "closed":
            return True

        if self._state == "open":
            # Check if timeout elapsed
            if self._last_failure_time and (
                datetime.utcnow() - self._last_failure_time
            ) > timedelta(seconds=self.timeout_seconds):
                self._state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False

        # half_open state - allow one attempt
        return True


class RateLimiter:
    """Prevent rate limit violations on external APIs."""

    def __init__(self, max_calls_per_minute: Dict[str, int]):
        """Initialize rate limiter."""
        self.max_calls = max_calls_per_minute
        self._call_history = defaultdict(list)

    def can_call(self, tool_name: str) -> bool:
        """Check if tool can be called."""
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        # Clean old history
        self._call_history[tool_name] = [
            ts for ts in self._call_history[tool_name] if ts > one_minute_ago
        ]

        # Check limit
        current_calls = len(self._call_history[tool_name])
        max_allowed = self.max_calls.get(tool_name, 10)

        return current_calls < max_allowed

    def record_call(self, tool_name: str) -> None:
        """Record tool call."""
        self._call_history[tool_name].append(datetime.utcnow())


class ToolExecutor:
    """Execute Claude tool calls with safety, validation, and error recovery."""

    def __init__(self, container: "DependencyContainer", config: Dict[str, Any]):
        """Initialize tool executor."""
        self.container = container
        self.config = config
        self._circuit_breakers = {
            "execute_trade": CircuitBreaker(failure_threshold=3, timeout_seconds=300),
            "close_position": CircuitBreaker(failure_threshold=3, timeout_seconds=300),
            "check_balance": CircuitBreaker(failure_threshold=5, timeout_seconds=60),
        }
        self._rate_limiter = RateLimiter(
            {
                "execute_trade": 5,  # Max 5 trades per minute
                "close_position": 10,
                "check_balance": 20,
            }
        )
        self._tool_handlers: Dict[str, Callable] = {}

    async def register_handlers(self) -> None:
        """Register tool handlers."""
        self._tool_handlers = {
            "execute_trade": self._handle_execute_trade,
            "close_position": self._handle_close_position,
            "check_balance": self._handle_check_balance,
        }
        logger.info("Tool handlers registered")

    async def execute(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool call with full validation and safety.

        Returns:
            {"success": bool, "output": Any, "error": Optional[str]}
        """
        # Check circuit breaker
        breaker = self._circuit_breakers.get(tool_name)
        if breaker and not breaker.can_execute():
            return {
                "success": False,
                "error": f"Circuit breaker open for {tool_name}. Too many failures.",
                "output": None,
            }

        # Check rate limit
        if not self._rate_limiter.can_call(tool_name):
            return {
                "success": False,
                "error": f"Rate limit exceeded for {tool_name}",
                "output": None,
            }

        try:
            # Layer 1: Schema validation
            validation_error = self._validate_schema(tool_name, tool_input)
            if validation_error:
                return {
                    "success": False,
                    "error": f"Schema validation failed: {validation_error}",
                    "output": None,
                }

            # Layer 2: Business rule validation (risk limits, position size)
            business_error = await self._validate_business_rules(tool_name, tool_input)
            if business_error:
                return {
                    "success": False,
                    "error": f"Business validation failed: {business_error}",
                    "output": None,
                }

            # Layer 3: Get handler and execute
            handler = self._tool_handlers.get(tool_name)
            if not handler:
                return {
                    "success": False,
                    "error": f"No handler for tool: {tool_name}",
                    "output": None,
                }

            # Execute with timeout
            result = await asyncio.wait_for(
                handler(tool_input), timeout=30.0  # 30 second timeout
            )

            # Record success
            if breaker:
                breaker.record_success()
            self._rate_limiter.record_call(tool_name)

            return {"success": True, "output": result, "error": None}

        except asyncio.TimeoutError:
            error_msg = f"Tool execution timeout ({tool_name})"
            logger.error(error_msg)
            if breaker:
                breaker.record_failure()
            return {"success": False, "error": error_msg, "output": None}

        except TradingError as e:
            error_msg = f"Trading error: {e.context.message}"
            logger.error(error_msg)
            if breaker:
                breaker.record_failure()
            return {"success": False, "error": error_msg, "output": None}

        except Exception as e:
            error_msg = f"Unexpected error in {tool_name}: {str(e)}"
            logger.error(error_msg)
            if breaker:
                breaker.record_failure()
            return {"success": False, "error": error_msg, "output": None}

    async def _handle_execute_trade(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trade via paper trading service."""
        # Get paper trading executor
        executor = await self.container.get("paper_trade_executor")

        symbol = input_data.get("symbol")
        action = input_data.get("action")  # "buy" or "sell"
        quantity = input_data.get("quantity")
        entry_price = input_data.get("entry_price")
        strategy_rationale = input_data.get("strategy_rationale", "")
        stop_loss = input_data.get("stop_loss")
        target_price = input_data.get("target_price")
        claude_session_id = input_data.get("claude_session_id", "unknown")

        # Execute based on action
        if action.lower() == "buy":
            result = await executor.execute_buy(
                account_id=input_data.get("account_id", "paper_swing_main"),
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                strategy_rationale=strategy_rationale,
                claude_session_id=claude_session_id,
                stop_loss=stop_loss,
                target_price=target_price,
            )
        elif action.lower() == "sell":
            result = await executor.execute_sell(
                account_id=input_data.get("account_id", "paper_swing_main"),
                symbol=symbol,
                quantity=quantity,
                exit_price=entry_price,
                strategy_rationale=strategy_rationale,
                claude_session_id=claude_session_id,
                stop_loss=stop_loss,
                target_price=target_price,
            )
        else:
            raise TradingError(
                f"Invalid action: {action}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        if result.get("success"):
            logger.info(f"Trade executed: {symbol} {action} {quantity}@{entry_price}")
        else:
            logger.error(f"Trade execution failed: {result.get('error')}")

        return result

    async def _handle_close_position(
        self, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Close a position via paper trading service."""
        executor = await self.container.get("paper_trade_executor")

        trade_id = input_data.get("trade_id")
        exit_price = input_data.get("exit_price")
        reason = input_data.get("reason", "Claude exit decision")

        result = await executor.close_position(
            trade_id=trade_id, exit_price=exit_price, reason=reason
        )

        if result.get("success"):
            logger.info(f"Position closed: {trade_id} @ {exit_price}")
        else:
            logger.error(f"Position close failed: {result.get('error')}")

        return result

    async def _handle_check_balance(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check account balance."""
        account_manager = await self.container.get("paper_trading_account_manager")

        account_id = input_data.get("account_id", "paper_swing_main")
        account = await account_manager.get_account(account_id)

        if not account:
            return {
                "success": False,
                "error": f"Account not found: {account_id}",
                "output": None,
            }

        balance_info = await account_manager.get_account_balance(account_id)

        return {"success": True, "output": balance_info, "error": None}

    def _validate_schema(
        self, tool_name: str, input_data: Dict[str, Any]
    ) -> Optional[str]:
        """Validate tool input against schema."""
        if tool_name == "execute_trade":
            required = [
                "symbol",
                "action",
                "quantity",
                "entry_price",
                "strategy_rationale",
            ]
            missing = [f for f in required if f not in input_data]
            if missing:
                return f"Missing required fields: {missing}"

            if input_data.get("action") not in ["buy", "sell"]:
                return f"Invalid action: {input_data.get('action')}"

            if (
                not isinstance(input_data.get("quantity"), int)
                or input_data.get("quantity", 0) <= 0
            ):
                return "Quantity must be positive integer"

            if (
                not isinstance(input_data.get("entry_price"), (int, float))
                or input_data.get("entry_price", 0) <= 0
            ):
                return "Entry price must be positive number"

            # Validate stop loss vs entry if present
            if input_data.get("stop_loss"):
                sl = input_data.get("stop_loss")
                ep = input_data.get("entry_price")
                if input_data.get("action").lower() == "buy" and sl >= ep:
                    return "Stop loss must be below entry price for BUY"
                elif input_data.get("action").lower() == "sell" and sl <= ep:
                    return "Stop loss must be above entry price for SELL"

        elif tool_name == "close_position":
            required = ["trade_id", "exit_price", "reason"]
            missing = [f for f in required if f not in input_data]
            if missing:
                return f"Missing required fields: {missing}"

            if (
                not isinstance(input_data.get("exit_price"), (int, float))
                or input_data.get("exit_price", 0) <= 0
            ):
                return "Exit price must be positive number"

        elif tool_name == "check_balance":
            # No validation needed
            pass

        return None

    async def _validate_business_rules(
        self, tool_name: str, input_data: Dict[str, Any]
    ) -> Optional[str]:
        """Validate against business rules (risk limits, position size)."""
        if tool_name == "execute_trade":
            account_id = input_data.get("account_id", "paper_swing_main")
            account_manager = await self.container.get("paper_trading_account_manager")

            # Check if account exists
            account = await account_manager.get_account(account_id)
            if not account:
                return f"Account not found: {account_id}"

            # Check buying power
            quantity = input_data.get("quantity", 0)
            entry_price = input_data.get("entry_price", 0)
            trade_value = quantity * entry_price

            can_execute, error = await account_manager.can_execute_trade(
                account_id=account_id,
                trade_value=trade_value,
                max_position_pct=self.config.get("max_position_size_pct", 5.0),
            )

            if not can_execute:
                return error

        return None

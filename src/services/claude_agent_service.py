"""Claude Agent SDK service for autonomous trading sessions."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from ..core.event_bus import EventHandler, Event, EventType, EventBus
from ..core.di import DependencyContainer
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
from ..config import Config
from ..models.claude_agent import SessionType, ClaudeSessionResult
from ..stores.claude_strategy_store import ClaudeStrategyStore

logger = logging.getLogger(__name__)


class ClaudeAgentService(EventHandler):
    """
    Claude Agent SDK service for autonomous trading.

    Integrates with existing architecture:
    - Uses DependencyContainer for service resolution
    - Emits events via EventBus
    - Follows TradingError patterns
    - Respects modularization limits (<350 lines)
    """

    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        container: DependencyContainer,
        strategy_store: ClaudeStrategyStore
    ):
        """Initialize service."""
        self.config = config
        self.event_bus = event_bus
        self.container = container
        self.strategy_store = strategy_store
        self._initialized = False
        self._coordinator = None
        self._token_budget_daily = config.get("claude_agent", {}).get("daily_token_budget", 15000)
        self._tokens_used_today = 0

    async def initialize(self) -> None:
        """Initialize service and subscribe to events."""
        try:
            # Get coordinator from container
            self._coordinator = await self.container.get("claude_agent_coordinator")

            # Subscribe to events that trigger sessions
            self.event_bus.subscribe(EventType.MARKET_OPEN, self)
            self.event_bus.subscribe(EventType.MARKET_CLOSE, self)
            self.event_bus.subscribe(EventType.SYSTEM_HEALTH_CHECK, self)

            self._initialized = True
            logger.info("ClaudeAgentService initialized")

        except Exception as e:
            logger.error(f"Failed to initialize ClaudeAgentService: {e}")
            raise TradingError(
                f"ClaudeAgentService initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if not self._initialized or not self._coordinator:
            return

        try:
            if event.type == EventType.MARKET_OPEN:
                # Market opened - trigger morning prep
                await self.run_morning_prep(account_type="swing")
                await self.run_morning_prep(account_type="options")

            elif event.type == EventType.MARKET_CLOSE:
                # Market closed - trigger evening review
                await self.run_evening_review(account_type="swing")
                await self.run_evening_review(account_type="options")

            elif event.type == EventType.SYSTEM_HEALTH_CHECK:
                # Periodic check - update token usage
                await self._update_token_usage()

        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")

    async def run_morning_prep(self, account_type: str) -> Optional[ClaudeSessionResult]:
        """
        Execute morning preparation session.

        Claude will:
        1. Review open positions
        2. Check earnings calendar
        3. Analyze market opportunities
        4. Execute autonomous trades
        """
        if not self._check_token_budget(2200):
            logger.warning(f"Insufficient token budget for morning prep ({account_type})")
            return None

        try:
            # Gather context
            context = await self._build_morning_context(account_type)

            logger.info(f"Starting morning prep session for {account_type}")

            # Run session via coordinator
            result = await self._coordinator.run_morning_prep_session(account_type, context)

            # Track tokens
            self._tokens_used_today += result.token_input + result.token_output

            # Emit event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_RECOMMENDATION,
                source="ClaudeAgentService",
                data={
                    "session_id": result.session_id,
                    "session_type": "morning_prep",
                    "account_type": account_type,
                    "trades_executed": len([d for d in result.decisions_made if d.get("tool") == "execute_trade"]),
                    "tokens_used": result.token_input + result.token_output
                }
            ))

            return result

        except Exception as e:
            logger.error(f"Morning prep failed for {account_type}: {e}")
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ERROR,
                source="ClaudeAgentService",
                data={"error": str(e), "session_type": "morning_prep"}
            ))
            return None

    async def run_evening_review(self, account_type: str) -> Optional[ClaudeSessionResult]:
        """
        Execute evening review session.

        Claude will:
        1. Calculate daily P&L
        2. Analyze strategy effectiveness
        3. Extract learnings
        4. Plan for next day
        """
        if not self._check_token_budget(1500):
            logger.warning(f"Insufficient token budget for evening review ({account_type})")
            return None

        try:
            # Gather context
            context = await self._build_evening_context(account_type)

            logger.info(f"Starting evening review session for {account_type}")

            # Run session via coordinator
            result = await self._coordinator.run_evening_review_session(account_type, context)

            # Track tokens
            self._tokens_used_today += result.token_input + result.token_output

            # Emit event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_LEARNING_UPDATE,
                source="ClaudeAgentService",
                data={
                    "session_id": result.session_id,
                    "session_type": "evening_review",
                    "account_type": account_type,
                    "learnings": result.learnings.to_dict() if result.learnings else None,
                    "tokens_used": result.token_input + result.token_output
                }
            ))

            return result

        except Exception as e:
            logger.error(f"Evening review failed for {account_type}: {e}")
            return None

    async def _build_morning_context(self, account_type: str) -> Dict[str, Any]:
        """Build context for morning session."""
        # Get account manager
        account_manager = await self.container.get("paper_trading_account_manager")
        account_id = f"paper_{account_type}_main"

        account = await account_manager.get_account(account_id)
        balance_info = await account_manager.get_account_balance(account_id)

        # Get open positions
        paper_store = await self.container.get("paper_trading_store")
        open_trades = await paper_store.get_open_trades(account_id)

        return {
            "balance": balance_info.get("current_balance", 100000),
            "buying_power": balance_info.get("buying_power", 100000),
            "open_positions": [
                {
                    "symbol": t.symbol,
                    "quantity": t.quantity,
                    "entry_price": t.entry_price,
                    "target": t.target_price,
                    "stop_loss": t.stop_loss
                }
                for t in open_trades[:5]  # Limit to top 5
            ],
            "account_type": account_type,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _build_evening_context(self, account_type: str) -> Dict[str, Any]:
        """Build context for evening session."""
        account_id = f"paper_{account_type}_main"
        paper_store = await self.container.get("paper_trading_store")

        # Get today's trades
        today = datetime.utcnow().strftime("%Y-%m-%d")
        async with paper_store.db.connect() as db:
            cursor = await db.execute(
                "SELECT * FROM paper_trades WHERE account_id = ? AND DATE(entry_timestamp) = ?",
                (account_id, today)
            )
            rows = await cursor.fetchall()

        today_trades = [dict(row) for row in rows] if rows else []

        # Calculate daily P&L
        daily_pnl = sum(float(t.get("realized_pnl", 0)) for t in today_trades)

        return {
            "account_type": account_type,
            "trades_today": len(today_trades),
            "daily_pnl": daily_pnl,
            "trades": today_trades[:10],
            "timestamp": datetime.utcnow().isoformat()
        }

    def _check_token_budget(self, needed_tokens: int) -> bool:
        """Check if token budget allows operation."""
        return self._tokens_used_today + needed_tokens <= self._token_budget_daily

    async def _update_token_usage(self) -> None:
        """Update token usage tracking."""
        # Get usage from store
        usage = await self.strategy_store.get_daily_token_usage()

        total_tokens = usage["total"]["input_tokens"] + usage["total"]["output_tokens"]
        remaining = self._token_budget_daily - total_tokens

        if remaining < 2000:
            logger.warning(f"Token budget low: {remaining} remaining")

            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_LEARNING_UPDATE,
                source="ClaudeAgentService",
                data={
                    "token_usage": usage,
                    "remaining_budget": remaining,
                    "daily_budget": self._token_budget_daily
                }
            ))

    async def close(self) -> None:
        """Cleanup service."""
        if not self._initialized:
            return

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MARKET_OPEN)
        self.event_bus.unsubscribe(EventType.MARKET_CLOSE)
        self.event_bus.unsubscribe(EventType.SYSTEM_HEALTH_CHECK)

        logger.info("ClaudeAgentService closed")

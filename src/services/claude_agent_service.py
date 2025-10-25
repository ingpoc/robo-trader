"""Claude Agent SDK service for autonomous trading sessions."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from ..core.event_bus import EventHandler, Event, EventType, EventBus
from ..core.di import DependencyContainer
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.config import Config
from ..models.claude_agent import SessionType, ClaudeSessionResult
from ..stores.claude_strategy_store import ClaudeStrategyStore
from .claude_agent import ClaudeAgentMCPServer
from ..auth.claude_auth import get_claude_status_cached

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
        self._mcp_server: Optional[ClaudeAgentMCPServer] = None
        # Removed duplicate SDK auth - using centralized auth
        self._coordinator = None
        self._token_budget_daily = config.get("claude_agent", {}).get("daily_token_budget", 15000)
        self._tokens_used_today = 0

    async def initialize(self) -> None:
        """Initialize service and subscribe to events."""
        try:
            # Initialize MCP server
            self._mcp_server = ClaudeAgentMCPServer(self.container)
            await self._mcp_server.initialize()

            # Get coordinator from container
            self._coordinator = await self.container.get("claude_agent_coordinator")

            # Subscribe to events that trigger sessions
            self.event_bus.subscribe(EventType.MARKET_OPEN, self)
            self.event_bus.subscribe(EventType.MARKET_CLOSE, self)
            self.event_bus.subscribe(EventType.SYSTEM_HEALTH_CHECK, self)

            self._initialized = True
            logger.info("ClaudeAgentService initialized with SDK integration")

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
        Execute morning preparation session via MCP server.

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
            # Validate SDK authentication using centralized auth
            auth_status = await get_claude_status_cached()
            if not auth_status.is_valid:
                logger.error(f"SDK authentication failed for morning prep: {auth_status.error}")
                return None

            # Gather context
            context = await self._build_morning_context(account_type)

            logger.info(f"Starting morning prep session for {account_type}")

            # Run session via MCP server
            result = await self._run_mcp_session("morning_prep", account_type, context)

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
        Execute evening review session via MCP server.

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
            # Validate SDK authentication using centralized auth
            auth_status = await get_claude_status_cached()
            if not auth_status.is_valid:
                logger.error(f"SDK authentication failed for evening review: {auth_status.error}")
                return None

            # Gather context
            context = await self._build_evening_context(account_type)

            logger.info(f"Starting evening review session for {account_type}")

            # Run session via MCP server
            result = await self._run_mcp_session("evening_review", account_type, context)

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

    async def _run_mcp_session(self, session_type: str, account_type: str, context: Dict[str, Any]) -> ClaudeSessionResult:
        """Run a session via ClaudeAgentCoordinator (real implementation)."""
        if not self._coordinator:
            raise TradingError(
                "ClaudeAgentCoordinator not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

        try:
            if session_type == "morning_prep":
                return await self._coordinator.run_morning_prep_session(account_type, context)
            elif session_type == "evening_review":
                return await self._coordinator.run_evening_review_session(account_type, context)
            else:
                raise TradingError(
                    f"Unknown session type: {session_type}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True
                )
        except Exception as e:
            logger.error(f"Session execution failed for {session_type}: {e}")
            raise TradingError(
                f"Claude session failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def _build_morning_context(self, account_type: str) -> Dict[str, Any]:
        """Build context for morning session using ContextBuilder."""
        # Get account manager
        account_manager = await self.container.get("paper_trading_account_manager")
        account_id = f"paper_{account_type}_main"

        account = await account_manager.get_account(account_id)
        balance_info = await account_manager.get_account_balance(account_id)

        # Get open positions
        paper_store = await self.container.get("paper_trading_store")
        open_trades = await paper_store.get_open_trades(account_id)

        # Get symbols to analyze (open positions + watchlist)
        symbols = list(set([t.symbol for t in open_trades[:10]]))  # From open positions

        # Fetch optimized data using prompt optimization service
        optimized_market_data = await self._fetch_optimized_market_data(symbols, account_type)

        # Get historical learnings for context
        recent_sessions = await self.strategy_store.get_recent_sessions(account_type, limit=3)
        historical_learnings = []
        for session in recent_sessions:
            if session.learnings:
                historical_learnings.extend(session.learnings.get_learnings_list()[:2])  # Top 2 per session

        # Use ContextBuilder for token-optimized context
        context_builder = await self.container.get("claude_context_builder")
        account_data = {
            "current_balance": balance_info.get("current_balance", 100000),
            "buying_power": balance_info.get("buying_power", 100000),
            "account_type": account_type
        }

        open_positions_data = [
            {
                "symbol": t.symbol,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "target_price": t.target_price,
                "stop_loss": t.stop_loss
            }
            for t in open_trades[:5]  # Limit to top 5
        ]

        # Build optimized context with historical learnings and optimized data
        context = await context_builder.build_morning_context(
            account_data=account_data,
            open_positions=open_positions_data,
            market_data=optimized_market_data.get("news"),  # Optimized news data
            earnings_today=optimized_market_data.get("earnings")  # Optimized earnings data
        )

        # Add optimized fundamentals and data quality metrics
        context["fundamentals_data"] = optimized_market_data.get("fundamentals")
        context["data_quality_summary"] = optimized_market_data.get("quality_summary")
        context["data_acquisition_method"] = "claude_optimized_prompts"

        # Add historical learnings for learning loop
        if historical_learnings:
            context["historical_learnings"] = historical_learnings[:5]  # Limit to 5 recent learnings

        return context

    async def _build_evening_context(self, account_type: str) -> Dict[str, Any]:
        """Build context for evening session using ContextBuilder."""
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

        # Get strategy effectiveness from recent sessions
        recent_sessions = await self.strategy_store.get_recent_sessions(account_type, limit=5)
        strategy_effectiveness = self._analyze_strategy_effectiveness(recent_sessions)

        # Use ContextBuilder for token-optimized context
        context_builder = await self.container.get("claude_context_builder")
        account_data = {"account_type": account_type}

        context = await context_builder.build_evening_context(
            account_data=account_data,
            today_trades=today_trades[:10],
            daily_pnl=daily_pnl,
            strategy_effectiveness=strategy_effectiveness
        )

        return context

    def _check_token_budget(self, needed_tokens: int) -> bool:
        """Check if token budget allows operation with per-account enforcement."""
        # Get current usage from store for real enforcement
        try:
            usage = self.strategy_store.get_daily_token_usage()
            total_used = usage["total"]["input_tokens"] + usage["total"]["output_tokens"]
            return total_used + needed_tokens <= self._token_budget_daily
        except Exception as e:
            logger.warning(f"Could not get real token usage, using cached: {e}")
            return self._tokens_used_today + needed_tokens <= self._token_budget_daily

    async def _update_token_usage(self) -> None:
        """Update token usage tracking with real enforcement."""
        # Get usage from store for real enforcement
        usage = await self.strategy_store.get_daily_token_usage()

        total_tokens = usage["total"]["input_tokens"] + usage["total"]["output_tokens"]
        remaining = self._token_budget_daily - total_tokens

        # Update cached usage for faster checks
        self._tokens_used_today = total_tokens

        if remaining < 2000:
            logger.warning(f"Token budget low: {remaining} remaining")

            # Emit alert for low budget
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_LEARNING_UPDATE,
                source="ClaudeAgentService",
                data={
                    "token_usage": usage,
                    "remaining_budget": remaining,
                    "daily_budget": self._token_budget_daily,
                    "alert": "low_budget" if remaining < 2000 else None
                }
            ))

            # If critically low, pause sessions
            if remaining < 500:
                logger.error("Token budget critically low - pausing Claude sessions")
                await self.event_bus.publish(Event(
                    id=str(uuid.uuid4()),
                    type=EventType.SYSTEM_ERROR,
                    source="ClaudeAgentService",
                    data={"error": "Token budget exhausted", "remaining": remaining}
                ))

    async def _fetch_optimized_market_data(self, symbols: list, account_type: str) -> Dict[str, Any]:
        """Fetch market data using Claude's optimized prompts."""
        if not symbols:
            return {
                "news": None,
                "earnings": None,
                "fundamentals": None,
                "quality_summary": {}
            }

        try:
            # Get prompt optimization service
            prompt_service = await self.container.get("prompt_optimization_service")

            # Create session ID for tracking
            session_id = f"morning_prep_{account_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            optimized_data = {}
            quality_summary = {}

            # Fetch optimized data for each data type
            data_types = ["news", "earnings", "fundamentals"]

            for data_type in data_types:
                try:
                    logger.info(f"Fetching optimized {data_type} data for {len(symbols)} symbols")

                    # Get optimized data with quality check
                    data, quality_score, final_prompt, optimization_metadata = await prompt_service.get_optimized_data(
                        data_type=data_type,
                        symbols=symbols,
                        session_id=session_id,
                        force_optimization=False  # Let Claude decide if optimization needed
                    )

                    optimized_data[data_type] = data
                    quality_summary[data_type] = {
                        "quality_score": quality_score,
                        "optimization_attempts": len(optimization_metadata.get("attempts", [])),
                        "optimization_triggered": optimization_metadata.get("optimization_triggered", False),
                        "prompt_optimized": optimization_metadata.get("optimization_successful", False)
                    }

                    # Emit data quality event for transparency
                    await self.event_bus.publish(Event(
                        id=str(uuid.uuid4()),
                        type=EventType.CLAUDE_DATA_QUALITY_ANALYSIS,
                        source="ClaudeAgentService",
                        data={
                            "session_id": session_id,
                            "data_type": data_type,
                            "quality_score": quality_score,
                            "symbols_count": len(symbols),
                            "optimization_metadata": optimization_metadata
                        }
                    ))

                    logger.info(f"Fetched {data_type} with quality score {quality_score}/10")

                except Exception as e:
                    logger.error(f"Failed to get optimized {data_type} data: {e}")
                    optimized_data[data_type] = None
                    quality_summary[data_type] = {
                        "quality_score": 0.0,
                        "error": str(e),
                        "optimization_attempts": 0
                    }

            return {
                "news": optimized_data.get("news"),
                "earnings": optimized_data.get("earnings"),
                "fundamentals": optimized_data.get("fundamentals"),
                "quality_summary": quality_summary,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Failed to fetch optimized market data: {e}")
            return {
                "news": None,
                "earnings": None,
                "fundamentals": None,
                "quality_summary": {"error": str(e)}
            }

    async def close(self) -> None:
        """Cleanup service."""
        if not self._initialized:
            return

        # Cleanup MCP server
        if self._mcp_server:
            await self._mcp_server.cleanup()

        # Cleanup coordinator
        if self._coordinator and hasattr(self._coordinator, 'cleanup'):
            await self._coordinator.cleanup()

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MARKET_OPEN)
        self.event_bus.unsubscribe(EventType.MARKET_CLOSE)
        self.event_bus.unsubscribe(EventType.SYSTEM_HEALTH_CHECK)

        logger.info("ClaudeAgentService closed")

    def _analyze_strategy_effectiveness(self, recent_sessions: List) -> Dict[str, Any]:
        """Analyze strategy effectiveness from recent sessions for learning loop."""
        if not recent_sessions:
            return {}

        worked_well = []
        failed = []

        for session in recent_sessions:
            if session.learnings:
                learnings_list = session.learnings.get_learnings_list()
                for learning in learnings_list:
                    if learning.get("confidence", 0) > 0.7:  # High confidence learnings
                        if learning.get("type") == "success":
                            worked_well.append(learning.get("description", ""))
                        elif learning.get("type") == "failure":
                            failed.append(learning.get("description", ""))

        return {
            "what_worked": worked_well[:3],  # Top 3 successes
            "what_failed": failed[:3]        # Top 3 failures
        }
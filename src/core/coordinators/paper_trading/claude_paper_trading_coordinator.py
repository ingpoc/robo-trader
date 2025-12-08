"""
Claude-Powered Paper Trading Coordinator

Uses Claude Agent SDK to:
1. Analyze market conditions
2. Generate trading strategies
3. Execute paper trades with real Kite Connect prices
4. Daily evaluate and improve strategies
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger

from ..base_coordinator import BaseCoordinator
from ...database_state import DatabaseStateManager
from ...event_bus import EventBus, Event, EventType
from ....services.paper_trading.account_manager import PaperTradingAccountManager
from ....services.paper_trading.trade_executor import PaperTradeExecutor
from ....services.kite_portfolio_service import KitePortfolioService
from ....services.technical_indicators_service import TechnicalIndicatorsService
from ....services.fundamental_service import FundamentalService
from ....config import Config


class ClaudePaperTradingCoordinator(BaseCoordinator):
    """
    Coordinator for Claude-powered paper trading.
    
    Responsibilities:
    - Daily strategy generation using Claude Agent SDK
    - Market analysis and opportunity identification
    - Paper trade execution with real Kite Connect prices
    - Performance evaluation and strategy improvement
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        event_bus: EventBus,
        account_manager: PaperTradingAccountManager,
        trade_executor: PaperTradeExecutor,
        kite_service: Optional[KitePortfolioService] = None,
        indicators_service: Optional[TechnicalIndicatorsService] = None,
        fundamental_service: Optional[FundamentalService] = None
    ):
        super().__init__(config, "claude_paper_trading_coordinator")
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.account_manager = account_manager
        self.trade_executor = trade_executor
        self.kite_service = kite_service
        self.indicators_service = indicators_service
        self.fundamental_service = fundamental_service

        # Default account ID for Claude's paper trading
        self.default_account_id = "claude_paper_trading_account"
        self.initial_capital = 100000.0  # ₹1 lakh

    async def initialize(self) -> None:
        """Initialize the coordinator."""
        logger.info("Initializing Claude Paper Trading Coordinator")
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        
        # Ensure default account exists
        await self._ensure_default_account()
        
        self._running = True
        logger.info("Claude Paper Trading Coordinator initialized")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self.event_bus.unsubscribe(EventType.MARKET_PRICE_UPDATE, self)
        self._running = False

    async def _ensure_default_account(self) -> None:
        """Ensure default paper trading account exists."""
        account = await self.account_manager.get_account(self.default_account_id)
        if not account:
            logger.info(f"Creating default paper trading account: {self.default_account_id}")
            account = await self.account_manager.create_account(
                account_name="Claude Paper Trading Account",
                initial_balance=self.initial_capital,
                account_id=self.default_account_id,
                strategy_type="SWING",
                risk_level="MODERATE",
                max_position_size=5.0,
                max_portfolio_risk=10.0
            )
            logger.info(f"Created account with initial balance: ₹{self.initial_capital}")

    async def generate_daily_strategy(self) -> Dict[str, Any]:
        """
        Generate daily trading strategy using Claude Agent SDK.
        
        Claude will:
        1. Analyze current market conditions
        2. Review portfolio performance
        3. Identify trading opportunities
        4. Generate buy/sell recommendations
        """
        try:
            logger.info("Generating daily trading strategy using Claude")

            # Get account details
            account = await self.account_manager.get_account(self.default_account_id)
            if not account:
                raise ValueError("Default account not found")

            # Get current portfolio
            open_positions = await self.account_manager.get_open_positions(self.default_account_id)
            balance_info = await self.account_manager.get_account_balance(self.default_account_id)

            # Analyze market conditions
            market_analysis = await self._analyze_market_conditions()

            # Generate strategy using Claude (this will use the strategy agent tools)
            strategy = await self._generate_strategy_with_claude(
                account_id=self.default_account_id,
                available_capital=balance_info.get("buying_power", 0),
                open_positions=open_positions,
                market_analysis=market_analysis
            )

            # Store strategy for execution
            await self._store_strategy(strategy)

            # Emit strategy generated event
            await self.event_bus.publish(Event(
                type=EventType.AI_RECOMMENDATION,
                source=self.name,
                data={
                    "account_id": self.default_account_id,
                    "strategy": strategy,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            ))

            logger.info(f"Daily strategy generated: {len(strategy.get('recommended_trades', []))} recommendations")
            return strategy

        except Exception as e:
            logger.error(f"Failed to generate daily strategy: {e}")
            raise

    async def execute_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trading strategy by placing paper trades.
        
        Uses real Kite Connect prices for execution.
        """
        try:
            logger.info("Executing trading strategy")

            recommended_trades = strategy.get("recommended_trades", [])
            executed_trades = []
            failed_trades = []

            for trade_recommendation in recommended_trades:
                try:
                    symbol = trade_recommendation.get("symbol")
                    action = trade_recommendation.get("action")  # BUY or SELL
                    quantity = trade_recommendation.get("quantity")
                    entry_price = trade_recommendation.get("entry_price")
                    stop_loss = trade_recommendation.get("stop_loss")
                    target_price = trade_recommendation.get("target_price")
                    rationale = trade_recommendation.get("rationale", "")

                    if not all([symbol, action, quantity]):
                        logger.warning(f"Incomplete trade recommendation: {trade_recommendation}")
                        continue

                    # Execute paper trade with real Kite Connect price
                    if action == "BUY":
                        result = await self.trade_executor.execute_buy(
                            account_id=self.default_account_id,
                            symbol=symbol,
                            quantity=quantity,
                            entry_price=entry_price or 0,  # Will use market price if 0
                            strategy_rationale=rationale,
                            claude_session_id="claude_strategy",
                            stop_loss=stop_loss,
                            target_price=target_price,
                            use_market_price=True  # Use real Kite Connect price
                        )
                    else:  # SELL
                        result = await self.trade_executor.execute_sell(
                            account_id=self.default_account_id,
                            symbol=symbol,
                            quantity=quantity,
                            exit_price=entry_price or 0,
                            strategy_rationale=rationale,
                            claude_session_id="claude_strategy",
                            stop_loss=stop_loss,
                            target_price=target_price
                        )

                    if result.get("success"):
                        executed_trades.append(result)
                        logger.info(f"Executed {action} trade: {symbol} {quantity} shares")
                    else:
                        failed_trades.append({
                            "trade": trade_recommendation,
                            "error": result.get("error", "Unknown error")
                        })

                except Exception as e:
                    logger.error(f"Failed to execute trade {trade_recommendation}: {e}")
                    failed_trades.append({
                        "trade": trade_recommendation,
                        "error": str(e)
                    })

            return {
                "executed_trades": executed_trades,
                "failed_trades": failed_trades,
                "total_executed": len(executed_trades),
                "total_failed": len(failed_trades)
            }

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            raise

    async def evaluate_daily_performance(self) -> Dict[str, Any]:
        """
        Evaluate daily performance and suggest strategy improvements.
        
        Uses Claude to analyze:
        - Trade performance
        - Winning/losing patterns
        - Strategy effectiveness
        - Improvement recommendations
        """
        try:
            logger.info("Evaluating daily performance")

            # Get trade history for today
            today = datetime.now(timezone.utc).date()
            closed_trades = await self.account_manager.get_closed_trades(
                self.default_account_id,
                month=today.month,
                year=today.year
            )

            # Filter today's trades
            today_trades = [
                t for t in closed_trades
                if datetime.fromisoformat(t.exit_date).date() == today
            ]

            # Get open positions
            open_positions = await self.account_manager.get_open_positions(self.default_account_id)

            # Get performance metrics
            performance = await self.account_manager.get_performance_metrics(
                self.default_account_id,
                period="today"
            )

            # Generate evaluation using Claude
            evaluation = await self._evaluate_with_claude(
                performance=performance,
                closed_trades=today_trades,
                open_positions=open_positions
            )

            # Store evaluation
            await self._store_evaluation(evaluation)

            logger.info("Daily performance evaluation completed")
            return evaluation

        except Exception as e:
            logger.error(f"Performance evaluation failed: {e}")
            raise

    async def _analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions."""
        # This would use the strategy agent tools
        # For now, return placeholder
        return {
            "market_sentiment": "neutral",
            "opportunities": []
        }

    async def _generate_strategy_with_claude(
        self,
        account_id: str,
        available_capital: float,
        open_positions: List[Any],
        market_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate strategy using Claude Agent SDK tools."""
        try:
            # Get Claude Agent Service from container
            from ....core.di import get_container
            container = get_container()
            claude_service = await container.get("claude_agent_service")

            # Build context for Claude
            context = {
                "account_id": account_id,
                "available_capital": available_capital,
                "open_positions": [
                    {
                        "symbol": pos.get("symbol"),
                        "quantity": pos.get("quantity"),
                        "entry_price": pos.get("entry_price"),
                        "current_price": pos.get("current_price"),
                        "unrealized_pnl": pos.get("unrealized_pnl", 0)
                    }
                    for pos in open_positions
                ],
                "market_analysis": market_analysis,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Run morning prep session to generate strategy
            session_result = await claude_service.run_morning_prep_session(
                account_type="paper",
                context=context
            )

            # Parse decisions from session result
            recommended_trades = []
            if hasattr(session_result, 'decisions_made') and session_result.decisions_made:
                for decision in session_result.decisions_made:
                    # Extract trade recommendations from decisions
                    if decision.get("action") in ["BUY", "SELL"]:
                        recommended_trades.append({
                            "symbol": decision.get("symbol"),
                            "action": decision.get("action"),
                            "quantity": decision.get("quantity", 1),
                            "entry_price": decision.get("price", 0),
                            "stop_loss": decision.get("stop_loss"),
                            "target_price": decision.get("target"),
                            "rationale": decision.get("reasoning", "")
                        })

            return {
                "account_id": account_id,
                "available_capital": available_capital,
                "recommended_trades": recommended_trades,
                "position_sizing": {},
                "stop_loss_levels": {},
                "target_prices": {},
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "session_id": getattr(session_result, 'session_id', None),
                "market_context": market_analysis
            }

        except Exception as e:
            logger.error(f"Claude SDK strategy generation failed: {e}")
            # Return empty strategy on error but log the issue
            return {
                "account_id": account_id,
                "available_capital": available_capital,
                "recommended_trades": [],
                "position_sizing": {},
                "stop_loss_levels": {},
                "target_prices": {},
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    async def _evaluate_with_claude(
        self,
        performance: Dict[str, Any],
        closed_trades: List[Any],
        open_positions: List[Any]
    ) -> Dict[str, Any]:
        """Evaluate performance using Claude Agent SDK."""
        return {
            "performance_summary": performance,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _store_strategy(self, strategy: Dict[str, Any]) -> None:
        """Store strategy in database."""
        # This would store in database
        pass

    async def _store_evaluation(self, evaluation: Dict[str, Any]) -> None:
        """Store evaluation in database."""
        # This would store in database
        pass

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.MARKET_PRICE_UPDATE:
            # Could trigger stop-loss checks, etc.
            pass


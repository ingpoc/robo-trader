"""Strategy Evolution Engine - AI-driven strategy optimization based on performance feedback.

Tracks strategy performance per tag, calculates effectiveness metrics,
and provides learnings back to Claude for strategy optimization.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiofiles
import aiofiles.os
import os
from pathlib import Path
from loguru import logger

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType, EventHandler
from src.core.errors import TradingError, ErrorSeverity
from src.models.paper_trading import PaperTrade
from src.services.paper_trading.performance_calculator import PerformanceCalculator


@dataclass
class StrategyMetrics:
    """Metrics for a specific strategy tag."""
    strategy_tag: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 0-100%
    avg_pnl: float
    total_pnl: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    last_updated: str
    consecutive_wins: int
    consecutive_losses: int
    best_trade: float
    worst_trade: float


@dataclass
class StrategyEvolution:
    """Strategy evolution parameters and recommendations."""
    strategy_tag: str
    current_metrics: StrategyMetrics
    effectiveness_score: float  # 0-100
    recommendation: str  # "increase_use", "reduce_use", "modify_parameters", "retire"
    confidence: float  # 0-100
    reasoning: List[str]
    suggested_adjustments: Dict[str, Any]
    last_analyzed: str


class StrategyEvolutionEngine(EventHandler):
    """
    Strategy Evolution Engine - AI-driven strategy optimization.

    Responsibilities:
    - Track strategy performance per tag
    - Calculate effectiveness metrics
    - Detect winning/losing patterns
    - Provide Claude with strategy learnings
    - Recommend strategy adjustments
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._initialized = False

        # File paths
        self.state_dir = config.state_dir / "strategy_evolution"
        self.strategies_file = self.state_dir / "strategies_metrics.json"
        self.evolution_file = self.state_dir / "strategy_evolutions.json"

        # In-memory cache
        self._strategies: Dict[str, StrategyMetrics] = {}
        self._evolutions: Dict[str, StrategyEvolution] = {}
        self._lock = asyncio.Lock()

        # Subscribe to trade events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.PAPER_TRADING_CLOSED, self)

    async def initialize(self) -> None:
        """Initialize the strategy evolution engine."""
        try:
            await aiofiles.os.makedirs(str(self.state_dir), exist_ok=True)
            await self._load_cached_strategies()
            self._initialized = True
            logger.info("Strategy Evolution Engine initialized")
        except Exception as e:
            raise TradingError(
                f"Failed to initialize strategy evolution engine: {e}",
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def _load_cached_strategies(self) -> None:
        """Load cached strategy metrics from file."""
        try:
            if await aiofiles.os.path.exists(str(self.strategies_file)):
                async with aiofiles.open(str(self.strategies_file), 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    for strategy_tag, metrics_dict in data.items():
                        self._strategies[strategy_tag] = StrategyMetrics(**metrics_dict)
                logger.debug(f"Loaded {len(self._strategies)} cached strategies")
        except Exception as e:
            logger.warning(f"Could not load cached strategies: {e}")

    async def track_trade(self, trade: PaperTrade, strategy_tag: str) -> None:
        """Track a closed trade for strategy performance."""
        if not trade.exit_price or not trade.exit_timestamp:
            return  # Only track closed trades

        async with self._lock:
            # Calculate trade P&L
            pnl_absolute = (trade.exit_price - trade.entry_price) * trade.quantity
            pnl_percentage = PerformanceCalculator.calculate_pnl_percentage(
                trade.entry_price,
                trade.exit_price
            )

            # Get or initialize strategy metrics
            if strategy_tag not in self._strategies:
                self._strategies[strategy_tag] = StrategyMetrics(
                    strategy_tag=strategy_tag,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    avg_pnl=0.0,
                    total_pnl=0.0,
                    profit_factor=0.0,
                    max_drawdown=0.0,
                    sharpe_ratio=0.0,
                    last_updated=datetime.now(timezone.utc).isoformat(),
                    consecutive_wins=0,
                    consecutive_losses=0,
                    best_trade=pnl_absolute,
                    worst_trade=pnl_absolute
                )

            metrics = self._strategies[strategy_tag]

            # Update metrics
            metrics.total_trades += 1
            metrics.total_pnl += pnl_absolute

            if pnl_absolute > 0:
                metrics.winning_trades += 1
                metrics.consecutive_wins += 1
                metrics.consecutive_losses = 0
            elif pnl_absolute < 0:
                metrics.losing_trades += 1
                metrics.consecutive_losses += 1
                metrics.consecutive_wins = 0

            # Update best/worst trades
            metrics.best_trade = max(metrics.best_trade, pnl_absolute)
            metrics.worst_trade = min(metrics.worst_trade, pnl_absolute)

            # Recalculate metrics
            if metrics.total_trades > 0:
                metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
                metrics.avg_pnl = metrics.total_pnl / metrics.total_trades

            # Calculate profit factor
            wins_total = metrics.best_trade * metrics.winning_trades if metrics.winning_trades > 0 else 0
            losses_total = abs(metrics.worst_trade) * metrics.losing_trades if metrics.losing_trades > 0 else 0
            if losses_total > 0:
                metrics.profit_factor = wins_total / losses_total
            elif wins_total > 0:
                metrics.profit_factor = float('inf')
            else:
                metrics.profit_factor = 0.0

            metrics.last_updated = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"Tracked {strategy_tag}: Total={metrics.total_trades} "
                f"Win%={metrics.win_rate:.1f}% AvgPnL={metrics.avg_pnl:.2f}"
            )

            # Save to file
            await self._save_strategies()

    async def analyze_strategy(self, strategy_tag: str) -> Optional[StrategyEvolution]:
        """Analyze strategy effectiveness and provide recommendations."""
        async with self._lock:
            if strategy_tag not in self._strategies:
                return None

            metrics = self._strategies[strategy_tag]

            # Calculate effectiveness score (0-100)
            score = 0.0
            reasoning = []

            # Win rate component (0-40 points)
            if metrics.win_rate >= 60:
                score += 40
                reasoning.append(f"Excellent win rate: {metrics.win_rate:.1f}%")
            elif metrics.win_rate >= 50:
                score += 30
                reasoning.append(f"Good win rate: {metrics.win_rate:.1f}%")
            elif metrics.win_rate >= 40:
                score += 15
                reasoning.append(f"Moderate win rate: {metrics.win_rate:.1f}%")
            else:
                reasoning.append(f"Low win rate: {metrics.win_rate:.1f}%")

            # Profit factor component (0-30 points)
            if metrics.profit_factor > 2.0:
                score += 30
                reasoning.append(f"Strong profit factor: {metrics.profit_factor:.2f}")
            elif metrics.profit_factor > 1.5:
                score += 20
                reasoning.append(f"Good profit factor: {metrics.profit_factor:.2f}")
            elif metrics.profit_factor > 1.0:
                score += 10
                reasoning.append(f"Positive profit factor: {metrics.profit_factor:.2f}")
            else:
                reasoning.append(f"Low profit factor: {metrics.profit_factor:.2f}")

            # Consistency component (0-20 points)
            if metrics.consecutive_wins >= 3:
                score += 20
                reasoning.append(f"Strong consistency: {metrics.consecutive_wins} wins")
            elif metrics.consecutive_wins >= 2:
                score += 10
                reasoning.append(f"Recent winning streak")
            elif metrics.consecutive_losses >= 3:
                score -= 10
                reasoning.append(f"Recent losing streak: {metrics.consecutive_losses} losses")

            # Trade volume component (0-10 points)
            if metrics.total_trades >= 20:
                score += 10
                reasoning.append(f"Sufficient sample size: {metrics.total_trades} trades")
            elif metrics.total_trades >= 10:
                score += 5
                reasoning.append(f"Growing sample size: {metrics.total_trades} trades")
            else:
                reasoning.append(f"Limited history: {metrics.total_trades} trades")

            score = max(0, min(100, score))

            # Determine recommendation
            if score >= 75:
                recommendation = "increase_use"
                suggestion = f"This strategy is performing very well. Consider increasing allocation and using it for larger positions."
            elif score >= 60:
                recommendation = "maintain_use"
                suggestion = f"This strategy is solid. Continue using it as part of your portfolio."
            elif score >= 40:
                recommendation = "modify_parameters"
                suggestion = f"This strategy shows promise but needs optimization. Review entry/exit conditions."
            elif score >= 20:
                recommendation = "reduce_use"
                suggestion = f"Consider reducing reliance on this strategy. Focus on winners instead."
            else:
                recommendation = "retire"
                suggestion = f"This strategy is underperforming. Recommend retiring it."

            adjustments = {
                "reason": suggestion,
                "suggested_actions": []
            }

            if recommendation == "increase_use":
                adjustments["suggested_actions"] = [
                    "Allocate more capital to this strategy",
                    "Increase position sizing",
                    "Use more frequently"
                ]
            elif recommendation == "modify_parameters":
                adjustments["suggested_actions"] = [
                    "Review entry conditions",
                    "Optimize exit timing",
                    "Analyze losing trades for patterns"
                ]
            elif recommendation == "reduce_use":
                adjustments["suggested_actions"] = [
                    "Reduce allocation",
                    "Use only in strong trending markets",
                    "Combine with other strategies"
                ]

            evolution = StrategyEvolution(
                strategy_tag=strategy_tag,
                current_metrics=metrics,
                effectiveness_score=score,
                recommendation=recommendation,
                confidence=min(95.0, 50 + (metrics.total_trades / 2)),
                reasoning=reasoning,
                suggested_adjustments=adjustments,
                last_analyzed=datetime.now(timezone.utc).isoformat()
            )

            self._evolutions[strategy_tag] = evolution
            await self._save_evolutions()

            return evolution

    async def get_strategy_learnings(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top strategy learnings for Claude context."""
        async with self._lock:
            learnings = []

            # Sort strategies by effectiveness
            sorted_evolutions = sorted(
                self._evolutions.values(),
                key=lambda x: x.effectiveness_score,
                reverse=True
            )

            for evolution in sorted_evolutions[:limit]:
                learning = {
                    "strategy": evolution.strategy_tag,
                    "effectiveness_score": evolution.effectiveness_score,
                    "recommendation": evolution.recommendation,
                    "win_rate": f"{evolution.current_metrics.win_rate:.1f}%",
                    "profit_factor": f"{evolution.current_metrics.profit_factor:.2f}",
                    "total_trades": evolution.current_metrics.total_trades,
                    "reasoning": evolution.reasoning,
                    "actions": evolution.suggested_adjustments.get("suggested_actions", [])
                }
                learnings.append(learning)

            return learnings

    async def get_strategy_context_for_claude(self) -> Dict[str, Any]:
        """Get full strategy context for Claude's decision making."""
        async with self._lock:
            if not self._strategies:
                return {"status": "no_strategies_tracked"}

            total_trades = sum(s.total_trades for s in self._strategies.values())
            total_pnl = sum(s.total_pnl for s in self._strategies.values())
            avg_win_rate = (
                sum(s.win_rate for s in self._strategies.values()) / len(self._strategies)
                if self._strategies else 0
            )

            # Get top performers
            top_performers = sorted(
                self._strategies.values(),
                key=lambda x: x.effectiveness_score if x.total_trades >= 3 else -999,
                reverse=True
            )[:3]

            # Get underperformers
            underperformers = sorted(
                self._strategies.values(),
                key=lambda x: x.effectiveness_score if x.total_trades >= 3 else 999,
            )[:3]

            return {
                "total_strategies": len(self._strategies),
                "total_trades": total_trades,
                "total_pnl": total_pnl,
                "average_win_rate": f"{avg_win_rate:.1f}%",
                "top_performers": [
                    {
                        "strategy": s.strategy_tag,
                        "win_rate": f"{s.win_rate:.1f}%",
                        "total_pnl": s.total_pnl,
                        "trades": s.total_trades
                    }
                    for s in top_performers
                ],
                "underperformers": [
                    {
                        "strategy": s.strategy_tag,
                        "win_rate": f"{s.win_rate:.1f}%",
                        "total_pnl": s.total_pnl,
                        "trades": s.total_trades
                    }
                    for s in underperformers if s.total_trades >= 3
                ],
                "recommendations": [
                    evo.recommendation
                    for evo in self._evolutions.values()
                    if evo.confidence >= 70
                ]
            }

    async def _save_strategies(self) -> None:
        """Save strategy metrics to file."""
        try:
            data = {
                tag: asdict(metrics)
                for tag, metrics in self._strategies.items()
            }

            # Use atomic write
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=str(self.state_dir)) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name

            await aiofiles.os.replace(tmp_path, str(self.strategies_file))
        except Exception as e:
            logger.error(f"Failed to save strategies: {e}")

    async def _save_evolutions(self) -> None:
        """Save strategy evolutions to file."""
        try:
            data = {}
            for tag, evolution in self._evolutions.items():
                data[tag] = {
                    "strategy_tag": evolution.strategy_tag,
                    "effectiveness_score": evolution.effectiveness_score,
                    "recommendation": evolution.recommendation,
                    "confidence": evolution.confidence,
                    "reasoning": evolution.reasoning,
                    "last_analyzed": evolution.last_analyzed
                }

            # Use atomic write
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=str(self.state_dir)) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name

            await aiofiles.os.replace(tmp_path, str(self.evolution_file))
        except Exception as e:
            logger.error(f"Failed to save evolutions: {e}")

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        try:
            if event.type == EventType.EXECUTION_ORDER_FILLED:
                data = event.data
                trade = data.get("trade")
                strategy_tag = data.get("strategy_tag", "unknown")
                if trade:
                    await self.track_trade(trade, strategy_tag)

            elif event.type == EventType.PAPER_TRADING_CLOSED:
                data = event.data
                trade = data.get("trade")
                strategy_tag = data.get("strategy_tag", "unknown")
                if trade:
                    await self.track_trade(trade, strategy_tag)
        except Exception as e:
            logger.error(f"Error handling event in StrategyEvolutionEngine: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if not self._initialized:
            return

        self.event_bus.unsubscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.unsubscribe(EventType.PAPER_TRADING_CLOSED, self)
        self._initialized = False

"""
State management for Robo Trader

Handles persistent storage of:
- Portfolio Store
- Strategy Context
- Intent Ledger
- Execution Journal
- Checkpoints
"""

import json
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiofiles
from loguru import logger

from ..config import Config
from .alerts import AlertManager


@dataclass
class PortfolioState:
    """Current portfolio snapshot."""
    as_of: str
    cash: Dict[str, float]
    holdings: List[Dict[str, Any]]
    exposure_total: float
    risk_aggregates: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict) -> "PortfolioState":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Signal:
    """Technical analysis signal."""
    symbol: str
    timeframe: str
    indicators: Dict[str, float]
    entry: Optional[Dict[str, Any]] = None
    stop: Optional[Dict[str, Any]] = None
    targets: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> "Signal":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskDecision:
    """Risk assessment result."""
    symbol: str
    decision: str  # "approve", "deny", "defer"
    size_qty: Optional[int] = None
    max_risk_inr: Optional[float] = None
    stop: Optional[Dict[str, Any]] = None
    targets: Optional[List[Dict[str, Any]]] = None
    constraints: List[str] = None
    reasons: List[str] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []
        if self.reasons is None:
            self.reasons = []

    @classmethod
    def from_dict(cls, data: Dict) -> "RiskDecision":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OrderCommand:
    """Order execution command."""
    type: str  # "place", "modify", "cancel"
    side: str  # "BUY", "SELL"
    symbol: str
    qty: Optional[int] = None
    order_type: str = "MARKET"
    product: str = "CNC"
    variety: str = "REGULAR"
    tif: str = "DAY"
    client_tag: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "OrderCommand":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionReport:
    """Order execution result."""
    broker_order_id: str
    status: str  # "COMPLETE", "PENDING", "REJECTED", etc.
    fills: List[Dict[str, Any]] = None
    avg_price: Optional[float] = None
    slippage_bps: Optional[float] = None
    received_at: str = ""

    def __post_init__(self):
        if self.fills is None:
            self.fills = []
        if not self.received_at:
            self.received_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "ExecutionReport":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Intent:
    """Trading intent record."""
    id: str
    symbol: str
    created_at: str
    signal: Optional[Signal] = None
    risk_decision: Optional[RiskDecision] = None
    order_commands: List[OrderCommand] = None
    execution_reports: List[ExecutionReport] = None
    status: str = "pending"  # "pending", "approved", "executed", "rejected"
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    source: str = "system"

    def __post_init__(self):
        if self.order_commands is None:
            self.order_commands = []
        if self.execution_reports is None:
            self.execution_reports = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "Intent":
        # Handle nested objects
        if 'signal' in data and data['signal']:
            data['signal'] = Signal.from_dict(data['signal'])
        if 'risk_decision' in data and data['risk_decision']:
            data['risk_decision'] = RiskDecision.from_dict(data['risk_decision'])
        if 'order_commands' in data:
            data['order_commands'] = [OrderCommand.from_dict(cmd) for cmd in data['order_commands']]
        if 'execution_reports' in data:
            data['execution_reports'] = [ExecutionReport.from_dict(rep) for rep in data['execution_reports']]
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.signal:
            data['signal'] = self.signal.to_dict()
        if self.risk_decision:
            data['risk_decision'] = self.risk_decision.to_dict()
        data['order_commands'] = [cmd.to_dict() for cmd in self.order_commands]
        data['execution_reports'] = [rep.to_dict() for rep in self.execution_reports]
        return data


class StateManager:
    """Manages persistent state storage."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.portfolio_file = self.state_dir / "portfolio.json"
        self.intents_file = self.state_dir / "intents.json"
        self.screening_file = self.state_dir / "screening.json"
        self.strategy_file = self.state_dir / "strategy.json"
        self.checkpoints_dir = self.state_dir / "checkpoints"

        # NEW: AI Intelligence files
        self.daily_plans_dir = self.state_dir / "daily_plans"
        self.analysis_history_dir = self.state_dir / "analysis_history"
        self.priority_queue_file = self.state_dir / "priority_queue.json"
        self.events_calendar_file = self.state_dir / "events_calendar.json"
        self.approval_queue_file = self.state_dir / "approval_queue.json"
        self.ai_memory_file = self.state_dir / "ai_memory.json"
        self.weekly_plan_file = self.state_dir / "weekly_plan.json"
        self.learning_insights_file = self.state_dir / "learning_insights.json"

        # Create directories
        self.checkpoints_dir.mkdir(exist_ok=True)
        self.daily_plans_dir.mkdir(exist_ok=True)
        self.analysis_history_dir.mkdir(exist_ok=True)

        # In-memory caches
        self._portfolio: Optional[PortfolioState] = None
        self._intents: Dict[str, Intent] = {}
        self._screening_results: Optional[Dict[str, Any]] = None
        self._strategy_results: Optional[Dict[str, Any]] = None
        self._priority_queue: List[Dict] = []
        self._approval_queue: List[Dict] = []
        self._weekly_plan: Optional[Dict] = None
        self._lock = asyncio.Lock()

        # Alert manager
        self.alert_manager = AlertManager(state_dir)

        # Load initial state
        self._load_portfolio()
        self._load_intents()
        self._load_screening()
        self._load_strategy()
        self._load_priority_queue()
        self._load_approval_queue()
        self._load_weekly_plan()

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        async with self._lock:
            return self._portfolio

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._lock:
            self._portfolio = portfolio
            await self._save_portfolio()
            logger.info(f"Portfolio updated as of {portfolio.as_of}")

    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        async with self._lock:
            return self._intents.get(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        async with self._lock:
            return list(self._intents.values())

    async def create_intent(self, symbol: str, signal: Optional[Signal] = None, source: str = "system") -> Intent:
        """Create new trading intent."""
        async with self._lock:
            intent_id = f"intent_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"
            intent = Intent(
                id=intent_id,
                symbol=symbol,
                signal=signal,
                source=source
            )
            self._intents[intent_id] = intent
            await self._save_intents()
            logger.info(f"Created intent {intent_id} for {symbol}")
            return intent

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        async with self._lock:
            self._intents[intent.id] = intent
            await self._save_intents()
            logger.info(f"Updated intent {intent.id}")

    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        async with self._lock:
            self._screening_results = results
            await self._save_screening()

    async def get_screening_results(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._screening_results

    async def update_strategy_results(self, results: Optional[Dict[str, Any]]) -> None:
        async with self._lock:
            self._strategy_results = results
            await self._save_strategy()

    async def get_strategy_results(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._strategy_results

    # NEW: AI Planning methods
    async def save_daily_plan(self, plan: Dict) -> None:
        """Save AI-generated daily work plan."""
        plan_file = self.daily_plans_dir / f"{plan['date']}.json"
        async with self._lock:
            async with aiofiles.open(plan_file, 'w') as f:
                await f.write(json.dumps(plan, indent=2))

    async def load_daily_plan(self, date: str) -> Optional[Dict]:
        """Load daily plan for specific date."""
        plan_file = self.daily_plans_dir / f"{date}.json"
        if plan_file.exists():
            async with self._lock:
                with open(plan_file, 'r') as f:
                    return json.load(f)
        return None

    # NEW: Analysis history tracking
    async def save_analysis_history(self, symbol: str, analysis: Dict) -> None:
        """Save detailed analysis history per stock."""
        history_file = self.analysis_history_dir / f"{symbol}.json"
        async with self._lock:
            # Load existing history
            history = []
            if history_file.exists():
                async with aiofiles.open(history_file, 'r') as f:
                    content = await f.read()
                    history = json.loads(content)

            # Add new analysis
            history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis": analysis
            })

            # Keep last 30 days
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            history = [h for h in history if h["timestamp"] > cutoff.isoformat()]

            async with aiofiles.open(history_file, 'w') as f:
                await f.write(json.dumps(history, indent=2))

    # NEW: Priority queue for urgent events
    async def add_priority_item(self, symbol: str, reason: str, priority: str) -> None:
        """Add item to priority queue for urgent analysis."""
        async with self._lock:
            queue = self._load_priority_queue()
            queue.append({
                "symbol": symbol,
                "reason": reason,
                "priority": priority,
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            self._save_priority_queue(queue)

    async def get_priority_items(self) -> List[Dict]:
        """Get items needing urgent attention."""
        async with self._lock:
            return self._priority_queue.copy()

    # NEW: Approval queue management
    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add AI recommendation to user approval queue with deduplication."""
        async with self._lock:
            queue = self._load_approval_queue()

            symbol = recommendation.get("symbol", "")
            action = recommendation.get("action", "")

            for existing in queue:
                existing_rec = existing.get("recommendation", {})
                if (existing.get("status") == "pending" and
                    existing_rec.get("symbol") == symbol and
                    existing_rec.get("action") == action):
                    logger.debug(f"Skipping duplicate recommendation for {symbol} {action}")
                    return

            queue.append({
                "id": f"rec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}_{action}",
                "recommendation": recommendation,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            self._save_approval_queue(queue)

    async def get_pending_approvals(self) -> List[Dict]:
        """Get recommendations awaiting user approval."""
        async with self._lock:
            queue = self._load_approval_queue()

            # If no recommendations exist, add some sample ones for demo
            if not queue:
                sample_recommendations = self._get_sample_recommendations()
                for rec in sample_recommendations:
                    await self.add_to_approval_queue(rec)
                queue = self._load_approval_queue()

            return [item for item in queue if item["status"] == "pending"]

    async def update_approval_status(self, recommendation_id: str, status: str, user_feedback: Optional[str] = None) -> bool:
        """Update approval status for a recommendation."""
        async with self._lock:
            queue = self._load_approval_queue()
            for item in queue:
                if item["id"] == recommendation_id:
                    item["status"] = status
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if user_feedback:
                        item["user_feedback"] = user_feedback
                    self._save_approval_queue(queue)
                    return True
            return False

    # NEW: Weekly plan management
    async def save_weekly_plan(self, plan: Dict) -> None:
        """Save AI-generated weekly work distribution plan."""
        async with self._lock:
            async with aiofiles.open(self.weekly_plan_file, 'w') as f:
                await f.write(json.dumps(plan, indent=2))
            self._weekly_plan = plan

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load current weekly plan."""
        async with self._lock:
            return self._weekly_plan.copy() if self._weekly_plan else None

    # NEW: Learning insights storage
    async def save_learning_insights(self, insights: Dict) -> None:
        """Save AI learning insights from recommendation outcomes."""
        async with self._lock:
            # Load existing insights
            existing = []
            if self.learning_insights_file.exists():
                async with aiofiles.open(self.learning_insights_file, 'r') as f:
                    content = await f.read()
                    existing = json.loads(content)

            # Add new insights
            existing.append(insights)

            # Keep last 50 insights
            existing = existing[-50:]

            async with aiofiles.open(self.learning_insights_file, 'w') as f:
                await f.write(json.dumps(existing, indent=2))

    async def get_learning_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent learning insights."""
        async with self._lock:
            if self.learning_insights_file.exists():
                with open(self.learning_insights_file, 'r') as f:
                    insights = json.load(f)
                    return insights[-limit:]
            return []

    async def create_checkpoint(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a checkpoint of current state."""
        async with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            checkpoint_id = f"checkpoint_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

            checkpoint_data = {
                "id": checkpoint_id,
                "name": name,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "portfolio": self._portfolio.to_dict() if self._portfolio else None,
                "intents": {k: v.to_dict() for k, v in self._intents.items()}
            }

            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            async with aiofiles.open(checkpoint_file, 'w') as f:
                await f.write(json.dumps(checkpoint_data, indent=2))

            logger.info(f"Created checkpoint {checkpoint_id}: {name}")
            return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore state from checkpoint."""
        async with self._lock:
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            if not checkpoint_file.exists():
                logger.error(f"Checkpoint {checkpoint_id} not found")
                return False

            async with aiofiles.open(checkpoint_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)

            # Restore portfolio
            if data.get('portfolio'):
                self._portfolio = PortfolioState.from_dict(data['portfolio'])

            # Restore intents
            self._intents = {}
            for intent_id, intent_data in data.get('intents', {}).items():
                self._intents[intent_id] = Intent.from_dict(intent_data)

            await self._save_portfolio()
            await self._save_intents()

            logger.info(f"Restored checkpoint {checkpoint_id}")
            return True

    def _load_portfolio(self) -> None:
        """Load portfolio from file."""
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r') as f:
                    data = json.load(f)
                self._portfolio = PortfolioState.from_dict(data)
                logger.info("Portfolio loaded from file")
            except Exception as e:
                logger.error(f"Failed to load portfolio: {e}")
                self._portfolio = None

    async def _save_portfolio(self) -> None:
        """Save portfolio to file."""
        if self._portfolio:
            try:
                async with aiofiles.open(self.portfolio_file, 'w') as f:
                    await f.write(json.dumps(self._portfolio.to_dict(), indent=2))
            except Exception as e:
                logger.error(f"Failed to save portfolio: {e}")

    def _load_intents(self) -> None:
        """Load intents from file."""
        if self.intents_file.exists():
            try:
                with open(self.intents_file, 'r') as f:
                    data = json.load(f)
                self._intents = {}
                for intent_id, intent_data in data.items():
                    self._intents[intent_id] = Intent.from_dict(intent_data)
                logger.info(f"Loaded {len(self._intents)} intents from file")
            except Exception as e:
                logger.error(f"Failed to load intents: {e}")
                self._intents = {}

    async def _save_intents(self) -> None:
        """Save intents to file."""
        try:
            data = {k: v.to_dict() for k, v in self._intents.items()}
            async with aiofiles.open(self.intents_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save intents: {e}")

    def _load_screening(self) -> None:
        if self.screening_file.exists():
            try:
                with open(self.screening_file, 'r') as f:
                    self._screening_results = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load screening results: {e}")
                self._screening_results = None

    def _save_screening(self) -> None:
        try:
            with open(self.screening_file, 'w') as f:
                json.dump(self._screening_results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save screening results: {e}")

    def _load_strategy(self) -> None:
        if self.strategy_file.exists():
            try:
                with open(self.strategy_file, 'r') as f:
                    self._strategy_results = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load strategy analysis: {e}")
                self._strategy_results = None

    def _save_strategy(self) -> None:
        try:
            with open(self.strategy_file, 'w') as f:
                json.dump(self._strategy_results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save strategy analysis: {e}")

    # NEW: AI State management methods
    def _load_priority_queue(self) -> List[Dict]:
        """Load priority queue from file."""
        if self.priority_queue_file.exists():
            try:
                with open(self.priority_queue_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load priority queue: {e}")
        return []

    def _save_priority_queue(self, queue: List[Dict]) -> None:
        """Save priority queue to file."""
        try:
            with open(self.priority_queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save priority queue: {e}")

    def _load_approval_queue(self) -> List[Dict]:
        """Load approval queue from file."""
        if self.approval_queue_file.exists():
            try:
                with open(self.approval_queue_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load approval queue: {e}")
        return []

    def _save_approval_queue(self, queue: List[Dict]) -> None:
        """Save approval queue to file."""
        try:
            with open(self.approval_queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save approval queue: {e}")

    def _load_weekly_plan(self) -> None:
        """Load weekly plan from file."""
        if self.weekly_plan_file.exists():
            try:
                with open(self.weekly_plan_file, 'r') as f:
                    self._weekly_plan = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load weekly plan: {e}")
                self._weekly_plan = None

    def _get_sample_recommendations(self) -> List[Dict]:
        """Get sample AI recommendations for demo purposes."""
        return [
            {
                "symbol": "AARTIIND",
                "action": "SELL",
                "confidence": 78,
                "reasoning": "Stock has declined 21.8% from purchase price. Fundamentals show deteriorating margins and high valuation (P/E 24.5 vs industry 18.2). Recent quarterly results missed expectations with revenue down 6%.",
                "analysis_type": "fundamental_analysis",
                "current_price": 377.85,
                "target_price": None,
                "stop_loss": 350.0,
                "quantity": 50,
                "potential_impact": "Free up ₹18,893 for better opportunities",
                "risk_level": "medium",
                "time_horizon": "immediate",
                "alternative_suggestions": ["Consider switching to APOLLOHOSP or DRREDDY in healthcare sector"]
            },
            {
                "symbol": "ASTERDM",
                "action": "BOOK_PROFIT",
                "confidence": 85,
                "reasoning": "Position up 78.7% since purchase. Strong fundamentals with ROE 21.2% and debt-to-equity 0.4. However, valuation has become stretched (P/E 28.5). Book 50% profit to secure gains while keeping exposure.",
                "analysis_type": "valuation_analysis",
                "current_price": 658.5,
                "target_price": 700.0,
                "stop_loss": 580.0,
                "quantity": 25,  # Half position
                "potential_impact": "Lock in ₹72,475 profit, reduce risk",
                "risk_level": "low",
                "time_horizon": "short_term",
                "alternative_suggestions": ["Consider adding to MAXHEALTH or NH in healthcare"]
            },
            {
                "symbol": "BANKBARODA",
                "action": "KEEP",
                "confidence": 72,
                "reasoning": "Banking sector recovery play. Stock up 82.9% with strong fundamentals. ROE 14.8%, NPA ratio improving. Recent RBI policy supportive. Continue holding for medium-term upside.",
                "analysis_type": "sector_analysis",
                "current_price": 266.0,
                "target_price": 320.0,
                "stop_loss": 220.0,
                "quantity": None,  # Keep full position
                "potential_impact": "Maintain exposure to banking sector recovery",
                "risk_level": "medium",
                "time_horizon": "medium_term",
                "alternative_suggestions": ["Monitor HDFCBANK and ICICIBANK for relative strength"]
            },
            {
                "symbol": "OIL",
                "action": "ADD",
                "confidence": 68,
                "reasoning": "Energy sector showing strong momentum. Stock up 363% with improving fundamentals. Oil prices stabilizing, government focus on energy security. Undervalued at current P/E of 8.2 vs historical 12.5.",
                "analysis_type": "technical_analysis",
                "current_price": 419.75,
                "target_price": 550.0,
                "stop_loss": 350.0,
                "quantity": 50,
                "potential_impact": "Add ₹20,987 exposure to energy sector",
                "risk_level": "high",
                "time_horizon": "medium_term",
                "alternative_suggestions": ["Consider NTPC or POWERGRID as alternatives"]
            },
            {
                "symbol": "CAPACITE",
                "action": "REDUCE",
                "confidence": 82,
                "reasoning": "IT sector stock showing weakness. Down 24.3% with deteriorating fundamentals. Revenue growth slowing, margins under pressure. High concentration risk in portfolio (IT sector exposure). Reduce position to rebalance.",
                "analysis_type": "risk_analysis",
                "current_price": 283.7,
                "target_price": None,
                "stop_loss": 250.0,
                "quantity": 15,  # Reduce by 50%
                "potential_impact": "Reduce IT sector concentration, free up ₹4,256",
                "risk_level": "high",
                "time_horizon": "immediate",
                "alternative_suggestions": ["Consider TCS or INFY for IT exposure"]
            }
        ]
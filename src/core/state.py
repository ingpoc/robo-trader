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
import tempfile
import os
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
    """Manages persistent state storage with atomic file operations and proper locking."""

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

        # Thread-safe locks for different operations
        self._memory_lock = asyncio.Lock()  # Protects in-memory state
        self._file_locks: Dict[Path, asyncio.Lock] = {}  # Per-file locks

        # Alert manager
        self.alert_manager = AlertManager(state_dir)

        # Load initial state (synchronous for __init__)
        self._load_portfolio_sync()
        self._load_intents_sync()
        self._load_screening_sync()
        self._load_strategy_sync()
        self._load_priority_queue_sync()
        self._load_approval_queue_sync()
        self._load_weekly_plan_sync()

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """Get or create a file-specific lock."""
        if file_path not in self._file_locks:
            self._file_locks[file_path] = asyncio.Lock()
        return self._file_locks[file_path]

    async def _read_json_atomic(self, file_path: Path, lock_timeout: float = 10.0) -> Optional[Any]:
        """Atomically read JSON file with proper error handling and lock timeout."""
        if not file_path.exists():
            return None

        lock = self._get_file_lock(file_path)

        try:
            # Acquire lock with timeout to prevent deadlocks
            await asyncio.wait_for(lock.acquire(), timeout=lock_timeout)

            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error reading {file_path}: {e}")
                return None
            finally:
                lock.release()

        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring lock for {file_path} after {lock_timeout}s")
            return None

    async def _write_json_atomic(self, file_path: Path, data: Any, lock_timeout: float = 10.0) -> bool:
        """Atomically write JSON file using temporary file + rename with lock timeout."""
        lock = self._get_file_lock(file_path)

        try:
            # Acquire lock with timeout to prevent deadlocks
            await asyncio.wait_for(lock.acquire(), timeout=lock_timeout)

            try:
                # Create temporary file in same directory for atomic rename
                temp_fd, temp_path = tempfile.mkstemp(
                    suffix='.tmp',
                    prefix=file_path.stem + '_',
                    dir=file_path.parent
                )

                try:
                    # Write to temporary file
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                        json.dump(data, temp_file, indent=2, ensure_ascii=False)

                    # Atomic rename (works across filesystems on POSIX)
                    os.rename(temp_path, file_path)
                    return True

                except Exception as e:
                    # Clean up temp file on error
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    raise e

            except Exception as e:
                logger.error(f"Failed to write {file_path}: {e}")
                return False
            finally:
                lock.release()

        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring lock for {file_path} after {lock_timeout}s")
            return False

    async def _read_modify_write_atomic(self, file_path: Path, modifier_func) -> bool:
        """Atomically read-modify-write a JSON file."""
        async with self._get_file_lock(file_path):
            try:
                # Read current data
                current_data = []
                if file_path.exists():
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        current_data = json.loads(content)
                        if not isinstance(current_data, list):
                            current_data = [current_data]

                # Apply modification
                modified_data = modifier_func(current_data)

                # Write atomically
                return await self._write_json_atomic(file_path, modified_data)

            except Exception as e:
                logger.error(f"Failed to read-modify-write {file_path}: {e}")
                return False

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        async with self._memory_lock:
            return self._portfolio

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._memory_lock:
            self._portfolio = portfolio
            success = await self._write_json_atomic(self.portfolio_file, portfolio.to_dict())
            if success:
                logger.info(f"Portfolio updated as of {portfolio.as_of}")
            else:
                logger.error("Failed to save portfolio to disk")

    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        async with self._memory_lock:
            return self._intents.get(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        async with self._memory_lock:
            return list(self._intents.values())

    async def create_intent(self, symbol: str, signal: Optional[Signal] = None, source: str = "system") -> Intent:
        """Create new trading intent."""
        async with self._memory_lock:
            intent_id = f"intent_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"
            intent = Intent(
                id=intent_id,
                symbol=symbol,
                signal=signal,
                source=source
            )
            self._intents[intent_id] = intent
            success = await self._write_json_atomic(self.intents_file, {k: v.to_dict() for k, v in self._intents.items()})
            if success:
                logger.info(f"Created intent {intent_id} for {symbol}")
            else:
                logger.error(f"Failed to save intent {intent_id} to disk")
            return intent

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        async with self._memory_lock:
            self._intents[intent.id] = intent
            success = await self._write_json_atomic(self.intents_file, {k: v.to_dict() for k, v in self._intents.items()})
            if success:
                logger.info(f"Updated intent {intent.id}")
            else:
                logger.error(f"Failed to save intent {intent.id} to disk")

    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        async with self._memory_lock:
            self._screening_results = results
            success = await self._write_json_atomic(self.screening_file, results)
            if not success:
                logger.error("Failed to save screening results to disk")

    async def get_screening_results(self) -> Optional[Dict[str, Any]]:
        async with self._memory_lock:
            return self._screening_results

    async def update_strategy_results(self, results: Optional[Dict[str, Any]]) -> None:
        async with self._memory_lock:
            self._strategy_results = results
            success = await self._write_json_atomic(self.strategy_file, results)
            if not success:
                logger.error("Failed to save strategy results to disk")

    async def get_strategy_results(self) -> Optional[Dict[str, Any]]:
        async with self._memory_lock:
            return self._strategy_results

    # NEW: AI Planning methods
    async def save_daily_plan(self, plan: Dict) -> None:
        """Save AI-generated daily work plan."""
        plan_file = self.daily_plans_dir / f"{plan['date']}.json"
        success = await self._write_json_atomic(plan_file, plan)
        if success:
            logger.debug(f"Saved daily plan for {plan['date']}")
        else:
            logger.error(f"Failed to save daily plan for {plan['date']}")

    async def load_daily_plan(self, date: str) -> Optional[Dict]:
        """Load daily plan for specific date."""
        plan_file = self.daily_plans_dir / f"{date}.json"
        return await self._read_json_atomic(plan_file)

    # NEW: Analysis history tracking with size-based rotation and compression
    async def save_analysis_history(self, symbol: str, analysis: Dict) -> None:
        """Save detailed analysis history per stock with size-based rotation and compression."""
        history_file = self.analysis_history_dir / f"{symbol}.json"
        compressed_file = self.analysis_history_dir / f"{symbol}_compressed.json"

        def modify_history(current_history):
            # Ensure current_history is a list
            if not isinstance(current_history, list):
                current_history = []

            # Add new analysis
            new_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis": analysis
            }
            current_history.append(new_entry)

            # Size-based rotation: keep max 1000 recent entries
            if len(current_history) > 1000:
                # Compress older entries (keep last 500, compress first 500)
                recent_entries = current_history[-500:]
                older_entries = current_history[:-500]

                # Compress older entries by removing detailed analysis data
                compressed_entries = []
                for entry in older_entries:
                    compressed_entries.append({
                        "timestamp": entry["timestamp"],
                        "compressed": True,
                        "summary": self._compress_analysis(entry["analysis"])
                    })

                # Save compressed data to separate file
                asyncio.create_task(self._save_compressed_history(compressed_file, compressed_entries))

                return recent_entries

            # Time-based cleanup: keep last 30 days for recent entries
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            return [h for h in current_history if h["timestamp"] > cutoff.isoformat()]

        success = await self._read_modify_write_atomic(history_file, modify_history)
        if success:
            logger.debug(f"Saved analysis history for {symbol}")
        else:
            logger.error(f"Failed to save analysis history for {symbol}")

    # NEW: Priority queue for urgent events
    async def add_priority_item(self, symbol: str, reason: str, priority: str) -> None:
        """Add item to priority queue for urgent analysis."""
        async with self._memory_lock:
            self._priority_queue.append({
                "symbol": symbol,
                "reason": reason,
                "priority": priority,
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            success = await self._write_json_atomic(self.priority_queue_file, self._priority_queue)
            if not success:
                logger.error("Failed to save priority queue to disk")

    async def get_priority_items(self) -> List[Dict]:
        """Get items needing urgent attention."""
        async with self._memory_lock:
            return self._priority_queue.copy()

    # NEW: Approval queue management
    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add AI recommendation to user approval queue with deduplication."""
        async with self._memory_lock:
            symbol = recommendation.get("symbol", "")
            action = recommendation.get("action", "")

            # Check for duplicates in memory
            for existing in self._approval_queue:
                existing_rec = existing.get("recommendation", {})
                if (existing.get("status") == "pending" and
                    existing_rec.get("symbol") == symbol and
                    existing_rec.get("action") == action):
                    logger.debug(f"Skipping duplicate recommendation for {symbol} {action}")
                    return

            # Add new recommendation
            new_item = {
                "id": f"rec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}_{action}",
                "recommendation": recommendation,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._approval_queue.append(new_item)

            success = await self._write_json_atomic(self.approval_queue_file, self._approval_queue)
            if not success:
                logger.error("Failed to save approval queue to disk")

    async def get_pending_approvals(self) -> List[Dict]:
        """Get recommendations awaiting user approval."""
        async with self._memory_lock:
            # If no recommendations exist, add some sample ones for demo
            if not self._approval_queue:
                sample_recommendations = self._get_sample_recommendations()
                for rec in sample_recommendations:
                    await self.add_to_approval_queue(rec)

            return [item for item in self._approval_queue if item["status"] == "pending"]

    async def update_approval_status(self, recommendation_id: str, status: str, user_feedback: Optional[str] = None) -> bool:
        """Update approval status for a recommendation."""
        async with self._memory_lock:
            for item in self._approval_queue:
                if item["id"] == recommendation_id:
                    item["status"] = status
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if user_feedback:
                        item["user_feedback"] = user_feedback

                    success = await self._write_json_atomic(self.approval_queue_file, self._approval_queue)
                    if not success:
                        logger.error(f"Failed to save approval queue update for {recommendation_id}")
                    return success
            return False

    # NEW: Weekly plan management
    async def save_weekly_plan(self, plan: Dict) -> None:
        """Save AI-generated weekly work distribution plan."""
        async with self._memory_lock:
            success = await self._write_json_atomic(self.weekly_plan_file, plan)
            if success:
                self._weekly_plan = plan
                logger.debug("Saved weekly plan")
            else:
                logger.error("Failed to save weekly plan to disk")

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load current weekly plan."""
        async with self._memory_lock:
            return self._weekly_plan.copy() if self._weekly_plan else None

    # NEW: Learning insights storage
    async def save_learning_insights(self, insights: Dict) -> None:
        """Save AI learning insights from recommendation outcomes."""
        def modify_insights(current_insights):
            if not isinstance(current_insights, list):
                current_insights = []

            # Add new insights
            current_insights.append(insights)

            # Keep last 50 insights
            return current_insights[-50:]

        success = await self._read_modify_write_atomic(self.learning_insights_file, modify_insights)
        if success:
            logger.debug("Saved learning insights")
        else:
            logger.error("Failed to save learning insights")

    async def get_learning_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent learning insights."""
        insights = await self._read_json_atomic(self.learning_insights_file)
        if insights and isinstance(insights, list):
            return insights[-limit:]
        return []

    # NEW: Analysis history compression methods
    def _compress_analysis(self, analysis: Dict) -> Dict:
        """Compress analysis data by removing detailed fields."""
        compressed = {
            "type": analysis.get("analysis_type", "unknown"),
            "action": analysis.get("action"),
            "confidence": analysis.get("confidence"),
            "risk_level": analysis.get("risk_level"),
            "timestamp": analysis.get("timestamp")
        }

        # Keep only essential fields, remove verbose content
        if "reasoning" in analysis:
            # Truncate reasoning to first 100 characters
            compressed["reasoning_summary"] = analysis["reasoning"][:100] + "..." if len(analysis["reasoning"]) > 100 else analysis["reasoning"]

        return compressed

    async def _save_compressed_history(self, compressed_file: Path, compressed_entries: List[Dict]) -> None:
        """Save compressed analysis history to separate file."""
        try:
            success = await self._write_json_atomic(compressed_file, compressed_entries)
            if success:
                logger.debug(f"Saved compressed history to {compressed_file}")
            else:
                logger.warning(f"Failed to save compressed history to {compressed_file}")
        except Exception as e:
            logger.error(f"Error saving compressed history: {e}")

    async def get_analysis_history(self, symbol: str, include_compressed: bool = False, limit: int = 100) -> List[Dict]:
        """Get analysis history for a symbol, optionally including compressed data."""
        history_file = self.analysis_history_dir / f"{symbol}.json"
        compressed_file = self.analysis_history_dir / f"{symbol}_compressed.json"

        # Get recent history
        recent_history = await self._read_json_atomic(history_file)
        if not recent_history:
            recent_history = []

        result = recent_history[-limit:] if len(recent_history) > limit else recent_history

        # Optionally include compressed history
        if include_compressed:
            compressed_history = await self._read_json_atomic(compressed_file)
            if compressed_history and isinstance(compressed_history, list):
                # Add compressed entries (they're already limited)
                result.extend(compressed_history)

        # Sort by timestamp
        result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return result[:limit]

    async def create_checkpoint(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a checkpoint of current state."""
        async with self._memory_lock:
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
            success = await self._write_json_atomic(checkpoint_file, checkpoint_data)
            if success:
                logger.info(f"Created checkpoint {checkpoint_id}: {name}")
                return checkpoint_id
            else:
                logger.error(f"Failed to create checkpoint {checkpoint_id}")
                raise RuntimeError(f"Failed to create checkpoint {checkpoint_id}")

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore state from checkpoint."""
        async with self._memory_lock:
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            data = await self._read_json_atomic(checkpoint_file)
            if not data:
                logger.error(f"Checkpoint {checkpoint_id} not found")
                return False

            # Restore portfolio
            if data.get('portfolio'):
                self._portfolio = PortfolioState.from_dict(data['portfolio'])

            # Restore intents
            self._intents = {}
            for intent_id, intent_data in data.get('intents', {}).items():
                self._intents[intent_id] = Intent.from_dict(intent_data)

            # Save restored state
            portfolio_success = await self._write_json_atomic(self.portfolio_file, self._portfolio.to_dict() if self._portfolio else None)
            intents_success = await self._write_json_atomic(self.intents_file, {k: v.to_dict() for k, v in self._intents.items()})

            if portfolio_success and intents_success:
                logger.info(f"Restored checkpoint {checkpoint_id}")
                return True
            else:
                logger.error(f"Failed to save restored checkpoint {checkpoint_id}")
                return False

    def _load_portfolio_sync(self) -> None:
        """Load portfolio from file synchronously for __init__."""
        try:
            data = self._read_json_sync(self.portfolio_file)
            if data:
                self._portfolio = PortfolioState.from_dict(data)
                logger.info("Portfolio loaded from file")
            else:
                self._portfolio = None
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            self._portfolio = None

    def _read_json_sync(self, file_path: Path) -> Optional[Any]:
        """Synchronous JSON read for initialization."""
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    def _load_intents_sync(self) -> None:
        """Load intents from file synchronously for __init__."""
        try:
            data = self._read_json_sync(self.intents_file)
            if data:
                self._intents = {}
                for intent_id, intent_data in data.items():
                    self._intents[intent_id] = Intent.from_dict(intent_data)
                logger.info(f"Loaded {len(self._intents)} intents from file")
            else:
                self._intents = {}
        except Exception as e:
            logger.error(f"Failed to load intents: {e}")
            self._intents = {}

    def _load_screening_sync(self) -> None:
        """Load screening results synchronously for __init__."""
        try:
            self._screening_results = self._read_json_sync(self.screening_file)
        except Exception as e:
            logger.error(f"Failed to load screening results: {e}")
            self._screening_results = None

    def _load_strategy_sync(self) -> None:
        """Load strategy results synchronously for __init__."""
        try:
            self._strategy_results = self._read_json_sync(self.strategy_file)
        except Exception as e:
            logger.error(f"Failed to load strategy analysis: {e}")
            self._strategy_results = None

    # NEW: AI State management methods
    def _load_priority_queue_sync(self) -> None:
        """Load priority queue from file synchronously for __init__."""
        try:
            data = self._read_json_sync(self.priority_queue_file)
            self._priority_queue = data if data else []
        except Exception as e:
            logger.error(f"Failed to load priority queue: {e}")
            self._priority_queue = []

    def _load_approval_queue_sync(self) -> None:
        """Load approval queue from file synchronously for __init__."""
        try:
            data = self._read_json_sync(self.approval_queue_file)
            self._approval_queue = data if data else []
        except Exception as e:
            logger.error(f"Failed to load approval queue: {e}")
            self._approval_queue = []

    def _load_weekly_plan_sync(self) -> None:
        """Load weekly plan from file synchronously for __init__."""
        try:
            self._weekly_plan = self._read_json_sync(self.weekly_plan_file)
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
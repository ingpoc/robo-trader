"""Persist daily strategy logs and Claude's self-reflection."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyLog:
    """Daily strategy log entry."""

    date: str  # ISO format date
    strategy_type: str  # "swing_trading" or "options_trading"
    what_worked: List[str] = field(default_factory=list)
    what_didnt_work: List[str] = field(default_factory=list)
    tomorrows_focus: List[str] = field(default_factory=list)
    market_observations: List[str] = field(default_factory=list)
    trades_executed: int = 0
    wins: int = 0
    losses: int = 0
    pnl_realized: float = 0.0
    token_usage: Dict[str, int] = field(
        default_factory=lambda: {"used": 0, "limit": 10000}
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "StrategyLog":
        """Create from dict."""
        return StrategyLog(**data)


class StrategyLogStore:
    """Persistent store for daily strategy logs."""

    def __init__(self, db_connection):
        """Initialize store with database connection.

        Args:
            db_connection: Active database connection
        """
        self.db = db_connection
        self._logs: Dict[str, List[StrategyLog]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load logs from database."""
        if self._initialized:
            return

        try:
            # Load all logs from database
            query = "SELECT * FROM strategy_logs ORDER BY strategy_type, date DESC"
            cursor = await self.db.execute(query)
            rows = await cursor.fetchall()

            self._logs = {}
            for row in rows:
                strategy_type = row[1]  # strategy_type column
                log = StrategyLog(
                    date=row[2],  # date column
                    strategy_type=strategy_type,
                    what_worked=json.loads(row[3]) if row[3] else [],
                    what_didnt_work=json.loads(row[4]) if row[4] else [],
                    tomorrows_focus=json.loads(row[5]) if row[5] else [],
                    market_observations=json.loads(row[6]) if row[6] else [],
                    trades_executed=row[7] or 0,
                    wins=row[8] or 0,
                    losses=row[9] or 0,
                    pnl_realized=row[10] or 0.0,
                    token_usage=(
                        json.loads(row[11]) if row[11] else {"used": 0, "limit": 10000}
                    ),
                    metadata=json.loads(row[12]) if row[12] else {},
                    created_at=row[13] or datetime.now().isoformat(),
                    updated_at=row[14] or datetime.now().isoformat(),
                )

                if strategy_type not in self._logs:
                    self._logs[strategy_type] = []
                self._logs[strategy_type].append(log)

            logger.info("Loaded strategy logs from database")

        except Exception as e:
            logger.error(f"Failed to load strategy logs from database: {e}")
            self._logs = {}

        self._initialized = True

    async def add_log(self, strategy_type: str, log: StrategyLog) -> None:
        """Add a new strategy log entry."""
        if strategy_type not in self._logs:
            self._logs[strategy_type] = []

        # Update timestamps
        log.updated_at = datetime.now().isoformat()

        # Check if log for today already exists, update or append
        today_iso = date.today().isoformat()
        existing_index = None

        for i, existing_log in enumerate(self._logs[strategy_type]):
            if existing_log.date == today_iso:
                existing_index = i
                break

        if existing_index is not None:
            # Merge with existing log
            existing = self._logs[strategy_type][existing_index]
            existing.what_worked.extend(log.what_worked)
            existing.what_didnt_work.extend(log.what_didnt_work)
            existing.tomorrows_focus = log.tomorrows_focus
            existing.market_observations.extend(log.market_observations)
            existing.trades_executed += log.trades_executed
            existing.wins += log.wins
            existing.losses += log.losses
            existing.pnl_realized += log.pnl_realized
            existing.updated_at = datetime.now().isoformat()
        else:
            self._logs[strategy_type].append(log)

        await self._save_log(strategy_type, log)

    async def get_today_log(self, strategy_type: str) -> Optional[StrategyLog]:
        """Get today's log for a strategy type."""
        if strategy_type not in self._logs:
            return None

        today_iso = date.today().isoformat()

        for log in self._logs[strategy_type]:
            if log.date == today_iso:
                return log

        return None

    async def get_logs_for_period(
        self, strategy_type: str, start_date: date, end_date: date
    ) -> List[StrategyLog]:
        """Get logs for a date range."""
        if strategy_type not in self._logs:
            return []

        result = []
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        for log in self._logs[strategy_type]:
            if start_iso <= log.date <= end_iso:
                result.append(log)

        return sorted(result, key=lambda x: x.date)

    async def get_recent_logs(
        self, strategy_type: str, days: int = 30
    ) -> List[StrategyLog]:
        """Get recent logs (last N days)."""
        start_date = date.today()
        from datetime import timedelta

        start_date = start_date - timedelta(days=days)
        end_date = date.today()

        return await self.get_logs_for_period(strategy_type, start_date, end_date)

    async def get_performance_summary(
        self, strategy_type: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get performance summary for a strategy."""
        logs = await self.get_recent_logs(strategy_type, days)

        if not logs:
            return {}

        total_trades = sum(log.trades_executed for log in logs)
        total_wins = sum(log.wins for log in logs)
        total_losses = sum(log.losses for log in logs)
        total_pnl = sum(log.pnl_realized for log in logs)

        return {
            "period_days": days,
            "total_logs": len(logs),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": (total_wins / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0,
        }

    async def get_insights(self, strategy_type: str, days: int = 30) -> Dict[str, Any]:
        """Extract insights from logs."""
        logs = await self.get_recent_logs(strategy_type, days)

        if not logs:
            return {}

        # Collect all what worked and didn't work
        what_worked_all = {}
        what_didnt_all = {}

        for log in logs:
            for item in log.what_worked:
                what_worked_all[item] = what_worked_all.get(item, 0) + 1

            for item in log.what_didnt_work:
                what_didnt_all[item] = what_didnt_all.get(item, 0) + 1

        # Sort by frequency
        top_working = sorted(what_worked_all.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        top_failing = sorted(what_didnt_all.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return {
            "period_days": days,
            "top_working_strategies": [item[0] for item in top_working],
            "top_failing_approaches": [item[0] for item in top_failing],
            "most_recent_focus": logs[-1].tomorrows_focus if logs else [],
        }

    async def _save_log(self, strategy_type: str, log: StrategyLog) -> None:
        """Persist log to database."""
        try:
            query = """
                INSERT INTO strategy_logs (
                    strategy_type, date, what_worked, what_didnt_work,
                    tomorrows_focus, market_observations, trades_executed,
                    wins, losses, pnl_realized, token_usage, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (strategy_type, date) DO UPDATE SET
                    what_worked = excluded.what_worked,
                    what_didnt_work = excluded.what_didnt_work,
                    tomorrows_focus = excluded.tomorrows_focus,
                    market_observations = excluded.market_observations,
                    trades_executed = excluded.trades_executed,
                    wins = excluded.wins,
                    losses = excluded.losses,
                    pnl_realized = excluded.pnl_realized,
                    token_usage = excluded.token_usage,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
            """

            await self.db.execute(
                query,
                (
                    log.strategy_type,
                    log.date,
                    json.dumps(log.what_worked),
                    json.dumps(log.what_didnt_work),
                    json.dumps(log.tomorrows_focus),
                    json.dumps(log.market_observations),
                    log.trades_executed,
                    log.wins,
                    log.losses,
                    log.pnl_realized,
                    json.dumps(log.token_usage),
                    json.dumps(log.metadata),
                    log.created_at,
                    log.updated_at,
                ),
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to save strategy log for {strategy_type}: {e}")
            await self.db.rollback()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass

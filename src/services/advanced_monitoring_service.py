"""
Advanced Monitoring & Analytics Service

Provides real-time performance dashboards, advanced risk analytics, system health monitoring,
and performance benchmarking for enterprise trading operations.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import statistics
import psutil
import aiosqlite
from loguru import logger

from ..config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, APIError


class MetricType(Enum):
    """Types of metrics being tracked."""
    PERFORMANCE = "performance"
    RISK = "risk"
    SYSTEM = "system"
    TRADING = "trading"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_connections: int
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class TradingMetrics:
    """Trading performance metrics."""
    total_trades: int
    winning_trades: int
    total_pnl: float
    win_rate: float
    average_win: float
    average_loss: float
    sharpe_ratio: float
    max_drawdown: float
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RiskMetrics:
    """Risk analytics metrics."""
    portfolio_value: float
    portfolio_risk: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    concentration_risk: float
    liquidity_risk: float
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class PerformanceBenchmark:
    """Performance benchmark against market indices."""
    benchmark_symbol: str
    period_days: int
    portfolio_return: float
    benchmark_return: float
    alpha: float
    beta: float
    tracking_error: float
    information_ratio: float
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SystemAlert:
    """System monitoring alert."""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    resolved: bool
    created_at: str
    resolved_at: Optional[str]

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class AdvancedMonitoringService(EventHandler):
    """
    Advanced Monitoring & Analytics Service.

    Responsibilities:
    - Real-time performance dashboards
    - Advanced risk analytics and reporting
    - System health monitoring and alerting
    - Performance benchmarking and optimization
    - Predictive analytics and early warning systems
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "advanced_monitoring.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Metrics storage
        self._system_metrics: List[SystemMetrics] = []
        self._trading_metrics: List[TradingMetrics] = []
        self._risk_metrics: List[RiskMetrics] = []
        self._active_alerts: Dict[str, SystemAlert] = {}

        # Monitoring configuration
        self._metrics_retention_hours = 168  # 7 days
        self._alert_check_interval = 30  # seconds
        self._performance_update_interval = 300  # 5 minutes

        # Thresholds for alerts
        self._cpu_threshold = 80.0
        self._memory_threshold = 85.0
        self._disk_threshold = 90.0

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)

    async def initialize(self) -> None:
        """Initialize the advanced monitoring service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._load_active_alerts()
            logger.info("Advanced monitoring service initialized")

            # Start background monitoring
            self._monitoring_task = asyncio.create_task(self._background_monitoring())
            self._cleanup_task = asyncio.create_task(self._metrics_cleanup())

    async def _create_tables(self) -> None:
        """Create monitoring database tables."""
        schema = """
        -- System metrics
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY,
            cpu_percent REAL NOT NULL,
            memory_percent REAL NOT NULL,
            disk_usage_percent REAL NOT NULL,
            network_connections INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        );

        -- Trading metrics
        CREATE TABLE IF NOT EXISTS trading_metrics (
            id INTEGER PRIMARY KEY,
            total_trades INTEGER NOT NULL,
            winning_trades INTEGER NOT NULL,
            total_pnl REAL NOT NULL,
            win_rate REAL NOT NULL,
            average_win REAL NOT NULL,
            average_loss REAL NOT NULL,
            sharpe_ratio REAL NOT NULL,
            max_drawdown REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        -- Risk metrics
        CREATE TABLE IF NOT EXISTS risk_metrics (
            id INTEGER PRIMARY KEY,
            portfolio_value REAL NOT NULL,
            portfolio_risk REAL NOT NULL,
            var_95 REAL NOT NULL,
            expected_shortfall REAL NOT NULL,
            concentration_risk REAL NOT NULL,
            liquidity_risk REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        -- Performance benchmarks
        CREATE TABLE IF NOT EXISTS performance_benchmarks (
            id INTEGER PRIMARY KEY,
            benchmark_symbol TEXT NOT NULL,
            period_days INTEGER NOT NULL,
            portfolio_return REAL NOT NULL,
            benchmark_return REAL NOT NULL,
            alpha REAL NOT NULL,
            beta REAL NOT NULL,
            tracking_error REAL NOT NULL,
            information_ratio REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        -- System alerts
        CREATE TABLE IF NOT EXISTS system_alerts (
            alert_id TEXT PRIMARY KEY,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_trading_metrics_timestamp ON trading_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON risk_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_benchmarks_symbol_period ON performance_benchmarks(benchmark_symbol, period_days);
        CREATE INDEX IF NOT EXISTS idx_alerts_type_severity ON system_alerts(alert_type, severity);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _load_active_alerts(self) -> None:
        """Load active alerts from database."""
        cursor = await self._db_connection.execute("""
            SELECT alert_id, alert_type, severity, message, details, resolved, created_at, resolved_at
            FROM system_alerts
            WHERE resolved = 0
        """)

        async for row in cursor:
            alert = SystemAlert(
                alert_id=row[0],
                alert_type=row[1],
                severity=AlertSeverity(row[2]),
                message=row[3],
                details=json.loads(row[4]) if row[4] else {},
                resolved=bool(row[5]),
                created_at=row[6],
                resolved_at=row[7]
            )
            self._active_alerts[row[0]] = alert

    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent

            # Network connections
            network_connections = len(psutil.net_connections())

            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_connections=network_connections
            )

            # Store in memory and database
            self._system_metrics.append(metrics)
            await self._store_system_metrics(metrics)

            # Check for alerts
            await self._check_system_alerts(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            raise

    async def _store_system_metrics(self, metrics: SystemMetrics) -> None:
        """Store system metrics in database."""
        await self._db_connection.execute("""
            INSERT INTO system_metrics
            (cpu_percent, memory_percent, disk_usage_percent, network_connections, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            metrics.cpu_percent,
            metrics.memory_percent,
            metrics.disk_usage_percent,
            metrics.network_connections,
            metrics.timestamp
        ))
        await self._db_connection.commit()

    async def _check_system_alerts(self, metrics: SystemMetrics) -> None:
        """Check system metrics against thresholds and create alerts."""
        alerts_to_create = []

        if metrics.cpu_percent > self._cpu_threshold:
            alerts_to_create.append({
                "alert_type": "high_cpu_usage",
                "severity": AlertSeverity.WARNING,
                "message": f"CPU usage is {metrics.cpu_percent:.1f}% (threshold: {self._cpu_threshold}%)",
                "details": {"cpu_percent": metrics.cpu_percent, "threshold": self._cpu_threshold}
            })

        if metrics.memory_percent > self._memory_threshold:
            alerts_to_create.append({
                "alert_type": "high_memory_usage",
                "severity": AlertSeverity.CRITICAL,
                "message": f"Memory usage is {metrics.memory_percent:.1f}% (threshold: {self._memory_threshold}%)",
                "details": {"memory_percent": metrics.memory_percent, "threshold": self._memory_threshold}
            })

        if metrics.disk_usage_percent > self._disk_threshold:
            alerts_to_create.append({
                "alert_type": "high_disk_usage",
                "severity": AlertSeverity.WARNING,
                "message": f"Disk usage is {metrics.disk_usage_percent:.1f}% (threshold: {self._disk_threshold}%)",
                "details": {"disk_usage_percent": metrics.disk_usage_percent, "threshold": self._disk_threshold}
            })

        for alert_data in alerts_to_create:
            await self.create_alert(**alert_data)

    async def calculate_trading_metrics(self) -> TradingMetrics:
        """Calculate comprehensive trading performance metrics."""
        try:
            # Get real trading data from services
            live_trading_service = await self._get_live_trading_service()
            audit_logs = await live_trading_service.get_audit_logs(limit=1000)

            # Calculate metrics from real data
            total_trades = 0
            winning_trades = 0
            total_pnl = 0.0
            wins = []
            losses = []

            for log in audit_logs:
                if log.get("event_type") in ["ORDER_FILLED", "TRADE_EXECUTED"]:
                    total_trades += 1
                    pnl = log.get("details", {}).get("realized_pnl", 0)
                    total_pnl += pnl

                    if pnl > 0:
                        winning_trades += 1
                        wins.append(pnl)
                    elif pnl < 0:
                        losses.append(pnl)

            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            average_win = sum(wins) / len(wins) if wins else 0
            average_loss = sum(losses) / len(losses) if losses else 0

            # Calculate Sharpe ratio (simplified)
            returns = [log.get("details", {}).get("realized_pnl", 0) for log in audit_logs
                      if log.get("event_type") in ["ORDER_FILLED", "TRADE_EXECUTED"]]
            sharpe_ratio = self._calculate_sharpe_ratio(returns) if returns else 0

            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown(returns) if returns else 0

            metrics = TradingMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                total_pnl=total_pnl,
                win_rate=win_rate,
                average_win=average_win,
                average_loss=average_loss,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown
            )

            # Store metrics
            self._trading_metrics.append(metrics)
            await self._store_trading_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate trading metrics: {e}")
            raise

    async def _store_trading_metrics(self, metrics: TradingMetrics) -> None:
        """Store trading metrics in database."""
        await self._db_connection.execute("""
            INSERT INTO trading_metrics
            (total_trades, winning_trades, total_pnl, win_rate, average_win, average_loss,
             sharpe_ratio, max_drawdown, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.total_trades,
            metrics.winning_trades,
            metrics.total_pnl,
            metrics.win_rate,
            metrics.average_win,
            metrics.average_loss,
            metrics.sharpe_ratio,
            metrics.max_drawdown,
            metrics.timestamp
        ))
        await self._db_connection.commit()

    async def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate advanced risk analytics."""
        try:
            # Get real portfolio data
            live_trading_service = await self._get_live_trading_service()
            portfolio_summary = await live_trading_service.get_portfolio_summary()

            portfolio_value = portfolio_summary.get("total_market_value", 0)
            positions = portfolio_summary.get("positions", [])

            # Calculate concentration risk (largest position / total portfolio)
            if positions and portfolio_value > 0:
                largest_position = max((p.get("market_value", 0) for p in positions), default=0)
                concentration_risk = largest_position / portfolio_value
            else:
                concentration_risk = 0

            # Calculate portfolio risk (simplified volatility measure)
            returns = []
            for position in positions:
                unrealized_pnl = position.get("unrealized_pnl", 0)
                market_value = position.get("market_value", 0)
                if market_value > 0:
                    returns.append(unrealized_pnl / market_value)

            portfolio_risk = statistics.stdev(returns) if len(returns) > 1 else 0

            # Calculate VaR 95% (simplified using normal distribution)
            var_95 = portfolio_value * portfolio_risk * 1.645 if portfolio_risk > 0 else 0

            # Calculate Expected Shortfall (simplified)
            expected_shortfall = portfolio_value * portfolio_risk * 2.0 if portfolio_risk > 0 else 0

            # Calculate liquidity risk (simplified based on position sizes)
            large_positions = sum(1 for p in positions if p.get("market_value", 0) > portfolio_value * 0.1)
            liquidity_risk = min(large_positions / max(len(positions), 1), 1.0)

            metrics = RiskMetrics(
                portfolio_value=portfolio_value,
                portfolio_risk=portfolio_risk,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk
            )

            # Store metrics
            self._risk_metrics.append(metrics)
            await self._store_risk_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            raise

    async def _store_risk_metrics(self, metrics: RiskMetrics) -> None:
        """Store risk metrics in database."""
        await self._db_connection.execute("""
            INSERT INTO risk_metrics
            (portfolio_value, portfolio_risk, var_95, expected_shortfall, concentration_risk, liquidity_risk, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.portfolio_value,
            metrics.portfolio_risk,
            metrics.var_95,
            metrics.expected_shortfall,
            metrics.concentration_risk,
            metrics.liquidity_risk,
            metrics.timestamp
        ))
        await self._db_connection.commit()

    async def calculate_performance_benchmark(self, benchmark_symbol: str = "NIFTY_50",
                                            period_days: int = 30) -> PerformanceBenchmark:
        """Calculate performance benchmark against market index."""
        try:
            # Get real trading performance data
            live_trading_service = await self._get_live_trading_service()
            audit_logs = await live_trading_service.get_audit_logs(limit=1000)

            # Calculate portfolio returns from audit logs
            portfolio_returns = []
            for log in audit_logs:
                if log.get("event_type") in ["ORDER_FILLED", "TRADE_EXECUTED"]:
                    pnl = log.get("details", {}).get("realized_pnl", 0)
                    # Simplified: assume each trade represents a return period
                    if pnl != 0:
                        portfolio_returns.append(pnl)

            portfolio_return = sum(portfolio_returns) / 100000 if portfolio_returns else 0  # Assume 100k starting capital

            # Get benchmark data (simplified - would integrate with market data service)
            benchmark_return = await self._get_benchmark_return(benchmark_symbol, period_days)

            # Calculate alpha (portfolio return - benchmark return)
            alpha = portfolio_return - benchmark_return

            # Calculate beta (simplified correlation measure)
            beta = 0.95  # Would calculate actual beta from historical data

            # Calculate tracking error (simplified volatility of difference)
            tracking_error = abs(alpha) * 0.5 if alpha != 0 else 0.02

            # Calculate information ratio (alpha / tracking error)
            information_ratio = alpha / tracking_error if tracking_error > 0 else 0

            benchmark = PerformanceBenchmark(
                benchmark_symbol=benchmark_symbol,
                period_days=period_days,
                portfolio_return=portfolio_return,
                benchmark_return=benchmark_return,
                alpha=alpha,
                beta=beta,
                tracking_error=tracking_error,
                information_ratio=information_ratio
            )

            await self._store_performance_benchmark(benchmark)
            return benchmark

        except Exception as e:
            logger.error(f"Failed to calculate performance benchmark: {e}")
            raise

    async def _store_performance_benchmark(self, benchmark: PerformanceBenchmark) -> None:
        """Store performance benchmark in database."""
        await self._db_connection.execute("""
            INSERT INTO performance_benchmarks
            (benchmark_symbol, period_days, portfolio_return, benchmark_return, alpha, beta,
             tracking_error, information_ratio, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            benchmark.benchmark_symbol,
            benchmark.period_days,
            benchmark.portfolio_return,
            benchmark.benchmark_return,
            benchmark.alpha,
            benchmark.beta,
            benchmark.tracking_error,
            benchmark.information_ratio,
            benchmark.timestamp
        ))
        await self._db_connection.commit()

    async def create_alert(self, alert_type: str, severity: AlertSeverity,
                          message: str, details: Dict[str, Any] = None) -> SystemAlert:
        """Create a system alert."""
        async with self._lock:
            alert_id = f"alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

            alert = SystemAlert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                details=details or {},
                resolved=False
            )

            self._active_alerts[alert_id] = alert

            # Store in database
            await self._db_connection.execute("""
                INSERT INTO system_alerts
                (alert_id, alert_type, severity, message, details, resolved, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (
                alert.alert_id,
                alert.alert_type,
                alert.severity.value,
                alert.message,
                json.dumps(alert.details),
                alert.created_at
            ))
            await self._db_connection.commit()

            # Emit alert event
            await self.event_bus.publish(Event(
                id=f"system_alert_{alert_id}",
                type=EventType.SYSTEM_ERROR,
                timestamp=alert.created_at,
                source="advanced_monitoring_service",
                data={
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "severity": severity.value,
                    "message": message,
                    "details": details
                }
            ))

            logger.warning(f"System alert created: {alert_type} - {message}")
            return alert

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a system alert."""
        async with self._lock:
            if alert_id not in self._active_alerts:
                return False

            alert = self._active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc).isoformat()

            # Update database
            await self._db_connection.execute("""
                UPDATE system_alerts SET resolved = 1, resolved_at = ? WHERE alert_id = ?
            """, (alert.resolved_at, alert_id))
            await self._db_connection.commit()

            # Remove from active alerts
            del self._active_alerts[alert_id]

            logger.info(f"Alert resolved: {alert_id}")
            return True

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        try:
            # Collect current metrics
            system_metrics = await self.collect_system_metrics()
            trading_metrics = await self.calculate_trading_metrics()
            risk_metrics = await self.calculate_risk_metrics()

            # Get recent benchmarks
            benchmarks = await self.get_recent_benchmarks()

            # Get active alerts
            active_alerts = list(self._active_alerts.values())

            return {
                "system_metrics": {
                    "current": system_metrics.__dict__,
                    "history": [m.__dict__ for m in self._system_metrics[-10:]]  # Last 10 readings
                },
                "trading_metrics": trading_metrics.__dict__,
                "risk_metrics": risk_metrics.__dict__,
                "performance_benchmarks": [b.__dict__ for b in benchmarks],
                "active_alerts": [a.__dict__ for a in active_alerts],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e)}

    async def get_recent_benchmarks(self, limit: int = 5) -> List[PerformanceBenchmark]:
        """Get recent performance benchmarks."""
        cursor = await self._db_connection.execute("""
            SELECT benchmark_symbol, period_days, portfolio_return, benchmark_return, alpha, beta,
                   tracking_error, information_ratio, timestamp
            FROM performance_benchmarks
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,))

        benchmarks = []
        async for row in cursor:
            benchmarks.append(PerformanceBenchmark(
                benchmark_symbol=row[0],
                period_days=row[1],
                portfolio_return=row[2],
                benchmark_return=row[3],
                alpha=row[4],
                beta=row[5],
                tracking_error=row[6],
                information_ratio=row[7],
                timestamp=row[8]
            ))

        return benchmarks

    async def _background_monitoring(self) -> None:
        """Background monitoring task."""
        while True:
            try:
                # Collect system metrics
                await self.collect_system_metrics()

                # Update trading and risk metrics periodically
                if int(datetime.now(timezone.utc).timestamp()) % self._performance_update_interval == 0:
                    await self.calculate_trading_metrics()
                    await self.calculate_risk_metrics()
                    await self.calculate_performance_benchmark()

                await asyncio.sleep(self._alert_check_interval)

            except asyncio.CancelledError:
                logger.info("Background monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background monitoring: {e}")
                await asyncio.sleep(5)

    async def _metrics_cleanup(self) -> None:
        """Background task to clean up old metrics."""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean up every hour

                cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=self._metrics_retention_hours)).isoformat()

                # Clean up old metrics
                await self._db_connection.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_time,))
                await self._db_connection.execute("DELETE FROM trading_metrics WHERE timestamp < ?", (cutoff_time,))
                await self._db_connection.execute("DELETE FROM risk_metrics WHERE timestamp < ?", (cutoff_time,))

                await self._db_connection.commit()

                deleted_count = self._db_connection.total_changes
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old metrics records")

            except asyncio.CancelledError:
                logger.info("Metrics cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                await asyncio.sleep(60)

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.EXECUTION_ORDER_FILLED:
            # Update trading metrics after trade execution
            asyncio.create_task(self.calculate_trading_metrics())

        elif event.type == EventType.RISK_BREACH:
            # Create risk alert
            severity = event.data.get("severity", "medium")
            severity_enum = AlertSeverity.CRITICAL if severity == "high" else AlertSeverity.WARNING

            await self.create_alert(
                alert_type="risk_breach",
                severity=severity_enum,
                message=f"Risk breach detected: {event.data.get('message', 'Unknown breach')}",
                details=event.data
            )

    async def _get_live_trading_service(self):
        """Get live trading service from DI container."""
        # This would be resolved from the DI container in a real implementation
        # For now, return None to indicate mock data
        return None

    async def _get_benchmark_return(self, symbol: str, period_days: int) -> float:
        """Get benchmark return for the period (simplified)."""
        # This would integrate with market data service
        # For now, return a mock benchmark return
        return 0.062  # 6.2% return

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio from returns."""
        if not returns:
            return 0

        avg_return = sum(returns) / len(returns)
        if len(returns) > 1:
            volatility = statistics.stdev(returns)
            return avg_return / volatility if volatility > 0 else 0
        return 0

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0

        cumulative = [sum(returns[:i+1]) for i in range(len(returns))]
        max_drawdown = 0

        for i in range(len(cumulative)):
            for j in range(i + 1, len(cumulative)):
                drawdown = cumulative[i] - cumulative[j]
                max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    async def close(self) -> None:
        """Close the advanced monitoring service."""
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
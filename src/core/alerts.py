"""
Alert Management System

Handles creation, storage, and retrieval of trading alerts.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import asyncio
from loguru import logger


@dataclass
class Alert:
    """Trading alert data structure."""
    id: str
    type: str
    severity: str
    title: str
    message: str
    timestamp: str
    symbol: str
    actionable: bool
    persistent: bool
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "Alert":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class AlertManager:
    """Manages trading alerts."""

    def __init__(self, state_dir: Path):
        self.alerts_file = state_dir / "alerts.json"
        self._alerts: Dict[str, Alert] = {}
        self._lock = asyncio.Lock()
        self._load_alerts()

    def _load_alerts(self) -> None:
        """Load alerts from file."""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r') as f:
                    data = json.load(f)
                self._alerts = {
                    alert_id: Alert.from_dict(alert_data)
                    for alert_id, alert_data in data.items()
                }
                logger.info(f"Loaded {len(self._alerts)} alerts")
            except Exception as e:
                logger.error(f"Failed to load alerts: {e}")
                self._alerts = {}

    async def _save_alerts(self) -> None:
        """Save alerts to file."""
        try:
            with open(self.alerts_file, 'w') as f:
                data = {k: v.to_dict() for k, v in self._alerts.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")

    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        symbol: str,
        actionable: bool = False,
        persistent: bool = False
    ) -> Alert:
        """Create a new alert."""
        async with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            alert_id = f"alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"

            alert = Alert(
                id=alert_id,
                type=alert_type,
                severity=severity,
                title=title,
                message=message,
                timestamp=timestamp,
                symbol=symbol,
                actionable=actionable,
                persistent=persistent
            )

            self._alerts[alert_id] = alert
            await self._save_alerts()
            logger.info(f"Created alert {alert_id}: {title}")
            return alert

    async def get_active_alerts(self) -> List[Alert]:
        """Get all active (non-acknowledged or persistent) alerts."""
        async with self._lock:
            return [
                alert for alert in self._alerts.values()
                if not alert.acknowledged or alert.persistent
            ]

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        async with self._lock:
            return self._alerts.get(alert_id)

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        async with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].acknowledged = True
                self._alerts[alert_id].acknowledged_at = datetime.now(timezone.utc).isoformat()
                await self._save_alerts()
                logger.info(f"Alert {alert_id} acknowledged")
                return True
            return False

    async def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss (delete) an alert."""
        async with self._lock:
            if alert_id in self._alerts:
                del self._alerts[alert_id]
                await self._save_alerts()
                logger.info(f"Alert {alert_id} dismissed")
                return True
            return False

    async def clear_acknowledged_alerts(self) -> int:
        """Clear all acknowledged non-persistent alerts."""
        async with self._lock:
            to_remove = [
                alert_id for alert_id, alert in self._alerts.items()
                if alert.acknowledged and not alert.persistent
            ]
            for alert_id in to_remove:
                del self._alerts[alert_id]

            if to_remove:
                await self._save_alerts()
                logger.info(f"Cleared {len(to_remove)} acknowledged alerts")

            return len(to_remove)

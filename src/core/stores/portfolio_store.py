"""
Portfolio State Store

Focused store managing only portfolio-related state.
Part of StateManager refactoring to follow Single Responsibility Principle.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict

from loguru import logger

from ..state import PortfolioState


class PortfolioStore:
    """
    Manages portfolio state with atomic operations.

    Responsibilities:
    - Portfolio snapshot storage
    - Checkpoint creation/restoration
    - Thread-safe portfolio access
    """

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.portfolio_file = self.state_dir / "portfolio.json"
        self.checkpoints_dir = self.state_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)

        self._portfolio: Optional[PortfolioState] = None
        self._lock = asyncio.Lock()
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Lazy load portfolio on first access (non-blocking)."""
        if self._loaded:
            return

        try:
            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            data = await temp_manager._read_json_atomic(self.portfolio_file)
            if data:
                self._portfolio = PortfolioState.from_dict(data)
                logger.info("Portfolio loaded from file (async)")
            else:
                self._portfolio = None
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            self._portfolio = None
        finally:
            self._loaded = True

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        async with self._lock:
            await self._ensure_loaded()
            return self._portfolio

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._lock:
            self._portfolio = portfolio

            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            success = await temp_manager._write_json_atomic(
                self.portfolio_file,
                portfolio.to_dict()
            )

            if success:
                logger.info(f"Portfolio updated as of {portfolio.as_of}")
            else:
                logger.error("Failed to save portfolio to disk")

    async def create_checkpoint(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a checkpoint of current portfolio state."""
        async with self._lock:
            await self._ensure_loaded()
            timestamp = datetime.now(timezone.utc).isoformat()
            checkpoint_id = f"checkpoint_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

            checkpoint_data = {
                "id": checkpoint_id,
                "name": name,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "portfolio": self._portfolio.to_dict() if self._portfolio else None
            }

            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"

            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            success = await temp_manager._write_json_atomic(checkpoint_file, checkpoint_data)

            if success:
                logger.info(f"Created portfolio checkpoint {checkpoint_id}: {name}")
                return checkpoint_id
            else:
                logger.error(f"Failed to create checkpoint {checkpoint_id}")
                raise RuntimeError(f"Failed to create checkpoint {checkpoint_id}")

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore portfolio state from checkpoint."""
        async with self._lock:
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"

            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            data = await temp_manager._read_json_atomic(checkpoint_file)

            if not data:
                logger.error(f"Checkpoint {checkpoint_id} not found")
                return False

            if data.get('portfolio'):
                self._portfolio = PortfolioState.from_dict(data['portfolio'])

            success = await temp_manager._write_json_atomic(
                self.portfolio_file,
                self._portfolio.to_dict() if self._portfolio else None
            )

            if success:
                logger.info(f"Restored portfolio checkpoint {checkpoint_id}")
                return True
            else:
                logger.error(f"Failed to save restored checkpoint {checkpoint_id}")
                return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get portfolio statistics."""
        async with self._lock:
            await self._ensure_loaded()
            if not self._portfolio:
                return {"status": "no_portfolio"}

            return {
                "as_of": self._portfolio.as_of,
                "cash_total": sum(self._portfolio.cash.values()),
                "holdings_count": len(self._portfolio.holdings),
                "exposure_total": self._portfolio.exposure_total,
                "has_risk_data": bool(self._portfolio.risk_aggregates)
            }

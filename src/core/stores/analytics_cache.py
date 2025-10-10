"""
Analytics Cache Store

Focused store managing screening and strategy analysis results.
Part of StateManager refactoring to follow Single Responsibility Principle.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger


class AnalyticsCache:
    """
    Manages cached analytics data with TTL support.

    Responsibilities:
    - Screening results caching
    - Strategy analysis caching
    - Analysis history tracking
    - Time-based cache invalidation
    """

    def __init__(self, state_dir: Path, ttl_seconds: int = 300):
        self.state_dir = state_dir
        self.ttl_seconds = ttl_seconds
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.screening_file = self.state_dir / "screening.json"
        self.strategy_file = self.state_dir / "strategy.json"
        self.analysis_history_dir = self.state_dir / "analysis_history"
        self.analysis_history_dir.mkdir(exist_ok=True)

        self._screening_results: Optional[Dict[str, Any]] = None
        self._screening_timestamp: Optional[datetime] = None
        self._strategy_results: Optional[Dict[str, Any]] = None
        self._strategy_timestamp: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._background_tasks: List[asyncio.Task] = []

        self._load_state_sync()

    def _load_state_sync(self) -> None:
        """Load analytics state synchronously for __init__."""
        try:
            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)

            self._screening_results = temp_manager._read_json_sync(self.screening_file)
            self._strategy_results = temp_manager._read_json_sync(self.strategy_file)

            logger.info("Analytics cache state loaded")
        except Exception as e:
            logger.error(f"Failed to load analytics state: {e}")
            self._screening_results = None
            self._strategy_results = None

    def _is_expired(self, timestamp: Optional[datetime]) -> bool:
        """Check if cached data has expired."""
        if timestamp is None:
            return True

        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return age > self.ttl_seconds

    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update screening results cache."""
        async with self._lock:
            self._screening_results = results
            self._screening_timestamp = datetime.now(timezone.utc)

            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            success = await temp_manager._write_json_atomic(self.screening_file, results)

            if not success:
                logger.error("Failed to save screening results to disk")

    async def get_screening_results(self, allow_expired: bool = True) -> Optional[Dict[str, Any]]:
        """Get screening results from cache."""
        async with self._lock:
            if not allow_expired and self._is_expired(self._screening_timestamp):
                logger.debug("Screening cache expired")
                return None

            return self._screening_results

    async def update_strategy_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update strategy analysis results cache."""
        async with self._lock:
            self._strategy_results = results
            self._strategy_timestamp = datetime.now(timezone.utc)

            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            success = await temp_manager._write_json_atomic(self.strategy_file, results)

            if not success:
                logger.error("Failed to save strategy results to disk")

    async def get_strategy_results(self, allow_expired: bool = True) -> Optional[Dict[str, Any]]:
        """Get strategy analysis results from cache."""
        async with self._lock:
            if not allow_expired and self._is_expired(self._strategy_timestamp):
                logger.debug("Strategy cache expired")
                return None

            return self._strategy_results

    async def save_analysis_history(self, symbol: str, analysis: Dict) -> None:
        """Save detailed analysis history per stock with size-based rotation."""
        history_file = self.analysis_history_dir / f"{symbol}.json"
        compressed_file = self.analysis_history_dir / f"{symbol}_compressed.json"

        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        def modify_history(current_history):
            if not isinstance(current_history, list):
                current_history = []

            new_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis": analysis
            }
            current_history.append(new_entry)

            if len(current_history) > 1000:
                recent_entries = current_history[-500:]
                older_entries = current_history[:-500]

                compressed_entries = []
                for entry in older_entries:
                    compressed_entries.append({
                        "timestamp": entry["timestamp"],
                        "compressed": True,
                        "summary": self._compress_analysis(entry["analysis"])
                    })

                compression_task = asyncio.create_task(
                    temp_manager._write_json_atomic(compressed_file, compressed_entries)
                )

                def _handle_compression_result(task: asyncio.Task):
                    try:
                        if task.exception():
                            logger.error(f"Compression failed for {symbol}: {task.exception()}")
                        else:
                            logger.debug(f"Compression completed for {symbol}")
                    except Exception as e:
                        logger.error(f"Error handling compression result: {e}")

                compression_task.add_done_callback(_handle_compression_result)
                self._background_tasks.append(compression_task)

                return recent_entries

            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            return [h for h in current_history if h["timestamp"] > cutoff.isoformat()]

        success = await temp_manager._read_modify_write_atomic(history_file, modify_history)

        if success:
            logger.debug(f"Saved analysis history for {symbol}")
        else:
            logger.error(f"Failed to save analysis history for {symbol}")

    def _compress_analysis(self, analysis: Dict) -> Dict:
        """Compress analysis data by removing detailed fields."""
        compressed = {
            "type": analysis.get("analysis_type", "unknown"),
            "action": analysis.get("action"),
            "confidence": analysis.get("confidence"),
            "risk_level": analysis.get("risk_level"),
            "timestamp": analysis.get("timestamp")
        }

        if "reasoning" in analysis:
            reasoning = analysis["reasoning"]
            compressed["reasoning_summary"] = (
                reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
            )

        return compressed

    async def get_analysis_history(
        self,
        symbol: str,
        include_compressed: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """Get analysis history for a symbol."""
        history_file = self.analysis_history_dir / f"{symbol}.json"
        compressed_file = self.analysis_history_dir / f"{symbol}_compressed.json"

        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        recent_history = await temp_manager._read_json_atomic(history_file)
        if not recent_history:
            recent_history = []

        result = recent_history[-limit:] if len(recent_history) > limit else recent_history

        if include_compressed:
            compressed_history = await temp_manager._read_json_atomic(compressed_file)
            if compressed_history and isinstance(compressed_history, list):
                result.extend(compressed_history)

        result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return result[:limit]

    async def invalidate_screening_cache(self) -> None:
        """Force invalidate screening cache."""
        async with self._lock:
            self._screening_timestamp = None

    async def invalidate_strategy_cache(self) -> None:
        """Force invalidate strategy cache."""
        async with self._lock:
            self._strategy_timestamp = None

    async def invalidate_all(self) -> None:
        """Invalidate all caches."""
        async with self._lock:
            self._screening_timestamp = None
            self._strategy_timestamp = None

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            now = datetime.now(timezone.utc)

            screening_age = None
            if self._screening_timestamp:
                screening_age = int((now - self._screening_timestamp).total_seconds())

            strategy_age = None
            if self._strategy_timestamp:
                strategy_age = int((now - self._strategy_timestamp).total_seconds())

            return {
                "screening": {
                    "cached": self._screening_results is not None,
                    "age_seconds": screening_age,
                    "expired": self._is_expired(self._screening_timestamp)
                },
                "strategy": {
                    "cached": self._strategy_results is not None,
                    "age_seconds": strategy_age,
                    "expired": self._is_expired(self._strategy_timestamp)
                },
                "ttl_seconds": self.ttl_seconds
            }

    async def cleanup(self) -> None:
        """Cleanup background tasks."""
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        self._background_tasks.clear()
        logger.debug("Analytics cache cleanup completed")

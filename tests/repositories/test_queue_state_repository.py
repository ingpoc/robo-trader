"""Unit tests for QueueStateRepository.

Tests efficient queue status queries and domain model mapping.
"""

import pytest
import aiosqlite
from datetime import datetime, timezone, timedelta

from src.repositories import QueueStateRepository
from src.models.domain import QueueState, QueueStatus
from src.core.database import Database


class TestQueueStateRepository:
    """Test suite for QueueStateRepository."""

    @pytest.fixture
    async def database(self):
        """Create in-memory test database."""
        # Create in-memory database
        connection = await aiosqlite.connect(":memory:")

        # Create scheduler_tasks table
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_tasks (
                task_id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                payload TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                scheduled_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
        """)
        await connection.commit()

        # Create Database wrapper
        db = Database(connection=connection)

        yield db

        # Cleanup
        await connection.close()

    @pytest.fixture
    async def repository(self, database):
        """Create QueueStateRepository instance."""
        repo = QueueStateRepository(database)
        await repo.initialize()
        return repo

    @pytest.fixture
    async def sample_tasks(self, database):
        """Insert sample tasks for testing."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        tasks = [
            # AI Analysis queue - running and pending
            ("task-001", "ai_analysis", "RECOMMENDATION_GENERATION", "pending", 7,
             (now - timedelta(minutes=5)).isoformat(), None, None),
            ("task-002", "ai_analysis", "RECOMMENDATION_GENERATION", "running", 7,
             (now - timedelta(minutes=3)).isoformat(),
             (now - timedelta(minutes=2)).isoformat(), None),
            ("task-003", "ai_analysis", "RECOMMENDATION_GENERATION", "completed", 7,
             (today_start + timedelta(hours=2)).isoformat(),
             (today_start + timedelta(hours=2, minutes=1)).isoformat(),
             (today_start + timedelta(hours=2, minutes=3)).isoformat()),
            ("task-004", "ai_analysis", "RECOMMENDATION_GENERATION", "completed", 7,
             (today_start + timedelta(hours=3)).isoformat(),
             (today_start + timedelta(hours=3, minutes=1)).isoformat(),
             (today_start + timedelta(hours=3, minutes=4)).isoformat()),

            # Data fetcher queue - some failed tasks
            ("task-005", "data_fetcher", "NEWS_MONITORING", "failed", 5,
             (now - timedelta(minutes=10)).isoformat(),
             (now - timedelta(minutes=9)).isoformat(), None),
            ("task-006", "data_fetcher", "EARNINGS_CHECK", "completed", 5,
             (today_start + timedelta(hours=1)).isoformat(),
             (today_start + timedelta(hours=1, minutes=1)).isoformat(),
             (today_start + timedelta(hours=1, minutes=2)).isoformat()),

            # Portfolio sync queue - idle (no pending)
            ("task-007", "portfolio_sync", "SYNC_ACCOUNT", "completed", 8,
             (today_start + timedelta(hours=0, minutes=30)).isoformat(),
             (today_start + timedelta(hours=0, minutes=31)).isoformat(),
             (today_start + timedelta(hours=0, minutes=32)).isoformat()),
        ]

        for task in tasks:
            await database.connection.execute(
                """
                INSERT INTO scheduler_tasks
                (task_id, queue_name, task_type, status, priority,
                 scheduled_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                task
            )

        await database.connection.commit()

    async def test_get_status_running_queue(self, repository, sample_tasks):
        """Test getting status for queue with running tasks."""
        status = await repository.get_status("ai_analysis")

        assert status.name == "ai_analysis"
        assert status.status == QueueStatus.RUNNING
        assert status.pending_tasks == 1
        assert status.running_tasks == 1
        assert status.completed_tasks == 2
        assert status.failed_tasks == 0
        assert status.current_task_id == "task-002"
        assert status.current_task_type == "RECOMMENDATION_GENERATION"
        assert status.is_active is True
        assert status.is_healthy is True

    async def test_get_status_error_queue(self, repository, sample_tasks):
        """Test getting status for queue with failed tasks."""
        status = await repository.get_status("data_fetcher")

        assert status.name == "data_fetcher"
        assert status.status == QueueStatus.ERROR
        assert status.pending_tasks == 0
        assert status.running_tasks == 0
        assert status.completed_tasks == 1
        assert status.failed_tasks == 1
        assert status.is_healthy is False

    async def test_get_status_idle_queue(self, repository, sample_tasks):
        """Test getting status for idle queue (no pending or running)."""
        status = await repository.get_status("portfolio_sync")

        assert status.name == "portfolio_sync"
        assert status.status == QueueStatus.IDLE
        assert status.pending_tasks == 0
        assert status.running_tasks == 0
        assert status.completed_tasks == 1
        assert status.failed_tasks == 0
        assert status.is_active is False

    async def test_get_status_empty_queue(self, repository):
        """Test getting status for queue with no tasks."""
        status = await repository.get_status("empty_queue")

        assert status.name == "empty_queue"
        assert status.status == QueueStatus.IDLE
        assert status.pending_tasks == 0
        assert status.running_tasks == 0
        assert status.completed_tasks == 0
        assert status.failed_tasks == 0
        assert status.total_tasks == 0

    async def test_get_all_statuses(self, repository, sample_tasks):
        """Test getting all queue statuses in single query."""
        statuses = await repository.get_all_statuses()

        # Should return statuses for all defined queues
        assert len(statuses) >= 3

        # Check specific queues
        assert "ai_analysis" in statuses
        assert "data_fetcher" in statuses
        assert "portfolio_sync" in statuses

        # Verify AI analysis queue
        ai_queue = statuses["ai_analysis"]
        assert ai_queue.status == QueueStatus.RUNNING
        assert ai_queue.running_tasks == 1
        assert ai_queue.pending_tasks == 1

        # Verify data fetcher queue
        data_queue = statuses["data_fetcher"]
        assert data_queue.status == QueueStatus.ERROR
        assert data_queue.failed_tasks == 1

    async def test_get_queue_statistics_summary(self, repository, sample_tasks):
        """Test getting aggregated statistics across all queues."""
        summary = await repository.get_queue_statistics_summary()

        assert summary["total_queues"] == 3
        assert summary["total_pending"] == 1
        assert summary["total_running"] == 1
        assert summary["total_completed_today"] == 4
        assert summary["total_failed"] == 1

    async def test_average_duration_calculation(self, repository, sample_tasks):
        """Test that average duration is calculated correctly."""
        status = await repository.get_status("ai_analysis")

        # Task 003: 2 minutes = 120000ms
        # Task 004: 3 minutes = 180000ms
        # Average: 150000ms
        assert status.avg_duration_ms == pytest.approx(150000.0, rel=1000)

    async def test_success_rate_property(self, repository, sample_tasks):
        """Test success rate calculation."""
        ai_status = await repository.get_status("ai_analysis")
        data_status = await repository.get_status("data_fetcher")

        # AI analysis: 2 completed, 0 failed = 100%
        assert ai_status.success_rate == 100.0

        # Data fetcher: 1 completed, 1 failed = 50%
        assert data_status.success_rate == 50.0

    async def test_to_dict_serialization(self, repository, sample_tasks):
        """Test QueueState serialization to dictionary."""
        status = await repository.get_status("ai_analysis")
        status_dict = status.to_dict()

        assert status_dict["queue_name"] == "ai_analysis"
        assert status_dict["status"] == "running"
        assert status_dict["pending_count"] == 1
        assert status_dict["running_count"] == 1
        assert status_dict["total_tasks"] == 4
        assert status_dict["is_healthy"] is True
        assert status_dict["is_active"] is True
        assert "current_task" in status_dict
        assert status_dict["current_task"]["task_id"] == "task-002"

    async def test_get_recent_completed_tasks(self, repository, sample_tasks):
        """Test getting recent completed tasks."""
        tasks = await repository.get_recent_completed_tasks(
            queue_name="ai_analysis",
            limit=10
        )

        assert len(tasks) == 2
        # Should be ordered by completion time descending
        assert tasks[0]["task_id"] == "task-004"
        assert tasks[1]["task_id"] == "task-003"

    async def test_get_failed_tasks(self, repository, sample_tasks):
        """Test getting failed tasks."""
        tasks = await repository.get_failed_tasks(queue_name="data_fetcher")

        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task-005"
        assert tasks[0]["status"] == "failed"

    async def test_current_task_correlation(self, repository, sample_tasks):
        """Test that current task is correctly correlated to queue."""
        status = await repository.get_status("ai_analysis")

        # Verify current task is included with queue context
        assert status.current_task_id == "task-002"
        assert status.current_task_type == "RECOMMENDATION_GENERATION"
        assert status.current_task_started_at is not None

        # Verify in to_dict output
        status_dict = status.to_dict()
        current_task = status_dict["current_task"]
        assert current_task is not None
        assert current_task["queue_name"] == "ai_analysis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

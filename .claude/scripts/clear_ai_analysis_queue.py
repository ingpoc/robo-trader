#!/usr/bin/env python3
"""
Clear AI_ANALYSIS queue before AnalysisScheduler deployment.

This script removes all pending AI_ANALYSIS tasks to prepare for the new
smart periodic analysis scheduler. After running this, AnalysisScheduler
will create fresh comprehensive analysis tasks on-demand.

Usage:
    python scripts/clear_ai_analysis_queue.py --dry-run     # Preview what will be deleted
    python scripts/clear_ai_analysis_queue.py --confirm     # Actually delete tasks
"""

import sys
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.core.database_state import DatabaseStateManager
from src.models.scheduler import QueueName, TaskStatus
from src.stores.scheduler_task_store import SchedulerTaskStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def clear_ai_analysis_queue(config: Config, dry_run: bool = True) -> dict:
    """
    Clear all pending AI_ANALYSIS tasks from database.

    Args:
        config: Application configuration
        dry_run: If True, show what would be deleted without deleting

    Returns:
        Dict with results: {
            "total_pending": int,
            "total_failed": int,
            "deleted_pending": int,
            "deleted_failed": int,
            "errors": List[str]
        }
    """
    results = {
        "total_pending": 0,
        "total_failed": 0,
        "deleted_pending": 0,
        "deleted_failed": 0,
        "errors": []
    }

    db = None
    try:
        import aiosqlite
        from pathlib import Path

        # Initialize database directly
        logger.info("Initializing database connection...")
        db_path = config.state_dir / "robo_trader.db"

        if not db_path.exists():
            logger.error(f"Database not found at {db_path}")
            return results

        # Open database connection directly
        db = await aiosqlite.connect(str(db_path))

        # Ensure queue_tasks table exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queue_tasks (
                task_id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                payload TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                scheduled_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()

        # Get all pending AI_ANALYSIS tasks
        logger.info("Querying pending AI_ANALYSIS tasks...")
        cursor = await db.execute(
            "SELECT task_id, task_type FROM queue_tasks WHERE queue_name = ? AND status = ?",
            ("ai_analysis", "pending")
        )
        pending_tasks = await cursor.fetchall()
        await cursor.close()

        results["total_pending"] = len(pending_tasks)
        logger.info(f"Found {len(pending_tasks)} pending AI_ANALYSIS tasks")

        if len(pending_tasks) == 0:
            logger.info("✅ Queue is empty - no tasks to delete")
            await db.close()
            return results

        # Get all failed AI_ANALYSIS tasks
        logger.info("Querying failed AI_ANALYSIS tasks...")
        cursor = await db.execute(
            "SELECT task_id, task_type FROM queue_tasks WHERE queue_name = ? AND status = ?",
            ("ai_analysis", "failed")
        )
        failed_tasks = await cursor.fetchall()
        await cursor.close()

        results["total_failed"] = len(failed_tasks)
        logger.info(f"Found {len(failed_tasks)} failed AI_ANALYSIS tasks")

        # Preview mode: just show summary
        if dry_run:
            logger.info("\n" + "="*80)
            logger.info("DRY RUN MODE - No tasks will be deleted")
            logger.info("="*80)
            logger.info(f"\nPending tasks to delete: {len(pending_tasks)}")
            if len(pending_tasks) > 0 and len(pending_tasks) <= 10:
                for task in pending_tasks[:10]:
                    logger.info(f"  - {task.task_id}: {task.task_type.value}")
            elif len(pending_tasks) > 10:
                logger.info(f"  (showing first 10 of {len(pending_tasks)})")
                for task in pending_tasks[:10]:
                    logger.info(f"  - {task.task_id}: {task.task_type.value}")

            logger.info(f"\nFailed tasks to delete: {len(failed_tasks)}")
            if len(failed_tasks) > 0 and len(failed_tasks) <= 10:
                for task in failed_tasks[:10]:
                    logger.info(f"  - {task.task_id}: {task.task_type.value} (error: {task.error_message[:50]})")
            elif len(failed_tasks) > 10:
                logger.info(f"  (showing first 10 of {len(failed_tasks)})")
                for task in failed_tasks[:10]:
                    logger.info(f"  - {task.task_id}: {task.task_type.value}")

            logger.info("\n" + "="*80)
            logger.info(f"To delete these {len(pending_tasks) + len(failed_tasks)} tasks, run:")
            logger.info("  python scripts/clear_ai_analysis_queue.py --confirm")
            logger.info("="*80)
            return results

        # Actual deletion mode
        logger.warning("\n" + "="*80)
        logger.warning("DELETING TASKS - This cannot be undone!")
        logger.warning("="*80)

        # Delete pending tasks
        if len(pending_tasks) > 0:
            logger.info(f"\nDeleting {len(pending_tasks)} pending tasks...")
            for i, task in enumerate(pending_tasks, 1):
                try:
                    task_id = task[0]
                    await db.execute("DELETE FROM queue_tasks WHERE task_id = ?", (task_id,))
                    results["deleted_pending"] += 1

                    if i % 100 == 0:
                        logger.info(f"  Deleted {i}/{len(pending_tasks)} pending tasks...")
                        await db.commit()

                except Exception as e:
                    logger.error(f"Failed to delete task {task[0]}: {e}")
                    results["errors"].append(f"Failed to delete {task[0]}: {str(e)}")

            # Final commit for pending tasks
            if results["deleted_pending"] > 0:
                await db.commit()
            logger.info(f"✅ Deleted {results['deleted_pending']} pending tasks")

        # Delete failed tasks
        if len(failed_tasks) > 0:
            logger.info(f"\nDeleting {len(failed_tasks)} failed tasks...")
            for i, task in enumerate(failed_tasks, 1):
                try:
                    task_id = task[0]
                    await db.execute("DELETE FROM queue_tasks WHERE task_id = ?", (task_id,))
                    results["deleted_failed"] += 1

                    if i % 100 == 0:
                        logger.info(f"  Deleted {i}/{len(failed_tasks)} failed tasks...")
                        await db.commit()

                except Exception as e:
                    logger.error(f"Failed to delete task {task[0]}: {e}")
                    results["errors"].append(f"Failed to delete {task[0]}: {str(e)}")

            # Final commit for failed tasks
            if results["deleted_failed"] > 0:
                await db.commit()
            logger.info(f"✅ Deleted {results['deleted_failed']} failed tasks")

        # Summary
        logger.info("\n" + "="*80)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*80)
        logger.info(f"Pending tasks deleted: {results['deleted_pending']}/{results['total_pending']}")
        logger.info(f"Failed tasks deleted: {results['deleted_failed']}/{results['total_failed']}")
        total_deleted = results['deleted_pending'] + results['deleted_failed']
        total_found = results['total_pending'] + results['total_failed']
        logger.info(f"Total deleted: {total_deleted}/{total_found}")

        if results["errors"]:
            logger.warning(f"\nErrors during deletion: {len(results['errors'])}")
            for error in results["errors"][:5]:
                logger.warning(f"  - {error}")
            if len(results["errors"]) > 5:
                logger.warning(f"  ... and {len(results['errors']) - 5} more")

        logger.info("="*80)

        # Close database
        await db.close()

        return results

    except Exception as e:
        logger.exception("Fatal error during queue cleanup")
        results["errors"].append(f"Fatal error: {str(e)}")
        # Ensure db is closed even on error
        if db:
            try:
                await db.close()
            except:
                pass
        return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clear AI_ANALYSIS queue before AnalysisScheduler deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview tasks that would be deleted (default)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete the tasks (required to perform deletion)"
    )

    args = parser.parse_args()

    # Load config
    try:
        config_path = Path(__file__).parent.parent / "config" / "config.json"
        config = Config.from_file(config_path)
        logger.info(f"Configuration loaded from: {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Run cleanup
    dry_run = not args.confirm
    try:
        results = await clear_ai_analysis_queue(config, dry_run=dry_run)

        if results["errors"]:
            return 1
        return 0

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

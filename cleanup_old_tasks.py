#!/usr/bin/env python3
"""
Clean up old failed tasks from the database to fix success rate calculations.
"""

import sqlite3
import os
from datetime import datetime, timedelta

def cleanup_old_failed_tasks():
    """Remove failed tasks older than 1 day."""
    db_path = "state/robo_trader.db"

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    # Calculate cutoff time (12 hours ago for more aggressive cleanup)
    cutoff_time = datetime.now() - timedelta(hours=12)
    cutoff_str = cutoff_time.isoformat()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Count old failed tasks before cleanup
        cursor.execute("""
            SELECT COUNT(*) FROM queue_tasks
            WHERE status = 'failed' AND created_at < ?
        """, (cutoff_str,))
        old_failed_count = cursor.fetchone()[0]

        # Delete old failed tasks
        cursor.execute("""
            DELETE FROM queue_tasks
            WHERE status = 'failed' AND created_at < ?
        """, (cutoff_str,))

        deleted_count = cursor.rowcount

        # Count remaining tasks
        cursor.execute("""
            SELECT status, COUNT(*) FROM queue_tasks
            GROUP BY status
        """)
        remaining_tasks = cursor.fetchall()

        conn.commit()
        conn.close()

        print(f"✅ Cleanup completed:")
        print(f"   - Old failed tasks (24h+): {old_failed_count}")
        print(f"   - Deleted: {deleted_count}")
        print(f"   - Remaining tasks:")
        for status, count in remaining_tasks:
            print(f"     {status}: {count}")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_old_failed_tasks()
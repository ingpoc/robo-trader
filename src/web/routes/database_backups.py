"""
Database Backup Management API Routes

Provides endpoints for:
- Viewing backup status
- Listing available backups
- Creating manual backups
- Restoring from backups
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from loguru import logger

from src.core.di import DependencyContainer
from ..dependencies import get_container
from src.core.errors import TradingError

router = APIRouter(prefix="/api/backups", tags=["database-backups"])


@router.get("/status")
async def get_backup_status(
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get database backup status and statistics."""
    try:
        database = await container.get("database")

        if not database or not database.backup_manager:
            raise HTTPException(
                status_code=500,
                detail="Backup manager not available"
            )

        stats = database.backup_manager.get_backup_stats()

        return {
            "status": "ok",
            "backup_manager_available": True,
            **stats
        }

    except TradingError as e:
        logger.error(f"Backup status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in backup status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list")
async def list_backups(
    hours: int = 168,  # Default: last 7 days
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """List available backups from the last N hours."""
    try:
        if hours < 1 or hours > 8760:  # Max 1 year
            raise HTTPException(
                status_code=400,
                detail="Hours must be between 1 and 8760"
            )

        database = await container.get("database")

        if not database or not database.backup_manager:
            raise HTTPException(
                status_code=500,
                detail="Backup manager not available"
            )

        backups = await database.backup_manager.get_backups(hours=hours)

        return {
            "status": "ok",
            "hours": hours,
            "backup_count": len(backups),
            "backups": [
                {
                    "filename": b.name,
                    "size_mb": round(b.stat().st_size / (1024 * 1024), 2),
                    "created_at": b.stat().st_mtime
                }
                for b in backups
            ]
        }

    except HTTPException:
        raise
    except TradingError as e:
        logger.error(f"Backup list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in backup list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/create")
async def create_backup(
    label: str = "manual",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Create a manual database backup."""
    try:
        if not label or len(label) > 50:
            raise HTTPException(
                status_code=400,
                detail="Label must be 1-50 characters"
            )

        # Sanitize label (alphanumeric, dash, underscore only)
        if not all(c.isalnum() or c in '-_' for c in label):
            raise HTTPException(
                status_code=400,
                detail="Label can only contain alphanumeric characters, dashes, and underscores"
            )

        database = await container.get("database")

        if not database or not database.backup_manager:
            raise HTTPException(
                status_code=500,
                detail="Backup manager not available"
            )

        # Create backup in background to avoid blocking request
        async def create_backup_task():
            try:
                backup_path = await database.backup_manager.create_backup(label=label)
                if backup_path:
                    logger.info(f"Manual backup created: {backup_path}")
                else:
                    logger.warning(f"Failed to create manual backup with label: {label}")
            except Exception as e:
                logger.error(f"Error creating backup in background: {e}")

        background_tasks.add_task(create_backup_task)

        return {
            "status": "ok",
            "message": "Backup creation started in background",
            "label": label
        }

    except HTTPException:
        raise
    except TradingError as e:
        logger.error(f"Backup creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error creating backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/latest")
async def get_latest_backup(
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get information about the latest backup."""
    try:
        database = await container.get("database")

        if not database or not database.backup_manager:
            raise HTTPException(
                status_code=500,
                detail="Backup manager not available"
            )

        latest = await database.backup_manager.get_latest_backup()

        if not latest:
            return {
                "status": "ok",
                "latest_backup": None,
                "message": "No backups found"
            }

        return {
            "status": "ok",
            "latest_backup": {
                "filename": latest.name,
                "path": str(latest),
                "size_mb": round(latest.stat().st_size / (1024 * 1024), 2),
                "created_at": latest.stat().st_mtime
            }
        }

    except HTTPException:
        raise
    except TradingError as e:
        logger.error(f"Get latest backup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error getting latest backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/restore/{backup_filename}")
async def restore_backup(
    backup_filename: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Restore database from a backup file."""
    try:
        if not backup_filename.endswith(".db"):
            raise HTTPException(
                status_code=400,
                detail="Invalid backup filename"
            )

        database = await container.get("database")

        if not database or not database.backup_manager:
            raise HTTPException(
                status_code=500,
                detail="Backup manager not available"
            )

        backup_dir = database.backup_manager.backup_dir
        backup_path = backup_dir / backup_filename

        if not backup_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Backup file not found: {backup_filename}"
            )

        success = await database.backup_manager.restore_backup(backup_path)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to restore backup"
            )

        return {
            "status": "ok",
            "message": "Database restored from backup",
            "backup_filename": backup_filename,
            "warning": "Server requires restart for changes to take effect"
        }

    except HTTPException:
        raise
    except TradingError as e:
        logger.error(f"Backup restore error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error restoring backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

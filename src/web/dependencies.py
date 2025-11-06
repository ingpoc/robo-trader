"""
FastAPI dependency injection utilities.

Provides dependency injection for routes following the DI pattern from CLAUDE.md.
"""

from typing import Optional

from fastapi import HTTPException, Request

from src.core.di import DependencyContainer


async def get_container(request: Request) -> DependencyContainer:
    """
    Get dependency container from application state.

    This dependency should be used in all route handlers instead of
    importing the container globally.

    Usage:
        @router.get("/endpoint")
        async def endpoint(container: DependencyContainer = Depends(get_container)):
            service = await container.get("service_name")
            return await service.do_something()

    Args:
        request: FastAPI request object

    Returns:
        DependencyContainer instance

    Raises:
        HTTPException: If container is not initialized
    """
    container: Optional[DependencyContainer] = getattr(
        request.app.state, "container", None
    )

    if container is None:
        raise HTTPException(
            status_code=503, detail="System not initialized. Container not available."
        )

    return container

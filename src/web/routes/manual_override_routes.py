"""
Manual Override API Routes

Provides endpoints for manual trading controls and safeguards:
- Emergency stop (halt all trading)
- Circuit breaker (pause trading temporarily)
- Position limits (restrict maximum position sizes)
- Daily loss limits (stop trading when losses exceed threshold)
"""

from datetime import datetime, time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.di import DependencyContainer
from src.core.errors import TradingError, ErrorCategory
from src.web.dependencies import get_container
from src.services.manual_override_service import OverrideRequest, OverrideType

router = APIRouter(
    prefix="/api/manual-override",
    tags=["manual-override"],
    responses={404: {"description": "Not found"}}
)


class OverrideStatusResponse(BaseModel):
    """Response model for override status"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class PositionLimitRequest(BaseModel):
    """Request model for position limits"""
    symbol: Optional[str] = Field(None, description="Specific symbol (optional, applies to all if not provided)")
    max_quantity: float = Field(..., gt=0, description="Maximum position size")
    max_percentage: Optional[float] = Field(None, gt=0, le=100, description="Maximum as % of portfolio")


class DailyLossLimitRequest(BaseModel):
    """Request model for daily loss limits"""
    max_daily_loss: float = Field(..., gt=0, description="Maximum daily loss amount")
    reset_time: Optional[time] = Field(None, description="Time when daily limit resets (default: 9:15 AM)")


# Emergency Stop Endpoints
@router.post("/emergency-stop/activate", response_model=OverrideStatusResponse)
async def activate_emergency_stop(
    request: OverrideRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Activate emergency stop to halt all trading immediately"""
    try:
        service = await container.get("manual_override_service")

        # Add user context to request
        request.triggered_by = "manual"

        result = await service.activate_emergency_stop(request)

        return OverrideStatusResponse(
            success=True,
            message="Emergency stop activated successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to activate emergency stop: {e}",
                "category": "system"
            }
        )


@router.post("/emergency-stop/deactivate", response_model=OverrideStatusResponse)
async def deactivate_emergency_stop(
    request: OverrideRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Deactivate emergency stop to resume trading"""
    try:
        service = await container.get("manual_override_service")

        # Add user context to request
        request.triggered_by = "manual"

        result = await service.deactivate_emergency_stop(request)

        return OverrideStatusResponse(
            success=True,
            message="Emergency stop deactivated successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to deactivate emergency stop: {e}",
                "category": "system"
            }
        )


# Circuit Breaker Endpoints
@router.post("/circuit-breaker/activate", response_model=OverrideStatusResponse)
async def activate_circuit_breaker(
    request: OverrideRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Activate circuit breaker to pause trading temporarily"""
    try:
        service = await container.get("manual_override_service")

        # Add user context to request
        request.triggered_by = "manual"

        result = await service.activate_circuit_breaker(request)

        return OverrideStatusResponse(
            success=True,
            message="Circuit breaker activated successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to activate circuit breaker: {e}",
                "category": "system"
            }
        )


@router.post("/circuit-breaker/deactivate", response_model=OverrideStatusResponse)
async def deactivate_circuit_breaker(
    request: OverrideRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Deactivate circuit breaker to resume trading"""
    try:
        service = await container.get("manual_override_service")

        # Add user context to request
        request.triggered_by = "manual"

        result = await service.deactivate_circuit_breaker(request)

        return OverrideStatusResponse(
            success=True,
            message="Circuit breaker deactivated successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to deactivate circuit breaker: {e}",
                "category": "system"
            }
        )


# Position Limits Endpoints
@router.post("/position-limits/set", response_model=OverrideStatusResponse)
async def set_position_limit(
    request: PositionLimitRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Set position limits for trading"""
    try:
        service = await container.get("manual_override_service")

        # Convert to OverrideRequest
        override_request = OverrideRequest(
            override_type=OverrideType.POSITION_LIMIT,
            parameters=request.dict(exclude_unset=True),
            triggered_by="manual",
            reason=f"Position limit set: max_quantity={request.max_quantity}"
        )

        result = await service.set_position_limit(override_request)

        return OverrideStatusResponse(
            success=True,
            message="Position limit set successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to set position limit: {e}",
                "category": "system"
            }
        )


@router.delete("/position-limits/remove", response_model=OverrideStatusResponse)
async def remove_position_limit(
    symbol: Optional[str] = Query(None, description="Specific symbol to remove limit for"),
    container: DependencyContainer = Depends(get_container)
):
    """Remove position limits"""
    try:
        service = await container.get("manual_override_service")

        # Convert to OverrideRequest
        override_request = OverrideRequest(
            override_type=OverrideType.POSITION_LIMIT,
            parameters={"symbol": symbol} if symbol else {"remove_all": True},
            triggered_by="manual",
            reason=f"Position limit removed for: {symbol or 'all symbols'}"
        )

        result = await service.remove_position_limit(override_request)

        return OverrideStatusResponse(
            success=True,
            message="Position limit removed successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to remove position limit: {e}",
                "category": "system"
            }
        )


# Daily Loss Limits Endpoints
@router.post("/daily-loss-limit/set", response_model=OverrideStatusResponse)
async def set_daily_loss_limit(
    request: DailyLossLimitRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Set daily loss limit"""
    try:
        service = await container.get("manual_override_service")

        # Convert to OverrideRequest
        override_request = OverrideRequest(
            override_type=OverrideType.DAILY_LOSS_LIMIT,
            parameters=request.dict(exclude_unset=True),
            triggered_by="manual",
            reason=f"Daily loss limit set: {request.max_daily_loss}"
        )

        result = await service.set_daily_loss_limit(override_request)

        return OverrideStatusResponse(
            success=True,
            message="Daily loss limit set successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to set daily loss limit: {e}",
                "category": "system"
            }
        )


@router.delete("/daily-loss-limit/remove", response_model=OverrideStatusResponse)
async def remove_daily_loss_limit(
    container: DependencyContainer = Depends(get_container)
):
    """Remove daily loss limit"""
    try:
        service = await container.get("manual_override_service")

        # Convert to OverrideRequest
        override_request = OverrideRequest(
            override_type=OverrideType.DAILY_LOSS_LIMIT,
            parameters={"remove": True},
            triggered_by="manual",
            reason="Daily loss limit removed"
        )

        result = await service.remove_daily_loss_limit(override_request)

        return OverrideStatusResponse(
            success=True,
            message="Daily loss limit removed successfully",
            data=result
        )
    except TradingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": str(e),
                "category": e.category.value
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to remove daily loss limit: {e}",
                "category": "system"
            }
        )


# Status Endpoint
@router.get("/status", response_model=OverrideStatusResponse)
async def get_override_status(
    container: DependencyContainer = Depends(get_container)
):
    """Get current status of all manual overrides"""
    try:
        service = await container.get("manual_override_service")
        status = await service.get_all_override_status()

        return OverrideStatusResponse(
            success=True,
            message="Override status retrieved successfully",
            data=status
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to get override status: {e}",
                "category": "system"
            }
        )
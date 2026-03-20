"""
Manual Override Service

Provides functionality for manual trading controls and safeguards:
- Emergency stop (halt all trading)
- Circuit breaker (pause trading temporarily)
- Position limits (restrict maximum position sizes)
- Daily loss limits (stop trading when losses exceed threshold)
"""

import logging
from datetime import datetime, time
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

from src.core.event_bus import Event, EventBus
from src.core.database_state.configuration_state import ManualOverrideState

logger = logging.getLogger(__name__)


class OverrideType(str, Enum):
    """Types of manual overrides."""
    EMERGENCY_STOP = "emergency_stop"
    CIRCUIT_BREAKER = "circuit_breaker"
    POSITION_LIMIT = "position_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"


class OverrideRequest(BaseModel):
    """Request model for manual override operations."""
    override_type: OverrideType = Field(..., description="Type of override")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Override parameters")
    triggered_by: str = Field(..., description="Who triggered the override")
    reason: str = Field(..., description="Reason for the override")
    timestamp: Optional[datetime] = Field(None, description="Override timestamp")


class ManualOverrideService:
    """
    Service for managing manual trading overrides and safeguards.

    Provides centralized control over:
    - Emergency trading halt
    - Circuit breaker for temporary pauses
    - Position size limits
    - Daily loss limits
    """

    def __init__(self, config_state: ManualOverrideState, event_bus: EventBus):
        """
        Initialize manual override service.

        Args:
            config_state: Configuration state manager
            event_bus: Event bus for broadcasting override events
        """
        self.config_state = config_state
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def activate_emergency_stop(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Activate emergency stop to halt all trading immediately.

        Args:
            request: Override request containing emergency stop details

        Returns:
            Dict with activation result
        """
        try:
            self.logger.info(f"Activating emergency stop - Triggered by: {request.triggered_by}, Reason: {request.reason}")

            # Store emergency stop state
            success = await self.config_state.manual_override.activate_emergency_stop(
                triggered_by=request.triggered_by,
                reason=request.reason
            )

            if success:
                # Broadcast emergency stop event
                await self._broadcast_override_event(
                    "emergency_stop_activated",
                    {
                        "triggered_by": request.triggered_by,
                        "reason": request.reason,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info("Emergency stop activated successfully")
                return {
                    "status": "activated",
                    "message": "All trading activities halted",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to activate emergency stop")

        except Exception as e:
            self.logger.error(f"Error activating emergency stop: {e}")
            raise

    async def deactivate_emergency_stop(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Deactivate emergency stop to resume trading.

        Args:
            request: Override request containing deactivation details

        Returns:
            Dict with deactivation result
        """
        try:
            self.logger.info(f"Deactivating emergency stop - Triggered by: {request.triggered_by}")

            # Remove emergency stop state
            success = await self.config_state.manual_override.deactivate_emergency_stop()

            if success:
                # broadcast emergency stop deactivation event
                await self._broadcast_override_event(
                    "emergency_stop_deactivated",
                    {
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info("Emergency stop deactivated successfully")
                return {
                    "status": "deactivated",
                    "message": "Trading activities can resume",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to deactivate emergency stop")

        except Exception as e:
            self.logger.error(f"Error deactivating emergency stop: {e}")
            raise

    async def activate_circuit_breaker(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Activate circuit breaker to pause trading temporarily.

        Args:
            request: Override request containing circuit breaker details

        Returns:
            Dict with activation result
        """
        try:
            self.logger.info(f"Activating circuit breaker - Triggered by: {request.triggered_by}")

            # Store circuit breaker state
            duration_minutes = request.parameters.get("duration_minutes", 60)
            success = await self.config_state.manual_override.activate_circuit_breaker(
                triggered_by=request.triggered_by,
                reason=request.reason,
                duration_minutes=duration_minutes
            )

            if success:
                # Broadcast circuit breaker event
                await self._broadcast_override_event(
                    "circuit_breaker_activated",
                    {
                        "triggered_by": request.triggered_by,
                        "reason": request.reason,
                        "duration_minutes": duration_minutes,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info(f"Circuit breaker activated for {duration_minutes} minutes")
                return {
                    "status": "activated",
                    "message": f"Trading paused for {duration_minutes} minutes",
                    "duration_minutes": duration_minutes,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to activate circuit breaker")

        except Exception as e:
            self.logger.error(f"Error activating circuit breaker: {e}")
            raise

    async def deactivate_circuit_breaker(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Deactivate circuit breaker to resume trading.

        Args:
            request: Override request containing deactivation details

        Returns:
            Dict with deactivation result
        """
        try:
            self.logger.info(f"Deactivating circuit breaker - Triggered by: {request.triggered_by}")

            # Remove circuit breaker state
            success = await self.config_state.manual_override.deactivate_circuit_breaker()

            if success:
                # Broadcast circuit breaker deactivation event
                await self._broadcast_override_event(
                    "circuit_breaker_deactivated",
                    {
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info("Circuit breaker deactivated successfully")
                return {
                    "status": "deactivated",
                    "message": "Trading can resume",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to deactivate circuit breaker")

        except Exception as e:
            self.logger.error(f"Error deactivating circuit breaker: {e}")
            raise

    async def set_position_limit(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Set position limits for trading.

        Args:
            request: Override request containing position limit details

        Returns:
            Dict with position limit result
        """
        try:
            self.logger.info(f"Setting position limit - Triggered by: {request.triggered_by}")

            symbol = request.parameters.get("symbol")
            max_quantity = request.parameters.get("max_quantity")
            max_percentage = request.parameters.get("max_percentage")

            # Store position limit
            success = await self.config_state.manual_override.set_position_limit(
                symbol=symbol,
                max_quantity=max_quantity,
                max_percentage=max_percentage,
                triggered_by=request.triggered_by,
                reason=request.reason
            )

            if success:
                # Broadcast position limit event
                await self._broadcast_override_event(
                    "position_limit_set",
                    {
                        "symbol": symbol,
                        "max_quantity": max_quantity,
                        "max_percentage": max_percentage,
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                target = f"symbol {symbol}" if symbol else "all symbols"
                self.logger.info(f"Position limit set for {target}")
                return {
                    "status": "set",
                    "message": f"Position limit set for {target}",
                    "symbol": symbol,
                    "max_quantity": max_quantity,
                    "max_percentage": max_percentage,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to set position limit")

        except Exception as e:
            self.logger.error(f"Error setting position limit: {e}")
            raise

    async def remove_position_limit(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Remove position limits.

        Args:
            request: Override request containing removal details

        Returns:
            Dict with removal result
        """
        try:
            self.logger.info(f"Removing position limit - Triggered by: {request.triggered_by}")

            symbol = request.parameters.get("symbol")
            remove_all = request.parameters.get("remove_all", False)

            # Remove position limit
            success = await self.config_state.manual_override.remove_position_limit(
                symbol=symbol,
                remove_all=remove_all,
                triggered_by=request.triggered_by,
                reason=request.reason
            )

            if success:
                # Broadcast position limit removal event
                await self._broadcast_override_event(
                    "position_limit_removed",
                    {
                        "symbol": symbol,
                        "remove_all": remove_all,
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                target = f"symbol {symbol}" if symbol and not remove_all else "all symbols"
                self.logger.info(f"Position limit removed for {target}")
                return {
                    "status": "removed",
                    "message": f"Position limit removed for {target}",
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to remove position limit")

        except Exception as e:
            self.logger.error(f"Error removing position limit: {e}")
            raise

    async def set_daily_loss_limit(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Set daily loss limit.

        Args:
            request: Override request containing daily loss limit details

        Returns:
            Dict with daily loss limit result
        """
        try:
            self.logger.info(f"Setting daily loss limit - Triggered by: {request.triggered_by}")

            max_daily_loss = request.parameters.get("max_daily_loss")
            reset_time = request.parameters.get("reset_time", time(9, 15))  # Default 9:15 AM

            # Store daily loss limit
            success = await self.config_state.manual_override.set_daily_loss_limit(
                max_daily_loss=max_daily_loss,
                reset_time=reset_time,
                triggered_by=request.triggered_by,
                reason=request.reason
            )

            if success:
                # Broadcast daily loss limit event
                await self._broadcast_override_event(
                    "daily_loss_limit_set",
                    {
                        "max_daily_loss": max_daily_loss,
                        "reset_time": reset_time.isoformat() if reset_time else None,
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info(f"Daily loss limit set to {max_daily_loss}")
                return {
                    "status": "set",
                    "message": f"Daily loss limit set to {max_daily_loss}",
                    "max_daily_loss": max_daily_loss,
                    "reset_time": reset_time.isoformat() if reset_time else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to set daily loss limit")

        except Exception as e:
            self.logger.error(f"Error setting daily loss limit: {e}")
            raise

    async def remove_daily_loss_limit(self, request: OverrideRequest) -> Dict[str, Any]:
        """
        Remove daily loss limit.

        Args:
            request: Override request containing removal details

        Returns:
            Dict with removal result
        """
        try:
            self.logger.info(f"Removing daily loss limit - Triggered by: {request.triggered_by}")

            # Remove daily loss limit
            success = await self.config_state.manual_override.remove_daily_loss_limit(
                triggered_by=request.triggered_by,
                reason=request.reason
            )

            if success:
                # Broadcast daily loss limit removal event
                await self._broadcast_override_event(
                    "daily_loss_limit_removed",
                    {
                        "triggered_by": request.triggered_by,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                self.logger.info("Daily loss limit removed")
                return {
                    "status": "removed",
                    "message": "Daily loss limit removed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Failed to remove daily loss limit")

        except Exception as e:
            self.logger.error(f"Error removing daily loss limit: {e}")
            raise

    async def get_all_override_status(self) -> Dict[str, Any]:
        """
        Get current status of all manual overrides.

        Returns:
            Dict containing status of all overrides
        """
        try:
            self.logger.debug("Fetching manual override status")

            # Get override states
            override_states = await self.config_state.manual_override.get_all_override_states()

            # Return all states
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overrides": override_states
            }

        except Exception as e:
            self.logger.error(f"Error getting override status: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "overrides": {}
            }

    async def _broadcast_override_event(self, event_type: str, data: Dict[str, Any]):
        """
        Broadcast override event to event bus.

        Args:
            event_type: Type of override event
            data: Event data
        """
        try:
            event = Event(
                type=event_type,
                data=data,
                source="manual_override_service",
                timestamp=datetime.utcnow()
            )

            await self.event_bus.emit(event)

        except Exception as e:
            self.logger.error(f"Error broadcasting override event {event_type}: {e}")
            # Don't raise - broadcasting failures shouldn't stop the override operation
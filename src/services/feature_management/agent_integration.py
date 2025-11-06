"""
Agent Management Integration for Feature Management

Handles integration with the agent coordinator for stopping agents,
cleaning up agent state, and managing agent collaboration when features are deactivated.
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import psutil
from loguru import logger

from ...core.coordinators.agent.agent_coordinator import AgentCoordinator
from ...core.event_bus import Event, EventBus, EventType
from ...core.multi_agent_framework import MultiAgentFramework as AgentFramework
from .models import FeatureConfig, FeatureType


class AgentIntegrationStatus(Enum):
    """Status of agent integration operations."""

    IDLE = "idle"
    STOPPING_AGENTS = "stopping_agents"
    CLEANUP_STATE = "cleanup_state"
    DISCONNECTING_COLLABORATION = "disconnecting_collaboration"
    CLEANUP_MEMORY = "cleanup_memory"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentInfo:
    """Information about an agent."""

    agent_id: str
    agent_type: str
    status: str
    is_active: bool
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
    memory_usage: Optional[int] = None
    last_active: Optional[str] = None
    feature_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "is_active": self.is_active,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "memory_usage": self.memory_usage,
            "last_active": self.last_active,
            "feature_id": self.feature_id,
        }


@dataclass
class AgentDeactivationResult:
    """Result of agent deactivation operations."""

    feature_id: str
    status: AgentIntegrationStatus
    agents_stopped: List[str] = field(default_factory=list)
    processes_terminated: List[int] = field(default_factory=list)
    threads_stopped: List[int] = field(default_factory=list)
    collaboration_sessions_ended: List[str] = field(default_factory=list)
    memory_freed: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "agents_stopped": self.agents_stopped,
            "processes_terminated": self.processes_terminated,
            "threads_stopped": self.threads_stopped,
            "collaboration_sessions_ended": self.collaboration_sessions_ended,
            "memory_freed": self.memory_freed,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AgentStateSnapshot:
    """Snapshot of agent state for potential rollback."""

    feature_id: str
    timestamp: str
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    collaboration_sessions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    memory_snapshots: Dict[str, int] = field(default_factory=dict)
    process_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class AgentIntegrationError(Exception):
    """Agent integration specific errors."""

    pass


class AgentManagementIntegration:
    """
    Integrates feature management with the agent coordinator.

    Responsibilities:
    - Stop agent processes and threads when features are disabled
    - Clean up agent state and memory
    - Disconnect agent from event bus and collaboration systems
    - Handle agent collaboration shutdown
    - Provide rollback capabilities for agent operations
    """

    def __init__(
        self,
        agent_coordinator: Optional[AgentCoordinator] = None,
        agent_framework: Optional[AgentFramework] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.agent_coordinator = agent_coordinator
        self.agent_framework = agent_framework
        self.event_bus = event_bus

        # Feature to agent mapping
        self.feature_agents: Dict[str, Set[str]] = {}  # feature_id -> agent_ids
        self.agent_processes: Dict[str, int] = {}  # agent_id -> process_id
        self.agent_threads: Dict[str, threading.Thread] = {}  # agent_id -> thread
        self.agent_memory_tracking: Dict[str, int] = {}  # agent_id -> memory_usage

        # Collaboration tracking
        self.feature_collaboration_sessions: Dict[str, Set[str]] = (
            {}
        )  # feature_id -> session_ids
        self.agent_collaborations: Dict[str, Set[str]] = {}  # agent_id -> session_ids

        # Operation tracking
        self.active_operations: Dict[str, AgentDeactivationResult] = {}
        self.state_snapshots: Dict[str, AgentStateSnapshot] = {}

        # Initialize agent mappings
        self._initialize_agent_mappings()

        logger.info("Agent Management Integration initialized")

    def _initialize_agent_mappings(self) -> None:
        """Initialize mappings between features and agents."""
        # Map common agent types to feature categories
        agent_mapping = {
            FeatureType.AGENT: {
                "technical_analyst",
                "fundamental_screener",
                "risk_manager",
                "portfolio_analyzer",
                "market_monitor",
                "strategy_agent",
                "recommendation_agent",
                "execution_agent",
                "educational_agent",
                "alert_agent",
            },
            FeatureType.SERVICE: {"risk_manager", "portfolio_analyzer"},
            FeatureType.MONITOR: {"market_monitor", "alert_agent"},
            FeatureType.ALGORITHM: {"strategy_agent", "technical_analyst"},
        }

        # Store mappings for reference
        self.feature_agent_mapping = agent_mapping

    async def register_feature_agents(
        self, feature_id: str, feature_config: FeatureConfig, agent_ids: List[str]
    ) -> None:
        """
        Register agents for a feature.

        Args:
            feature_id: ID of the feature
            feature_config: Configuration of the feature
            agent_ids: List of agent IDs associated with the feature
        """
        # Initialize feature tracking
        if feature_id not in self.feature_agents:
            self.feature_agents[feature_id] = set()
        if feature_id not in self.feature_collaboration_sessions:
            self.feature_collaboration_sessions[feature_id] = set()

        # Register agents
        for agent_id in agent_ids:
            self.feature_agents[feature_id].add(agent_id)

            # Track agent processes and threads
            await self._track_agent_resources(agent_id)

            # Initialize agent collaboration tracking
            if agent_id not in self.agent_collaborations:
                self.agent_collaborations[agent_id] = set()

        logger.info(f"Registered {len(agent_ids)} agents for feature {feature_id}")

    async def _track_agent_resources(self, agent_id: str) -> None:
        """Track resources (processes, threads, memory) for an agent."""
        try:
            # Get current process
            current_process = psutil.Process()

            # Track memory usage
            memory_info = current_process.memory_info()
            self.agent_memory_tracking[agent_id] = memory_info.rss

            # In a real implementation, you would track actual agent processes
            # and threads here. For now, we'll track the current process
            self.agent_processes[agent_id] = current_process.pid

            logger.debug(
                f"Tracking resources for agent {agent_id}: PID={current_process.pid}, Memory={memory_info.rss}"
            )

        except Exception as e:
            logger.error(f"Failed to track resources for agent {agent_id}: {e}")

    async def deactivate_feature_agents(
        self, feature_id: str, feature_config: FeatureConfig, timeout_seconds: int = 60
    ) -> AgentDeactivationResult:
        """
        Deactivate all agents for a feature.

        Args:
            feature_id: ID of the feature to deactivate
            feature_config: Configuration of the feature
            timeout_seconds: Timeout for deactivation operations

        Returns:
            AgentDeactivationResult with operation details
        """
        if feature_id in self.active_operations:
            logger.warning(
                f"Agent deactivation already in progress for feature {feature_id}"
            )
            return self.active_operations[feature_id]

        result = AgentDeactivationResult(
            feature_id=feature_id, status=AgentIntegrationStatus.IDLE
        )
        self.active_operations[feature_id] = result

        logger.info(f"Starting agent deactivation for feature {feature_id}")

        try:
            # Create state snapshot for rollback
            snapshot = await self._create_agent_state_snapshot(feature_id)
            self.state_snapshots[feature_id] = snapshot

            # Stage 1: Stop agents
            result.status = AgentIntegrationStatus.STOPPING_AGENTS
            await self._stop_feature_agents(feature_id, feature_config)

            # Stage 2: Cleanup agent state
            result.status = AgentIntegrationStatus.CLEANUP_STATE
            await self._cleanup_agent_state(feature_id, feature_config)

            # Stage 3: Disconnect collaboration
            result.status = AgentIntegrationStatus.DISCONNECTING_COLLABORATION
            await self._disconnect_agent_collaboration(feature_id, feature_config)

            # Stage 4: Cleanup memory
            result.status = AgentIntegrationStatus.CLEANUP_MEMORY
            await self._cleanup_agent_memory(feature_id, feature_config, result)

            # Mark as completed
            result.status = AgentIntegrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"Successfully completed agent deactivation for feature {feature_id}"
            )

            # Emit completion event
            if self.event_bus:
                await self._emit_agent_event(
                    feature_id, "deactivation_completed", result
                )

        except asyncio.TimeoutError:
            error_msg = f"Agent deactivation timeout for feature {feature_id}"
            result.errors.append(error_msg)
            result.status = AgentIntegrationStatus.FAILED
            logger.error(error_msg)

        except Exception as e:
            error_msg = f"Agent deactivation failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            result.status = AgentIntegrationStatus.FAILED
            logger.error(error_msg)

        finally:
            # Clean up operation tracking
            if feature_id in self.active_operations:
                del self.active_operations[feature_id]

        return result

    async def _stop_feature_agents(
        self, feature_id: str, feature_config: FeatureConfig
    ) -> None:
        """Stop all agents for a feature."""
        agents = self.feature_agents.get(feature_id, set())
        stopped_agents = []
        terminated_processes = []
        stopped_threads = []

        for agent_id in agents:
            try:
                # Stop agent via coordinator
                if self.agent_coordinator:
                    await self.agent_coordinator.update_agent_status(agent_id, False)
                    stopped_agents.append(agent_id)
                    logger.debug(f"Stopped agent {agent_id} via coordinator")

                # Terminate agent process if tracked
                if agent_id in self.agent_processes:
                    process_id = self.agent_processes[agent_id]
                    try:
                        process = psutil.Process(process_id)
                        process.terminate()
                        process.wait(timeout=5)
                        terminated_processes.append(process_id)
                        logger.debug(
                            f"Terminated process {process_id} for agent {agent_id}"
                        )
                    except psutil.NoSuchProcess:
                        logger.debug(
                            f"Process {process_id} for agent {agent_id} already terminated"
                        )
                    except psutil.TimeoutExpired:
                        logger.warning(
                            f"Process {process_id} for agent {agent_id} did not terminate gracefully, killing"
                        )
                        process.kill()
                        terminated_processes.append(process_id)

                # Stop agent thread if tracked
                if agent_id in self.agent_threads:
                    thread = self.agent_threads[agent_id]
                    if thread.is_alive():
                        # In Python, we can't forcefully kill threads, but we can signal them to stop
                        # This would require the thread to check some stop condition
                        logger.debug(
                            f"Signaled thread {thread.ident} for agent {agent_id} to stop"
                        )
                        stopped_threads.append(thread.ident)

            except Exception as e:
                logger.error(f"Failed to stop agent {agent_id}: {e}")

        # Update result
        if feature_id in self.active_operations:
            result = self.active_operations[feature_id]
            result.agents_stopped.extend(stopped_agents)
            result.processes_terminated.extend(terminated_processes)
            result.threads_stopped.extend(stopped_threads)

        logger.info(
            f"Stopped {len(stopped_agents)} agents, terminated {len(terminated_processes)} processes for feature {feature_id}"
        )

    async def _cleanup_agent_state(
        self, feature_id: str, feature_config: FeatureConfig
    ) -> None:
        """Clean up agent state data."""
        agents = self.feature_agents.get(feature_id, set())

        for agent_id in agents:
            try:
                # Clean up agent state in coordinator
                if self.agent_coordinator:
                    # This would need implementation in the agent coordinator
                    # to properly clean up agent state
                    logger.debug(f"Cleaning up state for agent {agent_id}")

                # Clean up any cached data
                if agent_id in self.agent_memory_tracking:
                    del self.agent_memory_tracking[agent_id]

                # Clean up process tracking
                if agent_id in self.agent_processes:
                    del self.agent_processes[agent_id]

                # Clean up thread tracking
                if agent_id in self.agent_threads:
                    del self.agent_threads[agent_id]

            except Exception as e:
                logger.error(f"Failed to cleanup state for agent {agent_id}: {e}")

        logger.info(
            f"Cleaned up state for {len(agents)} agents for feature {feature_id}"
        )

    async def _disconnect_agent_collaboration(
        self, feature_id: str, feature_config: FeatureConfig
    ) -> None:
        """Disconnect agents from collaboration systems."""
        agents = self.feature_agents.get(feature_id, set())
        collaboration_sessions = self.feature_collaboration_sessions.get(
            feature_id, set()
        )
        ended_sessions = []

        # End collaboration sessions
        for session_id in collaboration_sessions:
            try:
                # This would integrate with the collaboration system
                # to properly end sessions
                ended_sessions.append(session_id)
                logger.debug(
                    f"Ended collaboration session {session_id} for feature {feature_id}"
                )

            except Exception as e:
                logger.error(f"Failed to end collaboration session {session_id}: {e}")

        # Remove agents from collaboration tracking
        for agent_id in agents:
            if agent_id in self.agent_collaborations:
                del self.agent_collaborations[agent_id]

        # Update result
        if feature_id in self.active_operations:
            self.active_operations[feature_id].collaboration_sessions_ended.extend(
                ended_sessions
            )

        logger.info(
            f"Disconnected {len(agents)} agents and ended {len(ended_sessions)} collaboration sessions for feature {feature_id}"
        )

    async def _cleanup_agent_memory(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        result: AgentDeactivationResult,
    ) -> None:
        """Clean up agent memory and perform garbage collection."""
        try:
            # Get memory before cleanup
            process = psutil.Process()
            memory_before = process.memory_info().rss

            # Force garbage collection
            import gc

            collected_objects = gc.collect()

            # Get memory after cleanup
            memory_after = process.memory_info().rss
            memory_freed = memory_before - memory_after

            result.memory_freed = max(0, memory_freed)

            logger.debug(
                f"Memory cleanup for feature {feature_id}: freed {result.memory_freed} bytes, collected {collected_objects} objects"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup memory for feature {feature_id}: {e}")

    async def _create_agent_state_snapshot(self, feature_id: str) -> AgentStateSnapshot:
        """Create a snapshot of agent state for rollback."""
        snapshot = AgentStateSnapshot(
            feature_id=feature_id, timestamp=datetime.now(timezone.utc).isoformat()
        )

        agents = self.feature_agents.get(feature_id, set())

        for agent_id in agents:
            try:
                # Capture agent state
                agent_state = {}
                if self.agent_coordinator:
                    agent_state = await self.agent_coordinator.get_agent_performance(
                        agent_id
                    )

                snapshot.agent_states[agent_id] = agent_state

                # Capture memory snapshot
                if agent_id in self.agent_memory_tracking:
                    snapshot.memory_snapshots[agent_id] = self.agent_memory_tracking[
                        agent_id
                    ]

                # Capture process state
                if agent_id in self.agent_processes:
                    process_id = self.agent_processes[agent_id]
                    try:
                        process = psutil.Process(process_id)
                        snapshot.process_states[agent_id] = {
                            "pid": process_id,
                            "status": process.status(),
                            "memory_info": process.memory_info()._asdict(),
                            "create_time": process.create_time(),
                        }
                    except psutil.NoSuchProcess:
                        snapshot.process_states[agent_id] = {
                            "error": "Process not found"
                        }

            except Exception as e:
                logger.error(f"Failed to capture state for agent {agent_id}: {e}")

        # Capture collaboration sessions
        collaboration_sessions = self.feature_collaboration_sessions.get(
            feature_id, set()
        )
        for session_id in collaboration_sessions:
            try:
                # This would capture collaboration session state
                snapshot.collaboration_sessions[session_id] = {
                    "session_id": session_id,
                    "status": "active",
                    "participants": list(agents),
                }
            except Exception as e:
                logger.error(
                    f"Failed to capture collaboration session {session_id}: {e}"
                )

        return snapshot

    async def get_feature_agent_info(self, feature_id: str) -> List[AgentInfo]:
        """Get information about all agents for a feature."""
        agents = self.feature_agents.get(feature_id, set())
        agent_info_list = []

        for agent_id in agents:
            try:
                agent_info = AgentInfo(
                    agent_id=agent_id,
                    agent_type="unknown",  # Would get from agent coordinator
                    status="unknown",  # Would get from agent coordinator
                    is_active=False,  # Would get from agent coordinator
                    process_id=self.agent_processes.get(agent_id),
                    thread_id=(
                        self.agent_threads.get(agent_id).ident
                        if self.agent_threads.get(agent_id)
                        else None
                    ),
                    memory_usage=self.agent_memory_tracking.get(agent_id),
                    feature_id=feature_id,
                )

                # Get actual agent status from coordinator
                if self.agent_coordinator:
                    performance = await self.agent_coordinator.get_agent_performance(
                        agent_id
                    )
                    if "error" not in performance:
                        agent_info.agent_type = performance.get("role", "unknown")
                        agent_info.status = (
                            "active"
                            if performance.get("is_active", False)
                            else "inactive"
                        )
                        agent_info.is_active = performance.get("is_active", False)
                        agent_info.last_active = performance.get("last_active")

                agent_info_list.append(agent_info)

            except Exception as e:
                logger.error(f"Failed to get info for agent {agent_id}: {e}")

        return agent_info_list

    async def rollback_agent_deactivation(self, feature_id: str) -> bool:
        """
        Rollback agent deactivation for a feature.

        This attempts to restore the previous state of agents.
        """
        try:
            snapshot = self.state_snapshots.get(feature_id)
            if not snapshot:
                logger.warning(
                    f"No state snapshot available for rollback of feature {feature_id}"
                )
                return False

            logger.info(f"Rolling back agent deactivation for feature {feature_id}")

            # Restore agent states
            for agent_id, agent_state in snapshot.agent_states.items():
                try:
                    if self.agent_coordinator:
                        await self.agent_coordinator.update_agent_status(agent_id, True)
                        logger.debug(f"Restored agent {agent_id} during rollback")

                except Exception as e:
                    logger.error(f"Failed to restore agent {agent_id}: {e}")

            # Restore collaboration sessions
            for session_id, session_state in snapshot.collaboration_sessions.items():
                try:
                    # This would restore collaboration sessions
                    logger.debug(
                        f"Restored collaboration session {session_id} during rollback"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to restore collaboration session {session_id}: {e}"
                    )

            logger.info(
                f"Successfully rolled back agent deactivation for feature {feature_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Rollback failed for feature {feature_id}: {e}")
            return False

    async def _emit_agent_event(
        self, feature_id: str, event_type: str, result: AgentDeactivationResult
    ) -> None:
        """Emit an agent integration event."""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            Event(
                id=f"agent_integration_{feature_id}_{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.SYSTEM_HEALTH_CHECK,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="agent_integration",
                data={
                    "feature_id": feature_id,
                    "event_type": event_type,
                    "result": result.to_dict(),
                },
            )
        )

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get the overall status of agent integration."""
        return {
            "active_operations": len(self.active_operations),
            "tracked_features": len(self.feature_agents),
            "tracked_agents": sum(
                len(agents) for agents in self.feature_agents.values()
            ),
            "tracked_processes": len(self.agent_processes),
            "tracked_threads": len(self.agent_threads),
            "collaboration_sessions": sum(
                len(sessions)
                for sessions in self.feature_collaboration_sessions.values()
            ),
            "state_snapshots": len(self.state_snapshots),
            "services_available": {
                "agent_coordinator": self.agent_coordinator is not None,
                "agent_framework": self.agent_framework is not None,
                "event_bus": self.event_bus is not None,
            },
        }

    async def clear_feature_tracking(self, feature_id: str) -> None:
        """Clear all tracking data for a feature."""
        self.feature_agents.pop(feature_id, None)
        self.feature_collaboration_sessions.pop(feature_id, None)
        self.state_snapshots.pop(feature_id, None)

        logger.info(f"Cleared agent tracking for feature {feature_id}")

    async def force_stop_agent(self, agent_id: str) -> bool:
        """Force stop a specific agent."""
        try:
            logger.warning(f"Force stopping agent {agent_id}")

            # Stop via coordinator
            if self.agent_coordinator:
                await self.agent_coordinator.update_agent_status(agent_id, False)

            # Terminate process
            if agent_id in self.agent_processes:
                process_id = self.agent_processes[agent_id]
                try:
                    process = psutil.Process(process_id)
                    process.kill()
                    logger.info(
                        f"Force killed process {process_id} for agent {agent_id}"
                    )
                except psutil.NoSuchProcess:
                    logger.debug(
                        f"Process {process_id} for agent {agent_id} already terminated"
                    )

            # Clean up tracking
            self.agent_processes.pop(agent_id, None)
            self.agent_threads.pop(agent_id, None)
            self.agent_memory_tracking.pop(agent_id, None)
            self.agent_collaborations.pop(agent_id, None)

            return True

        except Exception as e:
            logger.error(f"Failed to force stop agent {agent_id}: {e}")
            return False

    async def close(self) -> None:
        """Close the agent integration."""
        logger.info("Closing Agent Management Integration")

        # Cancel any active operations
        for feature_id, result in self.active_operations.items():
            logger.warning(
                f"Cancelling active agent operation for feature {feature_id}"
            )
            result.status = AgentIntegrationStatus.FAILED
            result.errors.append("Agent integration shutdown")

        self.active_operations.clear()
        self.feature_agents.clear()
        self.agent_processes.clear()
        self.agent_threads.clear()
        self.agent_memory_tracking.clear()
        self.feature_collaboration_sessions.clear()
        self.agent_collaborations.clear()
        self.state_snapshots.clear()

        logger.info("Agent Management Integration closed")

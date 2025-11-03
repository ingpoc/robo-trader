"""
Coordinators for Multi-Agent Framework

Separated coordinators to follow the 350-line modularization rule.
"""

from .base_coordinator import BaseCoordinator

# Core coordinators
from .core.session_coordinator import SessionCoordinator
from .core.query_coordinator import QueryCoordinator
from .core.lifecycle_coordinator import LifecycleCoordinator
from .core.portfolio_coordinator import PortfolioCoordinator

# Status coordinators
from .status.status_coordinator import StatusCoordinator
from .status.system_status_coordinator import SystemStatusCoordinator
from .status.scheduler_status_coordinator import SchedulerStatusCoordinator
from .status.infrastructure_status_coordinator import InfrastructureStatusCoordinator
from .status.ai_status_coordinator import AIStatusCoordinator
from .status.agent_status_coordinator import AgentStatusCoordinator
from .status.portfolio_status_coordinator import PortfolioStatusCoordinator

# Queue coordinators
from .queue.queue_coordinator import QueueCoordinator
from .queue.queue_execution_coordinator import QueueExecutionCoordinator
from .queue.queue_monitoring_coordinator import QueueMonitoringCoordinator
from .queue.queue_event_coordinator import QueueEventCoordinator
from .queue.queue_lifecycle_coordinator import QueueLifecycleCoordinator

# Task coordinators
from .task.task_coordinator import TaskCoordinator
from .task.task_creation_coordinator import TaskCreationCoordinator
from .task.task_execution_coordinator import TaskExecutionCoordinator
from .task.task_maintenance_coordinator import TaskMaintenanceCoordinator

# Message coordinators
from .message.message_coordinator import MessageCoordinator
from .message.message_routing_coordinator import MessageRoutingCoordinator
from .message.message_handling_coordinator import MessageHandlingCoordinator

# Broadcast coordinators
from .broadcast.broadcast_coordinator import BroadcastCoordinator
from .broadcast.broadcast_execution_coordinator import BroadcastExecutionCoordinator
from .broadcast.broadcast_health_coordinator import BroadcastHealthCoordinator

# Agent coordinators
from .agent.agent_coordinator import AgentCoordinator
from .agent.claude_agent_coordinator import ClaudeAgentCoordinator
from .agent.session.agent_session_coordinator import AgentSessionCoordinator
from .agent.agent_tool_coordinator import AgentToolCoordinator
from .agent.agent_prompt_builder import AgentPromptBuilder
from .agent.agent_registration_coordinator import AgentRegistrationCoordinator
from .agent.agent_communication_coordinator import AgentCommunicationCoordinator

# Core processing coordinators
from .core.query_processing_coordinator import QueryProcessingCoordinator
from .core.session_authentication_coordinator import SessionAuthenticationCoordinator
from .core.session_lifecycle_coordinator import SessionLifecycleCoordinator

# Models
from .message.agent_message import AgentMessage, MessageType
from .agent.agent_profile import AgentProfile, AgentRole
from .task.collaboration_task import CollaborationTask, CollaborationMode

__all__ = [
    'AgentCoordinator',
    'TaskCoordinator',
    'MessageCoordinator',
    'BaseCoordinator',
    'AgentMessage',
    'MessageType',
    'AgentProfile',
    'AgentRole',
    'CollaborationTask',
    'CollaborationMode',
    'SessionCoordinator',
    'QueryCoordinator',
    'StatusCoordinator',
    'LifecycleCoordinator',
    'BroadcastCoordinator',
    'ClaudeAgentCoordinator',
    'SystemStatusCoordinator',
    'SchedulerStatusCoordinator',
    'InfrastructureStatusCoordinator',
    'AIStatusCoordinator',
    'AgentStatusCoordinator',
    'PortfolioStatusCoordinator',
    'AgentSessionCoordinator',
    'AgentToolCoordinator',
    'AgentPromptBuilder',
    'QueueExecutionCoordinator',
    'QueueMonitoringCoordinator',
    'QueueEventCoordinator',
    'QueueLifecycleCoordinator',
    'TaskCreationCoordinator',
    'TaskExecutionCoordinator',
    'TaskMaintenanceCoordinator',
    'MessageRoutingCoordinator',
    'MessageHandlingCoordinator',
    'BroadcastExecutionCoordinator',
    'BroadcastHealthCoordinator',
    'AgentRegistrationCoordinator',
    'AgentCommunicationCoordinator',
    'QueryProcessingCoordinator',
    'SessionAuthenticationCoordinator',
    'SessionLifecycleCoordinator'
]

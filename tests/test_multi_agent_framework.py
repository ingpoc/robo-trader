"""
Tests for Multi-Agent Collaboration Framework
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.core.multi_agent_framework import (
    MultiAgentFramework,
    AgentRole,
    CollaborationMode,
    MessageType,
    AgentMessage,
    CollaborationTask,
    AgentProfile
)
from src.config import Config
from src.core.database_state import DatabaseStateManager
from src.core.event_bus import EventBus


@pytest.fixture
def config():
    """Test configuration."""
    return Config()


@pytest.fixture
def mock_state_manager():
    """Mock state manager for testing."""
    return Mock(spec=DatabaseStateManager)


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    return Mock(spec=EventBus)


@pytest.fixture
async def framework(config, mock_state_manager, mock_event_bus):
    """Multi-agent framework instance for testing."""
    framework = MultiAgentFramework(config, mock_state_manager, mock_event_bus)
    await framework.initialize()
    yield framework
    await framework.cleanup()


class TestAgentMessage:
    """Test AgentMessage dataclass."""

    def test_creation(self):
        """Test creating AgentMessage."""
        message = AgentMessage(
            message_id="msg_123",
            sender_agent="technical_analyst",
            recipient_agent="coordinator",
            message_type=MessageType.ANALYSIS_RESPONSE,
            content={"analysis": "Bullish trend detected"},
            correlation_id="task_456",
            priority=8
        )

        assert message.message_id == "msg_123"
        assert message.sender_agent == "technical_analyst"
        assert message.recipient_agent == "coordinator"
        assert message.message_type == MessageType.ANALYSIS_RESPONSE
        assert message.correlation_id == "task_456"
        assert message.priority == 8

    def test_from_dict(self):
        """Test creating AgentMessage from dict."""
        data = {
            "message_id": "msg_789",
            "sender_agent": "risk_manager",
            "recipient_agent": "coordinator",
            "message_type": "analysis_response",
            "content": {"risk_score": 0.75},
            "correlation_id": "task_101",
            "priority": 9
        }
        message = AgentMessage.from_dict(data)

        assert message.message_id == "msg_789"
        assert message.message_type == MessageType.ANALYSIS_RESPONSE
        assert message.content["risk_score"] == 0.75


class TestCollaborationTask:
    """Test CollaborationTask dataclass."""

    def test_creation(self):
        """Test creating CollaborationTask."""
        task = CollaborationTask(
            task_id="collab_123",
            description="Analyze AAPL for potential trade",
            required_roles=[AgentRole.TECHNICAL_ANALYST, AgentRole.RISK_MANAGER],
            collaboration_mode=CollaborationMode.SEQUENTIAL,
            assigned_agents=["technical_analyst", "risk_manager"],
            status="in_progress"
        )

        assert task.task_id == "collab_123"
        assert len(task.required_roles) == 2
        assert task.collaboration_mode == CollaborationMode.SEQUENTIAL
        assert task.status == "in_progress"

    def test_from_dict(self):
        """Test creating CollaborationTask from dict."""
        data = {
            "task_id": "collab_456",
            "description": "Risk assessment for portfolio",
            "required_roles": ["risk_manager", "portfolio_analyzer"],
            "collaboration_mode": "parallel",
            "assigned_agents": ["risk_manager"],
            "status": "pending"
        }
        task = CollaborationTask.from_dict(data)

        assert task.task_id == "collab_456"
        assert len(task.required_roles) == 2
        assert task.required_roles[0] == AgentRole.RISK_MANAGER
        assert task.collaboration_mode == CollaborationMode.PARALLEL


class TestAgentProfile:
    """Test AgentProfile dataclass."""

    def test_creation(self):
        """Test creating AgentProfile."""
        profile = AgentProfile(
            agent_id="technical_analyst",
            role=AgentRole.TECHNICAL_ANALYST,
            capabilities=["chart_analysis", "pattern_recognition"],
            specialization_areas=["trend_analysis", "momentum_signals"],
            performance_score=0.85,
            is_active=True
        )

        assert profile.agent_id == "technical_analyst"
        assert profile.role == AgentRole.TECHNICAL_ANALYST
        assert profile.performance_score == 0.85
        assert profile.is_active == True

    def test_from_dict(self):
        """Test creating AgentProfile from dict."""
        data = {
            "agent_id": "fundamental_screener",
            "role": "fundamental_screener",
            "capabilities": ["financial_analysis", "valuation"],
            "specialization_areas": ["growth_stocks", "value_investing"],
            "performance_score": 0.78
        }
        profile = AgentProfile.from_dict(data)

        assert profile.agent_id == "fundamental_screener"
        assert profile.role == AgentRole.FUNDAMENTAL_SCREENER
        assert profile.performance_score == 0.78


class TestMultiAgentFramework:
    """Test MultiAgentFramework functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, framework):
        """Test framework initialization."""
        assert framework._running == True
        assert framework._coordinator_task is not None
        assert len(framework.registered_agents) > 0  # Should have builtin agents

    @pytest.mark.asyncio
    async def test_register_agent(self, framework):
        """Test agent registration."""
        profile = AgentProfile(
            agent_id="test_agent",
            role=AgentRole.STRATEGY_AGENT,
            capabilities=["strategy_design"],
            specialization_areas=["swing_trading"]
        )

        success = await framework.register_agent(profile)
        assert success == True
        assert "test_agent" in framework.registered_agents

    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, framework):
        """Test registering duplicate agent."""
        profile = AgentProfile(
            agent_id="duplicate_agent",
            role=AgentRole.TECHNICAL_ANALYST,
            capabilities=["analysis"],
            specialization_areas=["charts"]
        )

        # First registration should succeed
        success1 = await framework.register_agent(profile)
        assert success1 == True

        # Second registration should fail
        success2 = await framework.register_agent(profile)
        assert success2 == False

    @pytest.mark.asyncio
    async def test_create_collaboration_task(self, framework):
        """Test creating collaboration task."""
        task = await framework.create_collaboration_task(
            description="Test analysis task",
            required_roles=[AgentRole.TECHNICAL_ANALYST],
            collaboration_mode=CollaborationMode.SEQUENTIAL
        )

        assert task is not None
        assert task.description == "Test analysis task"
        assert len(task.required_roles) == 1
        assert task.collaboration_mode == CollaborationMode.SEQUENTIAL
        assert task.task_id in framework.active_tasks

    @pytest.mark.asyncio
    async def test_create_task_no_available_agents(self, framework):
        """Test creating task when no agents are available for required roles."""
        # Try to create task requiring a role that doesn't exist
        task = await framework.create_collaboration_task(
            description="Impossible task",
            required_roles=[AgentRole(999)],  # Invalid role
            collaboration_mode=CollaborationMode.SEQUENTIAL
        )

        assert task is None

    @pytest.mark.asyncio
    async def test_send_message(self, framework, mock_event_bus):
        """Test sending messages between agents."""
        message = AgentMessage(
            message_id="test_msg",
            sender_agent="sender",
            recipient_agent="recipient",
            message_type=MessageType.STATUS_UPDATE,
            content={"status": "working"}
        )

        await framework.send_message(message)

        # Check that event was published
        mock_event_bus.publish.assert_called_once()
        event_call = mock_event_bus.publish.call_args[0][0]
        assert event_call.data["task_type"] == "agent_message"
        assert event_call.data["message"]["message_id"] == "test_msg"

    @pytest.mark.asyncio
    async def test_get_collaboration_result_completed(self, framework):
        """Test getting result of completed task."""
        # Create a completed task
        task = CollaborationTask(
            task_id="completed_task",
            description="Test task",
            required_roles=[AgentRole.TECHNICAL_ANALYST],
            collaboration_mode=CollaborationMode.SEQUENTIAL,
            status="completed",
            result={"final_decision": "BUY", "confidence": 0.85}
        )
        framework.active_tasks[task.task_id] = task

        result = await framework.get_collaboration_result(task.task_id)
        assert result == task.result

    @pytest.mark.asyncio
    async def test_get_collaboration_result_incomplete(self, framework):
        """Test getting result of incomplete task."""
        # Create an incomplete task
        task = CollaborationTask(
            task_id="incomplete_task",
            description="Test task",
            required_roles=[AgentRole.TECHNICAL_ANALYST],
            collaboration_mode=CollaborationMode.SEQUENTIAL,
            status="in_progress"
        )
        framework.active_tasks[task.task_id] = task

        result = await framework.get_collaboration_result(task.task_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_agent_performance(self, framework):
        """Test getting agent performance metrics."""
        # Test with existing agent
        performance = await framework.get_agent_performance("technical_analyst")
        assert performance["agent_id"] == "technical_analyst"
        assert "performance_score" in performance
        assert "completed_tasks" in performance

    @pytest.mark.asyncio
    async def test_get_agent_performance_not_found(self, framework):
        """Test getting performance for non-existent agent."""
        performance = await framework.get_agent_performance("non_existent_agent")
        assert performance["error"] == "Agent not found"

    @pytest.mark.asyncio
    async def test_builtin_agents_registered(self, framework):
        """Test that builtin agents are registered."""
        expected_agents = [
            "technical_analyst",
            "fundamental_screener",
            "risk_manager",
            "portfolio_analyzer",
            "market_monitor",
            "strategy_agent"
        ]

        for agent_id in expected_agents:
            assert agent_id in framework.registered_agents
            agent = framework.registered_agents[agent_id]
            assert isinstance(agent, AgentProfile)
            assert agent.is_active == True

    @pytest.mark.asyncio
    async def test_message_processing(self, framework):
        """Test message processing in coordination loop."""
        # Create a task first
        task = await framework.create_collaboration_task(
            description="Test message processing",
            required_roles=[AgentRole.TECHNICAL_ANALYST],
            collaboration_mode=CollaborationMode.SEQUENTIAL
        )
        assert task is not None

        # Send an analysis response message
        message = AgentMessage(
            message_id="analysis_response_1",
            sender_agent="technical_analyst",
            recipient_agent="coordinator",
            message_type=MessageType.ANALYSIS_RESPONSE,
            content={"analysis": "Bullish signals detected", "confidence": 0.8},
            correlation_id=task.task_id
        )

        await framework.send_message(message)

        # Give the coordination loop time to process
        await asyncio.sleep(0.1)

        # Check that message was added to task
        updated_task = framework.active_tasks.get(task.task_id)
        assert updated_task is not None
        assert len(updated_task.messages) > 0
        assert updated_task.messages[-1].message_id == "analysis_response_1"


class TestAgentEnums:
    """Test agent-related enums."""

    def test_agent_role_values(self):
        """Test AgentRole enum values."""
        assert AgentRole.TECHNICAL_ANALYST.value == "technical_analyst"
        assert AgentRole.FUNDAMENTAL_SCREENER.value == "fundamental_screener"
        assert AgentRole.RISK_MANAGER.value == "risk_manager"
        assert AgentRole.PORTFOLIO_ANALYST.value == "portfolio_analyzer"
        assert AgentRole.MARKET_MONITOR.value == "market_monitor"
        assert AgentRole.STRATEGY_AGENT.value == "strategy_agent"
        assert AgentRole.EXECUTION_AGENT.value == "execution_agent"
        assert AgentRole.COORDINATOR.value == "coordinator"

    def test_collaboration_mode_values(self):
        """Test CollaborationMode enum values."""
        assert CollaborationMode.SEQUENTIAL.value == "sequential"
        assert CollaborationMode.PARALLEL.value == "parallel"
        assert CollaborationMode.VOTING.value == "voting"
        assert CollaborationMode.CONSENSUS.value == "consensus"
        assert CollaborationMode.HYBRID.value == "hybrid"

    def test_message_type_values(self):
        """Test MessageType enum values."""
        assert MessageType.ANALYSIS_REQUEST.value == "analysis_request"
        assert MessageType.ANALYSIS_RESPONSE.value == "analysis_response"
        assert MessageType.DECISION_PROPOSAL.value == "decision_proposal"
        assert MessageType.VOTE.value == "vote"
        assert MessageType.CONSENSUS_UPDATE.value == "consensus_update"
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.ERROR_REPORT.value == "error_report"


class TestFrameworkIntegration:
    """Integration tests for the framework."""

    @pytest.mark.asyncio
    async def test_full_collaboration_workflow(self, framework):
        """Test complete collaboration workflow."""
        # Create a collaboration task
        task = await framework.create_collaboration_task(
            description="Complete analysis workflow test",
            required_roles=[AgentRole.TECHNICAL_ANALYST, AgentRole.RISK_MANAGER],
            collaboration_mode=CollaborationMode.SEQUENTIAL
        )

        assert task is not None
        assert task.status == "pending"
        assert len(task.assigned_agents) == 2

        # Simulate agents sending analysis responses
        for agent_id in task.assigned_agents:
            message = AgentMessage(
                message_id=f"analysis_{agent_id}",
                sender_agent=agent_id,
                recipient_agent="coordinator",
                message_type=MessageType.ANALYSIS_RESPONSE,
                content={
                    "analysis": f"Analysis from {agent_id}",
                    "confidence": 0.8,
                    "recommendation": "BUY" if agent_id == "technical_analyst" else "HOLD"
                },
                correlation_id=task.task_id
            )
            await framework.send_message(message)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Check that task is still in progress (needs both responses for completion)
        # Note: In real implementation, this would trigger completion logic
        updated_task = framework.active_tasks.get(task.task_id)
        assert updated_task is not None
        assert len(updated_task.messages) == 2

    @pytest.mark.asyncio
    async def test_agent_assignment_logic(self, framework):
        """Test agent assignment for different roles."""
        # Test assignment for technical analyst
        task1 = await framework.create_collaboration_task(
            description="Technical analysis task",
            required_roles=[AgentRole.TECHNICAL_ANALYST],
            collaboration_mode=CollaborationMode.SEQUENTIAL
        )
        assert task1 is not None
        assert "technical_analyst" in task1.assigned_agents

        # Test assignment for multiple roles
        task2 = await framework.create_collaboration_task(
            description="Multi-role analysis task",
            required_roles=[AgentRole.TECHNICAL_ANALYST, AgentRole.RISK_MANAGER],
            collaboration_mode=CollaborationMode.PARALLEL
        )
        assert task2 is not None
        assert len(task2.assigned_agents) == 2
        assert "technical_analyst" in task2.assigned_agents
        assert "risk_manager" in task2.assigned_agents
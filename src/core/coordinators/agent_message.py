"""
Agent Message Types for Multi-Agent Framework

Defines message structure and types for inter-agent communication.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import uuid


class MessageType(Enum):
    """Types of messages between agents."""

    # Task-related messages
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESPONSE = "task_response"
    TASK_COMPLETION = "task_completion"

    # Analysis messages
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_RESPONSE = "analysis_response"

    # Decision messages
    DECISION_PROPOSAL = "decision_proposal"
    DECISION_FEEDBACK = "decision_feedback"
    VOTE = "vote"

    # Status messages
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"

    # Error messages
    ERROR_REPORT = "error_report"

    # Collaboration messages
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_RESPONSE = "collaboration_response"


@dataclass
class AgentMessage:
    """Message structure for inter-agent communication."""

    message_id: str
    sender_id: str
    recipient_id: Optional[str]
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    priority: int = 1  # 1=low, 5=high

    def __init__(
        self,
        sender_id: str,
        recipient_id: Optional[str],
        message_type: MessageType,
        content: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 1
    ):
        self.message_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content = content
        self.timestamp = datetime.now(timezone.utc)
        self.correlation_id = correlation_id or self.message_id
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        message = cls(
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            message_type=MessageType(data["message_type"]),
            content=data["content"],
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 1)
        )
        message.message_id = data["message_id"]
        message.timestamp = datetime.fromisoformat(data["timestamp"])
        return message
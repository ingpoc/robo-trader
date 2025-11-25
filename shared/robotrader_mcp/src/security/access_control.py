"""
Access Control System for Robo-Trader MCP Tools.

Implements Anthropic's allowed_callers pattern for secure tool access restrictions.
"""

from typing import Dict, List, Set, Optional, Any
from enum import Enum
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CallerRole(Enum):
    """Defined caller roles with permission levels."""
    DISCOVERY = "discovery"           # Can search and browse tools
    MONITORING = "monitoring"         # Can read system status and health
    ANALYSIS = "analysis"             # Can run analysis and diagnostic tools
    DEBUGGING = "debugging"           # Can access debugging and diagnostic tools
    ADMIN = "admin"                   # Full system access


@dataclass
class ToolPermissions:
    """Permission configuration for a tool."""
    allowed_callers: List[str]
    requires_context: bool = False
    context_requirements: Optional[Dict[str, Any]] = None
    rate_limit: Optional[int] = None  # Max calls per minute
    audit_log: bool = True


class AccessControlSystem:
    """Manages tool access control with caller context validation."""

    def __init__(self):
        self.tool_permissions: Dict[str, ToolPermissions] = self._initialize_permissions()
        self.caller_context_cache: Dict[str, Dict[str, Any]] = {}

    def _initialize_permissions(self) -> Dict[str, ToolPermissions]:
        """Define permission levels for all tools."""
        return {
            # Discovery Tools (Public Access)
            "list_directories": ToolPermissions(
                allowed_callers=["*"],  # All callers
                requires_context=False,
                audit_log=False
            ),
            "search_tools": ToolPermissions(
                allowed_callers=["*"],  # All callers
                requires_context=False,
                audit_log=False
            ),
            "read_file": ToolPermissions(
                allowed_callers=["*"],  # All callers
                requires_context=False,
                audit_log=False
            ),

            # System Monitoring Tools (Monitoring Role)
            "check_system_health": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "system", "operation": "health_check"},
                rate_limit=10
            ),
            "queue_status": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "queue", "operation": "status_monitoring"}
            ),
            "coordinator_status": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "coordinator", "operation": "health_check"}
            ),
            "real_time_performance_monitor": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "performance", "operation": "monitoring"}
            ),

            # Analysis Tools (Analysis Role)
            "analyze_logs": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "logs", "operation": "analysis"},
                rate_limit=20
            ),
            "query_portfolio": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "portfolio", "operation": "query"}
            ),
            "context_aware_summarize": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "data", "operation": "summarization"}
            ),
            "smart_file_read": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "filesystem", "operation": "read"}
            ),
            "execute_analysis": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "analysis", "operation": "execute"}
            ),

            # Advanced Tools (Debugging Role)
            "diagnose_database_locks": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "database", "operation": "diagnosis"},
                rate_limit=5
            ),
            "verify_configuration_integrity": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "config", "operation": "verification"}
            ),
            "suggest_fix": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "error", "operation": "fix_suggestion"}
            ),
            "knowledge_query": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "knowledge", "operation": "query"}
            ),
            "find_related_files": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "filesystem", "operation": "search"}
            ),

            # Execution Tools (Admin Role)
            "execute_python": ToolPermissions(
                allowed_callers=["admin"],
                requires_context=True,
                context_requirements={"component": "execution", "operation": "python_code"},
                rate_limit=10
            ),
            "workflow_orchestrator": ToolPermissions(
                allowed_callers=["admin"],
                requires_context=True,
                context_requirements={"component": "workflow", "operation": "orchestrate"},
                rate_limit=15
            ),

            # Performance & Metrics Tools
            "task_execution_metrics": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "metrics", "operation": "task_analysis"}
            ),
            "token_metrics_collector": ToolPermissions(
                allowed_callers=["monitoring", "analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "metrics", "operation": "token_analysis"}
            ),
            "smart_cache": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "cache", "operation": "analysis"}
            ),
            "session_context_injection": ToolPermissions(
                allowed_callers=["debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "session", "operation": "context_management"}
            ),
            "enhanced_differential_analysis": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "analysis", "operation": "differential"}
            ),
            "differential_analysis": ToolPermissions(
                allowed_callers=["analysis", "debugging", "admin"],
                requires_context=True,
                context_requirements={"component": "analysis", "operation": "differential"}
            )
        }

    def check_tool_access(self, tool_name: str, caller_context: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[str]]:
        """
        Check if the caller has permission to access the requested tool.

        Args:
            tool_name: Name of the tool being accessed
            caller_context: Context information about the caller

        Returns:
            Tuple of (has_access, denial_reason)
        """
        if tool_name not in self.tool_permissions:
            return False, f"Tool {tool_name} not found in permission registry"

        permissions = self.tool_permissions[tool_name]

        # Check wildcard access
        if "*" in permissions.allowed_callers:
            return True, None

        # For now, implement basic caller identification
        # In a full implementation, this would extract role from caller_context
        caller_role = self._extract_caller_role(caller_context)

        if caller_role not in permissions.allowed_callers:
            return False, f"Caller role '{caller_role}' not in allowed_callers for {tool_name}"

        if permissions.requires_context and not caller_context:
            return False, f"Tool {tool_name} requires caller context but none provided"

        # Additional context validation can be added here
        if permissions.context_requirements and caller_context:
            context_valid = self._validate_context_requirements(
                permissions.context_requirements,
                caller_context
            )
            if not context_valid:
                return False, f"Caller context does not meet requirements for {tool_name}"

        return True, None

    def _extract_caller_role(self, caller_context: Optional[Dict[str, Any]]) -> str:
        """
        Extract role from caller context.
        For now, default to 'analysis' role for basic functionality.

        In a full implementation, this would analyze the caller_context
        to determine the appropriate role based on:
        - Agent type/name
        - Task context
        - User permissions
        - Session information
        """
        if not caller_context:
            return "analysis"  # Default safe role

        # Extract role from context if provided
        if "role" in caller_context:
            return caller_context["role"]

        # Analyze context patterns to determine role
        context_str = json.dumps(caller_context, default=str).lower()

        if any(keyword in context_str for keyword in ["debug", "error", "issue", "problem"]):
            return "debugging"
        elif any(keyword in context_str for keyword in ["monitor", "health", "status", "metrics"]):
            return "monitoring"
        elif any(keyword in context_str for keyword in ["admin", "system", "config", "execute"]):
            return "admin"
        else:
            return "analysis"  # Default role

    def _validate_context_requirements(self, requirements: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate that caller context meets tool requirements."""
        # Simple key-based validation for now
        for key, expected_value in requirements.items():
            if key not in context:
                return False
            if context[key] != expected_value and isinstance(expected_value, str):
                # For string values, check if the expected value is contained in the context value
                if expected_value not in str(context[key]):
                    return False
        return True

    def log_tool_access(self, tool_name: str, caller_context: Optional[Dict[str, Any]], access_granted: bool) -> None:
        """Log tool access for audit purposes."""
        if not self.tool_permissions.get(tool_name, ToolPermissions([])).audit_log:
            return

        log_entry = {
            "tool": tool_name,
            "access_granted": access_granted,
            "caller_role": self._extract_caller_role(caller_context),
            "timestamp": json.dumps({"timestamp": "now"})  # Simplified
        }

        logger.info(f"Tool access: {json.dumps(log_entry)}")


# Global access control instance
access_control = AccessControlSystem()
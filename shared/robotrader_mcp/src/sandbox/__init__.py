"""
Sandbox execution module for secure Python code execution.

Provides isolated execution environment with:
- Filesystem restrictions (read-only access)
- Network isolation (localhost:8000 only)
- Resource limits (CPU, memory, timeout)
- Import restrictions (allowlist only)
- Safe NumPy/Pandas-like alternatives
"""

from .manager import SandboxManager, SandboxConfig, ExecutionResult, SandboxFactory
from .isolation import IsolationLevel, IsolationPolicy, DATABASE_READONLY_POLICY
from .numpy_safe import SafeArray, array, zeros, ones, linspace, arange
from .pandas_safe import SafeDataFrame, DataFrame, concat, merge

__all__ = [
    "SandboxManager",
    "SandboxConfig",
    "ExecutionResult",
    "SandboxFactory",
    "IsolationLevel",
    "IsolationPolicy",
    "DATABASE_READONLY_POLICY",
    # NumPy alternatives
    "SafeArray",
    "array",
    "zeros",
    "ones",
    "linspace",
    "arange",
    # Pandas alternatives
    "SafeDataFrame",
    "DataFrame",
    "concat",
    "merge",
]

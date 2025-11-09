"""
Isolation policy definitions for sandboxed execution.

Defines security levels, restrictions, and resource limits for code execution.
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class IsolationLevel(Enum):
    """Security isolation levels for code execution."""

    # Least restrictive - development/testing
    DEVELOPMENT = "development"

    # Moderate - production with monitoring
    PRODUCTION = "production"

    # Most restrictive - untrusted code
    HARDENED = "hardened"


@dataclass
class IsolationPolicy:
    """Defines isolation constraints for sandbox execution."""

    level: IsolationLevel = IsolationLevel.PRODUCTION

    # Import restrictions
    allowed_imports: List[str] = field(default_factory=lambda: [
        "json", "math", "statistics", "datetime",
        "itertools", "collections", "functools",
        "decimal", "fractions", "random",
        "re", "string", "typing", "types",
        "numbers", "abc", "enum", "copy",
        # Internal modules needed by standard library
        "_io", "_collections", "_functools", "_heapq",
        "_thread", "_weakref", "_operator"
    ])

    # Resource limits
    max_execution_time_sec: int = 30
    max_memory_mb: int = 256

    # Network restrictions
    allow_network: bool = False
    allowed_domains: List[str] = field(default_factory=list)

    # Filesystem restrictions
    allow_file_read: bool = False
    allow_file_write: bool = False
    allowed_read_paths: List[str] = field(default_factory=list)

    def apply_level(self, level: IsolationLevel) -> "IsolationPolicy":
        """Apply isolation level presets."""
        if level == IsolationLevel.DEVELOPMENT:
            self.max_execution_time_sec = 60
            self.max_memory_mb = 512
            self.allow_network = True
            self.allow_file_read = True

        elif level == IsolationLevel.HARDENED:
            self.max_execution_time_sec = 10
            self.max_memory_mb = 128
            self.allow_network = False
            self.allow_file_read = False
            self.allowed_imports = [
                "json", "math", "decimal", "statistics"
            ]

        self.level = level
        return self

    def validate(self) -> None:
        """Validate policy constraints."""
        if self.max_execution_time_sec < 1 or self.max_execution_time_sec > 300:
            raise ValueError("max_execution_time_sec must be between 1-300 seconds")

        if self.max_memory_mb < 32 or self.max_memory_mb > 2048:
            raise ValueError("max_memory_mb must be between 32-2048 MB")

        if self.allow_network and not self.allowed_domains:
            raise ValueError("allow_network=True requires allowed_domains to be specified")


# Default policies for common use cases
DEFAULT_POLICY = IsolationPolicy(
    level=IsolationLevel.PRODUCTION,
    allow_network=True,
    allowed_domains=["localhost:8000", "127.0.0.1:8000"]
)

ANALYSIS_POLICY = IsolationPolicy(
    level=IsolationLevel.PRODUCTION,
    allowed_imports=[
        # Core data analysis modules
        "json", "math", "statistics", "datetime",
        "itertools", "collections", "functools",
        "decimal", "fractions", "random",
        "re", "string", "typing", "types",
        "numbers", "abc", "enum", "copy", "operator",
        # Additional stdlib modules for comprehensive analysis
        "heapq", "bisect", "warnings", "sys", "os",
        # Internal modules needed by standard library (comprehensive set)
        "_io", "_collections", "_collections_abc", "_functools", "_heapq",
        "_thread", "_weakref", "_operator", "_stat", "_sre", "_warnings",
        "_codecs", "_codecs_iso2022", "_ctypes", "_ctypes_test"
    ],
    max_execution_time_sec=30,
    max_memory_mb=256,
    allow_network=True,
    allowed_domains=["localhost:8000"]
)

FILTERING_POLICY = IsolationPolicy(
    level=IsolationLevel.PRODUCTION,
    allowed_imports=["json", "datetime"],
    max_execution_time_sec=10,
    max_memory_mb=128,
    allow_network=False
)

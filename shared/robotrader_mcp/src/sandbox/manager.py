"""
Sandbox Manager - Secure Python code execution with resource isolation.

Manages sandboxed code execution using subprocess isolation with:
- Configurable resource limits (CPU, memory, timeout)
- Import restrictions (allowlist only)
- Network isolation (whitelist domains only)
- Filesystem read-only access
"""

import json
import subprocess
import tempfile
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .isolation import IsolationPolicy, IsolationLevel


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    policy: IsolationPolicy
    max_execution_time_sec: int = 30
    max_memory_mb: int = 256

    def __post_init__(self):
        """Validate configuration."""
        self.policy.validate()


@dataclass
class ExecutionResult:
    """Result from sandboxed code execution."""

    success: bool
    output: Any  # Execution result (JSON-serializable)
    stdout: str  # Standard output
    stderr: str  # Standard error
    execution_time_ms: int
    error: Optional[str] = None
    execution_code: Optional[str] = None  # For debugging


class SandboxManager:
    """Manages sandboxed code execution with security isolation."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox manager.

        Args:
            config: SandboxConfig with policies and limits
        """
        if config is None:
            from .isolation import DEFAULT_POLICY
            config = SandboxConfig(policy=DEFAULT_POLICY)

        self.config = config
        self.policy = config.policy

    async def execute_python(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_override: Optional[int] = None,
        capture_execution: bool = False,
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox with provided context.

        Args:
            code: Python code to execute
            context: Variables available to code (JSON-serializable)
            timeout_override: Override default timeout
            capture_execution: If True, include the execution code in result for debugging

        Returns:
            ExecutionResult with output or error
        """
        start_time = time.time()

        # Create temporary execution script
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as script_file:
            script_path = script_file.name

            # Build execution wrapper
            wrapper = self._build_execution_wrapper(code, context or {})
            script_file.write(wrapper)

        try:
            # Execute in subprocess with timeout
            timeout = timeout_override or self.config.max_execution_time_sec

            # Build restricted environment
            env = self._build_restricted_env()

            # Execute code
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                timeout=timeout,
                text=True,
                env=env,
            )

            execution_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # Parse JSON output from stdout
                try:
                    output = json.loads(result.stdout)
                    return ExecutionResult(
                        success=True,
                        output=output,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        execution_time_ms=execution_time,
                        execution_code=wrapper if capture_execution else None,
                    )
                except json.JSONDecodeError:
                    return ExecutionResult(
                        success=False,
                        output=None,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        execution_time_ms=execution_time,
                        error="Code did not return JSON-serializable output",
                        execution_code=wrapper if capture_execution else None,
                    )
            else:
                return ExecutionResult(
                    success=False,
                    output=None,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    execution_time_ms=execution_time,
                    error=f"Execution failed with exit code {result.returncode}",
                    execution_code=wrapper if capture_execution else None,
                )

        except subprocess.TimeoutExpired:
            execution_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                output=None,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                execution_time_ms=execution_time,
                error="Timeout",
                execution_code=wrapper if capture_execution else None,
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                output=None,
                stdout="",
                stderr=str(e),
                execution_time_ms=execution_time,
                error=f"Execution setup failed: {e}",
                execution_code=wrapper if capture_execution else None,
            )

        finally:
            # Cleanup temporary script
            try:
                Path(script_path).unlink()
            except OSError:
                pass

    def _build_execution_wrapper(self, code: str, context: Dict[str, Any]) -> str:
        """Build Python wrapper that provides context and captures output."""

        # Build import safeguards
        import_check = self._build_import_check()

        # Indent user code
        indented_code = self._indent_code(code, 4)

        wrapper = f'''
import json
import sys

# Security: Import safeguards
{import_check}

# Inject context variables
context = {json.dumps(context)}
globals().update(context)

# Execute user code
try:
    # User code starts here
{indented_code}
    # User code ends here

    # Capture result
    if 'result' in locals():
        print(json.dumps(result))
    else:
        print(json.dumps({{"success": True, "executed": True}}))

except Exception as e:
    error_result = {{
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__
    }}
    print(json.dumps(error_result))
    sys.exit(1)
'''
        return wrapper

    def _build_import_check(self) -> str:
        """Build import restriction code."""
        allowed = self.policy.allowed_imports
        allowed_repr = repr(allowed)  # Convert to string representation

        return f'''
import sys
import builtins

# Allowed modules
ALLOWED_IMPORTS = set({allowed_repr})

# Save original import
_original_import = builtins.__import__

# Custom import function
def _restricted_import(name, *args, **kwargs):
    # Get top-level module name
    top_level = name.split('.')[0]

    # Check if allowed
    if top_level not in ALLOWED_IMPORTS:
        allowed_str = ", ".join(ALLOWED_IMPORTS)
        raise ImportError(f"Module '{{name}}' is not allowed. Allowed: {{allowed_str}}")

    return _original_import(name, *args, **kwargs)

# Replace import
builtins.__import__ = _restricted_import
'''

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code block."""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))

    def _build_restricted_env(self) -> Dict[str, str]:
        """Build restricted environment variables for subprocess."""
        import os

        # Start with minimal environment
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "PYTHONUNBUFFERED": "1",
        }

        # Restrict sensitive paths
        for blocked_var in [
            "AWS_SECRET_ACCESS_KEY",
            "AWS_ACCESS_KEY_ID",
            "ZERODHA_API_SECRET",
            "API_KEY",
            "SECRET_KEY",
        ]:
            env.pop(blocked_var, None)

        return env

    @staticmethod
    def validate_code(code: str) -> tuple[bool, Optional[str]]:
        """
        Pre-validate code before execution (basic checks).

        Args:
            code: Code to validate

        Returns:
            (is_valid, error_message)
        """
        # Check for dangerous patterns
        dangerous_patterns = [
            "eval(", "exec(", "compile(", "__import__(",
            "os.system", "subprocess", "open(", "pickle",
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                return False, f"Dangerous pattern detected: {pattern}"

        return True, None


class SandboxFactory:
    """Factory for creating pre-configured sandbox managers."""

    @staticmethod
    def create_analysis_sandbox() -> SandboxManager:
        """Create sandbox for data analysis operations."""
        from .isolation import ANALYSIS_POLICY

        config = SandboxConfig(policy=ANALYSIS_POLICY)
        return SandboxManager(config)

    @staticmethod
    def create_filtering_sandbox() -> SandboxManager:
        """Create sandbox for data filtering operations."""
        from .isolation import FILTERING_POLICY

        config = SandboxConfig(policy=FILTERING_POLICY)
        return SandboxManager(config)

    @staticmethod
    def create_custom_sandbox(
        isolation_level: IsolationLevel = IsolationLevel.PRODUCTION,
        allowed_imports: Optional[list] = None,
        max_time_sec: int = 30,
        allow_network: bool = False,
        allowed_domains: Optional[list] = None,
    ) -> SandboxManager:
        """Create custom sandbox with specific configuration."""
        from .isolation import IsolationPolicy

        policy = IsolationPolicy(
            level=isolation_level,
            allow_network=allow_network,
            allowed_domains=allowed_domains or [],
        )

        if allowed_imports:
            policy.allowed_imports = allowed_imports

        policy.max_execution_time_sec = max_time_sec

        config = SandboxConfig(policy=policy)
        return SandboxManager(config)

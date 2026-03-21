"""
Test: No asyncio.get_event_loop() usage in the codebase.

This is a grep-based test that ensures no one reintroduces the
deprecated get_event_loop() pattern which can crash in Python 3.12+.
"""

import subprocess
import os


def test_no_get_event_loop_in_source():
    """Ensure no source files use asyncio.get_event_loop() (should use get_running_loop)."""
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    result = subprocess.run(
        ["grep", "-rn", "get_event_loop()", src_dir, "--include=*.py"],
        capture_output=True,
        text=True,
    )

    violations = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Allow get_event_loop_policy (different thing)
        if "get_event_loop_policy" in line:
            continue
        # Allow test files
        if "/tests/" in line or "test_" in line:
            continue
        # Allow comments
        stripped = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
        if stripped.startswith("#"):
            continue
        violations.append(line)

    assert not violations, (
        f"Found {len(violations)} uses of asyncio.get_event_loop() in source code.\n"
        f"Use asyncio.get_running_loop() instead.\n"
        f"Violations:\n" + "\n".join(violations)
    )


def test_no_get_event_loop_in_core():
    """Specifically check core/ directory which is most critical."""
    core_dir = os.path.join(os.path.dirname(__file__), "..", "src", "core")
    result = subprocess.run(
        ["grep", "-rn", "get_event_loop()", core_dir, "--include=*.py"],
        capture_output=True,
        text=True,
    )

    violations = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        if "get_event_loop_policy" in line:
            continue
        stripped = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
        if stripped.startswith("#"):
            continue
        violations.append(line)

    assert not violations, (
        f"Found get_event_loop() in core/:\n" + "\n".join(violations)
    )

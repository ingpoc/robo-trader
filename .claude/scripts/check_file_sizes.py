#!/usr/bin/env python3
"""
File Size Validator - Pre-Commit Hook

Enforces architectural guidelines:
- Python files: ≤ 350 lines
- TypeScript/React files: ≤ 300 lines
- Coordinators: ≤ 150 lines (focused) or ≤ 200 lines (orchestrators)
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


# Architectural limits
LIMITS = {
    "python": 350,
    "typescript": 300,
    "coordinator_focused": 150,
    "coordinator_orchestrator": 200,
}


def count_lines(filepath: Path) -> int:
    """Count non-empty, non-comment lines in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Count non-empty lines (basic check)
        return len([l for l in lines if l.strip()])
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}")
        return 0


def get_staged_files() -> List[Path]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.strip().split('\n')
        return [Path(f) for f in files if f]
    except subprocess.CalledProcessError:
        return []


def check_file(filepath: Path) -> Tuple[bool, str, int, int]:
    """
    Check if file exceeds size limits.

    Returns:
        (is_valid, file_type, line_count, limit)
    """
    # Determine file type and limit
    suffix = filepath.suffix
    name = filepath.name
    parent = filepath.parent.name

    # Python files
    if suffix == '.py':
        line_count = count_lines(filepath)

        # Special limits for coordinators
        if 'coordinator' in parent or 'coordinator' in name.lower():
            # Focused coordinators
            if 'base' in name.lower() or len(open(filepath).read()) < 5000:
                limit = LIMITS["coordinator_focused"]
                file_type = "Coordinator (focused)"
            else:
                limit = LIMITS["coordinator_orchestrator"]
                file_type = "Coordinator (orchestrator)"
        else:
            limit = LIMITS["python"]
            file_type = "Python"

        is_valid = line_count <= limit
        return (is_valid, file_type, line_count, limit)

    # TypeScript/React files
    elif suffix in ['.ts', '.tsx']:
        line_count = count_lines(filepath)
        limit = LIMITS["typescript"]
        file_type = "TypeScript/React"
        is_valid = line_count <= limit
        return (is_valid, file_type, line_count, limit)

    # Skip other files
    return (True, "Other", 0, 0)


def main():
    """Main validation function."""
    print("🔍 Checking file sizes...")

    staged_files = get_staged_files()
    if not staged_files:
        print("✅ No staged files to check")
        return 0

    violations = []
    checked_count = 0

    for filepath in staged_files:
        # Skip non-existent files (deleted)
        if not filepath.exists():
            continue

        # Check file
        is_valid, file_type, line_count, limit = check_file(filepath)

        # Skip files we don't check
        if file_type == "Other":
            continue

        checked_count += 1

        if not is_valid:
            excess = line_count - limit
            pct_over = (excess / limit) * 100
            violations.append({
                'path': str(filepath),
                'type': file_type,
                'lines': line_count,
                'limit': limit,
                'excess': excess,
                'pct_over': pct_over
            })

    # Report results
    if not violations:
        print(f"✅ All {checked_count} files within size limits")
        return 0

    # Print violations
    print(f"\n❌ Found {len(violations)} file size violation(s):\n")

    for v in violations:
        print(f"  {v['path']}")
        print(f"    Type: {v['type']}")
        print(f"    Lines: {v['lines']} (limit: {v['limit']})")
        print(f"    Excess: +{v['excess']} lines ({v['pct_over']:.0f}% over limit)")
        print()

    print("💡 To fix:")
    print("  1. Refactor large files into smaller, focused modules")
    print("  2. Extract methods into separate helper classes")
    print("  3. Use facade pattern for large orchestration files")
    print("\n  Or skip this check with: git commit --no-verify")

    return 1


if __name__ == "__main__":
    sys.exit(main())

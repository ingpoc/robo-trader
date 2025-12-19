#!/usr/bin/env python3
"""
Method Count Validator - Pre-Commit Hook

Enforces architectural guideline:
- Python classes: ≤ 10 methods (excluding __init__, __str__, __repr__)
"""

import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict


MAX_METHODS = 10
EXCLUDED_METHODS = {'__init__', '__str__', '__repr__', '__eq__', '__hash__'}


def count_class_methods(filepath: Path) -> Dict[str, int]:
    """
    Count methods in each class in a Python file.

    Returns:
        Dict mapping class names to method counts
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        class_methods = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count methods, excluding special methods
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name not in EXCLUDED_METHODS
                ]
                class_methods[node.name] = len(methods)

        return class_methods

    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}")
        return {}


def get_staged_python_files() -> List[Path]:
    """Get list of staged Python files from git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.strip().split('\n')
        python_files = [Path(f) for f in files if f.endswith('.py')]
        return [f for f in python_files if f.exists()]
    except subprocess.CalledProcessError:
        return []


def main():
    """Main validation function."""
    print("🔍 Checking method counts...")

    python_files = get_staged_python_files()
    if not python_files:
        print("✅ No Python files to check")
        return 0

    violations = []

    for filepath in python_files:
        class_methods = count_class_methods(filepath)

        for class_name, method_count in class_methods.items():
            if method_count > MAX_METHODS:
                excess = method_count - MAX_METHODS
                pct_over = (excess / MAX_METHODS) * 100
                violations.append({
                    'path': str(filepath),
                    'class': class_name,
                    'methods': method_count,
                    'limit': MAX_METHODS,
                    'excess': excess,
                    'pct_over': pct_over
                })

    # Report results
    if not violations:
        print(f"✅ All classes within {MAX_METHODS}-method limit")
        return 0

    # Print violations
    print(f"\n❌ Found {len(violations)} method count violation(s):\n")

    for v in violations:
        print(f"  {v['path']}")
        print(f"    Class: {v['class']}")
        print(f"    Methods: {v['methods']} (limit: {v['limit']})")
        print(f"    Excess: +{v['excess']} methods ({v['pct_over']:.0f}% over limit)")
        print()

    print("💡 To fix:")
    print("  1. Extract methods into separate helper/utility classes")
    print("  2. Use composition over large inheritance hierarchies")
    print("  3. Apply Single Responsibility Principle (SRP)")
    print("\n  Or skip this check with: git commit --no-verify")

    return 1


if __name__ == "__main__":
    sys.exit(main())

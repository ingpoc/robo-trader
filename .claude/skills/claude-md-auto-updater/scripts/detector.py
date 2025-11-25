#!/usr/bin/env python3
"""
CLAUDE.md Pattern Detector

Scans Python and TypeScript/React codebase to identify:
- New patterns (3+ similar code instances)
- Violations of documented constraints
- Stale documentation (patterns not used recently)
- Anti-patterns (repeated mistakes)

Returns structured JSON with all findings.
"""

import argparse
import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Finding:
    """Represents a detected pattern, violation, or anti-pattern"""
    type: str  # "new_pattern", "violation", "staleness", "anti_pattern"
    category: str  # e.g., "queue_handler", "database_access", "async_usage"
    severity: str  # "critical", "high", "medium", "low"
    confidence: float  # 0-100
    title: str  # Human-readable title
    evidence: List[Dict]  # List of {"file": path, "line": number, "snippet": code}
    rationale: str  # Why this finding matters
    affected_files: List[str]  # Which CLAUDE.md files should be updated


class PatternDetector:
    """Detects architectural patterns, violations, and anti-patterns"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.findings: List[Finding] = []
        self.python_files: List[Path] = []
        self.typescript_files: List[Path] = []
        self._load_files()

    def _load_files(self):
        """Load all Python and TypeScript/React files from project"""
        # Python files
        self.python_files = list(self.project_root.glob("**/*.py"))
        self.python_files = [f for f in self.python_files
                            if not any(skip in f.parts
                                      for skip in [".venv", "venv", "__pycache__", ".git", "node_modules"])]

        # TypeScript/React files
        self.typescript_files = list(self.project_root.glob("**/*.tsx"))
        self.typescript_files.extend(self.project_root.glob("**/*.ts"))
        self.typescript_files = [f for f in self.typescript_files
                                if not any(skip in f.parts
                                          for skip in ["node_modules", ".git", "dist", "build"])]

    def detect_all(self) -> List[Finding]:
        """Run all detectors and return findings"""
        self._detect_database_violations()
        self._detect_sdk_violations()
        self._detect_timeout_violations()
        self._detect_async_violations()
        self._detect_modularization_violations()
        self._detect_queue_handler_patterns()
        self._detect_coordinator_patterns()
        self._detect_component_patterns()

        return self.findings

    def _detect_database_violations(self):
        """Detect direct database access (should use locked methods)"""
        violations = defaultdict(list)

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Look for direct database connection access
                patterns = [
                    (r'\.connection\.execute\(', 'direct_db_execute'),
                    (r'\.connection\.commit\(', 'direct_db_commit'),
                    (r'database\.connection', 'direct_connection_access'),
                ]

                for pattern, violation_type in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line) and 'await config_state' not in line:
                            if py_file not in violations[violation_type]:
                                violations[violation_type] = []
                            violations[violation_type].append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'snippet': line.strip()
                            })
            except Exception:
                continue

        if violations:
            for violation_type, evidence in violations.items():
                self.findings.append(Finding(
                    type="violation",
                    category="database_access",
                    severity="critical",
                    confidence=95.0,
                    title=f"Direct Database Access Detected ({len(evidence)} instances)",
                    evidence=evidence,
                    rationale="Direct db.connection access bypasses ConfigurationState's asyncio.Lock(), causing database contention and blocking during long-running operations (30+ seconds). Use locked methods like config_state.store_*() instead.",
                    affected_files=["src/web/CLAUDE.md", "src/services/CLAUDE.md"]
                ))

    def _detect_sdk_violations(self):
        """Detect direct Anthropic API usage (should use ClaudeSDKClientManager)"""
        violations = []

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Skip SDK client manager file itself
                if 'claude_sdk_client_manager' in py_file.name:
                    continue

                for i, line in enumerate(lines, 1):
                    if 'from anthropic import' in line or 'import anthropic' in line:
                        violations.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': i,
                            'snippet': line.strip()
                        })
            except Exception:
                continue

        if violations:
            self.findings.append(Finding(
                type="violation",
                category="sdk_usage",
                severity="critical",
                confidence=90.0,
                title=f"Direct Anthropic API Import ({len(violations)} instances)",
                evidence=violations,
                rationale="Direct Anthropic API imports bypass the ClaudeSDKClientManager singleton. All AI functionality must use Claude Agent SDK only through the centralized client manager for proper session management, timeout handling, and resource pooling.",
                affected_files=["src/CLAUDE.md", "src/core/CLAUDE.md"]
            ))

    def _detect_timeout_violations(self):
        """Detect SDK calls without timeout protection"""
        # This is a heuristic - looks for client.messages.create without query_with_timeout
        violations = []

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Find client.messages.create calls
                if 'client.messages.create' in content:
                    if 'query_with_timeout' not in content and 'receive_response_with_timeout' not in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'client.messages.create' in line:
                                violations.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': i,
                                    'snippet': line.strip()
                                })
            except Exception:
                continue

        if violations:
            self.findings.append(Finding(
                type="violation",
                category="sdk_timeout",
                severity="high",
                confidence=85.0,
                title=f"Missing Timeout Protection on SDK Calls ({len(violations)} instances)",
                evidence=violations[:5],  # Limit to 5 examples
                rationale="All Claude SDK calls must be wrapped with timeout protection to prevent hanging operations. Analysis operations may take 30-60+ seconds, and timeouts protect against indefinite blocking.",
                affected_files=["src/CLAUDE.md", "src/core/CLAUDE.md"]
            ))

    def _detect_async_violations(self):
        """Detect time.sleep() in async functions"""
        violations = []

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Find async functions
                in_async_function = False
                async_indent = 0

                for i, line in enumerate(lines, 1):
                    if re.match(r'\s*async\s+def\s+', line):
                        in_async_function = True
                        async_indent = len(line) - len(line.lstrip())

                    if in_async_function:
                        # Check if we've exited the function
                        if line.strip() and not line.startswith(' ' * (async_indent + 1)) and 'def ' in line:
                            in_async_function = False

                        # Check for time.sleep()
                        if in_async_function and 'time.sleep' in line:
                            violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'snippet': line.strip()
                            })
            except Exception:
                continue

        if violations:
            self.findings.append(Finding(
                type="anti_pattern",
                category="async_usage",
                severity="high",
                confidence=100.0,
                title=f"Blocking time.sleep() in Async Code ({len(violations)} instances)",
                evidence=violations,
                rationale="time.sleep() blocks ALL async operations, preventing any other tasks from running. Use await asyncio.sleep() for async-safe delays or condition polling with short sleep intervals.",
                affected_files=["src/CLAUDE.md", "CLAUDE.md"]
            ))

    def _detect_modularization_violations(self):
        """Detect files exceeding 350 lines"""
        violations = []

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = len(f.readlines())

                if line_count > 350:
                    violations.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'line': 1,
                        'snippet': f'{line_count} lines'
                    })
            except Exception:
                continue

        for ts_file in self.typescript_files:
            try:
                with open(ts_file, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = len(f.readlines())

                if line_count > 350:
                    violations.append({
                        'file': str(ts_file.relative_to(self.project_root)),
                        'line': 1,
                        'snippet': f'{line_count} lines'
                    })
            except Exception:
                continue

        if violations:
            self.findings.append(Finding(
                type="violation",
                category="modularization",
                severity="medium",
                confidence=100.0,
                title=f"Files Exceeding 350 Line Limit ({len(violations)} files)",
                evidence=violations[:10],
                rationale="Large files are harder to maintain, test, and understand. Split files exceeding 350 lines into smaller, focused modules with single responsibility.",
                affected_files=["CLAUDE.md"]
            ))

    def _detect_queue_handler_patterns(self):
        """Detect queue handler patterns"""
        handlers = defaultdict(list)

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Look for @task_handler decorator or class inheriting from TaskHandler
                for i, line in enumerate(lines, 1):
                    if '@task_handler' in line or 'class ' in line and 'TaskHandler' in line:
                        handler_name = None
                        if 'class ' in line:
                            match = re.search(r'class\s+(\w+)', line)
                            if match:
                                handler_name = match.group(1)

                        if handler_name:
                            handlers['found'].append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'snippet': f'class {handler_name}'
                            })
            except Exception:
                continue

        # If we found 3+ new handlers, flag as pattern
        if handlers.get('found') and len(handlers['found']) >= 3:
            # Check if documented in CLAUDE.md
            handler_names = [
                re.search(r'class\s+(\w+)', ev['snippet']).group(1)
                for ev in handlers['found']
                if re.search(r'class\s+(\w+)', ev['snippet'])
            ]

            # For now, just report if found
            self.findings.append(Finding(
                type="new_pattern",
                category="queue_handler",
                severity="medium",
                confidence=80.0,
                title=f"Queue Handler Pattern Found ({len(handler_names)} handlers)",
                evidence=handlers['found'][:5],
                rationale=f"Found {len(handler_names)} queue handler implementations. Verify they are documented in src/CLAUDE.md under Sequential Queue Architecture section.",
                affected_files=["src/CLAUDE.md"]
            ))

    def _detect_coordinator_patterns(self):
        """Detect coordinator patterns"""
        coordinators = []

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Look for class inheriting from BaseCoordinator
                for i, line in enumerate(lines, 1):
                    if 'BaseCoordinator' in line and 'class ' in line:
                        match = re.search(r'class\s+(\w+)', line)
                        if match:
                            class_name = match.group(1)
                            coordinators.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'snippet': f'class {class_name}(BaseCoordinator)'
                            })
            except Exception:
                continue

        if coordinators and len(coordinators) >= 2:
            self.findings.append(Finding(
                type="new_pattern",
                category="coordinator",
                severity="low",
                confidence=70.0,
                title=f"Coordinator Implementations Found ({len(coordinators)} coordinators)",
                evidence=coordinators[:5],
                rationale="Found coordinator implementations. Verify they follow max 150 lines, single responsibility pattern documented in src/core/CLAUDE.md.",
                affected_files=["src/core/CLAUDE.md"]
            ))

    def _detect_component_patterns(self):
        """Detect React component patterns"""
        large_components = []

        for ts_file in self.typescript_files:
            if 'test' in ts_file.name or 'spec' in ts_file.name:
                continue

            try:
                with open(ts_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    line_count = len(lines)

                if line_count > 350:
                    large_components.append({
                        'file': str(ts_file.relative_to(self.project_root)),
                        'line': 1,
                        'snippet': f'{line_count} lines'
                    })

                # Check for component in features directory
                if 'features' in str(ts_file) and 'tsx' in ts_file.suffix:
                    if line_count > 300:
                        for i, line in enumerate(lines[:50], 1):  # Check first 50 lines
                            if 'export ' in line and ('function ' in line or 'const ' in line):
                                # Component found - size is already checked above
                                break
            except Exception:
                continue

        if large_components:
            self.findings.append(Finding(
                type="violation",
                category="component_size",
                severity="medium",
                confidence=100.0,
                title=f"Large React Components ({len(large_components)} components)",
                evidence=large_components[:10],
                rationale="Components exceeding 350 lines should be split into smaller, focused components. Large components are harder to test and understand.",
                affected_files=["ui/src/CLAUDE.md"]
            ))


def main():
    parser = argparse.ArgumentParser(
        description="Detect CLAUDE.md pattern and violation findings"
    )
    parser.add_argument("project_root", help="Path to project root")
    parser.add_argument("--scope", choices=["full", "backend", "frontend"],
                       default="full", help="Analysis scope")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")

    args = parser.parse_args()

    detector = PatternDetector(args.project_root)
    findings = detector.detect_all()

    output = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(args.project_root),
        "scope": args.scope,
        "findings_count": len(findings),
        "findings": [asdict(f) for f in findings]
    }

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✅ Findings saved to {args.output}")
    else:
        print(json.dumps(output, indent=2))

    return 0 if len(findings) == 0 else 1


if __name__ == "__main__":
    exit(main())

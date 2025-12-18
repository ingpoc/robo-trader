#!/usr/bin/env python3
"""
Auto-Fix Engine for Robo Trader
Detects common error patterns and applies fixes automatically
"""

import re
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Project root
PROJECT_ROOT = Path("/Users/gurusharan/Documents/remote-claude/robo-trader")

# Error patterns with confidence scores
ERROR_PATTERNS = {
    "missing_import": {
        "pattern": r"ImportError: cannot import name '(\w+)' from '([\w.]+)'",
        "confidence": 0.90,
        "description": "Missing import statement"
    },
    "database_lock": {
        "pattern": r"sqlite3\.OperationalError: database is locked",
        "confidence": 0.95,
        "description": "Database lock - use locked state methods"
    },
    "key_error": {
        "pattern": r"KeyError: '(\w+)'.*payload",
        "confidence": 0.85,
        "description": "Missing key in payload"
    },
    "missing_await": {
        "pattern": r"RuntimeWarning: coroutine '(\w+)' was never awaited",
        "confidence": 0.90,
        "description": "Missing await keyword"
    },
    "di_not_registered": {
        "pattern": r"KeyError: '(\w+)'.*container",
        "confidence": 0.80,
        "description": "Service not registered in DI container"
    },
    "port_in_use": {
        "pattern": r"Address already in use.*:(\d+)",
        "confidence": 1.0,
        "description": "Port already in use"
    }
}


class AutoFixEngine:
    def __init__(self, log_file: Path, apply_fixes: bool = False):
        self.log_file = log_file
        self.apply_fixes = apply_fixes
        self.fixes_applied = []
        self.fixes_suggested = []

    def parse_log(self) -> List[Dict]:
        """Parse log file and extract error information"""
        errors = []

        if not self.log_file.exists():
            print(f"Log file not found: {self.log_file}")
            return errors

        with open(self.log_file, 'r') as f:
            log_content = f.read()

        # Parse each error pattern
        for error_type, config in ERROR_PATTERNS.items():
            pattern = config["pattern"]
            matches = re.finditer(pattern, log_content, re.MULTILINE)

            for match in matches:
                error = {
                    "type": error_type,
                    "description": config["description"],
                    "confidence": config["confidence"],
                    "match": match.group(0),
                    "groups": match.groups()
                }

                # Extract file and line number if available
                file_line_pattern = r'File "([^"]+)", line (\d+)'
                context_start = max(0, match.start() - 200)
                context = log_content[context_start:match.end()]

                file_match = re.search(file_line_pattern, context)
                if file_match:
                    error["file"] = file_match.group(1)
                    error["line"] = int(file_match.group(2))

                errors.append(error)

        return errors

    def fix_missing_import(self, error: Dict) -> Optional[Dict]:
        """Fix missing import errors"""
        if not error.get("file") or not error.get("groups"):
            return None

        symbol = error["groups"][0]
        module = error["groups"][1]
        file_path = Path(error["file"])

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            content = f.read()

        # Check if import already exists
        import_pattern = f"from {module} import.*{symbol}"
        if re.search(import_pattern, content):
            return None

        # Find import section and add import
        lines = content.split('\n')
        import_line_idx = 0

        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                import_line_idx = i + 1

        new_import = f"from {module} import {symbol}"
        lines.insert(import_line_idx, new_import)

        if self.apply_fixes:
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))

        return {
            "type": "missing_import",
            "file": str(file_path),
            "line": import_line_idx,
            "original": "",
            "fixed": new_import,
            "confidence": error["confidence"]
        }

    def fix_database_lock(self, error: Dict) -> Optional[Dict]:
        """Fix database lock errors by suggesting locked state methods"""
        if not error.get("file"):
            return None

        file_path = Path(error["file"])

        suggestion = {
            "type": "database_lock",
            "file": str(file_path),
            "line": error.get("line", 0),
            "original": "Direct database access",
            "fixed": "Use config_state.store_*() methods instead",
            "confidence": error["confidence"],
            "manual_action_required": True
        }

        return suggestion

    def fix_key_error(self, error: Dict) -> Optional[Dict]:
        """Fix KeyError in payload by adding .get() with default"""
        if not error.get("file") or not error.get("line") or not error.get("groups"):
            return None

        key = error["groups"][0]
        file_path = Path(error["file"])

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            lines = f.readlines()

        line_idx = error["line"] - 1
        if line_idx >= len(lines):
            return None

        line = lines[line_idx]

        # Replace payload['key'] with payload.get('key', default)
        pattern = f"payload\\['{key}'\\]"
        if not re.search(pattern, line):
            pattern = f'payload\\["{key}"\\]'

        if re.search(pattern, line):
            # Determine appropriate default value
            default = "[]" if "symbol" in key.lower() else "None"
            new_line = re.sub(pattern, f"payload.get('{key}', {default})", line)

            if self.apply_fixes:
                lines[line_idx] = new_line
                with open(file_path, 'w') as f:
                    f.writelines(lines)

            return {
                "type": "key_error",
                "file": str(file_path),
                "line": error["line"],
                "original": line.strip(),
                "fixed": new_line.strip(),
                "confidence": error["confidence"]
            }

        return None

    def fix_missing_await(self, error: Dict) -> Optional[Dict]:
        """Fix missing await by adding await keyword"""
        if not error.get("file") or not error.get("line"):
            return None

        file_path = Path(error["file"])

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            lines = f.readlines()

        line_idx = error["line"] - 1
        if line_idx >= len(lines):
            return None

        line = lines[line_idx]

        # Add await if not already present
        if 'await ' not in line and '=' in line:
            # Find the assignment and add await
            parts = line.split('=', 1)
            if len(parts) == 2:
                new_line = parts[0] + '= await ' + parts[1]

                if self.apply_fixes:
                    lines[line_idx] = new_line
                    with open(file_path, 'w') as f:
                        f.writelines(lines)

                return {
                    "type": "missing_await",
                    "file": str(file_path),
                    "line": error["line"],
                    "original": line.strip(),
                    "fixed": new_line.strip(),
                    "confidence": error["confidence"]
                }

        return None

    def fix_port_in_use(self, error: Dict) -> Optional[Dict]:
        """Fix port in use by killing process"""
        if not error.get("groups"):
            return None

        port = error["groups"][0]

        if self.apply_fixes:
            import subprocess
            try:
                subprocess.run(
                    f"lsof -ti:{port} | xargs kill -9",
                    shell=True,
                    capture_output=True
                )
            except Exception as e:
                print(f"Failed to kill process on port {port}: {e}")
                return None

        return {
            "type": "port_in_use",
            "file": "system",
            "line": 0,
            "original": f"Port {port} in use",
            "fixed": f"Killed process on port {port}",
            "confidence": error["confidence"]
        }

    def apply_fix(self, error: Dict) -> Optional[Dict]:
        """Apply appropriate fix based on error type"""
        fix_methods = {
            "missing_import": self.fix_missing_import,
            "database_lock": self.fix_database_lock,
            "key_error": self.fix_key_error,
            "missing_await": self.fix_missing_await,
            "port_in_use": self.fix_port_in_use
        }

        method = fix_methods.get(error["type"])
        if method:
            return method(error)

        return None

    def run(self) -> Dict:
        """Run auto-fix engine"""
        print("=" * 60)
        print("Auto-Fix Engine Starting")
        print("=" * 60)

        # Parse errors from log
        errors = self.parse_log()
        print(f"\nFound {len(errors)} errors in log file")

        # Apply fixes
        for error in errors:
            print(f"\n[{error['type']}] {error['description']}")
            print(f"  Confidence: {error['confidence']:.0%}")

            if error["confidence"] >= 0.80:
                fix = self.apply_fix(error)

                if fix:
                    if self.apply_fixes:
                        self.fixes_applied.append(fix)
                        print(f"  ✓ Fix applied: {fix['fixed']}")
                    else:
                        self.fixes_suggested.append(fix)
                        print(f"  → Suggested fix: {fix['fixed']}")
                else:
                    print(f"  ⚠ Could not generate fix")
            else:
                print(f"  ⚠ Confidence too low, skipping")

        # Save fix history
        self._save_fix_history()

        print("\n" + "=" * 60)
        print(f"Fixes Applied: {len(self.fixes_applied)}")
        print(f"Fixes Suggested: {len(self.fixes_suggested)}")
        print("=" * 60)

        return {
            "total_errors": len(errors),
            "fixes_applied": len(self.fixes_applied),
            "fixes_suggested": len(self.fixes_suggested),
            "fixes": self.fixes_applied + self.fixes_suggested
        }

    def _save_fix_history(self):
        """Save fix history to JSON file"""
        history_file = PROJECT_ROOT / ".claude/progress/auto-fix-history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = {"fixes": []}

        # Add new fixes
        timestamp = datetime.utcnow().isoformat() + "Z"
        for fix in self.fixes_applied + self.fixes_suggested:
            fix["timestamp"] = timestamp
            fix["applied"] = fix in self.fixes_applied
            history["fixes"].append(fix)

        # Save history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Auto-Fix Engine for Robo Trader")
    parser.add_argument(
        "--log-file",
        type=str,
        default="logs/errors.log",
        help="Path to log file to analyze"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply fixes (default: only suggest)"
    )

    args = parser.parse_args()

    log_file = PROJECT_ROOT / args.log_file
    engine = AutoFixEngine(log_file, apply_fixes=args.apply)
    result = engine.run()

    # Exit with error if no fixes could be applied
    if result["total_errors"] > 0 and result["fixes_applied"] == 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

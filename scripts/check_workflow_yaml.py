#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    workflow_dir = project_root / ".github" / "workflows"
    workflow_paths = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))

    if not workflow_paths:
        print("No workflow files found.")
        return 0

    failures: list[str] = []
    for workflow_path in workflow_paths:
        try:
            with workflow_path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            failures.append(f"{workflow_path.relative_to(project_root)}: {exc}")

    if failures:
        print("Workflow YAML validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Workflow YAML validation passed for {len(workflow_paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

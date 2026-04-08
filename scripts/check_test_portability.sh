#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

PATTERN='/Users/|/home/runner/work/'

if rg -n "$PATTERN" tests; then
    echo
    echo "Test portability check failed: remove machine-specific absolute paths from tests."
    exit 1
fi

echo "Test portability check passed."

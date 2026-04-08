#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

if [ "$#" -gt 0 ]; then
    python -m pytest -p pytest_asyncio.plugin -p pytest_cov "$@"
else
    python -m pytest -p pytest_asyncio.plugin -p pytest_cov tests/ --tb=short
fi

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/shared/codex_runtime"

export CODEX_RUNTIME_HOST="${CODEX_RUNTIME_HOST:-127.0.0.1}"
export CODEX_RUNTIME_PORT="${CODEX_RUNTIME_PORT:-8765}"
export CODEX_WORKDIR="${CODEX_WORKDIR:-$ROOT_DIR}"
export CODEX_MODEL="${CODEX_MODEL:-gpt-5.4}"
export CODEX_REASONING_LIGHT="${CODEX_REASONING_LIGHT:-low}"
export CODEX_REASONING_DEEP="${CODEX_REASONING_DEEP:-medium}"

cd "$RUNTIME_DIR"

if [ ! -d node_modules ]; then
  npm install
fi

exec npm run start

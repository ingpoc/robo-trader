#!/bin/bash
# git_commit_feature.sh - Standardized git commits for features
# Usage: git_commit_feature.sh <feature_id> <message> [type] [scope]
# Output: JSON with status, commit_hash, files_changed

set -e

FEATURE_ID="$1"
MESSAGE="$2"
TYPE="${3:-feat}"
SCOPE="${4:-}"

# Validate commit type (conventional commits)
case "$TYPE" in
    feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)
        ;;
    *)
        echo "{\"status\":\"error\",\"message\":\"Invalid type: $TYPE. Use: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert\"}"
        exit 1
        ;;
esac

# Check if in git repo
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$PROJECT_ROOT" ]; then
    echo "{\"status\":\"error\",\"message\":\"Not in a git repository\"}"
    exit 1
fi

# Check for changes
if git diff --quiet && git diff --cached --quiet; then
    echo "{\"status\":\"error\",\"message\":\"No changes to commit\"}"
    exit 1
fi

# Build commit message
if [ -n "$SCOPE" ]; then
    COMMIT_MSG="${TYPE}(${SCOPE}): ${MESSAGE}"
else
    COMMIT_MSG="${TYPE}: ${MESSAGE}"
fi

# Add all changes
git add -A

# Get list of changed files
FILES_CHANGED=$(git diff --cached --name-only | jq -R . | jq -s .)

# Create commit
COMMIT_HASH=$(git commit -m "$COMMIT_MSG" 2>&1 | grep -oP '\[\w+\s+\K[0-9a-f]+' | head -1)

if [ -z "$COMMIT_HASH" ]; then
    # Fallback: get hash from log
    COMMIT_HASH=$(git log -1 --format=%H 2>/dev/null || echo "unknown")
fi

# Count files changed
FILE_COUNT=$(echo "$FILES_CHANGED" | jq 'length')

# Output result
jq -n \
    --arg status "success" \
    --arg feature_id "$FEATURE_ID" \
    --arg commit_hash "$COMMIT_HASH" \
    --arg commit_msg "$COMMIT_MSG" \
    --arg file_count "$FILE_COUNT" \
    --argjson files "$FILES_CHANGED" \
    '{
        status: $status,
        feature_id: $feature_id,
        commit_hash: $commit_hash,
        commit_message: $commit_msg,
        files_count: ($file_count | tonumber),
        files_changed: $files
    }'

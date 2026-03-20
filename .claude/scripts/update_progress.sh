#!/bin/bash
# update_progress.sh - Atomically update feature-list.json
# Usage: update_progress.sh <feature_id> <status> [progress_dir] [notes]
# Works with both: .features[] and categories.*.features[] structures

set -e

FEATURE_ID="$1"
NEW_STATUS="$2"
PROGRESS_DIR="${3:-.claude/progress}"
NOTES="${4:-}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FEATURE_LIST="$PROJECT_ROOT/$PROGRESS_DIR/feature-list.json"

# Validate status
case "$NEW_STATUS" in
    pending|in_progress|completed|tested|blocked)
        ;;
    *)
        echo '{"status":"error","message":"Invalid status"}'
        exit 1
        ;;
esac

# Check file exists
if [ ! -f "$FEATURE_LIST" ]; then
    echo "{\"status\":\"error\",\"message\":\"feature-list.json not found at: $FEATURE_LIST\"}"
    exit 1
fi

# Get timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create temp file
TEMP_FILE=$(mktemp)

# Check structure type and update accordingly
if jq -e '.features' "$FEATURE_LIST" >/dev/null 2>&1; then
    # Simple structure: .features[]
    if [ -n "$NOTES" ]; then
        UPDATED=$(jq -r \
            --arg id "$FEATURE_ID" \
            --arg status "$NEW_STATUS" \
            --arg notes "$NOTES" \
            --arg timestamp "$TIMESTAMP" \
            '(.features[] | select(.id == $id)) |=
                (.status = $status |
                .notes = (.notes // "") + "\n" + $timestamp + ": " + $notes |
                .updated_at = $timestamp)' \
            "$FEATURE_LIST")
    else
        UPDATED=$(jq -r \
            --arg id "$FEATURE_ID" \
            --arg status "$NEW_STATUS" \
            --arg timestamp "$TIMESTAMP" \
            '(.features[] | select(.id == $id)) |=
                (.status = $status | .updated_at = $timestamp)' \
            "$FEATURE_LIST")
    fi
else
    # Nested structure: categories.*.features[]
    if [ -n "$NOTES" ]; then
        UPDATED=$(jq -r \
            --arg id "$FEATURE_ID" \
            --arg status "$NEW_STATUS" \
            --arg notes "$NOTES" \
            --arg timestamp "$TIMESTAMP" \
            '(.. | .features? // empty) | arrays | (
                (.[] | select(.id == $id)) |=
                    (.status = $status |
                    .notes = (.notes // "") + "\n" + $timestamp + ": " + $notes |
                    .updated_at = $timestamp)
            ) | .' \
            "$FEATURE_LIST")
    else
        UPDATED=$(jq -r \
            --arg id "$FEATURE_ID" \
            --arg status "$NEW_STATUS" \
            --arg timestamp "$TIMESTAMP" \
            '(.. | .features? // empty) | arrays | (
                (.[] | select(.id == $id)) |=
                    (.status = $status | .updated_at = $timestamp)
            ) | .' \
            "$FEATURE_LIST")
    fi
fi

# Write to temp and atomic move
echo "$UPDATED" > "$TEMP_FILE"
mv "$TEMP_FILE" "$FEATURE_LIST"

# Output result
echo "{\"status\":\"success\",\"feature_id\":\"$FEATURE_ID\",\"new_status\":\"$NEW_STATUS\",\"timestamp\":\"$TIMESTAMP\"}"

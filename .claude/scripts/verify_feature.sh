#!/bin/bash
set -e

ENDPOINT="$1"
EXPECTED_FIELD="$2"
METHOD="${3:-GET}"
REQUEST_BODY="${4:-{}}"
BASE_URL="${5:-http://localhost:8000}"
LOG_FILE="${6:-logs/backend.log}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOG_PATH="$PROJECT_ROOT/$LOG_FILE"
LOG_BEFORE=$(wc -l < "$LOG_PATH" 2>/dev/null || echo "0")
LOG_BEFORE=${LOG_BEFORE// /}

if [ "$METHOD" = "POST" ]; then
    RAW_RESPONSE=$(curl -s -X POST "$BASE_URL$ENDPOINT" -H "Content-Type: application/json" -d "$REQUEST_BODY" --max-time 30 2>&1)
    HTTP_CODE=$(curl -s -X POST "$BASE_URL$ENDPOINT" -H "Content-Type: application/json" -d "$REQUEST_BODY" --max-time 30 -o /dev/null -w "%{http_code}" 2>/dev/null)
else
    RAW_RESPONSE=$(curl -s -X GET "$BASE_URL$ENDPOINT" -H "Content-Type: application/json" --max-time 30 2>&1)
    HTTP_CODE=$(curl -s -X GET "$BASE_URL$ENDPOINT" -H "Content-Type: application/json" --max-time 30 -o /dev/null -w "%{http_code}" 2>/dev/null)
fi

HTTP_CODE=${HTTP_CODE:-000}
FIELD_VALUE=$(echo "$RAW_RESPONSE" | jq -r "$EXPECTED_FIELD // empty" 2>/dev/null || echo "")

case "$FIELD_VALUE" in
    null|"0"|"0.0"|"[]"|"{}"|"")
        STATUS="FAIL"
        REASON="Field is empty got $FIELD_VALUE"
        ;;
    *)
        STATUS="PASS"
        REASON="Field has value $FIELD_VALUE"
        ;;
esac

LOG_AFTER=$(wc -l < "$LOG_PATH" 2>/dev/null || echo "0")
LOG_AFTER=${LOG_AFTER// /}
ERROR_COUNT=0

if [ "$LOG_AFTER" -gt "$LOG_BEFORE" ]; then
    NEW_LINES=$((LOG_AFTER - LOG_BEFORE))
    ERROR_LINES=$(tail -n "$NEW_LINES" "$LOG_PATH" 2>/dev/null | grep -i -E "error|exception" || true)
    if [ -n "$ERROR_LINES" ]; then
        ERROR_COUNT=1
    fi
fi

printf '{"status":"%s","endpoint":"%s","field_value":"%s","reason":"%s","http_code":%s,"errors_found":%d,"response":%s}\n' \
    "$STATUS" "$ENDPOINT" "$FIELD_VALUE" "$REASON" "$HTTP_CODE" "$ERROR_COUNT" "$RAW_RESPONSE"

[ "$STATUS" = "PASS" ] && exit 0 || exit 1

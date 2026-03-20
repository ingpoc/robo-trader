#!/bin/bash
# investigate_service.sh - Investigate a service's registration status
# Usage: investigate_service.sh <service_name> [src_dir]
# Output: JSON with file_location, di_status, constructor_params, examples

set -e

SERVICE_NAME="$1"
SRC_DIR="${2:-src}"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Output JSON helper
jq_out() {
    local status="$1"
    shift
    local data="$*"
    jq -n \
        --arg status "$status" \
        --arg data "$data" \
        '{status: $status, data: $data}' 2>/dev/null || echo "{\"status\":\"$status\",\"data\":\"$data\"}"
}

# Find service file
find_service_file() {
    local service="$1"
    local src="$2"

    # Try different patterns using grep/find
    local found=$(find "$PROJECT_ROOT/$src" -type f -name "${service}.py" 2>/dev/null | head -1)
    [ -n "$found" ] && echo "$found" && return 0

    found=$(find "$PROJECT_ROOT/$src" -type f -name "${service}_service.py" 2>/dev/null | head -1)
    [ -n "$found" ] && echo "$found" && return 0

    # Try removing _service suffix
    local base=$(echo "$service" | sed 's/_service$//')
    found=$(find "$PROJECT_ROOT/$src" -type f -name "${base}.py" 2>/dev/null | head -1)
    [ -n "$found" ] && echo "$found" && return 0

    return 1
}

# Check DI registration
check_di_registration() {
    local service="$1"
    local src="$2"

    # Find di registry files
    local reg_files=$(find "$PROJECT_ROOT/$src" -name "di_registry*.py" -o -name "di.py" 2>/dev/null)

    while IFS= read -r reg_file; do
        if grep -q "\"${service}\"" "$reg_file" 2>/dev/null; then
            echo "$reg_file"
            return 0
        fi
    done <<< "$reg_files"

    return 1
}

# Extract constructor params
extract_constructor() {
    local file="$1"

    # Find __init__ or class definition and extract params
    local init_line=$(grep -n "def __init__" "$file" 2>/dev/null | head -1 | cut -d: -f1)
    [ -z "$init_line" ] && return 1

    # Extract params from __init__ (skip self, include type hints)
    sed -n "${init_line},/def /p" "$file" | \
        grep -oE "[a-z_]+: [A-Z][a-zA-Z]+" | \
        awk -F: '{print $1}' | \
        grep -v "^self$" | \
        tr '\n' ', ' | \
        sed 's/, $//'
}

# Main
SERVICE_FILE=$(find_service_file "$SERVICE_NAME" "$SRC_DIR")
DI_FILE=$(check_di_registration "$SERVICE_NAME" "$SRC_DIR")
CONSTRUCTOR=$(extract_constructor "$SERVICE_FILE" 2>/dev/null || echo "unknown")

# Build JSON output
jq -n \
    --arg service "$SERVICE_NAME" \
    --arg file "${SERVICE_FILE:-not_found}" \
    --arg di_file "${DI_FILE:-not_registered}" \
    --arg di_status "$([ -n "$DI_FILE" ] && echo "registered" || echo "not_registered")" \
    --arg constructor "$CONSTRUCTOR" \
    --arg project_root "$PROJECT_ROOT" \
    '{
        service: $service,
        file_location: $file,
        di_status: $di_status,
        di_file: $di_file,
        constructor_params: $constructor,
        project_root: $project_root
    }'

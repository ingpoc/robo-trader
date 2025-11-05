#!/bin/bash
#
# Pre-Commit Hook - Robo Trader
#
# Fast validation before commit (target: < 30 seconds)
# - Architectural compliance (file sizes, method counts)
# - Python compilation and linting
# - TypeScript type checking
# - Code formatting
#
# Skip with: git commit --no-verify
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Pre-Commit Validation${NC}"
echo -e "${BLUE}================================${NC}\n"

# Track failures
FAILED=0

# Function to run check with timing
run_check() {
    local name="$1"
    local command="$2"

    echo -e "${BLUE}▶ ${name}...${NC}"
    start_time=$(date +%s)

    if eval "$command"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${GREEN}✅ ${name} passed${NC} (${duration}s)\n"
    else
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${RED}❌ ${name} failed${NC} (${duration}s)\n"
        FAILED=1
    fi
}

# Phase 1: Architectural Compliance (Fast)
echo -e "${YELLOW}Phase 1: Architectural Compliance${NC}\n"

run_check "File size validation" "python3 scripts/check_file_sizes.py"
run_check "Method count validation" "python3 scripts/check_method_counts.py"

# Phase 2: Python Validation
echo -e "${YELLOW}Phase 2: Python Validation${NC}\n"

# Get staged Python files
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -n "$STAGED_PY_FILES" ]; then
    # Python compilation check
    run_check "Python compilation" "python3 -m py_compile $STAGED_PY_FILES"

    # Python linting (if ruff is installed)
    if command -v ruff &> /dev/null; then
        run_check "Python linting (ruff)" "ruff check src/ --fix"
    else
        echo -e "${YELLOW}⚠ Skipping ruff (not installed)${NC}\n"
    fi

    # Code formatting check (if black is installed)
    if command -v black &> /dev/null; then
        run_check "Python formatting (black)" "black --check src/"
    else
        echo -e "${YELLOW}⚠ Skipping black (not installed)${NC}\n"
    fi
else
    echo -e "${GREEN}✅ No Python files to check${NC}\n"
fi

# Phase 3: TypeScript Validation
echo -e "${YELLOW}Phase 3: TypeScript/React Validation${NC}\n"

STAGED_TS_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx)$' || true)

if [ -n "$STAGED_TS_FILES" ]; then
    # Check if npm is available and ui directory exists
    if [ -d "ui" ] && command -v npm &> /dev/null; then
        # TypeScript type checking
        run_check "TypeScript type checking" "cd ui && npm run type-check"

        # ESLint (if configured)
        if [ -f "ui/.eslintrc.js" ] || [ -f "ui/.eslintrc.json" ]; then
            run_check "TypeScript linting (eslint)" "cd ui && npm run lint -- --fix"
        fi

        # Prettier (if configured)
        if [ -f "ui/.prettierrc" ] || [ -f "ui/.prettierrc.json" ]; then
            run_check "TypeScript formatting (prettier)" "cd ui && npm run format:check"
        fi
    else
        echo -e "${YELLOW}⚠ Skipping TypeScript checks (npm or ui/ not available)${NC}\n"
    fi
else
    echo -e "${GREEN}✅ No TypeScript files to check${NC}\n"
fi

# Summary
echo -e "${BLUE}================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All pre-commit checks passed!${NC}"
    echo -e "${BLUE}================================${NC}\n"
    exit 0
else
    echo -e "${RED}❌ Pre-commit checks failed${NC}"
    echo -e "${BLUE}================================${NC}\n"
    echo -e "${YELLOW}💡 To skip these checks (not recommended):${NC}"
    echo -e "   ${YELLOW}git commit --no-verify${NC}\n"
    exit 1
fi

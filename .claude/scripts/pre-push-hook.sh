#!/bin/bash
#
# Pre-Push Hook - Robo Trader
#
# Comprehensive validation before push (target: 1-2 minutes)
# - All pre-commit checks
# - Unit tests
# - Build verification
# - API smoke tests
#
# Skip with: git push --no-verify
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Pre-Push Validation${NC}"
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

# Phase 1: Quick Pre-Commit Checks
echo -e "${YELLOW}Phase 1: Quick Validation${NC}\n"

run_check "File sizes" "python3 scripts/check_file_sizes.py"
run_check "Method counts" "python3 scripts/check_method_counts.py"

# Phase 2: Backend Tests
echo -e "${YELLOW}Phase 2: Backend Testing${NC}\n"

if command -v pytest &> /dev/null; then
    # Run fast unit tests only (skip integration tests)
    run_check "Backend unit tests" "pytest tests/unit/ -v --tb=short 2>/dev/null || pytest tests/ -k 'not integration' -v --tb=short"
else
    echo -e "${YELLOW}⚠ Skipping pytest (not installed)${NC}\n"
fi

# Phase 3: Frontend Tests
echo -e "${YELLOW}Phase 3: Frontend Testing${NC}\n"

if [ -d "ui" ] && command -v npm &> /dev/null; then
    # TypeScript type checking
    run_check "TypeScript types" "cd ui && npm run type-check"

    # Frontend unit tests (if configured)
    if [ -f "ui/package.json" ] && grep -q '"test"' ui/package.json; then
        run_check "Frontend unit tests" "cd ui && npm test -- --watchAll=false --passWithNoTests"
    fi

    # Frontend build verification
    run_check "Frontend build" "cd ui && npm run build"
else
    echo -e "${YELLOW}⚠ Skipping frontend tests (npm or ui/ not available)${NC}\n"
fi

# Phase 4: API Health Check (if backend is running)
echo -e "${YELLOW}Phase 4: API Health Check${NC}\n"

if curl -s -f -m 3 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend API is healthy${NC}\n"
else
    echo -e "${YELLOW}⚠ Backend not running (skipping API tests)${NC}\n"
fi

# Summary
echo -e "${BLUE}================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All pre-push checks passed!${NC}"
    echo -e "${GREEN}   Safe to push to remote${NC}"
    echo -e "${BLUE}================================${NC}\n"
    exit 0
else
    echo -e "${RED}❌ Pre-push checks failed${NC}"
    echo -e "${BLUE}================================${NC}\n"
    echo -e "${YELLOW}💡 Fix the issues above before pushing${NC}"
    echo -e "   ${YELLOW}Or skip with: git push --no-verify${NC}\n"
    exit 1
fi

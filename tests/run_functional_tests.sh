#!/bin/bash

################################################################################
# ROBO TRADER - FUNCTIONAL TESTING SCRIPT
#
# This script runs comprehensive API-based functional tests against the running
# Robo Trader backend server. It verifies critical functionality and generates
# a test report.
#
# Usage:
#   ./tests/run_functional_tests.sh                    # Run all tests
#   ./tests/run_functional_tests.sh http://localhost:8001  # Custom backend URL
#
# Requirements:
#   - Backend server running (default: http://localhost:8000)
#   - curl installed
#   - jq installed (JSON query tool)
#
# Output:
#   - Console output: Real-time test results
#   - Report file: results/test_results_TIMESTAMP.txt
#
# Tests Included:
#   1. Backend Health Check
#   2. Analysis History API
#   3. Queue Status API
#   4. Recommendations API
#   5. Database Persistence
#   6. Portfolio Configuration
#   7. API Response Time Performance
#
################################################################################

set -e

# Configuration
BACKEND="${1:-http://localhost:8000}"
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/test_results_${TIMESTAMP}.txt"

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====== ROBO TRADER COMPREHENSIVE FUNCTIONAL TESTING ======"
echo "Execution Date: $(date)" | tee "$RESULTS_FILE"
echo "Backend URL: $BACKEND" | tee -a "$RESULTS_FILE"
echo "Test Report: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Helper function to print test results
print_test_result() {
  local test_name=$1
  local status=$2
  local message=$3

  if [ "$status" == "PASS" ]; then
    echo -e "${GREEN}✅ PASS${NC}: $test_name - $message" | tee -a "$RESULTS_FILE"
  elif [ "$status" == "FAIL" ]; then
    echo -e "${RED}❌ FAIL${NC}: $test_name - $message" | tee -a "$RESULTS_FILE"
  else
    echo -e "${YELLOW}⚠️  WARN${NC}: $test_name - $message" | tee -a "$RESULTS_FILE"
  fi
}

# TEST 1: Health Endpoint
echo "--- TEST 1.1: Backend Health Check ---" | tee -a "$RESULTS_FILE"
HEALTH=$(curl -s -m 5 "$BACKEND/api/health")
HEALTH_STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null || echo "FAILED")
echo "  Status: $HEALTH_STATUS" | tee -a "$RESULTS_FILE"
if [ "$HEALTH_STATUS" == "healthy" ]; then
  print_test_result "Backend Health" "PASS" "Backend is healthy"
else
  print_test_result "Backend Health" "FAIL" "Backend health check failed: $HEALTH"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 2: Analysis History API
echo "--- TEST 2.1: Analysis History Endpoint ---" | tee -a "$RESULTS_FILE"
ANALYSIS=$(curl -s -m 5 "$BACKEND/api/claude/transparency/analysis")
ANALYSIS_COUNT=$(echo "$ANALYSIS" | jq '.analysis.portfolio_analyses | length' 2>/dev/null || echo "0")
echo "  Baseline Analysis Count: $ANALYSIS_COUNT" | tee -a "$RESULTS_FILE"
if echo "$ANALYSIS" | jq '.analysis' > /dev/null 2>&1; then
  print_test_result "Analysis API" "PASS" "API responds with valid JSON ($ANALYSIS_COUNT analyses)"
else
  print_test_result "Analysis API" "FAIL" "Invalid response format"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 3: Queue Status
echo "--- TEST 3.1: Queue Status API ---" | tee -a "$RESULTS_FILE"
QUEUE=$(curl -s -m 5 "$BACKEND/api/queue/status")
QUEUE_COUNT=$(echo "$QUEUE" | jq '.queues | length' 2>/dev/null || echo "0")
echo "  Active Queues: $QUEUE_COUNT" | tee -a "$RESULTS_FILE"
if [ "$QUEUE_COUNT" -ge "2" ]; then
  print_test_result "Queue Status" "PASS" "Queue system operational ($QUEUE_COUNT queues)"
  echo "$QUEUE" | jq '.queues[]' | head -20 >> "$RESULTS_FILE"
else
  print_test_result "Queue Status" "WARN" "Expected at least 2 queues, got $QUEUE_COUNT"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 4: Recommendations API
echo "--- TEST 4.1: Recommendations Endpoint ---" | tee -a "$RESULTS_FILE"
RECS=$(curl -s -m 5 "$BACKEND/api/claude/transparency/recommendations")
REC_COUNT=$(echo "$RECS" | jq '.recommendations | length' 2>/dev/null || echo "0")
echo "  Recommendation Count: $REC_COUNT" | tee -a "$RESULTS_FILE"
if echo "$RECS" | jq '.recommendations' > /dev/null 2>&1; then
  print_test_result "Recommendations API" "PASS" "Recommendations endpoint responds ($REC_COUNT recommendations)"
else
  print_test_result "Recommendations API" "WARN" "Recommendations endpoint issue"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 5: Database File Check
echo "--- TEST 5.1: Database Persistence ---" | tee -a "$RESULTS_FILE"
if [ -f "state/robo_trader.db" ]; then
  DB_SIZE=$(ls -lh state/robo_trader.db | awk '{print $5}')
  echo "  Database Size: $DB_SIZE" | tee -a "$RESULTS_FILE"
  print_test_result "Database Persistence" "PASS" "Database file exists ($DB_SIZE)"
else
  print_test_result "Database Persistence" "FAIL" "Database file not found"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 6: Portfolio Configuration
echo "--- TEST 6.1: Portfolio Configuration Endpoint ---" | tee -a "$RESULTS_FILE"
PORTFOLIO=$(curl -s -m 5 "$BACKEND/api/config/portfolio")
PORT_COUNT=$(echo "$PORTFOLIO" | jq '.portfolio_count' 2>/dev/null || echo "0")
echo "  Portfolio Holdings: $PORT_COUNT" | tee -a "$RESULTS_FILE"
if [ "$PORT_COUNT" != "0" ] && [ "$PORT_COUNT" != "null" ]; then
  print_test_result "Portfolio Configuration" "PASS" "Portfolio loaded ($PORT_COUNT holdings)"
else
  print_test_result "Portfolio Configuration" "WARN" "No portfolio loaded"
fi
echo "" | tee -a "$RESULTS_FILE"

# TEST 7: Response Time Test
echo "--- TEST 7.1: API Response Time Performance ---" | tee -a "$RESULTS_FILE"
START=$(date +%s%N)
curl -s -m 5 "$BACKEND/api/claude/transparency/analysis" > /dev/null
END=$(date +%s%N)
RESPONSE_TIME=$(( (END - START) / 1000000 ))
echo "  Response Time: ${RESPONSE_TIME}ms" | tee -a "$RESULTS_FILE"
if [ "$RESPONSE_TIME" -lt "500" ]; then
  print_test_result "API Response Time" "PASS" "Response time excellent (<500ms): ${RESPONSE_TIME}ms"
elif [ "$RESPONSE_TIME" -lt "1000" ]; then
  print_test_result "API Response Time" "PASS" "Response time good (<1s): ${RESPONSE_TIME}ms"
else
  print_test_result "API Response Time" "WARN" "Response time slow (>1s): ${RESPONSE_TIME}ms - Check for database locks"
fi
echo "" | tee -a "$RESULTS_FILE"

echo "====== TEST EXECUTION COMPLETE ======" | tee -a "$RESULTS_FILE"
echo "Results saved to: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
echo ""
echo "To view results:"
echo "  cat $RESULTS_FILE"

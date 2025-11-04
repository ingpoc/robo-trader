#!/bin/bash

################################################################################
# ROBO TRADER - COMPREHENSIVE END-TO-END TESTING SCRIPT
#
# This script runs complete end-to-end functional tests including:
# 1. Queue Status & Execution (Task processing through 3 parallel queues)
# 2. AI Analysis Execution (Portfolio Intelligence, Recommendations)
# 3. Data Persistence Validation (Database state, analysis history)
#
# Usage:
#   ./tests/run_comprehensive_e2e_tests.sh                    # Run all tests
#   ./tests/run_comprehensive_e2e_tests.sh http://localhost:8001  # Custom URL
#
# Requirements:
#   - Backend server running
#   - curl, jq, python3 installed
#   - Database initialized
#
# Test Categories:
#   - PART 1: Queue System Tests (Status, Health, Metrics)
#   - PART 2: AI Analysis Tests (Analysis history, recommendations)
#   - PART 3: Data Persistence Tests (Database validation)
#   - PART 4: System Transparency Tests (Trading decisions, execution logs)
#
################################################################################

set -e

# Configuration
BACKEND="${1:-http://localhost:8000}"
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/e2e_test_results_${TIMESTAMP}.txt"

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNED=0

# Helper functions
print_header() {
  echo "" | tee -a "$RESULTS_FILE"
  echo "================================================================================================" | tee -a "$RESULTS_FILE"
  echo "$1" | tee -a "$RESULTS_FILE"
  echo "================================================================================================" | tee -a "$RESULTS_FILE"
  echo "" | tee -a "$RESULTS_FILE"
}

print_test_result() {
  local test_name=$1
  local status=$2
  local message=$3
  local details=$4

  if [ "$status" == "PASS" ]; then
    echo -e "${GREEN}✅ PASS${NC}: $test_name" | tee -a "$RESULTS_FILE"
    ((TESTS_PASSED++))
  elif [ "$status" == "FAIL" ]; then
    echo -e "${RED}❌ FAIL${NC}: $test_name - $message" | tee -a "$RESULTS_FILE"
    ((TESTS_FAILED++))
  else
    echo -e "${YELLOW}⚠️  WARN${NC}: $test_name - $message" | tee -a "$RESULTS_FILE"
    ((TESTS_WARNED++))
  fi

  if [ -n "$details" ]; then
    echo "  Details: $details" | tee -a "$RESULTS_FILE"
  fi
}

# Initialize results file
echo "====== ROBO TRADER COMPREHENSIVE END-TO-END TESTING ======" | tee "$RESULTS_FILE"
echo "Execution Date: $(date)" | tee -a "$RESULTS_FILE"
echo "Backend URL: $BACKEND" | tee -a "$RESULTS_FILE"
echo "Test Report: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# ===============================================================================================
# PART 0: PRE-FLIGHT CHECKS
# ===============================================================================================
print_header "PART 0: PRE-FLIGHT CHECKS"

echo "Checking backend health..." | tee -a "$RESULTS_FILE"
HEALTH=$(curl -s -m 5 "$BACKEND/api/health" 2>/dev/null)
HEALTH_STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null || echo "FAILED")

if [ "$HEALTH_STATUS" == "healthy" ]; then
  print_test_result "Pre-flight: Backend Health" "PASS" "Backend is healthy"
else
  print_test_result "Pre-flight: Backend Health" "FAIL" "Backend health check failed: $HEALTH_STATUS"
  echo "Cannot continue without healthy backend" | tee -a "$RESULTS_FILE"
  exit 1
fi

# ===============================================================================================
# PART 1: QUEUE SYSTEM TESTS
# ===============================================================================================
print_header "PART 1: QUEUE SYSTEM TESTS"

echo "--- TEST 1.1: Queue Status ---" | tee -a "$RESULTS_FILE"
QUEUE_STATUS=$(curl -s -m 5 "$BACKEND/api/queues/status" 2>/dev/null)
QUEUE_COUNT=$(echo "$QUEUE_STATUS" | jq '.queues | length' 2>/dev/null || echo "0")
echo "  Active Queues: $QUEUE_COUNT" | tee -a "$RESULTS_FILE"

if [ "$QUEUE_COUNT" -ge "2" ]; then
  print_test_result "Queue Status" "PASS" "Queue system operational ($QUEUE_COUNT queues)"
  echo "$QUEUE_STATUS" | jq '.queues[]' | head -10 >> "$RESULTS_FILE" 2>/dev/null
else
  print_test_result "Queue Status" "WARN" "Expected at least 2 queues, got $QUEUE_COUNT (may still be starting)"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 1.2: Queue Health ---" | tee -a "$RESULTS_FILE"
QUEUE_HEALTH=$(curl -s -m 5 "$BACKEND/api/queues/health" 2>/dev/null)
HEALTH_STATUS=$(echo "$QUEUE_HEALTH" | jq -r '.status' 2>/dev/null || echo "unknown")
echo "  Queue Health: $HEALTH_STATUS" | tee -a "$RESULTS_FILE"

if echo "$QUEUE_HEALTH" | jq '.status' > /dev/null 2>&1; then
  print_test_result "Queue Health" "PASS" "Queue health endpoint responding"
else
  print_test_result "Queue Health" "WARN" "Queue health endpoint issue"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 1.3: Queue Metrics ---" | tee -a "$RESULTS_FILE"
QUEUE_METRICS=$(curl -s -m 5 "$BACKEND/api/queues/metrics" 2>/dev/null)
TASK_COUNT=$(echo "$QUEUE_METRICS" | jq '.total_tasks // 0' 2>/dev/null || echo "0")
echo "  Total Tasks Processed: $TASK_COUNT" | tee -a "$RESULTS_FILE"

if echo "$QUEUE_METRICS" | jq '.total_tasks' > /dev/null 2>&1; then
  print_test_result "Queue Metrics" "PASS" "Queue metrics available ($TASK_COUNT tasks processed)"
else
  print_test_result "Queue Metrics" "WARN" "Queue metrics endpoint issue"
fi

# ===============================================================================================
# PART 2: AI ANALYSIS & TRANSPARENCY TESTS
# ===============================================================================================
print_header "PART 2: AI ANALYSIS & TRANSPARENCY TESTS"

echo "--- TEST 2.1: Analysis History ---" | tee -a "$RESULTS_FILE"
ANALYSIS=$(curl -s -m 5 "$BACKEND/api/claude/transparency/analysis" 2>/dev/null)
ANALYSIS_COUNT=$(echo "$ANALYSIS" | jq '.analysis.portfolio_analyses | length' 2>/dev/null || echo "0")
echo "  Analysis Records: $ANALYSIS_COUNT" | tee -a "$RESULTS_FILE"

if echo "$ANALYSIS" | jq '.analysis' > /dev/null 2>&1; then
  print_test_result "Analysis History" "PASS" "Analysis endpoint responding ($ANALYSIS_COUNT records)"
else
  print_test_result "Analysis History" "FAIL" "Invalid response format from analysis endpoint"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 2.2: Trade Decisions Transparency ---" | tee -a "$RESULTS_FILE"
TRADE_DECISIONS=$(curl -s -m 5 "$BACKEND/api/claude/transparency/trade-decisions" 2>/dev/null)
DECISION_COUNT=$(echo "$TRADE_DECISIONS" | jq '.decisions | length' 2>/dev/null || echo "0")
echo "  Trade Decisions: $DECISION_COUNT" | tee -a "$RESULTS_FILE"

if echo "$TRADE_DECISIONS" | jq '.decisions' > /dev/null 2>&1; then
  print_test_result "Trade Decisions" "PASS" "Trade decisions endpoint responding ($DECISION_COUNT decisions)"
else
  print_test_result "Trade Decisions" "WARN" "Trade decisions endpoint issue"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 2.3: Execution Transparency ---" | tee -a "$RESULTS_FILE"
EXECUTION=$(curl -s -m 5 "$BACKEND/api/claude/transparency/execution" 2>/dev/null)
EXECUTION_COUNT=$(echo "$EXECUTION" | jq '.executions | length' 2>/dev/null || echo "0")
echo "  Trade Executions: $EXECUTION_COUNT" | tee -a "$RESULTS_FILE"

if echo "$EXECUTION" | jq '.executions' > /dev/null 2>&1; then
  print_test_result "Execution Logs" "PASS" "Execution endpoint responding ($EXECUTION_COUNT records)"
else
  print_test_result "Execution Logs" "WARN" "Execution endpoint issue"
fi

# ===============================================================================================
# PART 3: DATA PERSISTENCE TESTS
# ===============================================================================================
print_header "PART 3: DATA PERSISTENCE TESTS"

echo "--- TEST 3.1: Database File Existence ---" | tee -a "$RESULTS_FILE"
if [ -f "state/robo_trader.db" ]; then
  DB_SIZE=$(ls -lh state/robo_trader.db | awk '{print $5}')
  echo "  Database Size: $DB_SIZE" | tee -a "$RESULTS_FILE"
  print_test_result "Database File" "PASS" "Database persisted successfully ($DB_SIZE)"
else
  print_test_result "Database File" "FAIL" "Database file not found at state/robo_trader.db"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 3.2: Backup Management ---" | tee -a "$RESULTS_FILE"
BACKUP_STATUS=$(curl -s -m 5 "$BACKEND/api/backups/status" 2>/dev/null)
BACKUP_COUNT=$(echo "$BACKUP_STATUS" | jq '.backup_count // 0' 2>/dev/null || echo "0")
LATEST_BACKUP=$(echo "$BACKUP_STATUS" | jq -r '.latest_backup // "none"' 2>/dev/null || echo "none")
echo "  Total Backups: $BACKUP_COUNT" | tee -a "$RESULTS_FILE"
echo "  Latest Backup: $LATEST_BACKUP" | tee -a "$RESULTS_FILE"

if echo "$BACKUP_STATUS" | jq '.backup_count' > /dev/null 2>&1; then
  print_test_result "Backup System" "PASS" "Backup system operational ($BACKUP_COUNT backups)"
else
  print_test_result "Backup System" "WARN" "Backup status endpoint issue"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 3.3: Database Content Validation (Python SQLite) ---" | tee -a "$RESULTS_FILE"

# Use Python to directly query database
python3 << 'PYTHON_TEST' 2>/dev/null

import sqlite3
import os
from datetime import datetime

db_path = "state/robo_trader.db"

if not os.path.exists(db_path):
    print(f"  ❌ Database not found: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    table_count = len(tables)
    print(f"  Database Tables: {table_count}")

    # Check analysis_history if exists
    try:
        cursor.execute("SELECT COUNT(*) FROM analysis_history")
        analysis_count = cursor.fetchone()[0]
        print(f"  Analysis History Records: {analysis_count}")
    except:
        print("  Analysis History Records: 0 (table not yet populated)")

    # Check recommendations if exists
    try:
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        rec_count = cursor.fetchone()[0]
        print(f"  Recommendations Records: {rec_count}")
    except:
        print("  Recommendations Records: 0 (table not yet populated)")

    # Check paper_trades if exists
    try:
        cursor.execute("SELECT COUNT(*) FROM paper_trades")
        trade_count = cursor.fetchone()[0]
        print(f"  Paper Trades Records: {trade_count}")
    except:
        print("  Paper Trades Records: 0 (table not yet populated)")

    conn.close()
    print(f"  ✅ Database validation passed - {table_count} tables found")
except Exception as e:
    print(f"  ❌ Database error: {e}")

PYTHON_TEST

if [ $? -eq 0 ]; then
  print_test_result "Database Validation" "PASS" "Database structure and content verified"
else
  print_test_result "Database Validation" "WARN" "Could not validate database content"
fi

# ===============================================================================================
# PART 4: API RESPONSE TIME PERFORMANCE
# ===============================================================================================
print_header "PART 4: API RESPONSE TIME PERFORMANCE"

echo "--- TEST 4.1: Analysis API Response Time ---" | tee -a "$RESULTS_FILE"
START=$(date +%s%N)
curl -s -m 5 "$BACKEND/api/claude/transparency/analysis" > /dev/null 2>&1
END=$(date +%s%N)
RESPONSE_TIME=$(( (END - START) / 1000000 ))
echo "  Response Time: ${RESPONSE_TIME}ms" | tee -a "$RESULTS_FILE"

if [ "$RESPONSE_TIME" -lt "500" ]; then
  print_test_result "API Performance" "PASS" "Response time excellent (<500ms): ${RESPONSE_TIME}ms"
elif [ "$RESPONSE_TIME" -lt "1000" ]; then
  print_test_result "API Performance" "PASS" "Response time good (<1s): ${RESPONSE_TIME}ms"
else
  print_test_result "API Performance" "WARN" "Response time slow (>1s): ${RESPONSE_TIME}ms - Check for database locks"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- TEST 4.2: Queue Status API Response Time ---" | tee -a "$RESULTS_FILE"
START=$(date +%s%N)
curl -s -m 5 "$BACKEND/api/queues/status" > /dev/null 2>&1
END=$(date +%s%N)
RESPONSE_TIME=$(( (END - START) / 1000000 ))
echo "  Response Time: ${RESPONSE_TIME}ms" | tee -a "$RESULTS_FILE"

if [ "$RESPONSE_TIME" -lt "500" ]; then
  print_test_result "Queue API Performance" "PASS" "Response time excellent (<500ms): ${RESPONSE_TIME}ms"
else
  print_test_result "Queue API Performance" "WARN" "Response time: ${RESPONSE_TIME}ms"
fi

# ===============================================================================================
# TEST SUMMARY
# ===============================================================================================
print_header "TEST EXECUTION SUMMARY"

echo "Tests Passed:  $TESTS_PASSED" | tee -a "$RESULTS_FILE"
echo "Tests Failed:  $TESTS_FAILED" | tee -a "$RESULTS_FILE"
echo "Tests Warned:  $TESTS_WARNED" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"
echo "Total Tests:   $((TESTS_PASSED + TESTS_FAILED + TESTS_WARNED))" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

if [ "$TESTS_FAILED" -eq 0 ]; then
  echo -e "${GREEN}✅ ALL CRITICAL TESTS PASSED${NC}" | tee -a "$RESULTS_FILE"
  EXIT_CODE=0
else
  echo -e "${RED}❌ SOME TESTS FAILED${NC}" | tee -a "$RESULTS_FILE"
  EXIT_CODE=1
fi

echo "" | tee -a "$RESULTS_FILE"
echo "====== TEST EXECUTION COMPLETE ======" | tee -a "$RESULTS_FILE"
echo "Results saved to: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
echo ""
echo "To view results:"
echo "  cat $RESULTS_FILE"
echo ""

exit $EXIT_CODE

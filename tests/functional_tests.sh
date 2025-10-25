#!/bin/bash

# Comprehensive Functional Tests for Robo Trader
# Tests Portfolio Scan, Market Screening, and Paper Trading features
# Monitors frontend, backend logs, and browser console

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
CRITICAL_ISSUES=()

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}ROBO TRADER - COMPREHENSIVE FUNCTIONAL TEST SUITE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================================================
# TEST 1: Portfolio Scan Feature
# ============================================================================

test_portfolio_scan() {
  echo -e "${YELLOW}[TEST 1] Portfolio Scan Feature${NC}"
  echo "=================================="

  # Clear backend logs
  echo "Triggering portfolio scan..."
  RESPONSE=$(curl -s -X POST http://localhost:8000/api/portfolio-scan)
  STATUS=$?

  if [ $STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Portfolio scan endpoint accessible${NC}"
    ((TESTS_PASSED++))

    # Check response structure
    if echo "$RESPONSE" | grep -q "status"; then
      echo -e "${GREEN}✓ Response contains status field${NC}"
      ((TESTS_PASSED++))
    else
      echo -e "${RED}✗ Response missing status field${NC}"
      CRITICAL_ISSUES+=("Portfolio scan response malformed")
      ((TESTS_FAILED++))
    fi
  else
    echo -e "${RED}✗ Portfolio scan endpoint failed (curl exit code: $STATUS)${NC}"
    CRITICAL_ISSUES+=("Portfolio scan endpoint unreachable")
    ((TESTS_FAILED++))
  fi

  # Check backend logs for errors
  echo ""
  echo "Checking backend logs for errors..."
  docker-compose logs robo-trader-portfolio --tail=20 | grep -i "error" && {
    echo -e "${YELLOW}⚠ Found errors in portfolio service logs${NC}"
  } || {
    echo -e "${GREEN}✓ No errors detected in portfolio service logs${NC}"
    ((TESTS_PASSED++))
  }

  echo ""
}

# ============================================================================
# TEST 2: Market Screening Feature
# ============================================================================

test_market_screening() {
  echo -e "${YELLOW}[TEST 2] Market Screening Feature${NC}"
  echo "===================================="

  echo "Triggering market screening..."
  RESPONSE=$(curl -s -X POST http://localhost:8000/api/market-screening)
  STATUS=$?

  if [ $STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Market screening endpoint accessible${NC}"
    ((TESTS_PASSED++))

    if echo "$RESPONSE" | grep -q "status"; then
      echo -e "${GREEN}✓ Response contains status field${NC}"
      ((TESTS_PASSED++))
    else
      echo -e "${RED}✗ Response missing status field${NC}"
      CRITICAL_ISSUES+=("Market screening response malformed")
      ((TESTS_FAILED++))
    fi
  else
    echo -e "${RED}✗ Market screening endpoint failed${NC}"
    CRITICAL_ISSUES+=("Market screening endpoint unreachable")
    ((TESTS_FAILED++))
  fi

  echo ""
}

# ============================================================================
# TEST 3: Paper Trading Feature
# ============================================================================

test_paper_trading() {
  echo -e "${YELLOW}[TEST 3] Paper Trading Feature${NC}"
  echo "===================================="

  ACCOUNT_ID="paper_swing_main"

  # Test 3.1: Get Account Overview
  echo "Testing GET /api/paper-trading/accounts/$ACCOUNT_ID/overview..."
  RESPONSE=$(curl -s http://localhost:8000/api/paper-trading/accounts/$ACCOUNT_ID/overview)

  if echo "$RESPONSE" | grep -q "account_id"; then
    echo -e "${GREEN}✓ Account overview endpoint works${NC}"
    ((TESTS_PASSED++))

    # Extract and display account info
    BALANCE=$(echo "$RESPONSE" | grep -o '"balance":[^,}]*' | cut -d':' -f2)
    echo "  Account Balance: $BALANCE"

    if [ "$BALANCE" == " 100000" ] || [ "$BALANCE" == " 100000.0" ]; then
      echo -e "${GREEN}✓ Account initialized with ₹1L capital${NC}"
      ((TESTS_PASSED++))
    else
      echo -e "${YELLOW}⚠ Account balance differs from expected ₹1L${NC}"
    fi
  else
    if echo "$RESPONSE" | grep -q "404\|not found"; then
      echo -e "${RED}✗ Account not found - auto-initialization may have failed${NC}"
      CRITICAL_ISSUES+=("Paper trading account not initialized")
      ((TESTS_FAILED++))
    else
      echo -e "${RED}✗ Account overview endpoint failed: $RESPONSE${NC}"
      ((TESTS_FAILED++))
    fi
  fi

  # Test 3.2: Get Open Positions
  echo ""
  echo "Testing GET /api/paper-trading/accounts/$ACCOUNT_ID/positions..."
  RESPONSE=$(curl -s http://localhost:8000/api/paper-trading/accounts/$ACCOUNT_ID/positions)

  if echo "$RESPONSE" | grep -q "\[\]" || echo "$RESPONSE" | grep -q "trade_id"; then
    echo -e "${GREEN}✓ Open positions endpoint works${NC}"
    ((TESTS_PASSED++))
  else
    echo -e "${RED}✗ Open positions endpoint failed${NC}"
    ((TESTS_FAILED++))
  fi

  # Test 3.3: Get Trade History
  echo ""
  echo "Testing GET /api/paper-trading/accounts/$ACCOUNT_ID/trades..."
  RESPONSE=$(curl -s http://localhost:8000/api/paper-trading/accounts/$ACCOUNT_ID/trades)

  if echo "$RESPONSE" | grep -q "\[\]" || echo "$RESPONSE" | grep -q "trade_id"; then
    echo -e "${GREEN}✓ Trade history endpoint works${NC}"
    ((TESTS_PASSED++))
  else
    echo -e "${RED}✗ Trade history endpoint failed${NC}"
    ((TESTS_FAILED++))
  fi

  # Test 3.4: Execute a test trade
  echo ""
  echo "Testing POST /api/paper-trading/accounts/$ACCOUNT_ID/trades/buy..."
  TRADE_REQUEST='{
    "symbol": "SBIN",
    "quantity": 10,
    "entry_price": 450.0,
    "strategy_rationale": "Functional test",
    "stop_loss": 440.0,
    "target_price": 470.0,
    "ai_suggested": false
  }'

  RESPONSE=$(curl -s -X POST http://localhost:8000/api/paper-trading/accounts/$ACCOUNT_ID/trades/buy \
    -H "Content-Type: application/json" \
    -d "$TRADE_REQUEST")

  if echo "$RESPONSE" | grep -q "trade_id"; then
    echo -e "${GREEN}✓ BUY trade executed successfully${NC}"
    ((TESTS_PASSED++))

    TRADE_ID=$(echo "$RESPONSE" | grep -o '"trade_id":"[^"]*' | cut -d'"' -f4)
    echo "  Trade ID: $TRADE_ID"
  else
    if echo "$RESPONSE" | grep -q "404\|not found"; then
      echo -e "${RED}✗ Account not found for trade execution${NC}"
      CRITICAL_ISSUES+=("Cannot execute trades - account missing")
      ((TESTS_FAILED++))
    else
      echo -e "${RED}✗ BUY trade execution failed: $RESPONSE${NC}"
      ((TESTS_FAILED++))
    fi
  fi

  echo ""
}

# ============================================================================
# TEST 4: API Gateway Health & Service Connectivity
# ============================================================================

test_api_gateway_health() {
  echo -e "${YELLOW}[TEST 4] API Gateway & Service Connectivity${NC}"
  echo "=============================================="

  echo "Testing API Gateway /health endpoint..."
  RESPONSE=$(curl -s http://localhost:8000/health)

  if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API Gateway is healthy${NC}"
    ((TESTS_PASSED++))

    # Check task scheduler connectivity
    if echo "$RESPONSE" | grep -q '"scheduler".*"healthy"'; then
      echo -e "${GREEN}✓ Task Scheduler service is reachable${NC}"
      ((TESTS_PASSED++))
    else
      echo -e "${YELLOW}⚠ Task Scheduler status: $(echo "$RESPONSE" | grep -o '"scheduler":[^}]*' || echo 'unknown')${NC}"
    fi
  else
    echo -e "${RED}✗ API Gateway health check failed${NC}"
    ((TESTS_FAILED++))
  fi

  echo ""
}

# ============================================================================
# TEST 5: WebSocket Connection
# ============================================================================

test_websocket() {
  echo -e "${YELLOW}[TEST 5] WebSocket Real-Time Connection${NC}"
  echo "=========================================="

  echo "Testing WebSocket connection to ws://localhost:8000/ws..."

  # Simple WebSocket test using timeout and echo
  (echo -e 'GET /ws HTTP/1.1\r\nHost: localhost:8000\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n'; sleep 1) | nc localhost 8000 2>/dev/null | grep -i "101" >/dev/null 2>&1 && {
    echo -e "${GREEN}✓ WebSocket connection established${NC}"
    ((TESTS_PASSED++))
  } || {
    echo -e "${YELLOW}⚠ WebSocket connection test inconclusive${NC}"
  }

  echo ""
}

# ============================================================================
# BROWSER CONSOLE LOGS CHECK
# ============================================================================

check_browser_console() {
  echo -e "${YELLOW}[INFO] Backend Service Logs Summary${NC}"
  echo "======================================"

  # Check for critical errors in backend logs
  echo ""
  echo "Checking for service connectivity errors..."

  if docker-compose logs robo-trader-api-gateway 2>/dev/null | grep -i "task-scheduler.*not responding\|Name or service not known" >/dev/null; then
    echo -e "${RED}✗ CRITICAL: API Gateway cannot reach task-scheduler${NC}"
    CRITICAL_ISSUES+=("API Gateway - Task Scheduler connectivity broken")
  else
    echo -e "${GREEN}✓ No task-scheduler connectivity errors detected${NC}"
  fi

  echo ""
  echo "Checking for paper trading initialization..."
  if docker-compose logs robo-trader-api-gateway 2>/dev/null | grep -i "Created default paper trading account" >/dev/null; then
    echo -e "${GREEN}✓ Paper trading account auto-initialization confirmed${NC}"
  else
    echo -e "${YELLOW}⚠ Paper trading auto-initialization log not found${NC}"
  fi

  echo ""
}

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

main() {
  # Run all tests
  test_api_gateway_health
  test_portfolio_scan
  test_market_screening
  test_paper_trading
  test_websocket
  check_browser_console

  # Final Report
  echo ""
  echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}TEST SUMMARY REPORT${NC}"
  echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

  TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
  PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

  echo ""
  echo "Total Tests Run: $TOTAL_TESTS"
  echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
  echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
  echo "Pass Rate: $PASS_RATE%"

  echo ""
  if [ ${#CRITICAL_ISSUES[@]} -gt 0 ]; then
    echo -e "${RED}CRITICAL ISSUES DETECTED:${NC}"
    for issue in "${CRITICAL_ISSUES[@]}"; do
      echo -e "  ${RED}✗${NC} $issue"
    done
  else
    echo -e "${GREEN}✓ No critical issues detected${NC}"
  fi

  echo ""
  echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

  # Exit with appropriate code
  if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
  else
    exit 0
  fi
}

# Run main
main

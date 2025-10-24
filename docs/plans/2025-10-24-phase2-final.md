# Phase 2: AI Transparency & Trade Execution - FINAL FOCUSED PLAN

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate real Claude AI transparency data and ensure trade execution forms work perfectly.

**Scope:**
- ✅ AI Transparency: Real trade decisions, research, reflections logged from Claude
- ✅ Trade Execution: Buy/sell/close forms with validation and real execution
- ✅ NO account creation (use existing paper_swing_main account)
- ✅ No mock data - only real Claude AI operations

**Tech Stack:** Python (FastAPI), React (TypeScript), SQLite, Claude Agent SDK

---

## Phase 2A: AI Transparency - Trade Decision Logging

### Task 1: Create TradeDecisionLogger Service

**Files:**
- Create: `src/services/claude_agent/trade_decision_logger.py`
- Create: `tests/services/claude_agent/test_trade_decision_logger.py`

**Implementation:**

```python
# src/services/claude_agent/trade_decision_logger.py
"""Trade decision logging service for Claude AI transparency."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiofiles

logger = logging.getLogger(__name__)


class TradeDecisionLogger:
    """Log and retrieve Claude's trade decisions for transparency."""

    def __init__(self, data_file: str = "data/trade_decisions.jsonl"):
        """Initialize with data file path."""
        self.data_file = data_file
        self._decisions: List[Dict[str, Any]] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing decisions from file."""
        try:
            async with aiofiles.open(self.data_file, 'r') as f:
                content = await f.read()
                if content.strip():
                    lines = content.strip().split('\n')
                    self._decisions = [json.loads(line) for line in lines if line.strip()]
        except FileNotFoundError:
            self._decisions = []
        self._initialized = True
        logger.info(f"TradeDecisionLogger initialized with {len(self._decisions)} decisions")

    async def log_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Log a new trade decision."""
        if not self._initialized:
            await self.initialize()

        if "logged_at" not in decision:
            decision["logged_at"] = datetime.now(timezone.utc).isoformat()

        self._decisions.append(decision)

        # Persist to file
        async with aiofiles.open(self.data_file, 'a') as f:
            await f.write(json.dumps(decision) + '\n')

        logger.info(f"Trade decision logged: {decision.get('trade_id')} - {decision.get('symbol')} {decision.get('action')}")
        return decision

    async def get_recent_decisions(self, limit: int = 20, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent trade decisions, optionally filtered by symbol."""
        if not self._initialized:
            await self.initialize()

        decisions = self._decisions.copy()

        if symbol:
            decisions = [d for d in decisions if d.get("symbol") == symbol]

        # Return most recent first
        return decisions[-limit:][::-1]

    async def get_decision_stats(self) -> Dict[str, Any]:
        """Get statistics about trade decisions."""
        if not self._initialized:
            await self.initialize()

        total = len(self._decisions)
        buy_decisions = sum(1 for d in self._decisions if d.get("action") == "BUY")
        sell_decisions = sum(1 for d in self._decisions if d.get("action") == "SELL")
        avg_confidence = sum(d.get("confidence", 0) for d in self._decisions) / total if total > 0 else 0

        symbols = set(d.get("symbol") for d in self._decisions if d.get("symbol"))

        return {
            "total_decisions": total,
            "buy_decisions": buy_decisions,
            "sell_decisions": sell_decisions,
            "avg_confidence": round(avg_confidence, 3),
            "symbols_traded": len(symbols),
            "unique_symbols": sorted(list(symbols))
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._initialized = False
```

**Test file:**

```python
# tests/services/claude_agent/test_trade_decision_logger.py
import pytest
from datetime import datetime
from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger

@pytest.mark.asyncio
async def test_log_trade_decision():
    """Test logging a trade decision."""
    logger = TradeDecisionLogger()
    await logger.initialize()

    decision = {
        "trade_id": "trade_001",
        "symbol": "HDFC",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 2750,
        "reasoning": "Momentum breakout confirmed by RSI",
        "confidence": 0.85,
        "stop_loss": 2650,
        "target": 2900,
        "research_sources": ["news_articles", "technical_analysis"],
        "decision_timestamp": datetime.now().isoformat()
    }

    result = await logger.log_decision(decision)

    assert result["trade_id"] == "trade_001"
    assert result["symbol"] == "HDFC"

    history = await logger.get_recent_decisions(limit=1)
    assert len(history) > 0
    assert history[0]["trade_id"] == "trade_001"

@pytest.mark.asyncio
async def test_get_recent_decisions():
    """Test retrieving recent trade decisions."""
    logger = TradeDecisionLogger()
    await logger.initialize()

    history = await logger.get_recent_decisions(limit=10)

    assert isinstance(history, list)
    if history:
        decision = history[0]
        assert "trade_id" in decision
        assert "symbol" in decision
        assert "action" in decision
```

**Commands:**

```bash
# Run tests
pytest tests/services/claude_agent/test_trade_decision_logger.py -v

# Expected: PASSED
```

---

### Task 2: Register TradeDecisionLogger in DI Container

**Files:**
- Modify: `src/core/di.py` (add registration around line 445)

**Step:**

Add to `create_orchestrator` function in DI container:

```python
# Register TradeDecisionLogger
from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger
trade_decision_logger = TradeDecisionLogger()
await trade_decision_logger.initialize()
container.register_singleton(trade_decision_logger, "trade_decision_logger")
```

**Verify:**

```bash
python -c "from src.core.di import DependencyContainer; print('DI registration works')"
```

---

### Task 3: Add API Endpoint for Trade Decisions

**Files:**
- Modify: `src/web/routes/claude_transparency.py` (add new endpoint)

**Implementation:**

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

@router.get("/transparency/trade-decisions")
@limiter.limit("20/minute")
async def get_trade_decisions(request: Request) -> Dict[str, Any]:
    """Get Claude's trade decision logs for AI transparency."""
    try:
        from ..app import container

        if not container:
            return JSONResponse({"error": "System not initialized"}, status_code=500)

        trade_decision_logger = container.get("trade_decision_logger")

        if not trade_decision_logger:
            return JSONResponse({"error": "Trade decision logger not available"}, status_code=500)

        recent_decisions = await trade_decision_logger.get_recent_decisions(limit=20)
        stats = await trade_decision_logger.get_decision_stats()

        return {
            "decisions": recent_decisions,
            "stats": stats,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Trade decisions retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
```

**Test:**

```bash
curl http://localhost:8000/api/claude/transparency/trade-decisions
# Expected: 200 OK with empty decisions array initially
```

---

### Task 4: Hook AIPlanner to Log Trade Decisions

**Files:**
- Modify: `src/core/ai_planner.py` (in trade execution methods)

**Step:**

After Claude AI executes a trade, log the decision:

```python
async def place_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
    """Place a trade and log the decision."""

    # Get the trade decision logger
    trade_decision_logger = self.container.get("trade_decision_logger")

    # Execute trade (existing code)
    result = await self._execute_trade(trade_request)

    # Log the decision
    if trade_decision_logger and result.get("trade_id"):
        decision = {
            "trade_id": result.get("trade_id"),
            "symbol": trade_request["symbol"],
            "action": trade_request["action"],
            "quantity": trade_request["quantity"],
            "entry_price": trade_request.get("price", result.get("entry_price")),
            "reasoning": trade_request.get("reasoning", ""),
            "confidence": trade_request.get("confidence", 0.5),
            "stop_loss": trade_request.get("stop_loss"),
            "target": trade_request.get("target"),
            "research_sources": trade_request.get("research_sources", []),
            "decision_timestamp": datetime.now().isoformat()
        }

        await trade_decision_logger.log_decision(decision)

    return result
```

**Test:**

```bash
# Execute a trade and verify it's logged
curl -X POST http://localhost:8000/api/paper-trading/accounts/paper_swing_main/trades/buy \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "HDFC",
    "quantity": 10,
    "entry_price": 2750,
    "strategy_rationale": "Momentum breakout"
  }'

# Check if logged
curl http://localhost:8000/api/claude/transparency/trade-decisions | jq .
```

---

### Task 5: Update Frontend to Fetch Real Trade Decisions

**Files:**
- Modify: `ui/src/features/ai-transparency/hooks/useAITransparency.ts`
- Modify: `ui/src/features/ai-transparency/components/TradeDecisionLog.tsx`

**Step:**

Update hook to call the trade decisions endpoint:

```typescript
// In useAITransparency hook
useEffect(() => {
  const fetchTradeDecisions = async () => {
    try {
      const response = await fetch('/api/claude/transparency/trade-decisions')
      if (!response.ok) throw new Error('Failed to fetch trade decisions')

      const data = await response.json()

      // Transform to match component interface
      const trades = data.decisions.map((decision: any) => ({
        id: decision.trade_id,
        symbol: decision.symbol,
        action: decision.action,
        quantity: decision.quantity,
        entry_price: decision.entry_price,
        reasoning: decision.reasoning,
        confidence: decision.confidence,
        research_sources: decision.research_sources,
        timestamp: new Date(decision.logged_at)
      }))

      setTradeDecisions(trades)
    } catch (error) {
      console.error('Failed to load trade decisions:', error)
    }
  }

  fetchTradeDecisions()
  const interval = setInterval(fetchTradeDecisions, 5000)
  return () => clearInterval(interval)
}, [])
```

**Test in Browser:**

Navigate to `http://localhost:3000/ai-transparency` → Trades tab → Execute a trade → Should see it appear in real-time.

---

### Task 6: Create ResearchActivityLogger Service

**Files:**
- Create: `src/services/claude_agent/research_activity_logger.py`

Similar structure to TradeDecisionLogger - logs research activities with data sources, symbols analyzed, findings.

**Implementation:** [Same pattern as Task 1]

---

### Task 7: Create StrategyReflectionLogger Service

**Files:**
- Create: `src/services/claude_agent/strategy_reflection_logger.py`

Similar structure - logs daily strategy reflections, learnings, and improvements.

**Implementation:** [Same pattern as Task 1]

---

### Task 8: Add API Endpoints for Research & Reflections

**Files:**
- Modify: `src/web/routes/claude_transparency.py`

Add two endpoints:
- `/api/claude/transparency/research-activities`
- `/api/claude/transparency/strategy-reflections`

---

## Phase 2B: Trade Execution Forms

### Task 9: Implement Trade Execution Forms

**Files:**
- Modify: `ui/src/pages/PaperTrading.tsx` (Execute Trade tab)

**Implementation:**

Create buy/sell form with validation:

```typescript
const [buyForm, setBuyForm] = useState({
  symbol: '',
  quantity: '',
  entry_price: '',
  strategy_rationale: '',
  stop_loss: '',
  target_price: ''
})

const handleBuySubmit = async (e: React.FormEvent) => {
  e.preventDefault()

  try {
    const response = await fetch(`/api/paper-trading/accounts/paper_swing_main/trades/buy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: buyForm.symbol.toUpperCase(),
        quantity: parseInt(buyForm.quantity),
        entry_price: parseFloat(buyForm.entry_price),
        strategy_rationale: buyForm.strategy_rationale,
        stop_loss: buyForm.stop_loss ? parseFloat(buyForm.stop_loss) : undefined,
        target_price: buyForm.target_price ? parseFloat(buyForm.target_price) : undefined
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Trade failed')
    }

    const result = await response.json()
    toast.success(`Trade executed: BUY ${result.quantity} ${result.symbol}`)

    // Reset form
    setBuyForm({ symbol: '', quantity: '', entry_price: '', strategy_rationale: '', stop_loss: '', target_price: '' })

    // Refresh positions
    await refetchPositions()

  } catch (error) {
    toast.error(`Trade failed: ${error.message}`)
  }
}
```

**Test:**

Execute a trade from the UI → Verify it appears in Positions tab → Verify it appears in AI Transparency.

---

### Task 10: Ensure Trade Execution Form Validation

**Files:**
- Modify: `ui/src/pages/PaperTrading.tsx`

Add form validation:
- Symbol: Required, uppercase, 1-20 characters
- Quantity: Required, > 0, integer
- Entry Price: Required, > 0, decimal
- Stop Loss/Target: Optional, > 0 if provided

---

## Phase 2C: Testing & Verification

### Task 11: End-to-End Testing

**Files:**
- Create: `tests/e2e/test_phase2_integration.py`

**Test:**

```python
@pytest.mark.asyncio
async def test_complete_trade_to_transparency_flow():
    """Test trade execution flows to AI transparency."""

    # 1. Execute trade via API
    trade_response = client.post(
        "/api/paper-trading/accounts/paper_swing_main/trades/buy",
        json={
            "symbol": "HDFC",
            "quantity": 10,
            "entry_price": 2750,
            "strategy_rationale": "E2E test trade"
        }
    )
    assert trade_response.status_code == 200
    trade_id = trade_response.json()["trade_id"]

    # 2. Verify in trade decisions
    decisions_response = client.get("/api/claude/transparency/trade-decisions")
    assert decisions_response.status_code == 200
    decisions = decisions_response.json()["decisions"]

    assert any(d["trade_id"] == trade_id for d in decisions)
    assert any(d["symbol"] == "HDFC" for d in decisions)
```

---

### Task 12: Browser Integration Testing

**Files:**
- Create: `tests/e2e/test_phase2_browser.py`

**Test:** Execute trade from UI form → Verify it appears in Positions → Verify it appears in AI Transparency tabs.

---

## Execution Flow

**Total Tasks: 12**
**Estimated Time: 4-6 hours**

**Task Dependencies:**
1. Tasks 1-2: Core logging infrastructure
2. Task 3: Expose via API
3. Task 4: Hook into execution
4. Task 5: Display in UI
5. Tasks 6-8: Repeat for research & reflections
6. Task 9-10: Trade execution forms
7. Tasks 11-12: Verify everything works

**Success Criteria:**
- ✅ Trade decisions logged automatically when executed
- ✅ Research activities tracked
- ✅ Strategy reflections saved
- ✅ All data visible in AI Transparency tabs
- ✅ Trade execution forms work perfectly
- ✅ No mock data - only real operations
- ✅ All tests passing

---

## Command Reference

```bash
# Start backend
python -m uvicorn src.web.app:app --reload

# Start frontend
cd ui && npm run dev

# Run tests
pytest tests/ -v

# Check trade decisions
curl http://localhost:8000/api/claude/transparency/trade-decisions | jq .

# Execute test trade
curl -X POST http://localhost:8000/api/paper-trading/accounts/paper_swing_main/trades/buy \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HDFC","quantity":10,"entry_price":2750,"strategy_rationale":"Test"}'
```

---

**Status: Ready for implementation**

Choose execution method:
1. **Subagent-Driven** - I dispatch fresh subagent per task, review code between tasks
2. **Separate Session** - Open new session with executing-plans skill

Which approach?

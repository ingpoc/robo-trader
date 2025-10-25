# Phase 2: AI Transparency Integration & Trade Execution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate real Claude AI transparency data (research, analysis, reflections, decisions) with functional trade execution and account creation features.

**Architecture:**
- Real Claude AI data flows from AIPlanner/LearningEngine → TradeDecisionLogger → API endpoints → Frontend
- Trade execution forms directly call backend APIs that execute trades via PaperTradingStore
- Account creation persists to database via PaperTradingStore
- No mock data - all data comes from actual Claude AI operations

**Tech Stack:** Python (FastAPI), React (TypeScript), SQLite (state management), Claude Agent SDK (AI decisions)

---

## Phase 2A: AI Transparency - Trade Decision Logging

### Task 1: Create TradeDecisionLogger Service

**Files:**
- Create: `src/services/claude_agent/trade_decision_logger.py`

**Step 1: Write test for trade decision logging**

```python
import pytest
from datetime import datetime
from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger

@pytest.mark.asyncio
async def test_log_trade_decision():
    """Test logging a trade decision with all details."""
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

    # Verify it was persisted
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
    # Each decision should have required fields
    if history:
        decision = history[0]
        assert "trade_id" in decision
        assert "symbol" in decision
        assert "action" in decision
        assert "reasoning" in decision
        assert "confidence" in decision
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/gurusharan/Documents/remote-claude/robo-trader
pytest tests/services/claude_agent/test_trade_decision_logger.py -v
```

Expected: `FAILED - ModuleNotFoundError: No module named 'src.services.claude_agent.trade_decision_logger'`

**Step 3: Create TradeDecisionLogger implementation**

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

        # Add timestamp if not present
        if "logged_at" not in decision:
            decision["logged_at"] = datetime.now(timezone.utc).isoformat()

        self._decisions.append(decision)

        # Persist to file
        async with aiofiles.open(self.data_file, 'a') as f:
            await f.write(json.dumps(decision) + '\n')

        logger.info(f"Trade decision logged: {decision.get('trade_id')} - {decision.get('symbol')} {decision.get('action')}")
        return decision

    async def get_recent_decisions(self, limit: int = 10, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
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

**Step 4: Run test to verify it passes**

```bash
pytest tests/services/claude_agent/test_trade_decision_logger.py -v
```

Expected: `PASSED - 2 passed in 0.XX seconds`

**Step 5: Commit**

```bash
git add src/services/claude_agent/trade_decision_logger.py tests/services/claude_agent/test_trade_decision_logger.py
git commit -m "feat: Implement TradeDecisionLogger for Claude AI transparency"
```

---

### Task 2: Integrate TradeDecisionLogger into DI Container

**Files:**
- Modify: `src/core/di.py:430-450` (in create_orchestrator function)

**Step 1: Write test for DI registration**

```python
@pytest.mark.asyncio
async def test_trade_decision_logger_in_container():
    """Test that TradeDecisionLogger is registered in DI container."""
    from src.core.di import DependencyContainer
    from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger

    container = DependencyContainer()
    # No initialization needed for singleton registration

    logger = container.get("trade_decision_logger")
    assert logger is not None
    assert isinstance(logger, TradeDecisionLogger)
```

**Step 2: Add TradeDecisionLogger to DI container**

In `src/core/di.py`, find the `create_orchestrator` function and add this around line 445:

```python
# Register TradeDecisionLogger
from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger
trade_decision_logger = TradeDecisionLogger()
await trade_decision_logger.initialize()
container.register_singleton(trade_decision_logger, "trade_decision_logger")
```

**Step 3: Run test**

```bash
pytest tests/core/test_di.py::test_trade_decision_logger_in_container -v
```

Expected: `PASSED`

**Step 4: Commit**

```bash
git add src/core/di.py tests/core/test_di.py
git commit -m "refactor: Register TradeDecisionLogger in DI container"
```

---

### Task 3: Hook AIPlanner to TradeDecisionLogger

**Files:**
- Modify: `src/core/ai_planner.py:200-250` (in trade execution methods)

**Step 1: Check AIPlanner's trade execution method**

Read `src/core/ai_planner.py` to find where trades are executed. Look for methods like `execute_trade` or `place_trade`.

**Step 2: Add logging hook**

After Claude AI makes a trade decision, log it:

```python
async def place_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
    """Place a trade and log the decision."""

    # Get the trade decision logger from container
    trade_decision_logger = self.container.get("trade_decision_logger")

    # Execute trade (existing code)
    result = await self._execute_trade(trade_request)

    # Log the decision with reasoning
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

**Step 3: Test manually**

Run the application and execute a trade through the API:

```bash
curl -X POST http://localhost:8000/api/paper-trading/accounts/paper_swing_main/trades/buy \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "HDFC",
    "quantity": 10,
    "entry_price": 2750,
    "strategy_rationale": "Momentum breakout"
  }'
```

Then verify the decision was logged:

```bash
cat data/trade_decisions.jsonl | tail -1 | jq .
```

**Step 4: Commit**

```bash
git add src/core/ai_planner.py
git commit -m "feat: Hook AIPlanner to log trade decisions via TradeDecisionLogger"
```

---

### Task 4: Create API Endpoint for Trade Decisions

**Files:**
- Modify: `src/web/routes/claude_transparency.py:200-250` (add new endpoint)

**Step 1: Write test for endpoint**

```python
@pytest.mark.asyncio
async def test_get_trade_decisions_endpoint(client):
    """Test getting trade decisions via API."""
    response = client.get("/api/claude/transparency/trade-decisions")

    assert response.status_code == 200
    data = response.json()

    assert "decisions" in data
    assert isinstance(data["decisions"], list)
    assert "stats" in data
    assert "total_decisions" in data["stats"]
```

**Step 2: Add endpoint to claude_transparency.py**

```python
@router.get("/transparency/trade-decisions")
@limiter.limit(transparency_limit)
async def get_trade_decisions(request: Request) -> Dict[str, Any]:
    """Get Claude's trade decision logs for transparency."""
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

**Step 3: Run test**

```bash
pytest tests/web/routes/test_claude_transparency.py::test_get_trade_decisions_endpoint -v
```

Expected: `PASSED`

**Step 4: Commit**

```bash
git add src/web/routes/claude_transparency.py tests/web/routes/test_claude_transparency.py
git commit -m "feat: Add trade decisions endpoint to AI transparency API"
```

---

### Task 5: Update Frontend Hook to Fetch Real Trade Decisions

**Files:**
- Modify: `ui/src/features/ai-transparency/hooks/useAITransparency.ts:30-80`

**Step 1: Update hook to call trade decisions endpoint**

```typescript
// Inside useAITransparency hook's useEffect

useEffect(() => {
  const fetchTradeDecisions = async () => {
    try {
      const response = await fetch('/api/claude/transparency/trade-decisions')
      if (!response.ok) throw new Error('Failed to fetch trade decisions')

      const data = await response.json()

      // Transform backend response to match frontend interface
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
      logger.error('Failed to load trade decisions:', error)
      setError('Unable to load trade decisions')
    }
  }

  fetchTradeDecisions()
  // Poll every 5 seconds for new decisions
  const interval = setInterval(fetchTradeDecisions, 5000)
  return () => clearInterval(interval)
}, [])
```

**Step 2: Test in browser**

Navigate to `http://localhost:3000/ai-transparency` and click the "Trades" tab. Should see real trade decisions instead of "No trade decision logs available".

**Step 3: Commit**

```bash
git add ui/src/features/ai-transparency/hooks/useAITransparency.ts
git commit -m "feat: Update AI Transparency hook to fetch real trade decisions"
```

---

## Phase 2B: AI Transparency - Research & Analysis

### Task 6: Create ResearchActivityLogger Service

**Files:**
- Create: `src/services/claude_agent/research_activity_logger.py`

**Step 1: Implement ResearchActivityLogger**

Similar structure to TradeDecisionLogger:

```python
# src/services/claude_agent/research_activity_logger.py
"""Research activity logging for Claude AI transparency."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiofiles

logger = logging.getLogger(__name__)


class ResearchActivityLogger:
    """Log and retrieve Claude's research activities."""

    def __init__(self, data_file: str = "data/research_activities.jsonl"):
        """Initialize with data file path."""
        self.data_file = data_file
        self._activities: List[Dict[str, Any]] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing activities from file."""
        try:
            async with aiofiles.open(self.data_file, 'r') as f:
                content = await f.read()
                if content.strip():
                    lines = content.strip().split('\n')
                    self._activities = [json.loads(line) for line in lines if line.strip()]
        except FileNotFoundError:
            self._activities = []
        self._initialized = True

    async def log_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Log a research activity."""
        if not self._initialized:
            await self.initialize()

        if "logged_at" not in activity:
            activity["logged_at"] = datetime.now(timezone.utc).isoformat()

        self._activities.append(activity)

        async with aiofiles.open(self.data_file, 'a') as f:
            await f.write(json.dumps(activity) + '\n')

        logger.info(f"Research activity logged: {activity.get('activity_type')} - {activity.get('symbols')}")
        return activity

    async def get_recent_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent research activities."""
        if not self._initialized:
            await self.initialize()

        activities = self._activities.copy()
        return activities[-limit:][::-1]

    async def get_activity_stats(self) -> Dict[str, Any]:
        """Get statistics about research activities."""
        if not self._initialized:
            await self.initialize()

        total = len(self._activities)
        activity_types = {}
        for activity in self._activities:
            atype = activity.get("activity_type", "unknown")
            activity_types[atype] = activity_types.get(atype, 0) + 1

        return {
            "total_activities": total,
            "activity_types": activity_types,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._initialized = False
```

**Step 2: Register in DI container (same pattern as Task 2)**

**Step 3: Add API endpoint (same pattern as Task 4)**

Create `/api/claude/transparency/research-activities`

**Step 4: Update frontend to fetch real research data**

**Step 5: Commit**

```bash
git commit -m "feat: Implement ResearchActivityLogger and API endpoint"
```

---

### Task 7: Create StrategyReflectionLogger Service

**Files:**
- Create: `src/services/claude_agent/strategy_reflection_logger.py`

Similar to above - logs Claude's daily strategy reflections and learnings.

**Step 1-5:** Follow same pattern as Task 6

**Step 6: Commit**

```bash
git commit -m "feat: Implement StrategyReflectionLogger for daily AI learnings"
```

---

## Phase 2C: Trade Execution Forms

### Task 8: Fix Trade Execution Forms in PaperTrading Component

**Files:**
- Modify: `ui/src/pages/PaperTrading.tsx:1200-1400` (Execute Trade tab form)

**Step 1: Write test for buy trade form submission**

```typescript
describe('PaperTrading Trade Execution', () => {
  it('should submit buy trade with validation', async () => {
    render(<PaperTradingPage />)

    // Navigate to Execute Trade tab
    const executeTab = screen.getByRole('tab', { name: /execute trade/i })
    fireEvent.click(executeTab)

    // Fill in form
    const symbolInput = screen.getByLabelText(/symbol/i)
    const quantityInput = screen.getByLabelText(/quantity/i)
    const priceInput = screen.getByLabelText(/price/i)

    fireEvent.change(symbolInput, { target: { value: 'HDFC' } })
    fireEvent.change(quantityInput, { target: { value: '10' } })
    fireEvent.change(priceInput, { target: { value: '2750' } })

    // Submit form
    const submitButton = screen.getByRole('button', { name: /buy/i })
    fireEvent.click(submitButton)

    // Wait for success message
    await waitFor(() => {
      expect(screen.getByText(/trade executed/i)).toBeInTheDocument()
    })
  })
})
```

**Step 2: Implement Buy Form in PaperTrading component**

```typescript
// In Execute Trade tab section
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
    const response = await fetch(`/api/paper-trading/accounts/${selectedAccount.account_id}/trades/buy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: buyForm.symbol.toUpperCase(),
        quantity: parseInt(buyForm.quantity),
        entry_price: parseFloat(buyForm.entry_price),
        strategy_rationale: buyForm.strategy_rationale,
        stop_loss: buyForm.stop_loss ? parseFloat(buyForm.stop_loss) : undefined,
        target_price: buyForm.target_price ? parseFloat(buyForm.target_price) : undefined,
        ai_suggested: false
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Trade failed')
    }

    const result = await response.json()

    // Success - refresh positions and reset form
    await refetchPositions()
    setBuyForm({
      symbol: '',
      quantity: '',
      entry_price: '',
      strategy_rationale: '',
      stop_loss: '',
      target_price: ''
    })

    // Show success toast
    toast.success(`Trade executed: BUY ${result.quantity} ${result.symbol}`)

  } catch (error) {
    toast.error(`Trade failed: ${error.message}`)
  }
}

// Render form
return (
  <div className="space-y-4">
    <form onSubmit={handleBuySubmit} className="space-y-3">
      <div>
        <label>Symbol</label>
        <Input
          value={buyForm.symbol}
          onChange={(e) => setBuyForm({...buyForm, symbol: e.target.value})}
          placeholder="e.g., HDFC"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label>Quantity</label>
          <Input
            type="number"
            value={buyForm.quantity}
            onChange={(e) => setBuyForm({...buyForm, quantity: e.target.value})}
            placeholder="10"
            required
          />
        </div>
        <div>
          <label>Entry Price</label>
          <Input
            type="number"
            step="0.01"
            value={buyForm.entry_price}
            onChange={(e) => setBuyForm({...buyForm, entry_price: e.target.value})}
            placeholder="2750.00"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label>Stop Loss (Optional)</label>
          <Input
            type="number"
            step="0.01"
            value={buyForm.stop_loss}
            onChange={(e) => setBuyForm({...buyForm, stop_loss: e.target.value})}
            placeholder="2650.00"
          />
        </div>
        <div>
          <label>Target Price (Optional)</label>
          <Input
            type="number"
            step="0.01"
            value={buyForm.target_price}
            onChange={(e) => setBuyForm({...buyForm, target_price: e.target.value})}
            placeholder="2900.00"
          />
        </div>
      </div>

      <div>
        <label>Strategy Rationale</label>
        <textarea
          value={buyForm.strategy_rationale}
          onChange={(e) => setBuyForm({...buyForm, strategy_rationale: e.target.value})}
          placeholder="Why are you buying this stock?"
          className="w-full h-24"
        />
      </div>

      <Button type="submit" className="w-full">
        Execute BUY
      </Button>
    </form>
  </div>
)
```

**Step 3: Implement Sell Form (same pattern)**

**Step 4: Test in browser**

Navigate to Paper Trading → Execute Trade tab and place a real trade.

**Step 5: Commit**

```bash
git add ui/src/pages/PaperTrading.tsx
git commit -m "feat: Implement trade execution forms for buy/sell with validation"
```

---

## Phase 2D: Account Creation

### Task 9: Create Account Creation API Endpoint

**Files:**
- Modify: `src/web/routes/paper_trading.py` (add new endpoint)

**Step 1: Write test for account creation endpoint**

```python
@pytest.mark.asyncio
async def test_create_paper_trading_account(client):
    """Test creating a new paper trading account."""
    response = client.post("/api/paper-trading/accounts", json={
        "account_name": "Options Trading Account",
        "initial_balance": 50000,
        "strategy_type": "options",
        "risk_level": "high",
        "max_position_size": 20000,
        "max_portfolio_risk": 5000
    })

    assert response.status_code == 201
    data = response.json()

    assert data["account_id"]
    assert data["account_name"] == "Options Trading Account"
    assert data["balance"] == 50000
```

**Step 2: Implement account creation endpoint**

```python
from pydantic import BaseModel, Field

class CreateAccountRequest(BaseModel):
    account_name: str = Field(..., min_length=3, max_length=100)
    initial_balance: float = Field(..., gt=10000, le=10000000)
    strategy_type: str = Field(..., pattern="^(swing|options|hybrid)$")
    risk_level: str = Field(..., pattern="^(low|moderate|high)$")
    max_position_size: float = Field(..., gt=0)
    max_portfolio_risk: float = Field(..., gt=0)

@router.post("/accounts", status_code=201)
@limiter.limit(account_limit)
async def create_account(request: Request, account_data: CreateAccountRequest) -> Dict[str, Any]:
    """Create a new paper trading account."""
    try:
        container = request.app.state.container

        if not container:
            return JSONResponse({"error": "System not initialized"}, status_code=500)

        store = await container.get("paper_trading_store")

        # Create account
        account = await store.create_account(
            account_name=account_data.account_name,
            initial_balance=account_data.initial_balance,
            strategy_type=account_data.strategy_type,
            risk_level=account_data.risk_level
        )

        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "balance": account.balance,
            "strategy_type": account.strategy_type,
            "created_at": account.created_at
        }

    except Exception as e:
        logger.error(f"Account creation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
```

**Step 3: Implement create_account method in PaperTradingStore**

**Step 4: Test**

```bash
curl -X POST http://localhost:8000/api/paper-trading/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Options Trading",
    "initial_balance": 50000,
    "strategy_type": "options",
    "risk_level": "high",
    "max_position_size": 20000,
    "max_portfolio_risk": 5000
  }'
```

**Step 5: Commit**

```bash
git commit -m "feat: Add account creation API endpoint with validation"
```

---

### Task 10: Update Frontend Account Context to Support Account Creation

**Files:**
- Modify: `ui/src/contexts/AccountContext.tsx:150-200`

**Step 1: Update createAccount method to call backend**

```typescript
const createAccount = async (accountData: CreateAccountData) => {
  try {
    setError(null)

    const response = await fetch('/api/paper-trading/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_name: accountData.account_name,
        initial_balance: accountData.initial_balance,
        strategy_type: accountData.strategy_type,
        risk_level: accountData.risk_level,
        max_position_size: accountData.max_position_size,
        max_portfolio_risk: accountData.max_portfolio_risk
      })
    })

    if (!response.ok) {
      throw new Error('Failed to create account')
    }

    const newAccountData = await response.json()

    const newAccount: Account = {
      account_id: newAccountData.account_id,
      account_name: newAccountData.account_name,
      account_type: newAccountData.strategy_type === 'swing' ? 'swing_trading' : 'options_trading',
      strategy_type: newAccountData.strategy_type,
      risk_level: accountData.risk_level,
      balance: newAccountData.balance,
      buying_power: newAccountData.balance,
      deployed_capital: 0,
      total_pnl: 0,
      total_pnl_pct: 0,
      monthly_pnl: 0,
      monthly_pnl_pct: 0,
      open_positions_count: 0,
      today_trades: 0,
      win_rate: 0,
      created_at: newAccountData.created_at,
      reset_date: ''
    }

    setAccounts(prev => [...prev, newAccount])
    selectAccount(newAccount)

  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to create account')
    throw err
  }
}
```

**Step 2: Test in browser**

Navigate to Paper Trading → click "New Account" → fill form → create.

**Step 3: Commit**

```bash
git commit -m "feat: Connect account creation form to backend API"
```

---

## Verification & Testing

### Task 11: End-to-End Testing

**Files:**
- Create: `tests/e2e/test_phase2_flow.py`

**Step 1: Write E2E test for complete flow**

```python
@pytest.mark.asyncio
async def test_complete_phase2_flow():
    """Test complete Phase 2 flow: account creation → trade execution → transparency."""

    # 1. Create new account
    account_response = client.post("/api/paper-trading/accounts", json={
        "account_name": "E2E Test Account",
        "initial_balance": 100000,
        "strategy_type": "swing",
        "risk_level": "moderate",
        "max_position_size": 50000,
        "max_portfolio_risk": 5000
    })
    assert account_response.status_code == 201
    account_id = account_response.json()["account_id"]

    # 2. Execute trade
    trade_response = client.post(
        f"/api/paper-trading/accounts/{account_id}/trades/buy",
        json={
            "symbol": "HDFC",
            "quantity": 10,
            "entry_price": 2750,
            "strategy_rationale": "Momentum breakout"
        }
    )
    assert trade_response.status_code == 200

    # 3. Verify trade in history
    history_response = client.get(f"/api/paper-trading/accounts/{account_id}/trades")
    assert history_response.status_code == 200
    trades = history_response.json()["trades"]
    assert len(trades) > 0

    # 4. Verify trade decision logged
    decisions_response = client.get("/api/claude/transparency/trade-decisions")
    assert decisions_response.status_code == 200
    decisions = decisions_response.json()["decisions"]
    assert any(d["symbol"] == "HDFC" for d in decisions)
```

**Step 2: Run E2E test**

```bash
pytest tests/e2e/test_phase2_flow.py -v
```

Expected: All tests pass

**Step 3: Commit**

```bash
git commit -m "test: Add comprehensive E2E tests for Phase 2 flow"
```

---

### Task 12: Browser Testing with Playwright

**Files:**
- Create: `tests/e2e/test_phase2_browser.py`

**Step 1: Write browser test**

```python
async def test_phase2_ui_flow():
    """Test Phase 2 UI: Create account → Execute trade → View AI Transparency."""

    browser = await playwright.chromium.launch()
    page = await browser.new_page()

    # Navigate to Paper Trading
    await page.goto("http://localhost:3000/paper-trading")

    # Create new account
    await page.click('button:has-text("New Account")')
    await page.fill('input[placeholder*="Account name"]', 'Browser Test Account')
    await page.fill('input[type="number"]', '50000')
    await page.click('button:has-text("Create")')

    # Wait for account to appear
    await page.wait_for_selector('text=Browser Test Account')

    # Navigate to AI Transparency
    await page.click('a:has-text("AI Transparency")')

    # Verify trade decisions are showing
    await page.click('role=tab[name="Trades"]')
    await page.wait_for_selector('text=HDFC', timeout=5000)

    await browser.close()
```

**Step 2: Run browser tests**

```bash
pytest tests/e2e/test_phase2_browser.py -v
```

**Step 3: Commit**

```bash
git commit -m "test: Add browser automation tests for Phase 2 UI flow"
```

---

## Summary of Changes

**Backend:**
- ✅ TradeDecisionLogger service
- ✅ ResearchActivityLogger service
- ✅ StrategyReflectionLogger service
- ✅ API endpoints for AI transparency
- ✅ Account creation endpoint
- ✅ DI container registration
- ✅ Hook into AIPlanner for decision logging

**Frontend:**
- ✅ Trade execution forms (buy/sell/close)
- ✅ Form validation and error handling
- ✅ AI Transparency tabs with real data
- ✅ Account creation dialog connected to backend
- ✅ Real-time polling for AI decisions

**Testing:**
- ✅ Unit tests for all new services
- ✅ API endpoint tests
- ✅ E2E flow tests
- ✅ Browser automation tests

**No Mock Data:**
All data flows from actual Claude AI operations through TradeDecisionLogger, ResearchActivityLogger, and StrategyReflectionLogger services. Frontend displays real AI transparency.

---

## Implementation Sequence

Execute tasks in this order (they're ordered by dependencies):

1. Task 1-5: Trade Decision Logging (backend → API → frontend)
2. Task 6-7: Research & Analysis Logging (similar pattern)
3. Task 8: Trade Execution Forms (uses existing backend endpoints)
4. Task 9-10: Account Creation (backend → frontend)
5. Task 11-12: Testing & Verification

Total estimated time: 6-8 hours for experienced developer

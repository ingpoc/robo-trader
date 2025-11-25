---
name: queue-operation-validation
enabled: true
event: prompt
pattern: (create|add|queue).*(task|job)|(AI_ANALYSIS|PORTFOLIO_SYNC|DATA_FETCHER).*(task|payload)
action: warn
---

🔍 **Queue Operation Detected**

You're creating a task for robo-trader queues.

**Critical rules**:
1. AI analysis → Must use AI_ANALYSIS queue (prevents token exhaustion)
2. Max 3 stocks per task: `{"agent_name": "scan", "symbols": ["AAPL", "GOOGL", "MSFT"]}`
3. Queue capacity: 20 max across all 3 queues
4. Required payload keys: `agent_name`, `symbols`

**Before creating task**:
- Check queue status: `mcp__robo-trader-dev__queue_status(queue_filter="AI_ANALYSIS")`
- Verify capacity not exceeded
- Validate payload structure

**I'll validate the queue operation follows these rules.**

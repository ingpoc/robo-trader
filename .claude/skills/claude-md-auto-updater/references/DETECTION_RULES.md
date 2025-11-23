# Detection Rules Reference

> **Purpose**: Detailed detection rules for identifying patterns, violations, staleness, and anti-patterns
> **Last Updated**: 2025-11-09

## Detection Rule Categories

### 1. New Pattern Detection

**Trigger Threshold**: 3+ similar code instances

**Process**:
1. Scan codebase for code patterns (AST-based for Python, Regex/AST for TypeScript)
2. Group similar patterns together
3. Count occurrences of each pattern group
4. Flag patterns with 3+ occurrences as "new pattern"
5. Check if pattern is documented in any CLAUDE.md file
6. If not documented → Generate recommendation

**Confidence Calculation**:
- Base confidence: 50%
- +10% per occurrence (3 occurrences = 80%, 4+ = 95%)
- +5% if pattern has consistent naming/structure
- +5% if pattern follows existing architectural style

### 2. Violation Detection

**Trigger Types**: Code breaks documented constraints

**Critical Violations** (Must detect):

#### Database Access Violations
```python
# VIOLATION: Direct connection access
await config_state.db.connection.execute(...)
await database.connection.commit()
```

**Detection**:
- Pattern: Direct calls to `.db.connection.execute()`
- Search: `(database|db|config_state)\.connection\.execute\(`
- File scope: `src/**/*.py` (all Python files)
- Severity: Critical
- Confidence: 95% (direct match)

**Correct Pattern**:
```python
# CORRECT: Use locked state methods
await config_state.store_analysis_history(...)
```

---

#### SDK Usage Violations
```python
# VIOLATION: Direct Anthropic API call
from anthropic import Anthropic
client = Anthropic()  # NO!
```

**Detection**:
- Pattern: Direct import of `Anthropic` class
- Search: `from anthropic import Anthropic` or `import anthropic`
- File scope: `src/**/*.py`
- Exception: Allowed only in `ClaudeSDKClientManager`
- Severity: Critical
- Confidence: 90%

---

#### Missing Timeout Protection
```python
# VIOLATION: SDK call without timeout
response = await client.messages.create(...)
```

**Detection**:
- Pattern: `ClaudeSDKClientManager` usage without `query_with_timeout` wrapper
- Search: Client calls not within `await query_with_timeout(...)`
- File scope: `src/**/*.py`
- Severity: High
- Confidence: 85%

**Correct Pattern**:
```python
response = await query_with_timeout(client, prompt, timeout=60.0)
```

---

#### Event Emission Violations
```python
# VIOLATION: Direct service call instead of event
await other_service.do_something()  # NO!
```

**Detection**:
- Pattern: Service calling another service method directly (except during initialization)
- Search: Method calls between service instances outside of constructors
- File scope: `src/services/**/*.py`
- Exception: Constructor/initialization code allowed
- Severity: Medium
- Confidence: 70%

**Correct Pattern**:
```python
await self.event_bus.publish(Event(...))
```

---

#### Modularization Violations
```python
# VIOLATION: File exceeds 350 lines
# src/services/portfolio_service.py:500 lines
```

**Detection**:
- Pattern: Python/TypeScript files with >350 lines
- Scope: All code files (exclude tests, config)
- Severity: Medium
- Confidence: 100% (line count)

---

#### Async Violations
```python
# VIOLATION: time.sleep() in async function
async def fetch_data():
    time.sleep(1)  # BLOCKS ALL ASYNC!
```

**Detection**:
- Pattern: `time.sleep()` calls within `async def` functions
- Search: Regex in AST context: `time\.sleep\(` within `async def` block
- File scope: `src/**/*.py`
- Severity: High (blocks all async operations)
- Confidence: 100% (direct pattern match)

**Correct Pattern**:
```python
async def fetch_data():
    await asyncio.sleep(0.1)  # Correct for async
```

---

#### Error Handling Violations
```python
# VIOLATION: Generic exception without context
raise Exception("Something failed")
```

**Detection**:
- Pattern: Bare `Exception()` or `ValueError()` without `TradingError` wrapper
- Search: `raise Exception(` or `raise [BuiltinError](`
- File scope: `src/**/*.py` (all application code)
- Exception: Allowed in tests and utilities
- Severity: Low
- Confidence: 80%

**Correct Pattern**:
```python
raise TradingError(
    category=ErrorCategory.VALIDATION,
    code="SYMBOL_NOT_FOUND",
    metadata={"symbol": symbol}
)
```

---

### 3. Staleness Detection

**Trigger**: Documented pattern hasn't appeared in code for 30+ days

**Process**:
1. Extract all documented patterns from CLAUDE.md files (regex patterns)
2. Search codebase for each documented pattern
3. For matches found: Get Git blame/history to find last modification date
4. Calculate days since last modification
5. If >30 days without modification: Mark as stale

**Staleness Confidence**:
- Base: 50%
- +10% per 10 days past 30-day threshold (60 days = 70%, 90+ = 95%)
- +5% if alternative pattern exists (old pattern replaced)

**Example Detection**:
```markdown
STALE PATTERN: AgentCoordinator
- Last documented: src/core/CLAUDE.md
- Last code occurrence: ~60 days ago
- Current status: No imports or usage found
- Recommendation: Mark for removal or archival
```

---

### 4. Anti-Pattern Detection

**Trigger**: Same mistake pattern appears 3+ times

**Common Anti-Patterns to Detect**:

#### Sleep in Async Code (Anti-Pattern)
```python
async def process_items():
    for item in items:
        time.sleep(1)  # BLOCKS!
```

**Detection**:
- Pattern: `time.sleep()` in async context
- Threshold: 3+ occurrences
- Search: AST analysis of async function bodies
- Severity: High
- Confidence: 95% (clear mistake)

**Suggested Fix Location**: `src/CLAUDE.md` → Add to "Async-First Design" section

---

#### Portfolio Analysis Inefficiency (Anti-Pattern)
```python
async def analyze_portfolio():
    for stock in portfolio:
        await analyzer.analyze(stock)  # Analyzes all, even recently done!
```

**Detection**:
- Pattern: No smart scheduling in stock analysis
- Check: Absence of conditions like `if not has_analysis(stock):`
- Search: Portfolio analysis functions without scheduling logic
- Severity: Medium
- Confidence: 75%

**Suggested Fix Location**: `src/services/CLAUDE.md` → Add to "Portfolio Analysis Scheduling"

---

#### Direct DB Access in Web Endpoints (Anti-Pattern)
```python
@router.get("/api/data")
async def get_data():
    database = await container.get("database")
    await database.connection.execute(...)  # LOCK!
```

**Detection**:
- Pattern: Direct `db.connection` access in web endpoints
- File scope: `src/web/routes/**/*.py`
- Severity: Critical (causes page freezing)
- Confidence: 95%

**Suggested Fix Location**: `src/web/CLAUDE.md` → Add to "Database Access" section

---

#### Prop Drilling in React (Anti-Pattern)
```typescript
// src/features/Dashboard/Dashboard.tsx
<ChildComponent prop1={prop1} prop2={prop2} prop3={prop3} prop4={prop4} />
```

**Detection**:
- Pattern: Props passed through >2 levels of components
- Search: Component definitions with >4 props that only pass them down
- File scope: `ui/src/features/**/*.tsx`
- Severity: Medium
- Confidence: 70%

**Suggested Fix Location**: `ui/src/CLAUDE.md` → Add to "State Management Patterns"

---

#### Oversized Components (Anti-Pattern)
```typescript
// src/features/Dashboard/Dashboard.tsx: 500 lines
```

**Detection**:
- Pattern: React components >350 lines
- File scope: `ui/src/**/*.tsx`
- Severity: Medium
- Confidence: 100%

**Suggested Fix Location**: `ui/src/CLAUDE.md` → Reinforce component size limits

---

### 5. Broken Reference Detection

**Trigger**: CLAUDE.md references non-existent files/sections

**Process**:
1. Extract all file paths mentioned in CLAUDE.md (e.g., `src/services/portfolio.py`)
2. Check if files exist in codebase
3. Extract all internal links (e.g., `#database-patterns`)
4. Verify linked sections exist
5. Report broken references

**Confidence**: 100% (verifiable)

---

## Confidence Scoring

### Scoring Factors

#### High Confidence (75-100%)
- Exact code pattern matches
- Multiple occurrences (4+)
- Documented constraints violated
- Statically verifiable (line count, file existence)

#### Medium Confidence (50-75%)
- Similar patterns (3 occurrences)
- Pattern matches with minor variations
- Potential violations (ambiguous code intent)

#### Low Confidence (25-50%)
- Single pattern occurrence
- Ambiguous pattern matching
- Requires semantic understanding

### Confidence Adjustments

**Increase Confidence**:
- Same developer pattern across files: +5%
- Consistent with existing violations: +10%
- Clear documentation violation: +15%

**Decrease Confidence**:
- Ambiguous pattern intent: -10%
- First occurrence only: -20%
- Legacy code exceptions: -15%

---

## Implementation Patterns

### Python Detection (AST-Based)

**Tools**: `ast`, `libcst`, regex

**Pattern Example - Queue Handlers**:
```python
# Look for class definitions with @task_handler decorator
import ast

class TaskHandlerVisitor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        has_task_handler = any(
            isinstance(dec, ast.Name) and dec.id == 'task_handler'
            or isinstance(dec, ast.Call) and getattr(dec.func, 'id', None) == 'task_handler'
            for dec in node.decorator_list
        )
        if has_task_handler:
            # Found a task handler
            handlers.append({
                'name': node.name,
                'file': current_file,
                'line': node.lineno
            })
```

### TypeScript Detection (Regex + AST)

**Tools**: `re` (regex), `esprima` (AST), `ast-grep`

**Pattern Example - Component Size**:
```bash
# Find TypeScript files >350 lines
find ui/src -name "*.tsx" -type f | while read f; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 350 ]; then
    echo "$f: $lines lines"
  fi
done
```

---

## Evidence Collection

### Evidence Quality Levels

**High Quality** (Use these):
- Exact code location with line numbers
- Multiple examples from different files
- Direct violation of documented rule

**Medium Quality** (Include):
- Pattern found but location varies
- Similar patterns grouped together
- Inferred from code structure

**Low Quality** (Avoid):
- Single example without context
- Ambiguous pattern matching
- Requires interpretation

### Evidence Format

```markdown
## Evidence

**File: src/services/scheduler/handlers/forecast_handler.py:12**
```python
@task_handler()
class ForecastAnalysisHandler(TaskHandler):
```

**File: src/services/scheduler/handlers/sentiment_handler.py:15**
```python
@task_handler()
class SentimentAnalysisHandler(TaskHandler):
```

**File: src/services/scheduler/handlers/signal_handler.py:18**
```python
@task_handler()
class SignalDetectionHandler(TaskHandler):
```
```

---

## False Positive Prevention

### Mitigation Strategies

1. **Confidence Thresholds**: Only report >70% confidence by default
2. **Multiple Occurrences**: Require 3+ matches before flagging new patterns
3. **Exception Lists**: Known false positives (legacy code, vendor libraries)
4. **Human Review**: Always propose, never auto-commit
5. **Feedback Learning**: Track which recommendations are false positives

### Known False Positives

- Vendored code in `vendor/` or `third_party/` directories
- Test fixtures and mock data
- Generated code files
- Configuration files (JSON, YAML)
- Migration scripts
- Example/sample code


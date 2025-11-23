# Models - src/models/

## Files
| File | Models | Purpose |
|------|--------|---------|
| paper_trading.py | Order, OrderStatus, Portfolio | Trading models |
| market_data.py | MarketData, PriceQuote | Market data |
| claude_agent.py | AgentTask, AgentResponse | Agent models |
| scheduler.py | SchedulerTask, TaskStatus, QueueName | Queue/task models |

## Patterns
```python
# Dataclass (simple)
@dataclass
class Order:
    symbol: str
    quantity: float
    status: OrderStatus

# Enum (fixed values)
class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"

# Pydantic (validation-heavy)
class Portfolio(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
```

## CRITICAL: Data Serialization
```python
# ✅ Storage: json.dumps()
payload_json = json.dumps(payload or {})

# ✅ Deserialization: 3-level fallback
def from_dict(data):
    if isinstance(data.get('payload'), str):
        try:
            data['payload'] = json.loads(payload_str)  # Level 1
        except:
            try:
                data['payload'] = ast.literal_eval(payload_str)  # Level 2
            except:
                data['payload'] = {}  # Level 3
```

## Rules
| Rule | Requirement |
|------|-------------|
| Type hints | Required on all fields |
| Max size | 350 lines per file |
| Domains | One domain per file |
| Business logic | NONE - models only |
| Serialization | json.dumps() ALWAYS (never str()) |


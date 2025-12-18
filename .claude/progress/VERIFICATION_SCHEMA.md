# Verification Metadata Schema

This document describes the verification metadata schema added to feature objects in `feature-list.json`.

## Schema Overview

When a feature is verified by the verifier-agent, a `verification` object is added to the feature:

```json
{
  "id": "PT-003",
  "name": "Morning Autonomous Trading Session",
  "status": "completed",
  "completed_at": "2025-12-09T10:30:00Z",
  "verification": {
    "verified": true,
    "verified_at": "2025-12-17T10:00:00Z",
    "attempts": 1,
    "tests_passed": 15,
    "tests_failed": 0,
    "auto_fixes_applied": 0,
    "playwright_passed": true,
    "verifier_notes": "All tests passed on first attempt"
  }
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `verified` | boolean | Whether the feature passed all verification checks |
| `verified_at` | string (ISO 8601) | Timestamp when verification completed |
| `attempts` | number | Number of verification attempts (includes retries) |
| `tests_passed` | number | Count of tests that passed |
| `tests_failed` | number | Count of tests that failed |
| `auto_fixes_applied` | number | Number of auto-fixes applied during verification |
| `playwright_passed` | boolean | Whether Playwright tests passed (UI features only) |
| `verifier_notes` | string | Human-readable notes about verification |

## Verification Failure Schema

If verification fails after max attempts, the feature is reverted:

```json
{
  "id": "PT-004",
  "status": "in_progress",
  "verification": {
    "verified": false,
    "verified_at": "2025-12-17T10:05:00Z",
    "attempts": 2,
    "tests_passed": 12,
    "tests_failed": 3,
    "auto_fixes_applied": 2,
    "failure_reason": "API test test_evening_session_endpoint failed after auto-fix attempts",
    "error_details": {
      "file": "src/core/coordinators/paper_trading/evening_session_coordinator.py",
      "line": 67,
      "error": "KeyError: 'trades' in payload"
    },
    "suggested_fix": "Add payload.get('trades', []) to handle missing trades key",
    "manual_intervention_required": true
  }
}
```

## Additional Fields for Failed Verification

| Field | Type | Description |
|-------|------|-------------|
| `failure_reason` | string | High-level reason for verification failure |
| `error_details` | object | Specific error information (file, line, error) |
| `suggested_fix` | string | Auto-generated fix suggestion |
| `manual_intervention_required` | boolean | Whether manual fix is needed |

## Verification Process

1. **Feature Completed**: coding-agent marks feature as "completed"
2. **Hook Triggered**: post-feature-verification hook prompts Opus
3. **Verifier Invoked**: Opus delegates to verifier-agent
4. **Verification Runs**:
   - Feature-specific tests
   - API tests
   - Log checks
   - Backend health
   - Playwright tests (UI features)
5. **Auto-Fix (if needed)**: Parse errors and apply fixes
6. **Retry**: Re-run verification after fixes
7. **Result**: Add verification metadata to feature

## Verification Criteria

A feature passes verification if ALL of these are true:

- Feature-specific tests pass
- API tests pass (all endpoints respond correctly)
- No errors in logs/errors.log or logs/critical.log
- Backend health returns 200
- Frontend loads without console errors
- Playwright tests pass (for UI features)

## Usage by verifier-agent

The verifier-agent updates verification metadata automatically:

```python
# Read feature
with open('.claude/progress/feature-list.json') as f:
    data = json.load(f)

# Find feature and add verification
for cat in data['categories'].values():
    for feat in cat['features']:
        if feat['id'] == feature_id:
            feat['verification'] = {
                "verified": True,
                "verified_at": datetime.utcnow().isoformat() + "Z",
                "attempts": 1,
                "tests_passed": 15,
                "tests_failed": 0,
                "auto_fixes_applied": 0,
                "playwright_passed": True,
                "verifier_notes": "All tests passed on first attempt"
            }

# Save
with open('.claude/progress/feature-list.json', 'w') as f:
    json.dump(data, f, indent=2)
```

## Benefits

1. **Transparency**: Clear record of what was verified and how
2. **Traceability**: Know when and how features were validated
3. **Quality Assurance**: Automated checks ensure working code
4. **Progress Tracking**: Easy to see what needs re-verification
5. **Auto-Fix History**: Track automatic fixes applied

## Related Files

- `.claude/progress/verification-log.json` - Complete verification history
- `.claude/progress/auto-fix-history.json` - Auto-fix tracking
- `.claude/scripts/auto-fix-engine.py` - Auto-fix engine
- `.claude/agents/verifier-agent.md` - Verifier agent definition

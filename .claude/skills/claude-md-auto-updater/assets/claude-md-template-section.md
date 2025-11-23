# CLAUDE.md Template Sections

These are templates for common CLAUDE.md sections that the auto-updater will use when recommending changes.

## New Pattern Section Template

```markdown
## [Pattern Name] Pattern

### Overview
[1-2 sentence description of the pattern]

### Usage
[Description of when and how to use this pattern]

### Example
```[language]
[Code example showing correct usage]
```

### Related Patterns
- [Related pattern 1](../CLAUDE.md#related-pattern-1)
- [Related pattern 2](../CLAUDE.md#related-pattern-2)

### Key Points
- [Key point 1]
- [Key point 2]
- [Key point 3]
```

---

## Anti-Pattern Section Template

```markdown
## Anti-Patterns

### ❌ DON'T: [What Not to Do]
[Brief description of why this is wrong]

```[language]
[Code example showing incorrect usage]
```

**Problems**:
- [Problem 1]
- [Problem 2]

### ✅ DO: [What to Do Instead]
[Brief description of why this is correct]

```[language]
[Code example showing correct usage]
```

**Benefits**:
- [Benefit 1]
- [Benefit 2]

### Why This Matters
[Explanation of impact/consequence]
```

---

## Architecture Pattern Section Template

```markdown
## [Component] Architecture

### Overview
[Description of what this component is and its role]

### Responsibilities
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

### Key Rules
- **[Rule Name]**: [Rule description]
- **[Rule Name]**: [Rule description]

### Implementation Example
```[language]
[Code example]
```

### Integration Points
- Connects to [Component A] for [purpose]
- Connects to [Component B] for [purpose]

### Common Mistakes
- ❌ [Mistake 1]
- ❌ [Mistake 2]

### File Reference
- `[file.py]` - [Purpose]
- `[file.py]` - [Purpose]
```

---

## Quick Reference Section Template

```markdown
## Quick Reference

### Commands
```bash
[Common command 1]
[Common command 2]
[Common command 3]
```

### Common Patterns
```[language]
// Pattern 1
[Code]

// Pattern 2
[Code]
```

### Critical Rules
- **[Rule 1]**: [Brief description]
- **[Rule 2]**: [Brief description]

### File Locations
| File | Purpose |
|------|---------|
| `path/to/file.py` | Description |
| `path/to/file.tsx` | Description |
```

---

## Critical Rules Section Template

```markdown
## Critical Rules

**MANDATORY**: These rules must be followed. Violations cause system failures or data loss.

- **[Rule Name]**: [Detailed explanation with consequences of violation]
  - Example: `[code example of correct usage]`

- **[Rule Name]**: [Detailed explanation]
  - **When**: [When this applies]
  - **Why**: [Why this matters]
  - **Exception**: [Any exceptions, or "None" if absolute]
```

---

## Code Example Template

```markdown
### [Pattern/Feature Name]

```[language]
[Working code example]
```

**What this does**:
- [Behavior 1]
- [Behavior 2]

**Key points**:
- [Point 1]
- [Point 2]

**Related**: See [Related Pattern](../CLAUDE.md#related-pattern) for more
```

---

## Integration Points Template

```markdown
## Integration Points

### [Component A] Integration
- **How**: [How this layer connects]
- **Communication**: [Event/API/Direct call]
- **Data Flow**: [What data flows between them]
- **Example**: [Code example of interaction]

### [Component B] Integration
- **How**: [How this layer connects]
- **Communication**: [Event/API/Direct call]
- **Data Flow**: [What data flows between them]
```

---

## Testing Guidelines Section Template

```markdown
## Testing Guidelines

### Unit Testing
- **Framework**: [pytest/jest/etc]
- **Pattern**: [One test per service/coordinator]
- **Coverage Target**: 80%+ on domain logic

**Example**:
```[language]
[Test code example]
```

### Integration Testing
- **Scope**: [What to integration test]
- **Approach**: [How to test integrations]
- **Verification**: [What to verify]

### Common Test Patterns
- [Pattern 1]
- [Pattern 2]
```

---

## Troubleshooting Section Template

```markdown
## Common Issues & Quick Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| [Symptom] | [Why it happens] | [How to fix it] |
| [Symptom] | [Why it happens] | [How to fix it] |
| [Symptom] | [Why it happens] | [How to fix it] |

### [Specific Issue Name]

**Symptom**: [How the issue manifests]

**Root Cause**: [Why this happens]

**Solution**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Prevention**: [How to avoid in future]
```

---

## Guidelines Section Template

```markdown
## Guidelines

### DO ✅
- [Guideline 1]
- [Guideline 2]
- [Guideline 3]

### DON'T ❌
- [Anti-guideline 1]
- [Anti-guideline 2]
- [Anti-guideline 3]

### Rationale
[Explanation of why these guidelines exist]

### Examples
```[language]
// DO
[Good example]

// DON'T
[Bad example]
```
```

---

## Migration Notes Section Template

```markdown
## Migration Notes

### What Changed
[Description of what changed]

### Why
[Rationale for the change]

### Migration Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Backward Compatibility
- [Status: Breaking/Backward compatible/Deprecated]
- [Deprecation timeline if applicable]

### Updated Examples
**Before**:
```[language]
[Old code]
```

**After**:
```[language]
[New code]
```
```

---

## File Reference Section Template

```markdown
## File Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `path/to/file.py` | [Description] | `ClassName`, `function_name()` |
| `path/to/file.py` | [Description] | `ClassName`, `function_name()` |

### Key Files

#### `src/services/portfolio_service.py`
- **Purpose**: Portfolio operations and calculations
- **Key Classes**: `PortfolioService`, `PortfolioCalculator`
- **Key Methods**: `update_position()`, `calculate_metrics()`
- **Uses**: `EventBus`, `DatabaseConnection`

#### `src/core/coordinators/portfolio_coordinator.py`
- **Purpose**: Orchestrates portfolio operations
- **Key Class**: `PortfolioCoordinator(BaseCoordinator)`
- **Responsibilities**: Coordinate between services and database
```

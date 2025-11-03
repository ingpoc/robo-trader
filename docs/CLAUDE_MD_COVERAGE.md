# CLAUDE.md File Coverage

## Overview

This document tracks CLAUDE.md file coverage across the codebase. Each directory with significant functionality should have a CLAUDE.md file specifying its purpose, patterns, and best practices.

## Coverage Status

### ✅ Complete Coverage

All major directories now have CLAUDE.md files with comprehensive guidelines:

| Directory | Purpose | CLAUDE.md Status |
|-----------|---------|------------------|
| **Root** | Project-wide guidelines | ✅ `CLAUDE.md` |
| **src/** | Backend architecture guidelines | ✅ `src/CLAUDE.md` |
| **src/core/** | Core infrastructure guidelines | ✅ `src/core/CLAUDE.md` |
| **src/core/coordinators/** | Coordinator organization | ✅ Subdirectories have CLAUDE.md |
| **src/core/coordinators/status/** | Status coordination | ✅ `src/core/coordinators/status/CLAUDE.md` |
| **src/core/coordinators/queue/** | Queue management | ✅ `src/core/coordinators/queue/CLAUDE.md` |
| **src/core/coordinators/task/** | Task management | ✅ `src/core/coordinators/task/CLAUDE.md` |
| **src/core/coordinators/message/** | Message routing | ✅ `src/core/coordinators/message/CLAUDE.md` |
| **src/core/coordinators/broadcast/** | Broadcast operations | ✅ `src/core/coordinators/broadcast/CLAUDE.md` |
| **src/core/coordinators/agent/** | Agent coordination | ✅ `src/core/coordinators/agent/CLAUDE.md` |
| **src/core/coordinators/core/** | Core system coordinators | ✅ `src/core/coordinators/core/CLAUDE.md` |
| **src/core/background_scheduler/** | Background task processing | ✅ `src/core/background_scheduler/CLAUDE.md` |
| **src/core/database_state/** | Database state management | ✅ `src/core/database_state/CLAUDE.md` |
| **src/services/** | Service layer guidelines | ✅ `src/services/CLAUDE.md` |
| **src/web/** | Web layer guidelines | ✅ `src/web/CLAUDE.md` |
| **src/web/routes/** | API route handlers | ✅ `src/web/routes/CLAUDE.md` |
| **src/web/utils/** | Web utilities | ✅ `src/web/utils/CLAUDE.md` |
| **src/agents/** | Multi-agent system | ✅ `src/agents/CLAUDE.md` |
| **src/auth/** | Authentication | ✅ `src/auth/CLAUDE.md` |
| **src/models/** | Data models | ✅ `src/models/CLAUDE.md` |
| **src/mcp/** | Model Context Protocol | ✅ `src/mcp/CLAUDE.md` |
| **src/stores/** | Data stores | ✅ `src/stores/CLAUDE.md` |
| **ui/src/** | Frontend guidelines | ✅ `ui/src/CLAUDE.md` |

## CLAUDE.md File Structure

Each CLAUDE.md file follows this structure:

1. **Purpose Section**: Clear statement of directory purpose
2. **Architecture Pattern**: Patterns used in this directory
3. **Rules Section**: ✅ DO and ❌ DON'T guidelines
4. **Implementation Patterns**: Code examples showing best practices
5. **Best Practices**: Additional recommendations
6. **Dependencies**: What this directory depends on

## Key Principles

### 1. Clear Purpose

Each CLAUDE.md file starts with a clear statement of the directory's purpose:

```markdown
## Purpose

The `directory_name/` directory contains [specific purpose]...
```

### 2. Pattern Documentation

Each file documents the architectural patterns used:

```markdown
## Architecture Pattern

### Pattern Name

Description of pattern...

### Directory Structure

[Directory tree if applicable]
```

### 3. Rules and Guidelines

Each file includes clear rules:

```markdown
## Rules

### ✅ DO
- Clear actionable rules

### ❌ DON'T
- Clear anti-patterns to avoid
```

### 4. Code Examples

Each file includes implementation examples:

```markdown
## Implementation Pattern

```python
# Example code showing best practices
```
```

### 5. Best Practices

Each file concludes with best practices:

```markdown
## Best Practices

1. First best practice
2. Second best practice
...
```

## Directory Organization

### Coordinator Subdirectories

All coordinator subdirectories are organized by domain:
- `status/` - Status coordination
- `queue/` - Queue management
- `task/` - Task management
- `message/` - Message routing
- `broadcast/` - Broadcast operations
- `agent/` - Agent coordination
- `core/` - Core system coordinators

Each has a focused CLAUDE.md file explaining:
- Domain-specific patterns
- Orchestrator + focused coordinator architecture
- Implementation examples
- Best practices

## Maintenance

### When to Update CLAUDE.md

1. **New Pattern Introduced**: Document new patterns
2. **Directory Purpose Changes**: Update purpose statement
3. **Best Practice Evolves**: Update best practices section
4. **New File Added**: Update directory structure if needed

### Review Checklist

When reviewing CLAUDE.md files:
- [ ] Purpose is clearly stated
- [ ] Patterns are documented with examples
- [ ] Rules are clear and actionable
- [ ] Code examples are accurate
- [ ] Best practices are up to date
- [ ] Dependencies are listed

## File Count Summary

- **Total CLAUDE.md Files**: 20
- **Root Level**: 1
- **Backend Directories**: 18
- **Frontend Directories**: 1

## Benefits

1. **Clear Guidance**: Each directory has clear purpose and patterns
2. **Consistency**: Consistent patterns across the codebase
3. **Onboarding**: New developers can understand structure quickly
4. **Maintainability**: Patterns documented for future reference
5. **Best Practices**: Best practices captured in one place per domain


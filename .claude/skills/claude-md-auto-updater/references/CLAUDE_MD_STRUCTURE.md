# CLAUDE.md File Structure Reference

> **Purpose**: Reference for CLAUDE.md organization, structure, and metadata conventions
> **Last Updated**: 2025-11-09

## File Organization

### Root Level Files

#### `CLAUDE.md` (Project Root)
- **Purpose**: Comprehensive project-wide architecture guide
- **Length**: 500-2000+ lines (comprehensive)
- **Audience**: All team members, onboarding developers
- **Sections**: Overview, architecture, quick start, patterns, guidelines, troubleshooting

**Typical Structure**:
```markdown
# CLAUDE.md

> **Last Updated**: YYYY-MM-DD | **Status**: Production Ready | **Tier**: Reference

## Project Overview
[1-2 sentence project summary]

## Quick Start Commands
[Common commands organized by task]

## Architecture Overview
[High-level architecture explanation]

### Core Architecture Pattern
[Main architectural decisions]

## Key File Locations
[Table of important files and their purposes]

## Development Workflow
[Before/after coding guidelines]

## Code Quality Standards
[Modularization, async, error handling, testing]

## Common Issues & Quick Fixes
[Troubleshooting guide]

## When in Doubt
[Decision-making framework]
```

#### `.claude/CLAUDE.md` (Quick Reference)
- **Purpose**: Concise quick reference for developers
- **Length**: 50-100 lines (strict)
- **Audience**: Developers in active work
- **Token-aware**: Must be lean (prepended to every prompt)
- **Content**: Essential rules only, no verbose explanations

**Typical Structure**:
```markdown
# Claude Code Guidelines

> **Last Updated**: YYYY-MM-DD | **Status**: Active | **Tier**: Reference

## Core Principles
- [Principle 1]
- [Principle 2]
- [Principle 3]

## Critical Constraints
- **[Constraint]**: [Brief description]

## [Domain Area]
- [Rule]
- [Rule]
```

### Layer-Specific Files

#### `src/CLAUDE.md` (Backend Layer)
- **Purpose**: Backend architecture and patterns
- **Length**: 300-500 lines
- **Scope**: All Python backend code in `src/`
- **Applies After**: Reading root `CLAUDE.md`

#### `src/core/CLAUDE.md` (Core Infrastructure)
- **Purpose**: Core infrastructure patterns
- **Length**: 200-400 lines
- **Scope**: DI, coordinators, event bus, queues
- **Applies After**: Reading `src/CLAUDE.md`

#### `src/services/CLAUDE.md` (Service Layer)
- **Purpose**: Service implementation patterns
- **Length**: 200-300 lines
- **Scope**: Services, business logic, event emission
- **Applies After**: Reading `src/CLAUDE.md`

#### `src/web/CLAUDE.md` (API/Web Layer)
- **Purpose**: API endpoints, route handlers
- **Length**: 150-250 lines
- **Scope**: FastAPI routes, request/response handling
- **Applies After**: Reading `src/CLAUDE.md`

#### `ui/src/CLAUDE.md` (Frontend Layer)
- **Purpose**: React/TypeScript frontend patterns
- **Length**: 250-400 lines
- **Scope**: Components, hooks, state management
- **Applies After**: Reading root `CLAUDE.md`

#### `ui/src/features/[feature]/CLAUDE.md` (Optional Feature)
- **Purpose**: Feature-specific patterns (if needed)
- **Length**: 100-200 lines
- **Scope**: Single feature implementation
- **Applies After**: Reading `ui/src/CLAUDE.md`

## Metadata Format

### Required Header (All Files)
```markdown
# [Title - Component/Module Name]

> **Last Updated**: YYYY-MM-DD | **Status**: [Active|Deprecated|Archived] | **Tier**: [Reference|Quick-Start|Guide]
```

**Fields**:
- `Last Updated`: ISO date when file was last modified
- `Status`: Current maintenance status
  - `Active`: File is current and used
  - `Deprecated`: File exists but outdated (will be removed)
  - `Archived`: File is historical reference only
- `Tier`: Importance level
  - `Reference`: Comprehensive guide
  - `Quick-Start`: Quick reference only
  - `Guide`: Procedural documentation

### Optional Metadata (Layer-Specific)
```markdown
> **Scope**: Applies to [directory path]. Read after [parent CLAUDE.md] for context.
>
> **Read in this order**:
> 1. [Parent CLAUDE.md] - [Context]
> 2. This file - [This layer's focus]
> 3. [Child CLAUDE.md] - [Next layer]
```

## Section Types and Standards

### Standard Sections (Appear in Most Files)

#### 1. Overview / Purpose
- **Length**: 2-4 sentences
- **Purpose**: Explain what this file covers
- **Required**: Yes (always first content section)

#### 2. Core Principles / Critical Rules
- **Format**: Bullet list
- **Length**: 3-5 items
- **Markers**: Use "CRITICAL" or "MANDATORY" for important rules
- **Required**: Yes (always second section)

#### 3. Architecture Patterns / Architecture Overview
- **Format**: Narrative explanation with structure details
- **Length**: 2-5 paragraphs
- **Subsections**: Allowed for different pattern types
- **Optional**: For most files

#### 4. Code Patterns
- **Format**: Code examples showing correct usage
- **Length**: 5-15 lines per example
- **Language**: Match the layer (Python for backend, TypeScript for frontend)
- **Required**: For layer-specific files (not for quick reference)

#### 5. Anti-Patterns
- **Format**: Two-column: ❌ DON'T vs. ✅ DO
- **Length**: 2-5 examples
- **Purpose**: Show what NOT to do with correction
- **Required**: For layer-specific files

#### 6. Common Commands / Quick Reference
- **Format**: Code blocks with bash/npm commands
- **Length**: 5-10 lines
- **Organization**: By task or workflow
- **Optional**: Helpful for developer speed

#### 7. File Reference / Key Locations
- **Format**: Table or bullet list with descriptions
- **Length**: 5-20 items
- **Content**: Important files and their purposes
- **Optional**: For larger layers

#### 8. Integration Points / Dependency Rules
- **Format**: Description of how layer connects to others
- **Length**: 3-5 bullet points
- **Optional**: For interdependent layers

#### 9. Testing Guidelines / Testing Requirements
- **Format**: Bullet points or code examples
- **Length**: 5-10 lines
- **Optional**: For complex patterns

#### 10. Common Issues & Troubleshooting
- **Format**: Problem → Root Cause → Solution table
- **Length**: 5-10 issues
- **Optional**: For commonly misunderstood areas

### Section Naming Conventions

✅ **GOOD** (Clear, specific, actionable):
- `Critical Rules`
- `Architecture Patterns`
- `Database Access Patterns`
- `Queue Handler Implementation`
- `Component Organization`
- `Anti-Patterns`
- `Common Mistakes`

❌ **BAD** (Vague, verbose, unclear):
- `Information`
- `Details`
- `Notes`
- `Miscellaneous Guidelines`
- `Things to Know`

## Content Guidelines

### DO ✅
- Use short, declarative bullet points
- Include code examples for patterns (especially layer-specific files)
- Reference related CLAUDE.md files by path
- Update "Last Updated" date when modifying
- Keep quick reference files <60 lines
- Use clear section headers
- Include "CRITICAL" or "MANDATORY" labels for important rules
- Provide file:line references when discussing specific code
- Link to parent/child CLAUDE.md files
- Use consistent formatting across files

### DON'T ❌
- Write long narrative paragraphs (use bullets instead)
- Include redundant information (cross-reference instead)
- State the obvious (e.g., "components folder contains components")
- Add commentary or nice-to-have information
- Duplicate content from parent CLAUDE.md files
- Include entire product requirement documents (link instead)
- Use verbose explanations when a bullet point suffices
- Include historical changelog (use Git history instead)
- Expose implementation details (focus on patterns/constraints)
- Include personal preferences (keep file objective)

## Markdown Formatting Standards

### Headings
```markdown
# H1 - Page Title Only
## H2 - Main Sections
### H3 - Subsections
#### H4 - Details (avoid if possible)
```

### Emphasis
- **Bold** for key terms and rule names
- `Code` for file paths, class names, function names
- _Italic_ rarely (only for clarification)

### Lists
- Bullet lists for collections
- Numbered lists only for step-by-step procedures
- Use consistent indentation (2 spaces)

### Code Examples
````markdown
```python
# Python code example
```

```typescript
// TypeScript code example
```

```bash
# Bash command example
```
````

### Tables
Use for comparison data, reference lists:
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data     | Data     | Data     |
```

### Links
- Use relative paths for internal CLAUDE.md files: `[src/CLAUDE.md](../src/CLAUDE.md)`
- Use absolute URLs for external references
- Use descriptive link text: `[Database patterns](../src/CLAUDE.md#database-patterns)`

## Consistency Across Files

### Metadata Consistency
- All files must have header with Last Updated, Status, Tier
- Status values must be: Active, Deprecated, or Archived
- Tier values must be: Reference, Quick-Start, or Guide

### Cross-File References
- Parent files should mention child files in overview
- Child files should reference parent file in scope section
- Links should use relative paths

### Rule Consistency
- No contradicting rules across CLAUDE.md files
- Critical rules only stated once (in most specific file)
- General rules in root, specific rules in layer-specific files

### Formatting Consistency
- Use same heading levels for same concept types
- Use consistent code block languages
- Use consistent emphasis (bold for rule names, etc.)

## Detection for Auto-Updates

### Signs a File Needs Updates

1. **Metadata out of date**: Last Updated is >3 months old
2. **Broken links**: References to deleted files or outdated sections
3. **Missing child references**: New CLAUDE.md files not mentioned in parent
4. **Code examples don't work**: Examples reference non-existent functions/classes
5. **Documented patterns don't exist**: Patterns no longer used in codebase
6. **Undocumented patterns**: New patterns in code not in documentation
7. **Inconsistent rules**: Same constraint stated differently in multiple files
8. **Length violations**: File exceeds recommended line counts

### Signs a File is Healthy

- Last Updated within 30 days
- All referenced files exist
- Code examples work/parse correctly
- Documented patterns match actual code usage
- No contradictions across files
- Proper metadata header
- Clear section organization
- Balanced length for file type

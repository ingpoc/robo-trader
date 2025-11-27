# Progress Tracking Directory

This directory contains progress tracking files for the Two-Agent Architecture pattern. These files enable systematic session restoration and context maintenance across multi-session development.

## Directory Structure

```
.claude/progress/
├── README.md                      # This file
├── .gitkeep                       # Ensures directory is tracked in git
├── feature-list.schema.json       # JSON Schema for validating feature-list.json
├── session-state.schema.json      # JSON Schema for validating session-state.json
├── progress-template.txt          # Template for claude-progress.txt
├── feature-list.json              # (Generated) Comprehensive feature tracking
├── claude-progress.txt            # (Generated) Human-readable progress summary
└── session-state.json             # (Generated) Session metadata and heartbeat
```

## Files Overview

### Schema Files (Static)

**feature-list.schema.json**
- Validates the structure of feature-list.json
- Ensures all required fields are present
- Validates feature IDs, dependencies, and status values
- Used by Initializer Agent during feature list creation

**session-state.schema.json**
- Validates the structure of session-state.json
- Ensures heartbeat mechanism is properly configured
- Validates session metrics and activity tracking
- Used by Coding Agent during session state updates

**progress-template.txt**
- Template for generating claude-progress.txt
- Contains placeholders for dynamic content
- Used by Initializer Agent to create initial progress file

### Generated Files (Dynamic)

**feature-list.json**
- Created by: Initializer Agent
- Updated by: Coding Agent (after each feature completion)
- Contains: Complete feature list with dependencies, tests, and status
- Format: JSON (validated against feature-list.schema.json)

**claude-progress.txt**
- Created by: Initializer Agent
- Updated by: Coding Agent (after each feature completion)
- Contains: Human-readable progress summary with visual progress bars
- Format: Plain text with ANSI-style formatting

**session-state.json**
- Created by: Initializer Agent
- Updated by: Coding Agent (throughout session)
- Contains: Session metadata, heartbeat, abnormal exit detection
- Format: JSON (validated against session-state.schema.json)

## Usage

### For Initializer Agent

When user provides a task prompt:
1. Read `progress-template.txt` for structure
2. Generate `feature-list.json` (validate with schema)
3. Generate `claude-progress.txt` (using template)
4. Generate `session-state.json` (validate with schema)

### For Coding Agent

At start of each session:
1. Read `feature-list.json` (validate with schema)
2. Read `claude-progress.txt` (check for blockers/warnings)
3. Read `session-state.json` (detect abnormal exits)
4. Verify git history and test state
5. Begin implementation

After each feature completion:
1. Update `feature-list.json` (mark feature completed, add commit SHA)
2. Update `claude-progress.txt` (add to recent activity)
3. Update `session-state.json` (update metrics, heartbeat)

## Validation

Validate generated files using JSON Schema:

```bash
# Install JSON Schema validator
npm install -g ajv-cli

# Validate feature-list.json
ajv validate -s .claude/progress/feature-list.schema.json -d .claude/progress/feature-list.json

# Validate session-state.json
ajv validate -s .claude/progress/session-state.schema.json -d .claude/progress/session-state.json
```

## Git Tracking

**Tracked Files**:
- `.gitkeep` (ensures directory exists)
- `feature-list.schema.json`
- `session-state.schema.json`
- `progress-template.txt`
- `README.md`

**Ignored Files** (add to .gitignore if desired):
- `feature-list.json` (project-specific, can be tracked or ignored)
- `claude-progress.txt` (generated summary, usually ignored)
- `session-state.json` (session-specific, should be ignored)

## Best Practices

1. **Never manually edit generated files** - Let agents update them
2. **Validate after updates** - Use JSON Schema validators
3. **Backup before major changes** - Copy generated files before refactoring
4. **Review progress regularly** - Check claude-progress.txt for warnings/blockers
5. **Clean up on completion** - Archive or delete generated files after project completion

## Troubleshooting

**Problem**: feature-list.json validation fails
**Solution**: Check for:
- Missing required fields
- Invalid feature ID format (must be `CATEGORY-NUMBER`)
- Circular dependencies
- Invalid status values

**Problem**: session-state.json shows abnormal exit
**Solution**:
- Check for uncommitted changes
- Verify last feature status in feature-list.json
- Review git history for unexpected commits
- Run Coding Agent's recovery protocol

**Problem**: claude-progress.txt shows warnings
**Solution**:
- Fix test failures before new work
- Address blockers (external dependencies, missing API keys, etc.)
- Update feature dependencies if blocked features are ready

## Integration with Robo-Trader

Progress tracking integrates with robo-trader's existing infrastructure:

**Coordinator Pattern**:
- Features respect max 150 lines per coordinator
- Progress tracking follows orchestrator + focused coordinator pattern

**Event Bus**:
- Progress updates can emit events via EventBus
- Status changes published as `PROGRESS_UPDATED` events

**MCP Server**:
- robo-trader-dev MCP can read progress files
- Use MCP tools to query feature status, blockers, next steps

**Testing**:
- Progress tracking enforces test-first approach
- Test status checked before marking features complete
- Playwright integration for E2E testing

## Version History

- v1.0.0 (2025-01-27): Initial implementation of Two-Agent Architecture
  - Added feature-list.schema.json
  - Added session-state.schema.json
  - Added progress-template.txt
  - Added README.md

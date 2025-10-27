# Robo Trader Documentation

This directory contains all documentation for the Robo Trader project. AI agents should reference these documents to understand system architecture, development workflows, and implementation guidelines.

## System Overview

Robo Trader is a Claude AI-powered paper trading system that enables autonomous trade execution via the Claude Agent SDK. The system features a multi-agent architecture with risk management, strategy learning, and performance tracking.

## Essential Documentation for AI Agents

### Core Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, components, and design patterns
- **[CLAUDE_SDK_SETUP_GUIDE.md](CLAUDE_SDK_SETUP_GUIDE.md)** - Complete guide to Claude SDK setup and usage
- **[API.md](API.md)** - API reference documentation with all endpoints and examples

### Development Documentation

- **[ASYNC_PATTERNS_CHEATSHEET.md](ASYNC_PATTERNS_CHEATSHEET.md)** - Quick reference for async/await patterns
- **[UI-workflow.md](UI-workflow.md)** - Full-stack development workflow guidelines

### Implementation Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for the UI
- **[ZERODHA_OAUTH_SETUP.md](ZERODHA_OAUTH_SETUP.md)** - Zerodha integration guide
- **[security.md](security.md)** - Security guidelines and best practices

## System Components

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **Core Layer** | Infrastructure, service coordination, event management | `src/core/` |
| **Services** | Business logic for trading, analysis, risk management | `src/services/` |
| **Agents** | Multi-agent coordination for trading operations | `src/agents/` |
| **Web UI** | React-based frontend with real-time updates | `ui/` |

## Key Architectural Patterns

- **Coordinator Pattern**: Thin facade delegating to focused coordinators
- **Event-Driven Architecture**: Internal event bus for loose coupling
- **Dependency Injection**: Centralized service lifecycle management
- **SDK-Only Architecture**: Claude Agent SDK for all AI functionality

## Common Implementation Tasks for AI Agents

### Adding New Features
1. Review **[ARCHITECTURE.md](ARCHITECTURE.md)** for component responsibilities
2. Follow **[UI-workflow.md](UI-workflow.md)** for development process
3. Use **[ASYNC_PATTERNS_CHEATSHEET.md](ASYNC_PATTERNS_CHEATSHEET.md)** for async implementation

### Claude SDK Integration
1. Reference **[CLAUDE_SDK_SETUP_GUIDE.md](CLAUDE_SDK_SETUP_GUIDE.md)** for authentication
2. Check **[API.md](API.md)** for existing tools and endpoints

### Security Implementation
1. Always review **[security.md](security.md)** before implementation
2. Ensure API keys are only stored in environment variables
3. Verify error handling doesn't expose sensitive information

## Getting Started

1. Review the system overview in **[ARCHITECTURE.md](ARCHITECTURE.md)**
2. Follow **[CLAUDE_SDK_SETUP_GUIDE.md](CLAUDE_SDK_SETUP_GUIDE.md)** to set up authentication
3. Check the **[QUICKSTART.md](QUICKSTART.md)** to get the UI running
4. Read **[UI-workflow.md](UI-workflow.md)** for full-stack development guidelines

## Additional Resources

- **Project Memory**: `[ROOT]/CLAUDE.md` - Permanent development rules and patterns
- **Main Documentation**: `[ROOT]/README.md` - Comprehensive project overview

## Implementation Guidelines for AI Agents

1. **Always follow security best practices** outlined in security.md
2. **Use async patterns** as documented in ASYNC_PATTERNS_CHEATSHEET.md
3. **Leverage Claude SDK** for all AI functionality as per CLAUDE_SDK_SETUP_GUIDE.md
4. **Follow the coordinator pattern** for service orchestration as per ARCHITECTURE.md
5. **Implement comprehensive testing** for all new features as per UI-workflow.md


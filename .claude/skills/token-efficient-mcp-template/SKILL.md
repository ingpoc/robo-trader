---
name: token-efficient-mcp-template
version: 1.0.0
description: This skill should be used when creating MCP servers for Claude Code CLI that need token efficiency, implementing progressive disclosure patterns, or reducing MCP tool context from 26K to 2-3K tokens. Achieves 85-90% token reduction through discovery-only tools pattern. Use when building custom MCP servers, optimizing existing servers, or debugging Claude Code token exhaustion.
---

# Token-Efficient MCP & Hook System Template

## Overview

Transform any web application into a token-efficient ecosystem with smart MCP server tools and sophisticated hook systems. Provides 95%+ token reduction through intelligent caching, progressive context loading, and optimized tool discovery patterns.

## Quick Start

**Initialize new project ecosystem:**
```bash
# Run the initialization script
python scripts/init_template.py --project-type {react|fastapi|django|node} --name my-project
```

**Generate specific components:**
- Hook system: `python scripts/generate_hooks.py --type {pre-tool|context|session}`
- MCP server: `python scripts/setup_mcp_server.py --categories {logs,system,database}`
- Caching: `python scripts/configure_caching.py --strategy {smart|progressive|differential}`

## Core Capabilities

### 1. Hook System Generation

Create sophisticated hook systems that provide real-time tool guidance and token efficiency nudges.

**Pre-Tool-Use Hooks:**
- Analyze tool usage patterns before execution
- Suggest token-efficient alternatives (95-99% savings)
- Validate tool parameters and security constraints
- Provide context-aware recommendations

**Context Injection Hooks:**
- Progressive context loading (summary → targeted → full)
- Session state management and tracking
- Dependency resolution and caching
- Background refresh mechanisms

**Session Management Hooks:**
- Timeout protection and resource limits
- Background task coordination
- Health monitoring and validation
- Graceful error handling and recovery

### 2. MCP Server Architecture

Bootstrap production-ready MCP servers with modular tool categories and intelligent caching.

**CRITICAL: Progressive Disclosure in Claude Code**
- Claude Code does NOT respect `defer_loading` parameter in Tool definitions
- `.mcp.json` toolset configurations don't work for progressive disclosure
- **Solution**: Only return 3 discovery tools from `list_tools()`, keep others callable
- Other tools discovered via `search_tools`, `list_directories`, `read_file`
- Achieves 85-90% token reduction (3 tools vs 25 tools loaded upfront)

**Tool Categories:**
- **logs**: Error pattern analysis, log aggregation, troubleshooting
- **system**: Health monitoring, performance metrics, status checks
- **database**: Query optimization, connection management, backup verification
- **performance**: Real-time monitoring, resource tracking, bottleneck detection
- **execution**: Sandboxed code execution, data transformation, analysis
- **optimization**: Token efficiency, cache management, progressive disclosure

**Built-in Features:**
- Smart caching with configurable TTLs
- Server-side progressive disclosure (not API defer_loading)
- Background refresh strategies
- Token usage optimization
- Security sandboxing

### 3. Token Efficiency Framework

Implement proven patterns for dramatic token reduction without sacrificing functionality.

**Smart Caching Strategies:**
- Differential analysis (99% token reduction)
- Context-aware summarization
- Intelligent cache invalidation
- Background refresh for stale data

**Progressive Context Loading:**
- Summary mode (150 tokens)
- Targeted mode (800 tokens)
- Full context (complete file/data)
- Automatic level selection based on user intent

**Optimization Patterns:**
- Query result aggregation
- Batch processing for multiple operations
- Compression of repetitive data
- Smart prefetching based on usage patterns

## Project Templates

### React/FastAPI Template
```bash
python scripts/init_template.py --project-type react-fastapi --name my-app
```
- Frontend-backend tool integration
- WebSocket real-time updates
- API endpoint monitoring
- Component-level performance tracking

### Django Analytics Template
```bash
python scripts/init_template.py --project-type django-analytics --name dashboard
```
- Database query optimization
- Admin panel integration
- User activity tracking
- Report generation tools

### Node.js Microservices Template
```bash
python scripts/init_template.py --project-type node-microservices --name services
```
- Service health monitoring
- Inter-service communication tracking
- Load balancing metrics
- Distributed tracing tools

## Resources

### scripts/
Executable automation scripts for template generation and project setup.

**Core Scripts:**
- `init_template.py` - Initialize complete project ecosystem
- `generate_hooks.py` - Generate hook system components
- `setup_mcp_server.py` - Create MCP server with tool categories
- `configure_caching.py` - Set up token efficiency strategies
- `health_check.py` - Validate system connectivity and health

**Usage Example:**
```bash
# Initialize React/FastAPI project with full ecosystem
python scripts/init_template.py \
  --project-type react-fastapi \
  --name my-ecommerce-app \
  --include-mcp-server \
  --include-hooks \
  --caching-strategy smart
```

### references/
Comprehensive documentation and implementation guides.

**Key References:**
- `hook_patterns.md` - Hook implementation best practices and patterns
- `mcp_design_guide.md` - MCP server architecture and design principles
- `token_optimization.md` - Caching strategies and token efficiency techniques
- `security_guide.md` - Sandbox configurations and security best practices
- `integration_examples.md` - Detailed integration examples for different stacks

**Reference Usage:**
- Load specific references when implementing custom components
- Consult design guides for architectural decisions
- Use examples as templates for project-specific customizations

### assets/
Template files and configurations for different project types.

**Template Categories:**
- `hook_templates/` - Hook system templates for different environments
- `mcp_templates/` - MCP server tool definitions and schemas
- `config_templates/` - YAML configurations for different stacks
- `docker_templates/` - Container configurations and deployment scripts

**Asset Usage:**
- Copy templates directly to new projects
- Customize configurations for specific requirements
- Use as starting points for custom implementations

## Implementation Workflow

### Phase 1: Project Analysis
1. Identify project type and requirements
2. Determine needed tool categories
3. Select caching and optimization strategies
4. Configure security and performance parameters

### Phase 2: Template Generation
1. Run initialization script with project parameters
2. Generate hook system components
3. Set up MCP server with selected tools
4. Configure caching and optimization strategies

### Phase 3: Customization
1. Adapt templates to project-specific needs
2. Configure tool parameters and security settings
3. Set up monitoring and health checks
4. Test integration and validate functionality

### Phase 4: Deployment
1. Configure deployment environments
2. Set up monitoring and alerting
3. Validate performance and token efficiency
4. Document customizations and usage patterns

## Best Practices

**Token Efficiency:**
- Always use progressive context loading for large files
- Implement smart caching with appropriate TTLs
- Use differential analysis for change detection
- Batch operations when possible

**Progressive Disclosure (Claude Code):**
```python
@server.list_tools()
async def list_tools() -> List[Tool]:
    """Only return discovery tools - others callable but not advertised."""
    return [
        Tool(name="list_directories", description="Browse categories",
             inputSchema=ListDirectoriesInput.model_json_schema()),
        Tool(name="search_tools", description="Search by keyword",
             inputSchema=SearchToolsInput.model_json_schema()),
        Tool(name="read_file", description="Read tool definitions",
             inputSchema=ReadFileInput.model_json_schema())
    ]
    # Other 20+ tools remain in call_tool() handler - fully callable
```

### Edge Cases

**More than 3 tool categories:**

- Use nested naming: `list_portfolio_tools`, `list_analysis_tools`, `list_system_tools`
- Each discovery tool can return 5-10 tools in its category
- Total context still <5K tokens with 30+ tools available

**When NOT to use this pattern:**

- Interactive MCP servers with user-facing UIs (all tools should be visible)
- Servers with <10 total tools (overhead not worth it)
- When every tool must be visible in every context (rare)
- API integrations expecting full tool list upfront

**Multiple MCP servers:**

- Each server implements its own progressive disclosure
- Claude Code loads discovery tools from all servers (~2-3K per server)
- Total context = (3 tools × number of servers) × ~800 tokens

**Security:**
- Configure sandboxing for code execution
- Implement proper authentication and authorization
- Use environment-specific configurations
- Regular security audits and updates

**Performance:**
- Monitor token usage and optimize patterns
- Use background refresh for stale data
- Implement proper error handling and recovery
- Regular performance validation and tuning

## Performance Metrics (robo-trader-dev Example)

| Scenario | Before | After | Reduction |
|----------|--------|-------|-----------|
| Initial load | 26.6K tokens | 2-3K tokens | 88-90% |
| Tool discovery | N/A | ~500 tokens | On-demand |
| Follow-up calls | 26.6K tokens | ~500 tokens | 98%+ |

**Calculation**:
- All tools listed: 25 tools × ~1K tokens = 26.6K tokens
- Discovery only: 3 tools × ~800 tokens = 2.4K tokens
- Cached results: Differential updates = ~100-500 tokens

## MCP Configuration

**File**: `.mcp.json` (project root)

```json
{
  "mcpServers": {
    "robo-trader-dev": {
      "command": "/path/to/start_mcp_server.sh",
      "args": []
    }
  }
}
```

**Key Points**:

- Simple command/args format (no toolset config needed)
- Progressive disclosure handled server-side in `list_tools()`
- Environment variables in startup script if needed

## See Also

- **plugin-dev:hook-development** - Use hooks to trigger MCP tools efficiently
- **plugin-dev:agent-development** - Integrate MCP servers with custom agents
- **mcp-builder** - Create new MCP servers from scratch

---

This skill transforms the sophisticated patterns from production systems into reusable templates, enabling any developer to create token-efficient tool ecosystems with minimal effort and maximum impact.

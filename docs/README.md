# Robo Trader Docs

This directory holds the repo-local operating contract for Robo Trader.

## Product Reality

Robo Trader is a paper-trading-first swing-trading operator console. The current product is centered on:

- paper-trading execution truth
- operator-visible capabilities and blockers
- Claude-assisted research, decision support, and review
- system-health and configuration surfaces that serve the paper-trading loop

It is not a generic multi-agent platform and it does not make an active claim of production-ready live trading.

## Start Here

- [Mission](reference/MISSION.md)
- [Repo Scope](reference/REPO-SCOPE.md)
- [Roadmap](../ROADMAP.md)
- [Mission-Cut ADR](adrs/0001-mission-cut-paper-trading-core.md)

## Workflow Docs

- [Repo Governance](workflow/repo-governance.md)
- [Research Validation Loop](workflow/research-validation-loop.md)
- [Browser Testing Control Plane](workflow/browser-testing-control-plane.md)
- [Git Governance Control Plane](workflow/git-governance-control-plane.md)
- [Linear Issue Control Plane](workflow/linear-issue-control-plane.md)
- [Notion Memory Control Plane](workflow/notion-memory-control-plane.md)
- [MCP/Auth Bootstrap](workflow/mcp-auth-bootstrap.md)

## Supporting Docs

- [Quickstart](QUICKSTART.md)
- [Zerodha OAuth Setup](ZERODHA_OAUTH_SETUP.md)
- [Claude SDK Setup Guide](CLAUDE_SDK_SETUP_GUIDE.md)
- [Security](security.md)

Use older architecture and historical notes only if they still match the active routed product. If a document describes removed product surfaces or legacy route families, treat it as historical until it is refreshed or superseded.

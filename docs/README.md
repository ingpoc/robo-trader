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
- [Zerodha Broker Control Plane](workflow/zerodha-broker-control-plane.md)
- [Codex Runtime Control Plane](workflow/codex-runtime-control-plane.md)
- [Git Governance Control Plane](workflow/git-governance-control-plane.md)
- [Introspection Control Plane](workflow/introspection-control-plane.md)
- [Autonomous Paper Entry Go-Live Checklist](workflow/autonomous-paper-entry-go-live-checklist.md)
- [Linear Issue Control Plane](workflow/linear-issue-control-plane.md)
- [Notion Memory Control Plane](workflow/notion-memory-control-plane.md)
- [MCP/Auth Bootstrap](workflow/mcp-auth-bootstrap.md)

Use older architecture and historical notes only if they still match the active routed product. If a document describes removed product surfaces or legacy route families, treat it as historical until it is refreshed or superseded.

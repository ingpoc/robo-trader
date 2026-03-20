# Robo Trader UI

The UI is a light-first operator console for the mission-aligned Robo Trader product.

## Active Surface

The frontend is intentionally limited to four top-level routes:

- `/` for Overview
- `/paper-trading`
- `/system-health`
- `/configuration`

`News & Earnings` and `AI Transparency` are embedded under `Paper Trading` as workflow tabs.

## Design System

- React + Vite
- TypeScript
- TanStack Query
- Tailwind CSS
- shadcn-style owned primitives under `src/components/ui`

The UI is light-only for now. Dark mode is intentionally unsupported until the design system is fully stabilized.

## Product Intent

This is not a generic trading dashboard and not an agent admin panel.

The UI exists to help an operator:

- see paper-trading account state and live paper P&L
- inspect candidate discovery, research, decision traces, and review flows
- understand whether Claude, broker data, queues, and system dependencies are ready
- configure the retained runtime without hiding blockers behind synthetic success states

## Structure

```text
ui/
├── src/
│   ├── api/                  # API client, endpoints, websocket client
│   ├── components/           # Shared app and UI primitives
│   ├── features/             # Routed feature surfaces
│   │   ├── dashboard/
│   │   ├── paper-trading/
│   │   ├── system-health/
│   │   └── configuration/
│   ├── hooks/                # Shared data/state hooks
│   ├── styles/               # Global tokens and shell styling
│   └── types/                # Frontend API and view models
└── vite.config.ts
```

## Local Development

Install:

```bash
cd ui
npm install
```

Run against an isolated backend:

```bash
VITE_PROXY_TARGET=http://127.0.0.1:8010 \
VITE_WS_TARGET=ws://127.0.0.1:8010 \
npm run dev -- --host 127.0.0.1 --port 3001
```

## API Expectations

The UI is aligned to the retained operator backend:

- `/api/dashboard`
- `/api/paper-trading/*`
- `/api/paper-trading/capabilities`
- `/api/monitoring/*`
- `/api/configuration/*`
- `/api/news-earnings/*` for embedded discovery flows
- `/api/claude-transparency/*` for embedded paper-trading review and trace views
- `/api/zerodha/*` for retained auth/data setup paths

Removed or deprecated admin/legacy APIs should not be reintroduced into active UI flows.

## UI Rules

- Use shared primitives before adding bespoke route-level styling.
- Keep surfaces neutral and operator-focused.
- Empty, blocked, and degraded states must be explicit.
- Do not invent default data when the backend has none.
- If the backend is blocked, show the blocker instead of a placeholder success state.

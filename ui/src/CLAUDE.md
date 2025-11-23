# Frontend UI - ui/src/

React/TypeScript modular feature-based architecture. Max 350 lines per component.

## Component Size Limits
| Component | Max Lines | Guideline |
|-----------|-----------|-----------|
| Feature main | 300 | Orchestrator + 2-3 sub-components |
| Sub-component | 200 | Single responsibility |
| Hook | 150 | Logic encapsulation |
| Utility | 100 | Pure functions |

## Structure
```
features/feature-name/
├── FeatureNameFeature.tsx    (300 lines max)
├── components/
│   ├── SubComponent1.tsx     (200 lines max)
│   └── SubComponent2.tsx
├── hooks/
│   └── useFeatureData.ts     (150 lines max)
└── utils/
    └── helpers.ts
```

## Rules
| Rule | Requirement |
|------|-------------|
| SDK | Consume SDK ONLY via /api/claude/* endpoints (NO direct imports) |
| Typing | No `any` types, export props interface |
| Styling | Tailwind classes or CSS modules (no inline styles) |
| State | useContext for shared, useState for local |
| WebSocket | Custom hooks with proper cleanup |
| Features | One responsibility per feature, internal components not exported |

## Anti-Patterns
❌ Inline styles, untyped props, direct API imports, no error boundaries
✅ Tailwind, typed exports, backend API consumption, error handling

## Pre-Commit
- [ ] Max size checked (300/200/150 lines)
- [ ] No `any` types in TS
- [ ] Proper error handling
- [ ] WebSocket cleanup
- [ ] Handles loading/error/empty states

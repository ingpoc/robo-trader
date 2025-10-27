# Frontend Architecture Guidelines

> **Scope**: Applies to all files under `ui/src/`. Read after root CLAUDE.md for project patterns.
> **Last Updated**: 2025-10-27 | **Status**: Production Ready - All core systems operational

Frontend architecture focuses on component organization, real-time data updates, and maintainable UI code. This file complements the root CLAUDE.md with React/TypeScript-specific patterns.

## Contents

- [Current Implementation Status](#current-implementation-status)
- [Claude Agent SDK Integration](#claude-agent-sdk-integration-critical)
- [Component Architecture Patterns](#component-architecture-patterns)
- [State Management Patterns](#state-management-patterns)
- [WebSocket Integration](#websocket-integration)
- [Error Handling Patterns](#error-handling-patterns)
- [Performance Optimization](#performance-optimization)
- [Development Workflow](#development-workflow)
- [Quick Reference - Frontend](#quick-reference---frontend)

## Current Implementation Status

### ✅ **COMPLETED FEATURES**
- **Modular Architecture**: Complete feature-based organization implemented
- **Dashboard**: Fully functional with real-time data and charts
- **Paper Trading**: Account selection, position viewing, trade history (AccountSelector fixed)
- **AI Transparency**: Complete 5-tab interface with research, analysis, execution monitoring
- **System Health**: Comprehensive monitoring interface
- **WebSocket Infrastructure**: Robust connection management implemented
- **Error Boundaries**: Proper error handling throughout application

### ❌ **CRITICAL MISSING FUNCTIONALITY**
- **Trade Execution**: Buy/sell/close position forms non-functional (backend APIs return 404)
- **Account Creation**: AccountSelector create dialog not connected to backend
- **Data Structure Alignment**: Frontend expects different field names than backend provides
- **Real-Time Updates**: WebSocket infrastructure ready but no active data streaming

### 🔧 **REMAINING TECHNICAL DEBT**
- **PaperTrading.tsx**: Still 59KB monolithic file (needs refactoring to features)
- **API Response Standardization**: Field name mismatches between frontend/backend
- **Loading States**: Some components need better loading/empty state handling

## Claude Agent SDK Integration (CRITICAL)

### SDK-Only Frontend Architecture (MANDATORY)

All AI-related frontend features must consume **ONLY** Claude Agent SDK services through backend APIs. No direct Anthropic API calls are permitted.

**AI Transparency Features** (SDK-Only):
- `features/ai-transparency/` - Claude trading transparency center
- `features/dashboard/` - AI insights and recommendations
- `features/agents/` - Multi-agent coordination monitoring

**SDK Service Consumption Pattern**:
```typescript
// features/ai-transparency/hooks/useAITransparency.ts
export const useAITransparency = () => {
  const [data, setData] = useState<AITransparencyData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Consume SDK-only backend APIs
    fetch('/api/claude/transparency/research')
      .then(response => response.json())
      .then(data => setData(data))
      .catch(error => setError(error.message));
  }, []);

  return { data, error };
};

// AITransparencyFeature.tsx
const AITransparencyFeature = () => {
  const { data, error } = useAITransparency();

  if (error) return <ErrorCard message={error} />;
  if (!data) return <LoadingSpinner />;

  return (
    <div>
      {/* Display SDK-powered AI transparency data */}
      <TradeDecisionLog trades={data.trades} />
      <StrategyReflections reflections={data.reflections} />
    </div>
  );
};
```

**❌ FORBIDDEN - Direct API Usage in Frontend:**
```typescript
// NEVER DO THIS in frontend code
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: 'sk-ant-...', // NEVER expose API keys in frontend
});

const response = await client.messages.create({
  model: 'claude-3-sonnet-20240229',
  max_tokens: 1000,
  messages: [{ role: 'user', content: 'Hello' }],
});
```

**Backend API Consumption Only**:
- All AI features consume backend APIs that use SDK services
- Backend APIs registered in `src/web/claude_agent_api.py`
- SDK services registered in DI container
- No API keys or direct Claude calls in frontend

**Security Benefits**:
- API keys never exposed to frontend
- All AI calls go through authenticated backend
- Rate limiting and validation on backend
- Consistent error handling and logging

## Frontend Architecture

### 1. Pages (`ui/src/pages/`)

**Responsibility**: Legacy route components being phased out in favor of features.

**Remaining Pages** (to be refactored to features):
- `Trading.tsx` - Trading interface
- `PaperTrading.tsx` - Paper trading account management (59KB - candidate for refactoring)
- `AgentConfig.tsx` - Agent configuration
- `Agents.tsx` - Agent management
- `Config.tsx` - System configuration
- `Logs.tsx` - Logs viewer
- `OrderManagement.tsx` - Order execution and management
- `RiskConfiguration.tsx` - Risk settings and configuration
- `QueueManagement.tsx` - Background task queue monitoring

**Removed Pages** (migrated to features):
- ~~`Dashboard.tsx`~~ → `features/dashboard/DashboardFeature.tsx`
- ~~`ClaudeTransparency.tsx`~~ → `features/ai-transparency/AITransparencyFeature.tsx`
- ~~`NewsEarnings.tsx`~~ → `features/news-earnings/NewsEarningsFeature.tsx`

**Rules**:
- ✅ Prefer features over pages for new functionality
- ✅ One page component per file
- ✅ Connect to WebSocket for real-time data
- ✅ Handle loading and error states
- ✅ Delegate to feature components
- ❌ Don't create new pages - use features instead
- ❌ Don't add styling directly (use Tailwind or external CSS)

### 2. Features (`ui/src/features/`)

**Responsibility**: Self-contained feature modules with multiple related components and domain-specific logic.

**Current Features**:
- `dashboard/` - Main trading dashboard with portfolio overview, metrics, and insights
  - `DashboardFeature.tsx` - Main component
  - `components/` - MetricsGrid, PerformanceCharts, PortfolioOverview, AIInsightsSummary, AlertsSummary
  - `hooks/` - useDashboardData

- `ai-transparency/` - Claude AI trading transparency and learning visibility
  - `AITransparencyFeature.tsx` - Main component with 5 tabs (Trades, Reflections, Recommendations, Sessions, Analytics)
  - `components/` - TradeDecisionLog, StrategyReflections, RecommendationAudit, SessionTranscripts, PerformanceAttribution
  - `hooks/` - useAITransparency

- `system-health/` - System monitoring and health status
  - `SystemHealthFeature.tsx` - Main component with 5 tabs (Schedulers, Queues, Database, Resources, Errors)
  - `components/` - SchedulerStatus, QueueHealthMonitor, DatabaseStatus, ResourceUsage, ErrorAlerts
  - `hooks/` - useSystemHealth

- `news-earnings/` - News feed and earnings analysis (existing)
  - `NewsEarningsFeature.tsx` - Main component
  - `components/` - NewsFeed, EarningsReports, RecommendationsPanel, SymbolSelector, etc.

- `paper-trading/` - Paper trading account management (planned refactoring)
- `agents/` - Multi-agent coordination and monitoring (planned)
- `order-management/` - Order execution and management (existing)
- `queue-management/` - Background task queue management (existing)
- `risk-management/` - Risk assessment and controls (existing)

**Feature Structure Template**:
```
features/feature-name/
├── FeatureNameFeature.tsx       (Main entry point, max 300 lines)
├── components/
│   ├── SubComponent1.tsx        (Self-contained, max 200 lines)
│   ├── SubComponent2.tsx
│   └── index.ts                 (Optional: export all components)
├── hooks/
│   ├── useFeatureData.ts        (Data fetching, max 150 lines)
│   └── index.ts                 (Optional: export all hooks)
└── utils/                       (Optional: feature-specific utilities)
    ├── helper.ts
    └── constants.ts
```

**Rules**:
- ✅ One feature = one major responsibility domain
- ✅ Main feature file (`FeatureName.tsx`) is the only export from folder
- ✅ Internal components in `components/` subfolder - NOT exported
- ✅ Feature-specific hooks in `hooks/` subfolder
- ✅ All state management encapsulated within feature
- ✅ Feature exports only: main component, hooks, types
- ✅ Max 300 lines for main feature component
- ✅ Max 200 lines for individual sub-components
- ❌ Don't export internal sub-components from feature
- ❌ Don't mix multiple responsibilities in one feature
- ❌ Don't create circular dependencies between features

### 3. Shared Components (`ui/src/components/`)

**Responsibility**: Reusable UI components and layouts.

**Structure**:
- `Sidebar/` - Navigation sidebar
- `Dashboard/` - Dashboard-specific cards and panels
- `ui/` - Reusable primitives (Button, Input, Card, Dialog, etc.)

**Component Types**:

#### Shared UI Primitives (`ui/src/components/ui/`)
- `Button.tsx` - Button component
- `Input.tsx` - Input field
- `Card.tsx` - Card container
- `Dialog.tsx` - Modal dialog
- `Badge.tsx` - Badge labels
- `Select.tsx` - Select dropdown
- `Popover.tsx` - Popover menu
- `Tooltip.tsx` - Tooltip
- `Command.tsx` - Command palette
- `SymbolCombobox.tsx` - Symbol selection

**Rules**:
- ✅ One component per file
- ✅ Export both component and props interface
- ✅ Use TypeScript (no `any` types)
- ✅ Add Storybook stories for complex components
- ✅ Make components composable and reusable
- ❌ Don't add page-specific logic
- ❌ Don't hard-code styling

#### Dashboard Components (`ui/src/components/Dashboard/`)
- `ChartCard.tsx` - Chart display
- `MetricCard.tsx` - Metric display
- `HoldingsTable.tsx` - Holdings table
- `AlertItem.tsx` - Alert item
- `AIInsights.tsx` - AI insights panel
- `AgentConfigPanel.tsx` - Agent config panel
- `QuickTradeForm.tsx` - Quick trade form

**Rules**:
- ✅ Specific to dashboard functionality
- ✅ Use shared UI primitives
- ✅ Accept data as props
- ✅ Handle empty/loading states
- ❌ Don't fetch data directly (props only)

### 4. Hooks (`ui/src/hooks/`)

**Responsibility**: Custom React hooks for shared logic.

**Pattern**:
```typescript
export const useWebSocket = (url: string) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // WebSocket logic here
  }, [url]);

  return { data, error, loading };
};
```

**Rules**:
- ✅ One hook per file
- ✅ Encapsulate complex logic
- ✅ Return typed data
- ✅ Handle cleanup in useEffect
- ❌ Don't duplicate logic in components

### 5. Utilities (`ui/src/utils/`)

**Responsibility**: Helper functions and utilities.

**Current Utilities**:
- `format.ts` - Formatting functions (numbers, dates, currencies)
- `validation.ts` - Input validation
- `cn.ts` - Classname merging utility

**Rules**:
- ✅ Pure functions (no side effects)
- ✅ Well-documented with examples
- ✅ Properly typed
- ✅ Reusable across components
- ❌ Don't add component logic
- ❌ Don't make HTTP requests

---

## Component Architecture Pattern

### ✅ DO

```typescript
// ui/src/components/MyComponent.tsx
import React, { useState } from 'react';
import { Card } from './ui/Card';

export interface MyComponentProps {
  title: string;
  onAction: (data: string) => void;
  isLoading?: boolean;
}

export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  onAction,
  isLoading = false
}) => {
  const [input, setInput] = useState('');

  const handleClick = () => {
    onAction(input);
  };

  return (
    <Card>
      <h2>{title}</h2>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={isLoading}
      />
      <button onClick={handleClick} disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Submit'}
      </button>
    </Card>
  );
};

export default MyComponent;
```

### ❌ DON'T

```typescript
// WRONG - Multiple components in one file
export const MyComponent = () => { ... };
export const MyOtherComponent = () => { ... };

// WRONG - Direct styling
const MyComponent = () => (
  <div style={{ color: 'red', fontSize: '16px' }}>
    Content
  </div>
);

// WRONG - No typing
const MyComponent = (props: any) => {
  return <div>{props.data}</div>;
};

// WRONG - Direct data fetching in component
const MyComponent = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/data').then(d => setData(d));
  }, []);

  return <div>{data}</div>;
};
```

---

## Feature Module Pattern

### ✅ DO

```typescript
// features/myfeature/MyFeatureComponent.tsx
import React, { useState } from 'react';
import { SubComponent } from './components/SubComponent';

export interface MyFeatureProps {
  onClose?: () => void;
}

export const MyFeatureComponent: React.FC<MyFeatureProps> = ({ onClose }) => {
  const [state, setState] = useState('initial');

  return (
    <div className="space-y-4">
      <SubComponent state={state} onChange={setState} />
    </div>
  );
};

export default MyFeatureComponent;
```

### ❌ DON'T

```typescript
// WRONG - Exporting internal components
export { SubComponent } from './components/SubComponent';

// WRONG - Complex logic outside feature
// Instead: Keep all feature logic within feature folder
```

---

## WebSocket Integration Pattern

### ✅ DO

```typescript
// Custom hook for WebSocket data
export const useDashboardData = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/dashboard');

    ws.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data);
        setData(prev => prev ? { ...prev, ...update } : update);
      } catch (e) {
        setError('Failed to parse data');
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
    };

    return () => {
      ws.close();
    };
  }, []);

  return { data, error };
};

// Usage in component
const Dashboard = () => {
  const { data, error } = useDashboardData();

  if (error) return <ErrorCard message={error} />;
  if (!data) return <LoadingSpinner />;

  return <DashboardContent data={data} />;
};
```

### ❌ DON'T

```typescript
// WRONG - Direct WebSocket in component
const Dashboard = () => {
  useEffect(() => {
    const ws = new WebSocket('...');
    ws.onmessage = ...;
    // ... no cleanup
  }, []);
};

// WRONG - Polling instead of WebSocket
const Dashboard = () => {
  useEffect(() => {
    setInterval(() => {
      fetch('/api/data').then(setData);
    }, 1000);
  }, []);
};
```

---

## State Management Pattern

### ✅ DO

```typescript
// Local component state for UI state
const [isOpen, setIsOpen] = useState(false);

// Context for shared feature state
const [items, setItems] = useState<Item[]>([]);

// WebSocket for real-time updates
const { data } = useDashboardData();
```

### ❌ DON'T

```typescript
// WRONG - Global Redux or complex state management for UI
// Use local component state instead

// WRONG - Fetching data on every render
const Dashboard = () => {
  const data = fetchData(); // Called on every render!
  return <div>{data}</div>;
};
```

---

## Styling Rules

### ✅ DO

```typescript
// Use Tailwind classes
<div className="flex items-center justify-between space-y-4">
  <h1 className="text-2xl font-bold text-gray-900">Title</h1>
</div>

// Use CSS modules for component-specific styles
import styles from './Component.module.css';
<div className={styles.container}>

// Use external CSS files
import './styles.css';
<div className="custom-class">
```

### ❌ DON'T

```typescript
// WRONG - Inline styles
<div style={{ color: 'red', fontSize: '16px' }}>

// WRONG - Styled components in this project
import styled from 'styled-components';

// WRONG - CSS-in-JS beyond Tailwind
const styles = { container: { color: 'red' } };
```

---

## TypeScript Rules

- ✅ No `any` types - always define proper interfaces
- ✅ Export component props interface
- ✅ Type all function parameters and returns
- ✅ Use discriminated unions for complex state
- ❌ Don't use `as unknown as Type` casting
- ❌ Don't skip type checking

---

## Frontend Performance Patterns

### Component Memoization
- ✅ Use `React.memo()` for expensive components
- ✅ Memoize callbacks with `useCallback()` for event handlers
- ✅ Memoize computed values with `useMemo()`
- ❌ Don't over-memoize simple components (adds overhead)
- ❌ Don't memoize without dependencies array

### WebSocket Optimization
- ✅ Use differential updates (only changed fields)
- ✅ Batch updates, don't update every frame
- ✅ Debounce frequent updates (price tickers)
- ✅ Lazy load feature components
- ❌ NEVER fetch full state on every update
- ❌ NEVER render without error boundaries

---

## Anti-Patterns - Frontend (What to Avoid)

### Inline Styling Anti-Pattern
**Problem**: Inline styles duplicate across files, hard to maintain
```typescript
// WRONG
<div style={{ color: 'red', fontSize: '16px' }}>
```
**Solution**: Use Tailwind classes or CSS modules

### Missing Error Boundaries Anti-Pattern
**Problem**: Single component error crashes entire page
```typescript
// WRONG - No error boundary
const Dashboard = () => {
  return <div><ProblematicComponent /></div>;
};
```
**Solution**: Wrap components with error boundaries, show fallback UI

### Direct Data Fetching Anti-Pattern
**Problem**: Multiple instances fetch same data, hard to test
```typescript
// WRONG - Fetching in component
const Component = () => {
  useEffect(() => {
    fetch('/api/data').then(setData);
  }, []);
};
```
**Solution**: Use custom hooks, mock for testing

### No WebSocket Cleanup Anti-Pattern
**Problem**: Memory leaks, connections pile up
```typescript
// WRONG - No cleanup
useEffect(() => {
  const ws = new WebSocket('...');
  ws.onmessage = ...;
  // Missing return cleanup
}, []);
```
**Solution**: Always return cleanup function that closes connection

### Prop Drilling Anti-Pattern
**Problem**: Passing props through many levels gets unmaintainable
```typescript
// WRONG - Drilling 5 levels deep
<Page data={data}>
  <Section data={data}>
    <Component data={data}>
      <Child data={data}>
        <GrandChild data={data} />
```
**Solution**: Use Context for shared data, keep to 2-3 levels

---

## Pre-Commit Checklist - Frontend

- [ ] One component per file
- [ ] Props interface exported and typed
- [ ] No `any` types in TypeScript (use proper types)
- [ ] Handles loading/error/empty states
- [ ] WebSocket subscribed and properly cleaned up
- [ ] No inline styling (use Tailwind/CSS modules)
- [ ] Reusable components in `components/`
- [ ] Features self-contained and isolated
- [ ] No direct API calls in components (use hooks/props)
- [ ] Proper TypeScript types throughout
- [ ] Component under 200 lines (split if larger)
- [ ] No unused dependencies or props
- [ ] Memoization applied only where needed (not over-optimized)
- [ ] Error handling for async operations

---

## Quick Reference - Frontend Patterns

| Need | Location | Pattern | Max Size |
|------|----------|---------|----------|
| New page | `pages/` | One file, imports features | 300 lines |
| New feature | `features/name/` | Main file + components/ | 400 lines |
| Shared component | `components/` | One file, typed props | 200 lines |
| Reusable hook | `hooks/` | Custom hook with types | 150 lines |
| Helper function | `utils/` | Pure function, no side effects | 100 lines |
| Global style | `styles/` | CSS or Tailwind | N/A |
| Real-time data | `hooks/useWebSocket*` | Custom hook with WebSocket | 150 lines |

---

## Development Workflow - Frontend

### 1. New Page

- Create in `pages/` directory
- Import feature components as needed
- Connect to WebSocket for real-time data
- Handle loading/error states with proper fallbacks
- Max 300 lines per page

### 2. New Feature

- Create `features/name/` directory
- Main component in `features/name/FeatureName.tsx`
- Sub-components in `features/name/components/`
- Export main feature component only
- Keep all logic and state within feature
- Max 400 lines for main feature file

### 3. New Shared Component

- Create in `components/` or `components/ui/`
- Export typed props interface
- Make fully composable (props-only, no side effects)
- Use in at least 2-3 places before sharing
- No feature-specific logic
- Max 200 lines per component

### 4. New Custom Hook

- Create in `hooks/` directory
- Encapsulate complex logic (WebSocket, data fetching)
- Return typed data
- Implement proper cleanup
- Include useEffect cleanup functions
- Max 150 lines per hook

### 5. Bug Fix

- Identify component file
- Fix logic
- Verify props and types are correct
- Test WebSocket updates if component uses real-time data
- Verify in multiple states (loading, error, empty)

### 6. Performance Optimization

- Profile with React DevTools first
- Memoize only if profiler shows re-render issue
- Use lazy loading for route components
- Batch WebSocket updates
- Avoid prop drilling (use Context if needed)

---

## Common Frontend Mistakes

### Mistake 1: No Loading State
**Problem**: Users think app is frozen during load
**Solution**: Show loading spinner, disable inputs during load

### Mistake 2: WebSocket Never Reconnects
**Problem**: Connection drops, no updates, user refreshes page
**Solution**: Implement reconnection logic with exponential backoff

### Mistake 3: No Error Messages
**Problem**: User doesn't know why action failed
**Solution**: Show clear, actionable error messages

### Mistake 4: Untyped Props
**Problem**: Hard to know what props a component needs
**Solution**: Always export interface, use TypeScript strictly

### Mistake 5: Component Too Large
**Problem**: Hard to read, test, and reuse
**Solution**: Split into smaller components when over 200 lines

---

## Frontend Refactoring (Phase 1) - Completed Oct 24, 2024

### Overview
Completed comprehensive frontend refactoring to eliminate bloated monolithic pages, consolidate duplicate components, and establish a modular, feature-based architecture.

### Changes Made

#### 1. Created New Feature Modules
- **`dashboard/`** - Main trading dashboard
  - Consolidated from 435-line `Dashboard.tsx`
  - Split into: DashboardFeature (main), MetricsGrid, PerformanceCharts, PortfolioOverview, AIInsightsSummary, AlertsSummary
  - Added `useDashboardData` hook

- **`ai-transparency/`** - Claude trading transparency center
  - Consolidated from 667-line `ClaudeTransparencyDashboard.tsx`
  - Split into: AITransparencyFeature (main), TradeDecisionLog, StrategyReflections, RecommendationAudit, SessionTranscripts, PerformanceAttribution
  - Added `useAITransparency` hook

- **`system-health/`** - System monitoring and infrastructure
  - New feature for backend system monitoring
  - Components: SchedulerStatus, QueueHealthMonitor, DatabaseStatus, ResourceUsage, ErrorAlerts
  - Added `useSystemHealth` hook

#### 2. Removed Dead Code
- Deleted `pages/Dashboard.tsx` (435 lines)
- Deleted `pages/ClaudeTransparency.tsx` (5.2 KB)
- These are now accessed via features in App.tsx routing

#### 3. Updated Routing
- `App.tsx` - Updated imports and routes:
  - `/` → `DashboardFeature` (was Dashboard page)
  - `/ai-transparency` → `AITransparencyFeature` (was `/claude-transparency`)
  - `/system-health` → `SystemHealthFeature` (new)
  - Removed old page imports

- `Navigation.tsx` - Updated sidebar menu:
  - Replaced `/claude-transparency` with `/ai-transparency`
  - Added `/system-health` route

#### 4. Code Quality Improvements
- Reduced component file sizes (max 200 lines per component)
- Extracted data fetching to feature-specific hooks
- Consolidated duplicate component logic
- Improved separation of concerns (features contain their own state, hooks, and components)

### Remaining Work
- **PaperTrading.tsx** (59 KB) - Candidate for refactoring to `features/paper-trading/`
- **NewsEarnings.tsx** (45 KB) - Partially refactored; complete modularization
- **Agents/Agent-related pages** - Consider consolidating to `features/agents/`

### Benefits Achieved
✅ **Modularity**: Each feature self-contained with clear boundaries
✅ **Maintainability**: Easier to locate and modify feature-specific code
✅ **Reusability**: Components can be reused within and across features
✅ **Scalability**: New features follow established pattern
✅ **Performance**: Lazy loading of route components via features
✅ **Type Safety**: All components fully typed with exported props interfaces

### Files Changed
- Created: 15 new feature component files
- Modified: App.tsx, Navigation.tsx, ui/src/CLAUDE.md
- Deleted: 2 monolithic page files (440 lines removed)


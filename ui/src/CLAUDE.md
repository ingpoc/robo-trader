# Frontend Architecture Guidelines

> **Scope**: Applies to all files under `ui/src/`. Read after root CLAUDE.md.

## Frontend Architecture

### 1. Pages (`ui/src/pages/`)

**Responsibility**: Top-level route components.

**Current Pages**:
- `Dashboard.tsx` - Main trading dashboard
- `Trading.tsx` - Trading interface
- `AgentConfig.tsx` - Agent configuration
- `Agents.tsx` - Agent management
- `NewsEarnings.tsx` - News and earnings feature
- `Config.tsx` - System configuration
- `Logs.tsx` - Logs viewer

**Rules**:
- ✅ One page component per file
- ✅ Connect to WebSocket for real-time data
- ✅ Handle loading and error states
- ✅ Use feature components for complex sections
- ❌ Don't add styling directly (use Tailwind or external CSS)
- ❌ Don't duplicate logic across pages

### 2. Features (`ui/src/features/`)

**Responsibility**: Self-contained feature modules with multiple related components.

**Current Features**:
- `news-earnings/` - News feed, earnings reports, recommendations, symbol selector, upcoming earnings

**Structure**:
```
features/news-earnings/
├── NewsEarningsFeature.tsx     (Main feature entry)
├── components/
│   ├── NewsFeed.tsx
│   ├── EarningsReports.tsx
│   ├── RecommendationsPanel.tsx
│   ├── SymbolSelector.tsx
│   └── UpcomingEarnings.tsx
```

**Rules**:
- ✅ One feature = one responsibility
- ✅ Main feature file exports default component
- ✅ Shared components in `components/` subfolder
- ✅ Local state management within feature
- ✅ Export interfaces for type safety
- ❌ Don't mix features
- ❌ Don't export private components from main file

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

## Pre-Commit Checklist - Frontend

- [ ] One component per file
- [ ] Props interface exported and typed
- [ ] No `any` types in TypeScript
- [ ] Handles loading/error states
- [ ] WebSocket subscribed and cleaned up
- [ ] No inline styling (use Tailwind/CSS)
- [ ] Reusable components in `components/`
- [ ] Features self-contained
- [ ] No data fetching in components (use hooks)
- [ ] Proper TypeScript types throughout

---

## Quick Reference - Frontend Patterns

| Need | Location | Pattern |
|------|----------|---------|
| New page | `pages/` | One file, imports features |
| New feature | `features/name/` | Main file + components/ |
| Shared component | `components/` | One file, typed props |
| Reusable hook | `hooks/` | Custom hook with typed returns |
| Helper function | `utils/` | Pure function, no side effects |
| Global style | `styles/` | CSS or Tailwind |
| Real-time data | `hooks/useWebSocket*` | Custom hook with WebSocket |

---

## Development Workflow - Frontend

1. **New Page**
   - Create in `pages/` directory
   - Import feature components as needed
   - Connect to WebSocket for data
   - Handle loading/error states

2. **New Feature**
   - Create `features/name/` directory
   - Main component in `features/name/FeatureName.tsx`
   - Sub-components in `features/name/components/`
   - Keep all logic within feature

3. **New Shared Component**
   - Create in `components/` or `components/ui/`
   - Export typed props interface
   - Make fully composable (props-only, no side effects)
   - Use in multiple places before sharing

4. **Bug Fix**
   - Identify component file
   - Fix logic
   - Verify props and types
   - Test WebSocket updates if applicable


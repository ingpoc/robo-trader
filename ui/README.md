# Robo Trader UI

A production-ready React application for the autonomous Robo Trader system, built with Swiss Digital Minimalism principles and Dieter Rams' "Less but Better" philosophy.

## Design Philosophy

### Swiss Digital Minimalism
- **Grayscale base + single accent color** (blue: #2563eb)
- **Typography creates all hierarchy** - no color coding for meaning
- **8px base unit spacing system** for mathematical precision
- **Maximum 1.005x hover scale** - minimal, sophisticated interactions
- **Essential information only** - no decorative elements

### Tech Stack
- **React 18** with TypeScript strict mode
- **Vite** for blazing fast development
- **TanStack Query** for server state management
- **Zustand** for client state management
- **React Hook Form + Zod** for type-safe forms
- **Recharts** for minimalist data visualization
- **Radix UI** for accessible primitives
- **Tailwind CSS** with custom Swiss theme

## Project Structure

```
ui/
├── src/
│   ├── api/                  # API client and endpoints
│   │   ├── client.ts         # Fetch wrapper with error handling
│   │   ├── endpoints.ts      # All API endpoints
│   │   └── websocket.ts      # WebSocket client with reconnection
│   ├── components/
│   │   ├── ui/               # Base Radix components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Dialog.tsx
│   │   │   └── Toast.tsx
│   │   ├── Dashboard/        # Dashboard-specific components
│   │   │   ├── MetricCard.tsx       # Rolling number animations
│   │   │   ├── ChartCard.tsx        # Recharts wrapper
│   │   │   ├── HoldingsTable.tsx    # Virtualized table
│   │   │   ├── QuickTradeForm.tsx   # Trade execution form
│   │   │   └── AIInsights.tsx       # AI status display
│   │   ├── Sidebar/
│   │   │   └── Navigation.tsx
│   │   └── common/
│   │       └── Toaster.tsx   # Toast notification manager
│   ├── hooks/                # Custom React hooks
│   │   ├── useWebSocket.ts   # WebSocket connection
│   │   ├── usePortfolio.ts   # Portfolio data and actions
│   │   ├── useRecommendations.ts
│   │   └── useAgents.ts
│   ├── pages/                # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── Agents.tsx
│   │   ├── Trading.tsx
│   │   ├── Config.tsx
│   │   └── Logs.tsx
│   ├── store/
│   │   └── dashboardStore.ts # Zustand store
│   ├── types/
│   │   └── api.ts            # TypeScript interfaces
│   ├── utils/
│   │   ├── format.ts         # Formatting utilities
│   │   └── validation.ts     # Zod schemas
│   ├── styles/
│   │   └── globals.css       # Swiss minimalist styles
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── README.md
```

## Setup Instructions

### Prerequisites
- Node.js >= 18.0.0
- npm or yarn
- Running FastAPI backend at `http://localhost:8000`

### Installation

1. **Install dependencies**
```bash
cd ui
npm install
```

2. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
```

3. **Start development server**
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Development Commands

```bash
npm run dev          # Start dev server with HMR
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run type-check   # Check TypeScript types
```

## Backend Integration

### API Endpoints Used

The UI integrates with the following backend endpoints:

**Dashboard & Portfolio:**
- `GET /api/dashboard` - Portfolio, analytics, intents
- `POST /api/portfolio-scan` - Trigger portfolio analysis
- `POST /api/market-screening` - Market screening
- `WebSocket /ws` - Real-time updates every 5 seconds

**Trading:**
- `POST /api/manual-trade` - Execute manual trades

**AI & Recommendations:**
- `GET /api/ai/status` - Current AI activity
- `GET /api/ai/recommendations` - Pending recommendations
- `POST /api/recommendations/approve/{id}`
- `POST /api/recommendations/reject/{id}`
- `POST /api/recommendations/discuss/{id}`

**Agents:**
- `GET /api/agents/status` - All agents status
- `GET /api/agents/{name}/config`
- `POST /api/agents/{name}/config`

**Emergency:**
- `POST /api/emergency/stop`
- `POST /api/emergency/resume`

**Configuration:**
- `GET /api/config`
- `POST /api/config`

**Analytics:**
- `GET /api/analytics/portfolio-deep`
- `GET /api/analytics/performance/{period}`

**Alerts:**
- `GET /api/alerts/active`
- `POST /api/alerts/{id}/action`

### WebSocket Protocol

The WebSocket connection provides real-time updates:

```typescript
interface WebSocketMessage {
  portfolio: Portfolio
  analytics: Analytics
  intents: Intent[]
  ai_status: AIStatus
  recommendations: Recommendation[]
  timestamp: string
}
```

**Connection Features:**
- Automatic reconnection with exponential backoff
- Maximum 10 reconnection attempts
- Reconnect delay: 1s → 2s → 4s → 8s → 16s → 30s (max)
- Connection status indicator in sidebar

## Key Features

### 1. Real-time Dashboard
- **4 Metric Cards** with CSS-only rolling number animations
- **Portfolio Performance Chart** - Line chart with 30-day history
- **Asset Allocation Chart** - Pie chart for portfolio distribution
- **AI Insights Panel** - Current task, health, API usage with progress bar
- **Holdings Table** - Virtualized table for performance with 1000+ rows

### 2. Quick Trade Execution
- Type-safe form validation with Zod
- Real-time validation feedback
- Risk manager integration
- Success/error toast notifications

### 3. AI Recommendations
- Pending recommendation queue
- Approve/Reject/Discuss actions
- Confidence scoring
- Reasoning display

### 4. Agent Monitoring
- Status of all 8 agents
- Task completion counts
- Uptime tracking
- Configuration management

### 5. Accessibility
- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus management
- Screen reader announcements
- Skip links for navigation

## Performance Optimizations

### Code Splitting
- Route-based code splitting
- Lazy loading for modals
- Vendor chunk separation
- Charts in separate chunk

### Data Fetching
- TanStack Query with intelligent caching
- 5-second stale time for dashboard data
- Automatic background refetching
- Optimistic updates for mutations

### Rendering
- Virtual scrolling for large tables (TanStack Virtual)
- React.memo for expensive components
- Debounced form validation
- Efficient re-render patterns

### Bundle Size
- Tree-shaking with ES modules
- Production build with minification
- Gzip compression
- Source maps for debugging

## Swiss Design Implementation

### Color System
```css
Grayscale: #fafafa → #171717 (50 → 900)
Accent:    #2563eb (blue, ONLY accent color)
```

### Typography Hierarchy
```
Display:  2.25rem / 36px  - Page titles
Heading:  1.5rem / 24px   - Section titles
Body:     1rem / 16px     - Main content
Label:    0.875rem / 14px - Form labels
Caption:  0.75rem / 12px  - Metadata
```

### Spacing System (8px base)
```
Space-1: 8px    Space-5: 40px
Space-2: 16px   Space-6: 48px
Space-3: 24px   Space-7: 56px
Space-4: 32px   Space-8: 64px
```

### Interaction Principles
- **No gradients** - Flat design only
- **No shadows** - Maximum 1px border
- **No decorative icons** - Text-based hierarchy
- **150ms transitions** - Fast, precise
- **Hover: opacity change only** - No scale effects

## Deployment

### Production Build

```bash
npm run build
```

Output in `dist/` directory:
- `index.html`
- `assets/` - Hashed JS/CSS bundles
- Source maps for debugging

### Environment Variables

For production, set:
```env
VITE_API_BASE_URL=https://your-api-domain.com
VITE_WS_URL=wss://your-api-domain.com/ws
VITE_ENVIRONMENT=production
```

### Serving

**Static hosting (Vercel, Netlify, etc.):**
```bash
npm run build
# Deploy dist/ directory
```

**With Vite preview:**
```bash
npm run preview
```

**With Docker:**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### CORS Configuration

Ensure backend allows requests from frontend domain:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Browser Support

- Chrome/Edge >= 90
- Firefox >= 88
- Safari >= 14
- Opera >= 76

Modern browsers with ES2020 support required.

## Troubleshooting

### WebSocket Connection Issues
- Check backend is running at correct URL
- Verify CORS settings
- Check browser console for connection errors
- Ensure WebSocket endpoint is accessible

### API Request Failures
- Verify `VITE_API_BASE_URL` in `.env`
- Check network tab for failed requests
- Ensure backend CORS is configured
- Check backend logs for errors

### Build Errors
```bash
rm -rf node_modules
npm install
npm run build
```

### Type Errors
```bash
npm run type-check
```

## Contributing

### Code Style
- No comments unless explicitly needed
- Meaningful variable names over explanatory comments
- Single-responsibility functions
- Prefer editing existing files over creating new ones

### Component Guidelines
- Use forwardRef for all UI components
- Provide TypeScript interfaces for all props
- Include ARIA labels for accessibility
- Follow Swiss minimalism principles

## License

MIT

## Support

For issues or questions:
1. Check troubleshooting section
2. Review backend API documentation
3. Check browser console for errors
4. Verify environment configuration

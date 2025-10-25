# Comprehensive E2E Testing Plan - Robo Trader

> **For Claude:** Use this plan with browser testing to validate all 8 documented pages against their specifications.

**Goal**: Verify each documented page displays correct data structure, UI components, and interactions as specified in documentation.

**Methodology**: Browser automation (Playwright) with screenshot verification, data validation, and issue documentation.

**Tech Stack**: Playwright MCP, Vite dev server (port 3000), Docker backend (port 8000)

---

## Page 1: Dashboard (Overview)

**Route**: `/`
**Documentation**: `documentation/dashboard_page.md`

### Expected Components

1. **Portfolio Summary Card**
   - Shows: Swing Balance, Options Balance, Combined Total
   - Data: Balance (₹), Today P&L (₹), Monthly ROI (%), Win Rate (%), Active Positions (#)
   - Example: Swing: ₹1,02,500 | Options: ₹98,500 | Combined: ₹2,01,000

2. **AI Insights Panel**
   - Shows: Top Buy Opportunities (3), Top Sell Signals (3)
   - Data per recommendation: Symbol, Price, Confidence (%), Rationale
   - Example: HDFC @ ₹2,800 (92% confidence), INFY @ ₹3,200 (78% confidence)
   - Buttons: [View All] [Approve Top 3]

3. **Strategy Effectiveness Gauge**
   - Two columns: "Working Well" (✓) and "Failing" (✗)
   - Shows: Strategy name, Win rate (%), # of trades
   - Example: Momentum Breakout (68%), RSI Support Bounce (72%)

4. **Claude Activity Summary**
   - Shows: Last action, Token usage (used/budget), Trades executed, Token warning (yellow > 70%, red > 90%)
   - Example: 8,500 / 15,000 tokens (57%), 3 trades today

5. **System Health Monitor**
   - Shows: Portfolio Scheduler status, News Monitor status, Claude Agent status, Database status, WebSocket status
   - Data: Status icon (✓/⚠/✗), Last run time, Current task
   - Example: ✓ Portfolio Scheduler (15 min ago), ✓ Database (42 connections)

6. **Quick Action Buttons**
   - Buttons: [Scan Portfolio] [Check News] [View Recommendations] [Swing Trading] [Options Trading] [System Health]

### Test Cases

**TC-DASHBOARD-1: Page loads with portfolio summary**
- Step 1: Navigate to `/`
- Step 2: Wait for portfolio summary card to appear
- Step 3: Verify shows Swing Balance, Options Balance, Combined Total
- Step 4: Verify numbers are formatted as Indian currency (₹)
- Expected data: Swing: ₹102,500+ | Options: ₹98,500+ | Combined: ₹200,000+
- Screenshot: dashboard_portfolio_summary.png

**TC-DASHBOARD-2: AI Insights Panel shows recommendations**
- Step 1: Check AI Insights Panel visible
- Step 2: Verify "Active Recommendations: X pending" displayed
- Step 3: Verify at least 3 buy opportunities shown (symbol, price, confidence)
- Step 4: Verify at least 2 sell signals shown
- Step 5: Verify [View All] and [Approve Top 3] buttons present
- Expected: HDFC, INFY, TCS shown with confidence 70%+
- Screenshot: dashboard_ai_insights.png

**TC-DASHBOARD-3: Strategy effectiveness gauge displays correctly**
- Step 1: Check Strategy Effectiveness section visible
- Step 2: Verify "Working Well" section shows 3+ strategies with win rates
- Step 3: Verify "Failing" section shows 2+ strategies
- Step 4: Verify color coding: Green for 65%+, Red for <50%
- Expected: Momentum Breakout (68%), RSI Support Bounce (72%), Protective Hedges (85%)
- Screenshot: dashboard_strategy_gauge.png

**TC-DASHBOARD-4: Claude Activity Summary shows token usage**
- Step 1: Check Claude Activity Summary visible
- Step 2: Verify shows "Last action: X min ago"
- Step 3: Verify token usage bar shown with percentage (used / budget)
- Step 4: Verify "Trades executed today: X" displayed
- Step 5: Verify "Next scheduled: X at HH:MM IST" shown
- Expected: Token usage 57% (8,500/15,000), 3 trades executed
- Screenshot: dashboard_claude_activity.png

**TC-DASHBOARD-5: System Health Monitor shows component status**
- Step 1: Check System Health Monitor visible
- Step 2: Verify all 5 components shown: Portfolio Scheduler, News Monitor, Claude Agent, Database, WebSocket
- Step 3: Verify each has status icon (✓ for healthy, ⚠ for warning, ✗ for error)
- Step 4: Verify "Last run" or "Current task" shown for each
- Step 5: Click on component to verify detailed status page link
- Expected: All 5 components visible with status indicators
- Screenshot: dashboard_system_health.png

**TC-DASHBOARD-6: Quick Action buttons are functional**
- Step 1: Verify all 6 buttons visible: [Scan Portfolio] [Check News] [View Recommendations] [Swing Trading] [Options Trading] [System Health]
- Step 2: Hover over each button to verify tooltip
- Step 3: Click [View Recommendations] button and verify navigation to recommendations page
- Step 4: Click [System Health] button and verify navigation to system health page
- Expected: All buttons clickable and navigate correctly
- Screenshot: dashboard_quick_actions.png

---

## Page 2: News & Earnings

**Route**: `/news-earnings`
**Documentation**: `documentation/news_earnings_page.md`

### Expected Components

1. **News Feed Panel**
   - Shows: Symbol tag, Title, Source, Date, Sentiment badge
   - Each item has: "Read more" link, "Mark as reviewed" checkbox, Fetch timestamp
   - Example: "INFY news" | "Infosys Q3 earnings beat expectations" | Source: Reuters | 2h ago | Positive

2. **News Monitoring Status Table**
   - Columns: Symbol, Last News Check, Next Check, Status
   - Color coding: Green (today), Yellow (yesterday), Red (2+ days old)
   - Buttons: "Fetch News Now" (per stock), "Fetch All Missing News"

3. **Earnings Calendar**
   - Columns: Date, Symbol, EPS Est, EPS Actual, Surprise %, Report Time
   - Shows upcoming earnings (next 30 days) and past earnings
   - Click row to expand with: Full details, Fundamentals snapshot, Price movement, Claude's analysis

4. **Fundamentals Dashboard**
   - Metric cards: Revenue, Earnings, P/E, ROE, Debt, Fair Value
   - Includes: Trend indicators (↑↓), Comparison vs sector average, Last analysis date

5. **Investment Recommendations**
   - Table: Symbol, Recommendation, Confidence, Fair Value, Last Updated
   - Shows: Pending, Approved & Executed, Rejected with reason

6. **Earnings Scheduler Config**
   - Toggles: Auto-fetch first earnings, Re-check fundamentals on negative news
   - Settings: Check for upcoming earnings every X days, Run earnings scheduler on n+1 day

### Test Cases

**TC-NEWS-1: News feed displays articles**
- Step 1: Navigate to `/news-earnings`
- Step 2: Verify News Feed Panel visible
- Step 3: Verify at least 5 news items displayed with: Symbol tag, Title, Source, Date, Sentiment badge
- Step 4: Verify each has "Read more" link and "Mark as reviewed" checkbox
- Step 5: Verify "Fetched X ago via Perplexity" timestamp shown
- Expected: News items from INFY, TCS, HDFC, SBIN, or similar
- Screenshot: news_earnings_feed.png

**TC-NEWS-2: Earnings Calendar shows upcoming and past earnings**
- Step 1: Check Earnings Calendar visible
- Step 2: Verify column headers: Date, Symbol, EPS Est, EPS Actual, Surprise %, Report Time
- Step 3: Verify upcoming earnings (next 30 days) highlighted/marked differently
- Step 4: Verify past earnings show actuals filled in
- Step 5: Click on earnings row to expand and verify shows: Details, Fundamentals snapshot, Price movement, Claude's analysis
- Expected: TCS, INFY, HDFC earnings visible with dates and EPS data
- Screenshot: news_earnings_calendar.png

**TC-NEWS-3: Fundamentals Dashboard shows metric cards**
- Step 1: Check Fundamentals section visible
- Step 2: Verify cards displayed: Revenue, Earnings, P/E, ROE, Debt, Fair Value
- Step 3: Verify each card shows: Current value, Trend indicator (↑↓ with %), Comparison vs sector
- Step 4: Verify "Last analysis: X days ago" shown with [Re-analyze] button
- Expected: All 6+ metric cards displayed with trend indicators
- Screenshot: news_earnings_fundamentals.png

**TC-NEWS-4: News Monitoring Status table shows check schedule**
- Step 1: Check News Monitoring Status table visible
- Step 2: Verify columns: Symbol, Last News Check, Next Check, Status
- Step 3: Verify color coding: Green (today), Yellow (yesterday), Red (2+ days old)
- Step 4: Verify buttons: "Fetch News Now" for each stock, "Fetch All Missing News" button
- Step 5: Click "Fetch News Now" for one stock and verify action
- Expected: 10+ stocks listed with check status
- Screenshot: news_earnings_monitoring.png

**TC-NEWS-5: Investment Recommendations shows pending and executed**
- Step 1: Check Investment Recommendations section visible
- Step 2: Verify columns: Symbol, Recommendation, Confidence, Fair Value, Last Updated
- Step 3: Verify pending recommendations highlighted and sortable
- Step 4: Verify approved recommendations marked as executed
- Step 5: Verify rejected recommendations show rejection reason
- Expected: Mix of pending (3+), approved (2+), rejected (1+) recommendations
- Screenshot: news_earnings_recommendations.png

**TC-NEWS-6: Earnings Scheduler config is editable**
- Step 1: Check Earnings Scheduler Config section visible
- Step 2: Verify toggle: "Auto-fetch first earnings for new stocks" (default ON)
- Step 3: Verify setting: "Check for upcoming earnings every X days" dropdown
- Step 4: Verify setting: "Run earnings scheduler on n+1 day" toggle
- Step 5: Verify setting: "Recheck fundamentals if news sentiment < -0.5" toggle
- Step 6: Change one setting and verify saves
- Expected: All 4 settings editable and persist
- Screenshot: news_earnings_config.png

---

## Page 3: Agents Configuration

**Route**: `/agents`
**Documentation**: `documentation/agents_page.md` and `documentation/AI_agents_page.md`

### Expected Components

1. **Agent Status Dashboard**
   - Shows: Claude Main Agent status, Morning Prep Agent (Swing), Morning Prep Agent (Options), Evening Review Agents
   - Data per agent: Status (Active/Idle/Analyzing), Last action time, Tokens used (used/budget), Next scheduled task
   - Example: Status: Active | Last action: 2 min ago | Tokens: 8,500/15,000 | Next: Evening review 16:30

2. **Token Budget Management**
   - Shows: Daily Budget (15,000), Allocation breakdown (Swing 40%, Options 35%, Analysis 25%, Reserved 1,000)
   - Shows: Today's usage breakdown by category
   - Warning indicators: Yellow if > 70%, Red if > 90%

3. **Agent Configuration Panel**
   - Editable settings:
     - Max tokens per session (default 10,000)
     - Planning frequency (Daily 09:15, Weekly Monday 09:15, Monthly 1st)
     - Data fetch frequency (News every 1h, Earnings every 7 days, Fundamentals weekly)
     - Strategy settings (Swing strategy, Options strategy, Risk per trade 2%, Portfolio exposure <80%)
     - Recommendation thresholds (Auto-approve >90%, Manual 60-90%, Optional <60%)

4. **Task Queue Status**
   - Shows: Data Fetcher Queue and AI Analysis Queue
   - For each queue: In Progress tasks, Queued tasks, Performance metrics (avg task time, success rate)
   - Buttons: [Pause] [Resume] [Clear Queue]

5. **Claude Planning Section**
   - Shows: Last daily plan, Last weekly plan
   - Lists bullet points of focus areas and tasks
   - Buttons: [Trigger Daily Plan] [Trigger Weekly Plan]

6. **Recommendation Approvals**
   - Pending recommendations with: Symbol, Action (BUY/SELL/HOLD), Confidence %, Price, Rationale
   - Buttons per recommendation: [Approve] [Reject] [Discuss]
   - Stats: Pending (X), Approved today (X), Rejected today (X)
   - Batch action: [Bulk Approve Top 3] [Clear All]

### Test Cases

**TC-AGENTS-1: Agent Status Dashboard shows all agents**
- Step 1: Navigate to `/agents`
- Step 2: Check "Active Agents" tab is visible
- Step 3: Verify Claude Main Agent card shows: Status icon, Last action time, Token usage bar, Next scheduled task
- Step 4: Verify 4 sub-agents visible: Morning Prep (Swing), Morning Prep (Options), Evening Review (Swing), Evening Review (Options)
- Step 5: Verify [Trigger] button present for each agent
- Expected: 5+ agent cards visible with status and scheduling info
- Screenshot: agents_status_dashboard.png

**TC-AGENTS-2: Token Budget shows allocation and usage**
- Step 1: Check Token Budget Management section visible
- Step 2: Verify shows: Daily Budget 15,000, Allocation bars (Swing 40%, Options 35%, Analysis 25%)
- Step 3: Verify "Today's Usage" section shows breakdown:
   - Swing prep: 2,500
   - Options prep: 2,000
   - News analysis: 1,500
   - Recommendations: 1,200
   - Learning logs: 800
- Step 4: Verify warning indicator color (Yellow if > 70%, Red if > 90%)
- Step 5: Verify "Remaining: X tokens" displayed
- Expected: Full allocation breakdown shown, remaining tokens calculated correctly
- Screenshot: agents_token_budget.png

**TC-AGENTS-3: Configuration Panel has editable fields**
- Step 1: Click "Configuration" tab
- Step 2: Verify "Max tokens per session" input field (default 10,000)
- Step 3: Verify "Planning frequency" settings:
   - Daily time: Time picker showing 09:15 IST
   - Weekly day: Dropdown showing Monday
   - Monthly day: Number picker showing 1
- Step 4: Verify "Data fetch frequency" dropdowns:
   - News: Every 1 hour
   - Earnings: Every 7 days
   - Fundamentals: Weekly
- Step 5: Verify "Strategy settings" sliders for Risk per trade (2%) and Portfolio exposure (<80%)
- Step 6: Verify [Save Settings] button present
- Expected: All settings visible and editable
- Screenshot: agents_configuration.png

**TC-AGENTS-4: Task Queue Status shows queued tasks**
- Step 1: Check Task Queue Status section visible
- Step 2: Verify "Data Fetcher Queue" section shows:
   - In Progress task with progress bar and time remaining
   - 2+ Queued tasks listed
- Step 3: Verify "AI Analysis Queue" section shows:
   - In Progress task with progress bar
   - 2+ Queued tasks listed
- Step 4: Verify performance metrics shown: Avg task time (45 sec), Success rate (98.5%)
- Step 5: Verify queue control buttons: [Pause] [Resume] [Clear Queue]
- Expected: 3+ tasks in Data Fetcher Queue, 4+ tasks in AI Analysis Queue
- Screenshot: agents_task_queue.png

**TC-AGENTS-5: Claude Planning shows daily and weekly plans**
- Step 1: Check Claude Planning section visible
- Step 2: Verify "Last daily plan: Today 09:15" shown with bullet points:
   - "Focus on momentum breakouts"
   - "Monitor NIFTY for 23000 breakout"
   - "Check earnings for TCS, INFY today"
- Step 3: Verify "Last weekly plan: Monday 09:15" shown with bullet points
- Step 4: Verify [Trigger Daily Plan] and [Trigger Weekly Plan] buttons present
- Step 5: Click [Trigger Daily Plan] and verify action triggered
- Expected: Current plans displayed with focus areas and tasks
- Screenshot: agents_planning.png

**TC-AGENTS-6: Recommendation Approvals shows pending decisions**
- Step 1: Check Recommendation Approvals section visible
- Step 2: Verify "Pending (3)" section shows 3 recommendations:
   - [BUY] INFY @ ₹3,200 | Confidence: 92% | Rationale visible
   - [SELL] TCS @ ₹4,500 | Confidence: 78% | Rationale visible
   - [HOLD] HDFC | Confidence: 65% | Rationale visible
- Step 3: Verify buttons for each: [Approve] [Reject] [Discuss]
- Step 4: Verify stats shown: Approved today (2), Rejected today (0), Discussed today (1)
- Step 5: Click [Approve] on one recommendation and verify status changes
- Expected: 3 pending recommendations with full details and action buttons
- Screenshot: agents_recommendations.png

---

## Page 4: Paper Trading

**Route**: `/paper-trading`
**Documentation**: `documentation/paper_trading_page.md`

### Expected Components (Swing Trading Tab)

1. **Account Status Card**
   - Shows: Balance (₹1,02,500), Today P&L (+₹500), Monthly ROI (2.5%), Win Rate (65%), Active Strategy (Momentum + RSI)
   - Shows: Cash Available, Deployed Capital

2. **Active Positions Table**
   - Columns: Symbol, Entry Date, Entry Price, Qty, LTP, P&L (₹), %, Days, Target, SL
   - Actions per position: [Set Exit] [Set Stop Loss] [Manual Exit]

3. **Closed Trades Journal**
   - Columns: Date, Symbol, Entry, Exit, Qty, Hold, P&L (₹), %, Strategy, Notes
   - Filters: Today, This Week, This Month, All
   - Sort options: By P&L, By Date, By Strategy

4. **Daily Strategy Log**
   - Shows: What worked today, What didn't work, Tomorrow's focus, Token usage

5. **Trade Setup Controls**
   - Symbol selector with indicators, Buy/Sell form, Strategy tag selector, [Execute] button

6. **Performance Analytics**
   - Win/Loss chart (30 days), Strategy effectiveness bars, Top/Bottom stocks

### Expected Components (Options Trading Tab)

1. **Account Status Card (Options)**
   - Shows: Balance (₹98,500), Premium Collected (₹5,500), Premium Paid (₹2,000), Monthly ROI (-1.5%), Hedge Effectiveness (92%)

2. **Open Positions - Hedging Strategy**
   - Columns: Type, Symbol, Expiry, Strike, Entry, Current, Qty, P&L, Hedge
   - Example: Call Spread: NIFTY 23000/23200 CE | 10 lots | +200

3. **Closed Positions**
   - Columns: Expiry, Type, Symbol, Premium, Expiration, P&L, Hedge Ratio

4. **Daily Strategy Log (PR Sundar)**
   - Shows: Market analysis, Hedging decisions, Position adjustments, Tomorrow's plan

5. **Greeks & Risk Dashboard**
   - Shows: Portfolio Delta, Portfolio Theta, Max Loss, Break Even range

6. **Option Chain Quick Setup**
   - Symbol selector, Expiry selector, Greeks display, Spread suggestions, [Create Position] button

### Test Cases

**TC-PAPER-1: Swing Trading tab loads with account status**
- Step 1: Navigate to `/paper-trading`
- Step 2: Verify "Swing Trading" tab is visible and selected
- Step 3: Check Account Status Card shows:
   - Balance: ₹102,500+ (formatted with Indian currency)
   - Today P&L: +₹500 (green if positive)
   - Monthly ROI: 2.5%
   - Win Rate: 65%
   - Active Strategy: Momentum + RSI
- Step 4: Verify Cash Available and Deployed Capital shown
- Expected: Full account status visible with correct formatting
- Screenshot: paper_trading_swing_status.png

**TC-PAPER-2: Active Positions table shows open trades**
- Step 1: Check Active Positions table visible under Swing tab
- Step 2: Verify columns visible: Symbol, Entry Date, Entry Price, Qty, LTP, P&L, %, Days, Target, SL
- Step 3: Verify at least 3 active positions shown with sample data
- Step 4: Verify action buttons present for each: [Set Exit] [Set Stop Loss] [Manual Exit]
- Step 5: Click [Set Stop Loss] on one position and verify modal opens
- Expected: 3+ active positions with full details and action buttons
- Screenshot: paper_trading_positions.png

**TC-PAPER-3: Closed Trades Journal shows trade history**
- Step 1: Check Closed Trades Journal visible
- Step 2: Verify columns visible: Date, Symbol, Entry, Exit, Qty, Hold, P&L, %, Strategy, Notes
- Step 3: Verify at least 10 closed trades shown
- Step 4: Verify filters visible: [Today] [Week] [Month] [All]
- Step 5: Click [Month] filter and verify trades filtered to current month
- Step 6: Verify sort options present: By P&L, By Date, By Strategy
- Expected: 10+ closed trades visible with filters and sort options
- Screenshot: paper_trading_closed_trades.png

**TC-PAPER-4: Daily Strategy Log shows Claude's reflection**
- Step 1: Check Daily Strategy Log section visible
- Step 2: Verify "What worked today:" section shows bullet points
   - Example: "RSI divergence at support worked 2/3 times"
- Step 3: Verify "What didn't work:" section shows bullet points
   - Example: "Breakout on low volume failed once"
- Step 4: Verify "Tomorrow's focus:" section shows bullet points
- Step 5: Verify token usage bar shown (e.g., 2,500 / 10,000)
- Step 6: Verify [Save Strategy Notes] button present
- Expected: Full daily reflection with all 3 sections populated
- Screenshot: paper_trading_strategy_log.png

**TC-PAPER-5: Trade Setup Controls allow new trade execution**
- Step 1: Check Trade Setup Controls section visible
- Step 2: Verify Symbol selector dropdown with stock options
- Step 3: Verify Buy/Sell toggle buttons
- Step 4: Verify Entry Price field (auto-filled with LTP)
- Step 5: Verify Quantity input field
- Step 6: Verify Exit Target (%) field
- Step 7: Verify Stop Loss (%) field
- Step 8: Verify Strategy Tag selector dropdown
- Step 9: Verify [Execute] button enabled when form valid
- Expected: All form fields visible and functional
- Screenshot: paper_trading_trade_setup.png

**TC-PAPER-6: Performance Analytics show charts and metrics**
- Step 1: Check Performance Analytics section visible
- Step 2: Verify Win/Loss chart displayed (30-day history)
   - Green bars = profits
   - Red bars = losses
- Step 3: Verify Strategy Effectiveness bars shown for each strategy
- Step 4: Verify Top/Bottom stocks displayed
   - Top 5 stocks by ROI
   - Bottom 5 stocks by ROI
- Expected: All 3 analytics sections visible with data
- Screenshot: paper_trading_analytics.png

**TC-PAPER-7: Options Trading tab loads with account status**
- Step 1: Click "Options Trading" tab
- Step 2: Verify tab switched to options view
- Step 3: Check Account Status Card (Options) shows:
   - Balance: ₹98,500
   - Premium Collected: ₹5,500 (green)
   - Premium Paid: ₹2,000 (red)
   - Monthly ROI: -1.5% (red if negative)
   - Hedge Effectiveness: 92%
- Expected: Options account status visible with correct values
- Screenshot: paper_trading_options_status.png

**TC-PAPER-8: Options Open Positions show hedging strategy**
- Step 1: Check Open Positions (Hedging Strategy) table visible
- Step 2: Verify columns: Type, Symbol, Expiry, Strike, Entry, Current, Qty, P&L, Hedge
- Step 3: Verify at least 2 positions shown:
   - Example: Call Spread: NIFTY 23000/23200 CE | 10 lots | +200
- Step 4: Verify action buttons: [Adjust] [Close] [Extend]
- Expected: 2+ hedging positions visible with full Greeks
- Screenshot: paper_trading_options_positions.png

**TC-PAPER-9: Greeks & Risk Dashboard shows portfolio Greeks**
- Step 1: Check Greeks & Risk Dashboard visible
- Step 2: Verify Portfolio Delta shown with gauge (0.25 = slightly bullish)
- Step 3: Verify Portfolio Theta shown (+100 = time decay favorable)
- Step 4: Verify Portfolio Gamma displayed
- Step 5: Verify Portfolio Vega displayed
- Step 6: Verify Max Loss shown (₹8,000)
- Step 7: Verify Break Even range shown (±2%)
- Expected: All Greeks displayed with correct values
- Screenshot: paper_trading_greeks.png

**TC-PAPER-10: Option Chain Quick Setup allows position creation**
- Step 1: Check Option Chain Quick Setup section visible
- Step 2: Verify Symbol selector (NIFTY, BANKNIFTY, or stocks with options)
- Step 3: Verify Expiry selector dropdown with available expiries
- Step 4: Verify Greeks table displayed with option chain
   - Columns: Strike, Call Delta, Call Theta, Put Delta, Put Theta, etc.
- Step 5: Verify Spread suggestions shown (e.g., "Create call spreads", "Create put spreads")
- Step 6: Verify [Create Position] button enabled when strikes selected
- Expected: Full option chain table with Greeks and position creation
- Screenshot: paper_trading_option_chain.png

---

## Page 5: AI Transparency

**Route**: `/ai-transparency`
**Documentation**: Read from dashboard_page.md (AI transparency features)

### Expected Components

1. **Page Title & Description**
   - Title: "AI Transparency Center"
   - Subtitle: "Complete visibility into Claude's learning and trading process"

2. **Information Cards (4)**
   - Research Tracking: "See what data sources Claude uses..."
   - Decision Analysis: "Understand Claude's step-by-step reasoning..."
   - Execution Monitoring: "Monitor trade execution quality..."
   - Learning Progress: "Track how Claude evaluates strategies daily..."

3. **Trust Statement Section**
   - "Transparency You Can Trust" with detailed explanation

4. **Tabbed Interface (5 Tabs)**
   - Trades: Trade decision logs with reasoning
   - Reflections: Daily strategy reflections and learnings
   - Recommendations: Trade recommendations with analysis
   - Sessions: Historical Claude sessions and summaries
   - Analytics: Performance attribution and insights

### Test Cases

**TC-AI-TRANS-1: Page title and intro cards visible**
- Step 1: Navigate to `/ai-transparency`
- Step 2: Verify page title: "AI Transparency Center" displayed
- Step 3: Verify subtitle: "Complete visibility into Claude's learning and trading process"
- Step 4: Verify 4 information cards visible:
   - Research Tracking
   - Decision Analysis
   - Execution Monitoring
   - Learning Progress
- Step 5: Verify each card has icon, title, and description text
- Expected: All intro cards visible with proper formatting
- Screenshot: ai_trans_intro.png

**TC-AI-TRANS-2: Trust Statement section explains transparency**
- Step 1: Scroll to "Transparency You Can Trust" section
- Step 2: Verify heading visible: "Transparency You Can Trust"
- Step 3: Verify detailed explanation text visible:
   - "Every decision Claude makes is logged and explained..."
   - "You can see exactly how it analyzes markets..."
   - "No black boxes - just clear, comprehensive visibility..."
- Step 4: Verify section properly formatted with icon
- Expected: Trust statement section complete and readable
- Screenshot: ai_trans_trust.png

**TC-AI-TRANS-3: Tabbed interface shows all 5 tabs**
- Step 1: Check tablist visible with 5 tabs
- Step 2: Verify tabs: Trades, Reflections, Recommendations, Sessions, Analytics
- Step 3: Verify first tab "Trades" is selected by default
- Step 4: Verify all tabs are clickable
- Expected: All 5 tabs visible and accessible
- Screenshot: ai_trans_tabs.png

**TC-AI-TRANS-4: Trades tab shows decision logs**
- Step 1: Verify "Trades" tab is selected
- Step 2: Check tab content area shows trade decision logs
- Step 3: Verify each trade shows: Symbol, Entry, Exit, Confidence, Reasoning
- Step 4: Verify trades are sortable/filterable
- Expected: Trade logs displayed with Claude's reasoning
- Screenshot: ai_trans_trades.png

**TC-AI-TRANS-5: Click tabs to switch content**
- Step 1: Click "Reflections" tab
- Step 2: Verify tab switched and content changed
- Step 3: Verify shows daily strategy reflections
- Step 4: Click "Recommendations" tab and verify content changed
- Step 5: Click "Sessions" tab and verify content changed
- Step 6: Click "Analytics" tab and verify content changed
- Expected: All tabs switch content correctly
- Screenshot: ai_trans_tab_switching.png

---

## Page 6: System Health

**Route**: `/system-health`
**Documentation**: dashboard_page.md (System Health Monitor section)

### Expected Components

1. **Page Title & Description**
   - Title: "System Health"
   - Subtitle: "Monitor backend systems, schedulers, and infrastructure"

2. **Status Cards (4)**
   - Schedulers: "Healthy" | "Last run: 2025-10-24T05:43:19.576Z"
   - Queues: "5" | "Total tasks queued"
   - Database: "Connected" | "Connections: 10"
   - Alerts: "0" | "Recent errors"

3. **Tabbed Interface (5 Tabs)**
   - Schedulers: Scheduler status and last run times
   - Queues: Queue health and task counts
   - Database: Database connection and performance metrics
   - Resources: CPU, Memory, Disk usage
   - Errors: Recent errors and alerts

### Test Cases

**TC-SYS-1: System Health page loads with status cards**
- Step 1: Navigate to `/system-health`
- Step 2: Verify page title: "System Health" displayed
- Step 3: Verify subtitle visible
- Step 4: Verify 4 status cards visible:
   - Schedulers: Status + last run time
   - Queues: Count of queued tasks
   - Database: Connection status + count
   - Alerts: Recent error count
- Expected: All 4 status cards visible and populated
- Screenshot: system_health_status_cards.png

**TC-SYS-2: Tab interface shows 5 tabs**
- Step 1: Check tablist visible with 5 tabs
- Step 2: Verify tabs: Schedulers, Queues, Database, Resources, Errors
- Step 3: Verify first tab "Schedulers" selected by default
- Step 4: Verify all tabs clickable
- Expected: All 5 tabs visible
- Screenshot: system_health_tabs.png

**TC-SYS-3: Schedulers tab shows scheduler status**
- Step 1: Verify "Schedulers" tab is selected
- Step 2: Check tab shows scheduler list with status
- Step 3: Verify data shown: Status, Last Run, Next Run
- Step 4: Verify status indicators (green/yellow/red)
- Expected: Scheduler status displayed correctly
- Screenshot: system_health_schedulers.png

**TC-SYS-4: Switch between tabs shows different content**
- Step 1: Click "Queues" tab
- Step 2: Verify content changed to show queue status
- Step 3: Click "Database" tab and verify content changed
- Step 4: Click "Resources" tab and verify content changed
- Step 5: Click "Errors" tab and verify content changed
- Expected: All tabs show correct content when clicked
- Screenshot: system_health_tab_switching.png

---

## Page 7: Configuration

**Route**: `/config`
**Documentation**: `documentation/configuration_page.md`

### Expected Components

1. **Scheduler Configuration**
   - Portfolio Scan Frequency: Every 60 min (editable)
   - News Monitoring: Daily at 16:00 (editable)
   - Earnings Check: Weekly, every 7 days (editable)
   - Fundamental Re-check: Automatic on material news (toggle)
   - Market hours: 09:15 - 15:30 IST

2. **Trading Configuration**
   - Environment: Paper Trading (toggle to Live)
   - Paper capital allocation: Swing ₹1,00,000, Options ₹1,00,000
   - Risk settings: Max position 5%, Portfolio max 10%, Stop loss 2%
   - Trade approval: Auto-approve toggle

3. **AI Agent Configuration**
   - Daily tokens budget: 15,000 (editable)
   - Daily planning time: 09:15 IST (editable)
   - Weekly planning day: Monday (editable)
   - Token allocations: Swing 40%, Options 35%, Analysis 25%

4. **Data Source Configuration**
   - Perplexity API key: [****] [Change]
   - Query templates (News, Earnings, Fundamentals)
   - Query versioning: ON/OFF toggle

5. **Database Configuration**
   - Database path: /data/robo-trader.db
   - Backup frequency: Daily (editable)
   - Backup retention: 7 days (editable)
   - [Backup Now] [Restore] buttons

6. **Broker Configuration (if Live)**
   - Broker: Zerodha Kite
   - API key, API secret, Account ID
   - [Save Credentials] button

### Test Cases

**TC-CONFIG-1: Page loads with configuration sections**
- Step 1: Navigate to `/config`
- Step 2: Verify page title/breadcrumb shows "Configuration"
- Step 3: Verify sections visible:
   - Scheduler Configuration
   - Trading Configuration
   - AI Agent Configuration
   - Data Source Configuration
   - Database Configuration
- Expected: All configuration sections visible
- Screenshot: config_page.png

**TC-CONFIG-2: Scheduler settings are editable**
- Step 1: Check Scheduler Configuration section
- Step 2: Verify "Portfolio Scan Frequency" field editable (currently 60 min)
- Step 3: Verify "News Monitoring" time picker (currently 16:00)
- Step 4: Verify "Earnings Check" dropdown (currently 7 days)
- Step 5: Verify "Automatic on material news" toggle (currently ON)
- Step 6: Change "Portfolio Scan Frequency" to 30 min and verify saves
- Expected: All scheduler settings editable and persist
- Screenshot: config_scheduler.png

**TC-CONFIG-3: Trading configuration allows environment toggle**
- Step 1: Check Trading Configuration section
- Step 2: Verify "Environment" toggle: currently "Paper Trading"
- Step 3: Verify Paper capital allocation shown: Swing ₹1,00,000, Options ₹1,00,000
- Step 4: Verify Risk settings:
   - Max position size: 5% (editable)
   - Portfolio max risk: 10% (editable)
   - Stop loss default: 2% (editable)
- Step 5: Verify "Trade approval" toggle for auto-approve
- Step 6: Change "Max position size" to 7% and verify saves
- Expected: All trading settings editable
- Screenshot: config_trading.png

**TC-CONFIG-4: AI Agent configuration shows token budget**
- Step 1: Check AI Agent Configuration section
- Step 2: Verify "Daily tokens budget" field: 15,000 (editable)
- Step 3: Verify "Daily planning time" picker: 09:15 IST (editable)
- Step 4: Verify "Weekly planning day" dropdown: Monday (editable)
- Step 5: Verify token allocations (Swing 40%, Options 35%, Analysis 25%)
- Step 6: Change "Daily tokens budget" to 18,000 and verify saves
- Expected: All agent settings editable
- Screenshot: config_agent.png

**TC-CONFIG-5: Data Source config allows API key management**
- Step 1: Check Data Source Configuration section
- Step 2: Verify "Perplexity API key" field shown as [****] [Change]
- Step 3: Click [Change] button and verify modal opens
- Step 4: Verify query templates editable:
   - News: "Fetch latest news on [SYMBOL]"
   - Earnings: "Fetch earnings date for [SYMBOL]"
   - Fundamentals: "Fetch current fundamentals for [SYMBOL]"
- Step 5: Verify "Query versioning" toggle (currently ON)
- Expected: API key and query templates manageable
- Screenshot: config_data_source.png

**TC-CONFIG-6: Database and Backup settings visible**
- Step 1: Check Database Configuration section
- Step 2: Verify "Database path" shown: /data/robo-trader.db
- Step 3: Verify "Backup frequency" dropdown: Daily (editable)
- Step 4: Verify "Backup retention" field: 7 days (editable)
- Step 5: Verify [Backup Now] button present
- Step 6: Verify [Restore] button present
- Step 7: Click [Backup Now] and verify backup triggered
- Expected: Database settings and backup controls visible
- Screenshot: config_database.png

---

## Page 8: System Logs

**Route**: `/logs`
**Documentation**: `documentation/logs_page.md`

### Expected Components

1. **Real-Time Log Viewer**
   - Columns: Timestamp, Level, Component, Message
   - Filters: By Level (Error, Warning, Info, Debug)
   - Filters: By Component (Scheduler, Execution, AI, Risk, etc.)
   - Search: By message content
   - Auto-scroll: ON/OFF toggle
   - Clear logs button

2. **Error Summary**
   - Total errors today: Counter
   - Recent errors list with timestamps and messages

3. **Performance Metrics**
   - Scheduler tasks completed: X / Y (%)
   - Average task duration: XX sec
   - Failed tasks: X (Y% retry pending)
   - Database sync latency: Xms avg
   - WebSocket latency: Xms avg

### Test Cases

**TC-LOGS-1: Log viewer displays real-time logs**
- Step 1: Navigate to `/logs`
- Step 2: Verify page title/breadcrumb shows "System Logs"
- Step 3: Verify log viewer table visible with columns:
   - Timestamp
   - Level
   - Component
   - Message
- Step 4: Verify at least 20+ log entries displayed
- Step 5: Verify entries show example data:
   - Timestamps in ISO format
   - Level badges (INFO, WARNING, ERROR, DEBUG)
   - Component names (Scheduler, Execution, AI, etc.)
   - Log messages
- Expected: Log table populated with real data
- Screenshot: logs_viewer.png

**TC-LOGS-2: Log filters work correctly**
- Step 1: Check filter controls visible
- Step 2: Verify "Level" filter dropdown with options:
   - Error
   - Warning
   - Info
   - Debug
- Step 3: Verify "Component" filter dropdown with options:
   - Scheduler
   - Execution
   - AI
   - Risk
   - etc.
- Step 4: Select "ERROR" from Level filter and verify logs filtered
- Step 5: Select "Scheduler" from Component filter and verify filtered
- Expected: Filters reduce log list to matching entries
- Screenshot: logs_filtered.png

**TC-LOGS-3: Search functionality works**
- Step 1: Verify search input box visible
- Step 2: Type "error" in search box and verify logs filtered
- Step 3: Verify shows only logs containing "error" in message
- Step 4: Clear search and verify all logs reappear
- Step 5: Search for specific component name and verify filtered
- Expected: Search filters logs by message content
- Screenshot: logs_search.png

**TC-LOGS-4: Error Summary shows recent errors**
- Step 1: Check Error Summary section visible
- Step 2: Verify "Total errors today: X" counter shown
- Step 3: Verify recent errors list displayed with:
   - Timestamp (e.g., 14:23)
   - Error message
   - Error type
- Step 4: Verify at least 3 recent errors shown
- Example: "14:23 - API rate limit exceeded (Perplexity)"
- Expected: Error summary populated with current day's errors
- Screenshot: logs_error_summary.png

**TC-LOGS-5: Performance Metrics show system performance**
- Step 1: Check Performance Metrics section visible
- Step 2: Verify metrics displayed:
   - "Scheduler tasks completed: X / Y (ZZ%)"
   - "Average task duration: 2.3 min"
   - "Failed tasks: 2 (7% retry pending)"
   - "Database sync latency: 120ms avg"
   - "WebSocket latency: 45ms avg"
- Step 3: Verify percentages and times formatted correctly
- Expected: All performance metrics visible and populated
- Screenshot: logs_performance.png

**TC-LOGS-6: Auto-scroll and clear buttons work**
- Step 1: Verify "Auto-scroll" toggle visible (currently ON/OFF)
- Step 2: Verify "Clear logs" button visible
- Step 3: Toggle auto-scroll and verify behavior
- Step 4: Click "Clear logs" and verify confirmation dialog
- Step 5: Confirm clear and verify log table emptied (or showing only new logs)
- Expected: Auto-scroll and clear functionality work
- Screenshot: logs_controls.png

---

## Testing Execution Protocol

### Before Starting Tests

1. **Server Status Check**
   - Verify backend running: `docker-compose ps`
   - Verify frontend running: Vite dev server on port 3000
   - Navigate to http://localhost:3000 to verify page loads

2. **Browser Console Setup**
   - Open browser DevTools (F12)
   - Go to Console tab
   - Note any startup errors

3. **Screenshot Directory**
   - Create directory: `/test_screenshots/` in project root
   - Each screenshot named: `page-name_component_name.png`

### During Each Test

1. **Take Initial Screenshot**
   - Document page load and initial state
   - Filename: `page-name_initial.png`

2. **Execute Test Steps**
   - Follow steps exactly as written
   - Note any deviations from expected
   - Check browser console for errors

3. **Verify Data**
   - Confirm numbers match specifications
   - Verify formatting (currency, dates, percentages)
   - Check color coding (green/red for P&L)

4. **Take Action Screenshots**
   - Before clicking buttons: `page-name_before_action.png`
   - After actions complete: `page-name_after_action.png`

5. **Document Issues**
   - If test fails, note:
   - What was expected vs actual
   - Browser console errors
   - Network tab failures (if any)
   - Missing data or components

### Issue Documentation Template

```markdown
## Issue: [Brief Title]

**Severity**: [CRITICAL/HIGH/MEDIUM/LOW]
**Page**: [Page Name]
**Test Case**: [TC-PAGE-#]

**Expected**: [What specification says]
**Actual**: [What actually happened]

**Reproduction Steps**:
1. [Step 1]
2. [Step 2]
...

**Evidence**:
- Screenshot: [filename]
- Browser console: [error message]
- Network error: [if any]

**Root Cause**: [Your hypothesis]

**Impact**: [How this affects user]
```

### After Completion

1. **Create Summary Report**
   - Total test cases: X
   - Passed: X
   - Failed: X
   - Issues found: X
   - Screenshots taken: X

2. **Organize Artifacts**
   - Move all screenshots to `/test_screenshots/`
   - Collect issue reports
   - Document patterns/commonalities

3. **Update Documentation**
   - Note any specification gaps found
   - Update API endpoint expectations
   - Document actual vs expected data

---

## Success Criteria

✅ **All 8 pages load successfully**
✅ **All expected components visible on each page**
✅ **Data displays in correct format** (currency, percentages, dates)
✅ **All interactive elements functional** (buttons, tabs, filters)
✅ **No unhandled JavaScript errors in console**
✅ **API calls complete successfully** (or fail gracefully)
✅ **Color coding and indicators work correctly**
✅ **Navigation between pages works smoothly**
✅ **Forms are editable and changes persist**
✅ **All filters and search functionality work**

---

**Plan Created**: October 24, 2025
**Execution Method**: Browser automation (Playwright MCP)
**Target Completion**: All 8 pages, 100% specification coverage

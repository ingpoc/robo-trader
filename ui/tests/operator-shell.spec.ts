import { expect, test, type Page } from '@playwright/test'

const NOW = '2026-03-25T12:00:00.000Z'
const ACCOUNT_ID = 'paper_swing_main'

const accountFixture = {
  accountId: ACCOUNT_ID,
  accountName: 'Paper Trading Account',
  accountType: 'swing',
  riskLevel: 'moderate',
  currentBalance: 100000,
  marginAvailable: 76000,
  totalInvested: 24000,
  createdDate: NOW,
}

const jsonResponse = (payload: unknown, status = 200) => ({
  status,
  contentType: 'application/json',
  body: JSON.stringify(payload),
})

async function installShellMocks(page: Page) {
  await page.addInitScript(() => {
    class MockWebSocket {
      static CONNECTING = 0
      static OPEN = 1
      static CLOSING = 2
      static CLOSED = 3

      url: string
      readyState = MockWebSocket.CONNECTING
      onopen: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null
      onerror: ((event: Event) => void) | null = null
      onclose: ((event: CloseEvent) => void) | null = null

      constructor(url: string) {
        this.url = url
        window.setTimeout(() => {
          this.readyState = MockWebSocket.OPEN
          this.onopen?.(new Event('open'))
        }, 0)
      }

      send(_data?: string) {}

      close() {
        this.readyState = MockWebSocket.CLOSED
        this.onclose?.(new CloseEvent('close', { code: 1000, wasClean: true }))
      }
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      writable: true,
      value: MockWebSocket,
    })
  })

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const { pathname, searchParams } = url

    if (!pathname.startsWith('/api/')) {
      return route.continue()
    }

    if (pathname === '/api/dashboard') {
      return route.fulfill(
        jsonResponse({
          portfolio: {
            holdings: [],
            cash: { free: 76000, used: 24000, total: 100000 },
            exposure_total: 24000,
            summary: {
              accounts: 1,
              total_balance: 100000,
              cash_available: 76000,
              deployed_capital: 24000,
              active_positions: 0,
              unrealized_pnl: 0,
            },
          },
          analytics: {
            portfolio: {
              concentration_risk: 0.18,
              dominant_sector: 'Technology',
              active_accounts: 1,
            },
            paper_trading: {
              pnl: 1250,
              win_rate: 64,
              portfolio_value: 101250,
              unrealized_pnl: 0,
              total_closed_trades: 12,
              capability_status: 'ready',
              blockers: [],
            },
            portfolio_value: 101250,
            pnl_absolute: 1250,
            pnl_percentage: 1.25,
            win_rate: 64,
          },
          alerts: [],
          ai_status: {
            portfolio_health: 'healthy',
            current_task: 'idle',
            api_budget_used: 3,
            daily_api_limit: 25,
          },
          timestamp: NOW,
          intents: [],
        })
      )
    }

    if (pathname === '/api/paper-trading/accounts') {
      return route.fulfill(jsonResponse({ accounts: [accountFixture] }))
    }

    if (pathname === '/api/paper-trading/capabilities') {
      const accountId = searchParams.get('account_id')
      return route.fulfill(
        jsonResponse({
          mode: 'paper_trading',
          overall_status: 'ready',
          automation_allowed: true,
          generated_at: NOW,
          account_id: accountId,
          blockers: [],
          checks: [
            {
              key: 'claude_runtime',
              label: 'Claude Runtime',
              status: 'ready',
              blocking: false,
              summary: 'Claude runtime is ready for operator workflows.',
              detail: null,
              metadata: {},
            },
            {
              key: 'market_data',
              label: 'Market Data',
              status: 'ready',
              blocking: false,
              summary: 'Market data path is healthy.',
              detail: null,
              metadata: {},
            },
          ],
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/overview`) {
      return route.fulfill(
        jsonResponse({
          success: true,
          data: {
            account_id: ACCOUNT_ID,
            balance: 100000,
            deployed_capital: 24000,
            buying_power: 76000,
            cash_available: 76000,
            last_updated: NOW,
          },
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/positions`) {
      return route.fulfill(jsonResponse({ success: true, positions: [] }))
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/trades`) {
      return route.fulfill(jsonResponse({ success: true, trades: [] }))
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/performance`) {
      return route.fulfill(
        jsonResponse({
          success: true,
          performance: {
            winning_trades: 8,
            losing_trades: 4,
            win_rate: 66.7,
            avg_win: 420,
            avg_loss: -190,
            profit_factor: 1.9,
            best_trade: 900,
            worst_trade: -320,
            largest_win_streak: 4,
            largest_loss_streak: 2,
            total_pnl: 1250,
            max_drawdown: -540,
            max_drawdown_pct: -0.9,
            sharpe_ratio: 1.4,
            return_on_equity: 1.25,
          },
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/discovery`) {
      return route.fulfill(
        jsonResponse({
          status: 'ready',
          generated_at: NOW,
          blockers: [],
          context_mode: 'paper_trading',
          artifact_count: 1,
          candidates: [
            {
              candidate_id: 'candidate-infy',
              symbol: 'INFY',
              company_name: 'Infosys',
              sector: 'Technology',
              source: 'screening',
              priority: 'high',
              confidence: 0.68,
              rationale: 'Relative strength remains constructive.',
              next_step: 'Open focused research',
              generated_at: NOW,
            },
          ],
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/research`) {
      return route.fulfill(
        jsonResponse({
          status: 'blocked',
          generated_at: NOW,
          blockers: ['Select a discovery candidate to run focused research.'],
          context_mode: 'paper_trading',
          artifact_count: 0,
          research: null,
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/decisions`) {
      return route.fulfill(
        jsonResponse({
          status: 'blocked',
          generated_at: NOW,
          blockers: ['No decision packet is available yet.'],
          context_mode: 'paper_trading',
          artifact_count: 0,
          decisions: [],
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/review`) {
      return route.fulfill(
        jsonResponse({
          status: 'ready',
          generated_at: NOW,
          blockers: [],
          context_mode: 'paper_trading',
          artifact_count: 1,
          review: {
            review_id: 'review-1',
            summary: 'Paper-trading review is available for the selected account.',
            strengths: ['Entry discipline stayed consistent.'],
            weaknesses: ['A few setups arrived late in the session.'],
            risk_flags: [],
            top_lessons: ['Keep position sizing bounded to the signal quality.'],
            strategy_proposals: [],
            generated_at: NOW,
          },
        })
      )
    }

    if (pathname === '/api/monitoring/status') {
      return route.fulfill(
        jsonResponse({
          status: 'healthy',
          timestamp: NOW,
          blockers: [],
          initialization: {
            orchestrator_initialized: true,
            bootstrap_completed: true,
            initialization_errors: [],
            last_error: null,
          },
          components: {
            orchestrator: {
              status: 'healthy',
              initialized: true,
              summary: 'Core runtime initialized.',
            },
            database: {
              status: 'healthy',
              summary: 'Database connected.',
              connections: 1,
              portfolioLoaded: true,
            },
            event_bus: {
              status: 'healthy',
              summary: 'Event bus active.',
            },
            websocket: {
              status: 'healthy',
              summary: 'This operator session is connected to the live WebSocket.',
              clients: 1,
            },
          },
        })
      )
    }

    if (pathname === '/api/configuration/ai-agents') {
      return route.fulfill(
        jsonResponse({
          ai_agents: {
            focused_research: {
              enabled: true,
              useClaude: true,
              tools: ['web_search', 'market_data'],
              responseFrequency: 15,
              responseFrequencyUnit: 'minutes',
              scope: 'watchlist',
              maxTokensPerRequest: 2000,
            },
          },
        })
      )
    }

    if (pathname === '/api/configuration/global-settings') {
      return route.fulfill(
        jsonResponse({
          global_settings: {
            claudeUsage: {
              enabled: true,
              dailyTokenLimit: 50000,
              costAlerts: true,
              costThreshold: 0.8,
            },
            schedulerDefaults: {
              defaultFrequency: 15,
              defaultFrequencyUnit: 'minutes',
              marketHoursOnly: true,
              retryAttempts: 3,
              retryDelayMinutes: 5,
            },
            maxTurns: 5,
            riskTolerance: 5,
            dailyApiLimit: 25,
            quoteStreamProvider: 'zerodha_kite',
            quoteStreamMode: 'ltpc',
            quoteStreamSymbolLimit: 50,
          },
        })
      )
    }

    return route.fulfill(jsonResponse({ status: 'ok' }))
  })
}

test.describe('Operator Shell', () => {
  test.beforeEach(async ({ page }) => {
    await installShellMocks(page)
  })

  test('loads the app shell and primary navigation', async ({ page }) => {
    await page.goto('/')

    await expect(page).toHaveTitle(/Robo Trader/i)
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Paper Trading' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'System Health' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Configuration' })).toBeVisible()
  })

  test('navigates across the four mission-aligned routes', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Paper Trading' }).click()
    await expect(page).toHaveURL(/\/paper-trading$/)
    await expect(page.getByText('Paper Trading Account', { exact: true })).toBeVisible()

    await page.getByRole('link', { name: 'System Health' }).click()
    await expect(page).toHaveURL(/\/system-health$/)
    await expect(page.getByRole('heading', { name: 'System Health' })).toBeVisible()

    await page.getByRole('link', { name: 'Configuration' }).click()
    await expect(page).toHaveURL(/\/configuration$/)
    await expect(page.getByRole('heading', { name: 'Configuration' })).toBeVisible()

    await page.getByRole('link', { name: 'Overview' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
  })

  test('does not expose removed top-level routes in the navigation', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('link', { name: 'News & Earnings' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'AI Transparency' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Agents' })).toHaveCount(0)
  })
})

import { execSync } from 'node:child_process'
import { expect, test, type Page } from '@playwright/test'

const NOW = '2026-03-25T12:00:00.000Z'
const ACCOUNT_ID = 'paper_swing_main'
const GIT_SHA = execSync('git rev-parse HEAD', {
  stdio: ['ignore', 'pipe', 'ignore'],
}).toString().trim()
const GIT_SHORT_SHA = GIT_SHA.slice(0, 12)

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

interface ShellMockOptions {
  overviewFailure?: {
    status: number
    payload: unknown
  }
}

async function installShellMocks(page: Page, options: ShellMockOptions = {}) {
  await page.addInitScript(() => {
    const registeredTools = new Map<string, { name: string; description: string; inputSchema: Record<string, unknown>; execute: (input?: Record<string, unknown>) => unknown | Promise<unknown> }>()

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

    Object.defineProperty(navigator, 'modelContext', {
      configurable: true,
      writable: true,
      value: {
        registerTool(tool: { name: string; description: string; inputSchema: Record<string, unknown>; execute: (input?: Record<string, unknown>) => unknown | Promise<unknown> }) {
          if (registeredTools.has(tool.name)) {
            throw new Error(`Duplicate tool name: ${tool.name}`)
          }
          registeredTools.set(tool.name, tool)
        },
      },
    })

    Object.defineProperty(navigator, 'modelContextTesting', {
      configurable: true,
      writable: true,
      value: {
        async listTools() {
          return Array.from(registeredTools.values()).map(tool => ({
            name: tool.name,
            description: tool.description,
            inputSchema: JSON.stringify(tool.inputSchema ?? {}),
          }))
        },
        async executeTool(name: string, input = '{}') {
          const tool = registeredTools.get(name)
          if (!tool) {
            throw new Error(`Unknown tool: ${name}`)
          }
          const parsedInput = typeof input === 'string' && input ? JSON.parse(input) : {}
          const result = await tool.execute(parsedInput)
          return typeof result === 'string' ? result : JSON.stringify(result)
        },
      },
    })
  })

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const { pathname, searchParams } = url

    if (!pathname.startsWith('/api/')) {
      return route.continue()
    }

    if (pathname === '/api/health') {
      return route.fulfill(
        jsonResponse({
          status: 'healthy',
          message: 'API container is initialized.',
          runtime_identity: {
            runtime: 'backend',
            git_sha: GIT_SHA,
            git_short_sha: GIT_SHORT_SHA,
            build_id: `backend-${GIT_SHORT_SHA}-${NOW}`,
            started_at: NOW,
            workspace_path: '/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader',
          },
          components: {
            container: 'initialized',
            background_orchestrator: 'disabled',
            runtime_mode: 'request_driven',
          },
          active_lane: {
            base_url: 'http://127.0.0.1:8000',
            host: '127.0.0.1',
            port: 8000,
          },
          callback_listener: {
            port: 8010,
            active: false,
          },
          ai_runtime_quota: {
            usage_limited: false,
            retry_at: null,
            last_error: null,
          },
          readiness: {
            container: 'ready',
            ai_runtime: { status: 'ready' },
            quote_stream: { status: 'ready' },
            market_data: { status: 'ready' },
          },
          timestamp: NOW,
        }),
      )
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

    if (pathname === '/api/configuration/status') {
      return route.fulfill(
        jsonResponse({
          configuration_status: {
            status: 'manual_only',
            manualOnly: true,
            backgroundSchedulers: {
              status: 'removed',
              active: 0,
              message: 'All executions must be operator triggered.',
            },
            aiAgents: {
              configured: 1,
              enabled: 1,
            },
            aiRuntime: {
              provider: 'codex',
              authenticated: true,
              ready: true,
              checkedAt: NOW,
              lastSuccessfulValidationAt: NOW,
              readinessTtlSeconds: 120,
              error: null,
            },
            globalSettings: {
              claudeEnabled: true,
              claudeDailyTokenLimit: 120000,
              claudeCostAlerts: true,
              claudeCostThreshold: 10,
              dailyApiLimit: 25,
              quoteStreamProvider: 'zerodha_kite',
              quoteStreamMode: 'ltpc',
              quoteStreamSymbolLimit: 50,
            },
            effectiveQuoteStream: {
              provider: 'zerodha_kite',
              mode: 'ltpc',
              symbolLimit: 50,
            },
            effectiveExecutionPosture: {
              mode: 'operator_confirmed_execution',
              account_id: ACCOUNT_ID,
              source: 'paper_trading_account_policy',
            },
            persistence: {
              source: 'database_first',
              global_settings_loaded: true,
              ai_agents_loaded: true,
              checkedAt: NOW,
            },
            runtimeIdentityLink: {
              source: '/api/health',
              field: 'runtime_identity',
            },
            checkedAt: NOW,
          },
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/operator-snapshot`) {
      if (options.overviewFailure) {
        return route.fulfill(jsonResponse(options.overviewFailure.payload, options.overviewFailure.status))
      }

      return route.fulfill(
        jsonResponse({
          generated_at: NOW,
          selected_account_id: ACCOUNT_ID,
          execution_mode: 'operator_confirmed_execution',
          account_policy: {
            account_id: ACCOUNT_ID,
            execution_mode: 'operator_confirmed_execution',
            max_open_positions: 8,
            max_new_entries_per_day: 3,
            max_deployed_capital_pct: 80,
            default_stop_loss_pct: 5,
            default_target_pct: 10,
            per_trade_exposure_pct: 5,
            max_portfolio_risk_pct: 10,
            risk_level: 'moderate',
            updated_at: NOW,
            created_at: NOW,
          },
          overview_summary: {
            generated_at: NOW,
            account_id: ACCOUNT_ID,
            execution_mode: 'operator_confirmed_execution',
            selected_account: {
              account_id: ACCOUNT_ID,
              buying_power: 76000,
              cash_available: 76000,
              deployed_capital: 24000,
              balance: 100000,
              position_count: 0,
              valuation_status: 'live',
              valuation_detail: null,
              mark_freshness: 'ready',
            },
            readiness: {
              overall_status: 'ready',
              blocker_count: 0,
              first_blocker: null,
            },
            next_action: {
              summary: 'Run focused research on the top candidate or review open positions.',
              detail: 'The operator path is ready for monitored research and operator-confirmed actions.',
              route: '/paper-trading',
            },
            act_now: [
              {
                label: 'Evaluate closed trades',
                detail: '1 closed trade still needs outcome evaluation.',
                priority: 'medium',
              },
            ],
            staleness: {
              discovery: { status: 'fresh', age_seconds: 60 },
              review: { status: 'fresh', age_seconds: 120 },
            },
            queue: {
              unevaluated_closed_trades: 1,
              queued_promotable_improvements: 2,
              decision_pending_improvements: 1,
              recent_runs: 4,
              ready_now_promotions: 1,
            },
            performance: {
              portfolio_value: 101250,
              unrealized_pnl: 1250,
              win_rate: 64,
              closed_trades: 12,
            },
            recent_stage_outputs: [
              { label: 'Discovery', status: 'ready', generated_at: NOW, last_generated_at: NOW, freshness_state: 'fresh', status_reason: 'Fresh discovery list available.', considered_count: 2 },
              { label: 'Focused Research', status: 'blocked', generated_at: NOW, last_generated_at: NOW, freshness_state: 'unknown', empty_reason: 'requires_selection', status_reason: 'Select a candidate to run focused research.', considered_count: 1 },
              { label: 'Decision Review', status: 'blocked', generated_at: NOW, last_generated_at: NOW, freshness_state: 'unknown', empty_reason: 'no_candidates', status_reason: 'No open positions require action.', considered_count: 0 },
              { label: 'Daily Review', status: 'ready', generated_at: NOW, last_generated_at: NOW, freshness_state: 'fresh', status_reason: 'Recent review is available.', considered_count: 1 },
            ],
            guardrails: {
              execution_mode: 'operator_confirmed_execution',
              per_trade_exposure_pct: 5,
              max_portfolio_risk_pct: 10,
              max_open_positions: 8,
              max_new_entries_per_day: 3,
              max_deployed_capital_pct: 80,
            },
            incidents: [
              {
                incident_id: 'incident-1',
                status: 'degraded',
                summary: 'One improvement decision is pending operator review.',
                detail: 'Queued improvement evidence is ready for review.',
              },
            ],
          },
          configuration_status: {
            status: 'manual_only',
            manualOnly: true,
            checkedAt: NOW,
          },
          capability_snapshot: {
            mode: 'paper_trading',
            overall_status: 'ready',
            automation_allowed: true,
            generated_at: NOW,
            account_id: ACCOUNT_ID,
            blockers: [],
            checks: [
              {
                key: 'ai_runtime',
                label: 'AI Runtime',
                status: 'ready',
                blocking: false,
                summary: 'AI runtime is ready for operator workflows.',
                detail: null,
                metadata: {},
              },
              {
                key: 'broker_auth',
                label: 'Broker Auth',
                status: 'ready',
                blocking: false,
                summary: 'Broker auth is live.',
                detail: null,
                metadata: {},
              },
              {
                key: 'quote_stream',
                label: 'Quote Stream',
                status: 'ready',
                blocking: false,
                summary: 'Quote stream is connected.',
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
              {
                key: 'paper_account',
                label: 'Selected Account',
                status: 'ready',
                blocking: false,
                summary: 'Selected account is ready.',
                detail: null,
                metadata: {},
              },
            ],
          },
          queue_status: { stats: { total_pending_tasks: 0, total_active_tasks: 0 } },
          overview: {
            account_id: ACCOUNT_ID,
            balance: 100000,
            deployed_capital: 24000,
            buying_power: 76000,
            cash_available: 76000,
            last_updated: NOW,
          },
          positions: [],
          trades: [],
          performance: {
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
          },
          discovery: {
            status: 'ready',
            generated_at: NOW,
            blockers: [],
            context_mode: 'paper_trading',
            artifact_count: 1,
            criteria: [
              'Show discovery candidates only when confidence is at least 0.45.',
              'Promote to focused research only when confidence is at least 0.60.',
            ],
            considered: [
              'INFY · 68% · research-ready',
              'TCS · below discovery threshold of 0.45',
            ],
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
          },
          research: {
            status: 'blocked',
            generated_at: NOW,
            blockers: ['Select a discovery candidate to run focused research.'],
            context_mode: 'paper_trading',
            artifact_count: 0,
            criteria: [
              'Research runs one candidate at a time from discovery or an explicit symbol selection.',
              'Actionable research requires thesis confidence at least 0.60 and zero blockers.',
            ],
            considered: ['No candidate is currently staged for focused research.'],
            research: null,
          },
          decisions: {
            status: 'blocked',
            generated_at: NOW,
            blockers: ['No open positions currently require decision review.'],
            context_mode: 'paper_trading',
            artifact_count: 0,
            criteria: ['Decision review considers open positions only; it does not generate new entries.'],
            considered: ['No open positions are being reviewed because the stage is blocked.'],
            decisions: [],
          },
          review: {
            status: 'ready',
            generated_at: NOW,
            blockers: [],
            context_mode: 'paper_trading',
            artifact_count: 1,
            criteria: ['Daily review is observational unless confidence clears the promotion threshold.'],
            considered: ['INFY · recent realized outcome in review memory'],
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
          },
          learning_summary: { account_id: ACCOUNT_ID },
          improvement_report: { account_id: ACCOUNT_ID },
          run_history: { account_id: ACCOUNT_ID, count: 4, runs: [] },
          incidents: [
            {
              incident_id: 'incident-1',
              status: 'degraded',
              summary: 'One improvement decision is pending operator review.',
              detail: 'Queued improvement evidence is ready for review.',
            },
          ],
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
              key: 'ai_runtime',
              label: 'AI Runtime',
              status: 'ready',
              blocking: false,
              summary: 'AI runtime is ready for operator workflows.',
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
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'paper_trading',
          artifact_count: 1,
          criteria: [
            'Show discovery candidates only when confidence is at least 0.45.',
            'Promote to focused research only when confidence is at least 0.60.',
          ],
          considered: [
            'INFY · 68% · watch_only · fresh research memory',
            'TCS · below discovery threshold of 0.45',
          ],
          freshness_state: 'fresh',
          empty_reason: null,
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
              last_researched_at: NOW,
              last_actionability: 'watch_only',
              last_thesis_confidence: 0.31,
              last_analysis_mode: 'stale_evidence',
              research_freshness: 'fresh',
              fresh_primary_source_count: 1,
	              fresh_external_source_count: 0,
	              market_data_freshness: 'fresh',
	              technical_context_available: true,
	              evidence_mode: 'stale_evidence',
	              lifecycle_state: 'keep_watch',
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
          last_generated_at: NOW,
          blockers: ['Select a discovery candidate to run focused research.'],
          context_mode: 'paper_trading',
          artifact_count: 0,
          criteria: [
            'Research runs one candidate at a time from discovery or an explicit symbol selection.',
            'Actionable research requires thesis confidence at least 0.60 and zero blockers.',
          ],
          considered: ['No candidate is currently staged for focused research.'],
          freshness_state: 'unknown',
          empty_reason: 'requires_selection',
          research: null,
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/decisions`) {
      return route.fulfill(
        jsonResponse({
          status: 'blocked',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: ['No decision packet is available yet.'],
          context_mode: 'paper_trading',
          artifact_count: 0,
          criteria: [
            'Decision review considers open positions only; it does not generate new entries.',
            'Actions are limited to hold, review_exit, tighten_stop, or take_profit.',
          ],
          considered: ['INFY · open position in current review set'],
          freshness_state: 'unknown',
          empty_reason: 'no_candidates',
          decisions: [],
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/review`) {
      return route.fulfill(
        jsonResponse({
          status: 'ready',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'paper_trading',
          artifact_count: 1,
          criteria: [
            'Daily review is observational unless confidence clears the promotion threshold.',
            'No recent closed trades caps review confidence below the ready threshold.',
          ],
          considered: ['INFY · recent realized outcome in review memory'],
          freshness_state: 'fresh',
          empty_reason: null,
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
            claudeEnabled: true,
            claudeDailyTokenLimit: 120000,
            claudeCostAlerts: true,
            claudeCostThreshold: 10,
            dailyApiLimit: 25,
            quoteStreamProvider: 'zerodha_kite',
            quoteStreamMode: 'ltpc',
            quoteStreamSymbolLimit: 50,
          },
        })
      )
    }

    if (pathname === `/api/paper-trading/accounts/${ACCOUNT_ID}/policy`) {
      return route.fulfill(
        jsonResponse({
          success: true,
          account_id: ACCOUNT_ID,
          policy: {
            account_id: ACCOUNT_ID,
            execution_mode: 'operator_confirmed_execution',
            max_open_positions: 8,
            max_new_entries_per_day: 3,
            max_deployed_capital_pct: 80,
            default_stop_loss_pct: 5,
            default_target_pct: 10,
            per_trade_exposure_pct: 5,
            max_portfolio_risk_pct: 10,
            risk_level: 'moderate',
            updated_at: NOW,
            created_at: NOW,
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
    await expect(page.getByRole('link', { name: 'Health' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Paper Trading' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Configuration' })).toBeVisible()
  })

  test('navigates across the four mission-aligned routes', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Health' }).click()
    await expect(page).toHaveURL(/\/health$/)
    await expect(page.getByRole('heading', { name: 'Health' })).toBeVisible()

    await page.getByRole('link', { name: 'Paper Trading' }).click()
    await expect(page).toHaveURL(/\/paper-trading$/)
    await expect(page.getByRole('heading', { name: 'Paper Trading', exact: true })).toBeVisible()

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
    await expect(page.getByRole('link', { name: 'System Health' })).toHaveCount(0)
  })

  test('shows an explicit overview error surface when operator snapshot data fails', async ({ page }) => {
    await page.unroute('**/api/**')
    await installShellMocks(page, {
      overviewFailure: {
        status: 500,
        payload: { error: 'Operator snapshot unavailable.' },
      },
    })

    await page.goto('/')

    await expect(page.getByText('Operator overview unavailable')).toBeVisible()
    await expect(page.getByText('Operator snapshot unavailable.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Retry overview' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Open Health' })).toBeVisible()
  })

  test('renders the operator-first overview cockpit', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Immediate blockers and next action' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Selected account snapshot' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Work queue and performance' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Guardrails in force' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Stage outputs in flight' })).toBeVisible()
  })

  test('keeps full health truth off overview and paper trading', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Canonical lane')).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Runtime identity in sync' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'What I can run end to end right now' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Mission status' })).toHaveCount(0)

    await page.goto('/paper-trading')
    await expect(page.getByText('Canonical lane')).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Runtime identity in sync' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'What I can run end to end right now' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Mission status' })).toHaveCount(0)
  })

  test('renders configuration as policy surfaces only', async ({ page }) => {
    await page.goto('/configuration')

    await expect(page.getByRole('heading', { name: 'Global Policy' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Account Policy' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Stage Criteria and Guardrails' })).toBeVisible()
    await expect(page.getByText('This tab owns editable defaults and guardrails only.')).toBeVisible()
    await expect(page.getByText('Execution mode', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('Discovery control surface')).toBeVisible()
    await expect(page.getByText('Focused Research control surface')).toBeVisible()
  })

  test('shows ready operator gates on the health surface', async ({ page }) => {
    await page.goto('/health')

    await expect(page.getByRole('heading', { name: 'Mission status' })).toBeVisible()
    await expect(page.getByText('All current automation gates are satisfied for the selected paper account.')).toBeVisible()
    await expect(page.getByText('AI Runtime', { exact: true })).toBeVisible()
    await expect(page.getByText('AI runtime is ready for operator workflows.')).toBeVisible()
    await expect(page.getByText('Market Data', { exact: true })).toBeVisible()
    await expect(page.getByText('Market data path is healthy.')).toBeVisible()
    await expect(page.getByText(/WebMCP ready \(\d+\)/)).toBeVisible()
  })

  test('shows runtime truth and autonomy boundary on the health surface', async ({ page }) => {
    await page.goto('/health')

    await expect(page.getByRole('heading', { name: 'Runtime identity in sync' })).toBeVisible()
    await expect(page.getByText('Canonical lane')).toBeVisible()
    await expect(page.getByText('http://127.0.0.1:8000')).toBeVisible()
    await expect(page.getByText('Account:')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'What I can run end to end right now' })).toBeVisible()
    await expect(page.getByText('Autonomous Now', { exact: true })).toBeVisible()
    await expect(page.getByText('Still Blocked', { exact: true })).toBeVisible()
  })

  test('shows the stage criteria sidecars on paper trading', async ({ page }) => {
    await page.goto('/paper-trading')

    await expect(page.getByRole('heading', { name: 'Discovery control surface' })).toBeVisible()
    await expect(page.getByText('Rules in force')).toHaveCount(4)
    await expect(page.getByText('Currently considered')).toHaveCount(4)
    await expect(page.getByRole('heading', { name: 'Focused Research control surface' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Decision Review control surface' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Daily Review control surface' })).toBeVisible()
  })

  test('renders visible discovery candidates on first load', async ({ page }) => {
    await page.goto('/paper-trading')

    await expect(page.getByText('INFY', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('Show discovery candidates only when confidence is at least 0.45.')).toBeVisible()
  })

  test('moves researched names into a separate analyzed watchlist and stages the next fresh candidate', async ({ page }) => {
    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/discovery`, async route => {
      await route.fulfill(
        jsonResponse({
          status: 'ready',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'stateful_watchlist',
          artifact_count: 2,
          criteria: [
            'Fresh watch-only packets should stay visible in watchlist memory until new evidence appears.',
            'Names without fresh research memory stay in the ready-for-research queue.',
          ],
          considered: [
            'KAYNES · watch_only · fresh research memory',
            'HAVELLS · research-ready',
          ],
          freshness_state: 'fresh',
          empty_reason: null,
          candidates: [
            {
              candidate_id: 'candidate-kaynes',
              symbol: 'KAYNES',
              company_name: 'Kaynes Technology',
              sector: 'Electronics',
              source: 'watchlist',
              priority: 'high',
              confidence: 0.78,
              rationale: 'Stored packet says stay on watch until fresh external evidence improves.',
              next_step: 'Re-open this packet only if a new catalyst or earnings update appears.',
              generated_at: NOW,
              last_researched_at: NOW,
              last_actionability: 'watch_only',
              last_thesis_confidence: 0.31,
              last_analysis_mode: 'stale_evidence',
              research_freshness: 'fresh',
              fresh_primary_source_count: 0,
              fresh_external_source_count: 0,
              market_data_freshness: 'fresh',
              technical_context_available: true,
              evidence_mode: 'stale_evidence',
            },
            {
              candidate_id: 'candidate-havells',
              symbol: 'HAVELLS',
              company_name: 'Havells India',
              sector: 'Electrical Equipment',
              source: 'watchlist',
              priority: 'medium',
	              confidence: 0.74,
	              rationale: 'This candidate has not been researched in the current cycle yet.',
	              next_step: 'Run focused research before spending more operator attention here.',
	              generated_at: NOW,
	              lifecycle_state: 'fresh_queue',
	            },
          ],
        }),
      )
    })

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/research**`, async route => {
      const url = new URL(route.request().url())
      const candidateId = url.searchParams.get('candidate_id')

      if (candidateId === 'candidate-kaynes') {
        await route.fulfill(
          jsonResponse({
            status: 'ready',
            generated_at: NOW,
            last_generated_at: NOW,
            blockers: [],
            context_mode: 'single_candidate_research',
            artifact_count: 1,
            criteria: ['Reuse the latest persisted packet when it is still fresh.'],
            considered: ['KAYNES · watch_only packet is still fresh'],
            freshness_state: 'fresh',
            empty_reason: null,
            research: {
              research_id: 'research-kaynes',
              candidate_id: 'candidate-kaynes',
              account_id: ACCOUNT_ID,
              symbol: 'KAYNES',
              thesis: 'Stay on watch until a fresh catalyst appears.',
              evidence: ['Fresh quote context exists but external evidence remains thin.'],
              risks: ['Packet is stale-evidence and does not justify entry.'],
              invalidation: 'A fresh catalyst or earnings surprise would reopen the setup.',
              confidence: 0.31,
              screening_confidence: 0.78,
              thesis_confidence: 0.31,
              analysis_mode: 'stale_evidence',
              actionability: 'watch_only',
              external_evidence_status: 'partial',
              why_now: 'No new trigger yet.',
              source_summary: [],
              evidence_citations: [],
              market_data_freshness: {
                status: 'fresh',
                summary: 'Live quotes are available.',
                timestamp: NOW,
                provider: 'zerodha_kite',
                has_intraday_quote: true,
                has_historical_data: true,
              },
              blockers: [],
              warnings: ['Wait for new evidence before re-promoting this name.'],
              next_step: 'Keep on watchlist memory.',
              generated_at: NOW,
            },
          }),
        )
        return
      }

      await route.fulfill(
        jsonResponse({
          status: 'empty',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'single_candidate_research',
          artifact_count: 0,
          criteria: ['Research runs one candidate at a time from discovery or an explicit symbol selection.'],
          considered: ['HAVELLS · no stored packet yet'],
          freshness_state: 'unknown',
          empty_reason: 'requires_selection',
          research: null,
        }),
      )
    })

    await page.goto('/paper-trading')

    const discoverySection = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Stage only the names worth real research' }),
    }).first()
    const analyzedSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Carry-forward analyzed watchlist' }),
    }).first()

	    await expect(discoverySection.getByRole('heading', { name: 'Fresh queue' })).toBeVisible()
	    await expect(analyzedSection.getByRole('heading', { name: 'Carry-forward analyzed watchlist' })).toBeVisible()
	    await expect(discoverySection.getByText('HAVELLS', { exact: true }).first()).toBeVisible()
	    await expect(discoverySection.getByText('KAYNES', { exact: true })).toHaveCount(0)
	    await expect(analyzedSection.getByText('KAYNES', { exact: true }).first()).toBeVisible()
	    await expect(analyzedSection.getByRole('heading', { name: 'Keep watch' })).toBeVisible()
    await expect(page.getByText('Staged candidate').locator('..')).toContainText('HAVELLS')
    await expect(analyzedSection.getByRole('button', { name: 'Open packet' })).toBeVisible()
  })

  test('runs the loop until one actionable candidate is found and updates the four lanes', async ({ page }) => {
    const discoveryPayload = {
      status: 'ready',
      generated_at: NOW,
      last_generated_at: NOW,
      blockers: [],
      context_mode: 'stateful_watchlist',
      artifact_count: 3,
      criteria: ['Discovery should keep only fresh-queue names visible.'],
      considered: ['KAYNES · fresh_queue', 'HAVELLS · fresh_queue', 'KPITTECH · fresh_queue'],
      freshness_state: 'fresh',
      empty_reason: null,
      loop_summary: {
        target_actionable_count: 1,
        actionable_found_count: 0,
        research_attempt_count: 0,
        attempted_candidates: [],
        attempted_candidate_ids: [],
        queue_exhausted: false,
        termination_reason: 'awaiting_research',
        current_candidate_symbol: 'KAYNES',
        current_candidate_id: 'candidate-kaynes',
        latest_transition_reason: null,
        model_usage_by_phase: {},
        token_usage_by_phase: {},
        total_candidates_scanned: 3,
        promoted_actionable_symbols: [],
      },
      candidates: [
        {
          candidate_id: 'candidate-kaynes',
          symbol: 'KAYNES',
          company_name: 'Kaynes Technology',
          sector: 'Electronics',
          source: 'watchlist',
          priority: 'high',
          confidence: 0.81,
          rationale: 'Dark-horse electronics exposure with a weak recent packet.',
          next_step: 'Run research.',
          generated_at: NOW,
          lifecycle_state: 'fresh_queue',
          dark_horse_score: 88,
          evidence_quality_score: 42,
        },
        {
          candidate_id: 'candidate-havells',
          symbol: 'HAVELLS',
          company_name: 'Havells India',
          sector: 'Electrical Equipment',
          source: 'watchlist',
          priority: 'medium',
          confidence: 0.75,
          rationale: 'Needs evidence refresh.',
          next_step: 'Run research.',
          generated_at: NOW,
          lifecycle_state: 'fresh_queue',
          dark_horse_score: 76,
          evidence_quality_score: 38,
        },
        {
          candidate_id: 'candidate-kpit',
          symbol: 'KPITTECH',
          company_name: 'KPIT Technologies',
          sector: 'Technology',
          source: 'watchlist',
          priority: 'high',
          confidence: 0.79,
          rationale: 'Fresh trigger improved the setup.',
          next_step: 'Run research.',
          generated_at: NOW,
          lifecycle_state: 'fresh_queue',
          dark_horse_score: 91,
          evidence_quality_score: 64,
        },
      ],
    }

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/discovery`, async route => {
      await route.fulfill(jsonResponse(discoveryPayload))
    })

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/research**`, async route => {
      await route.fulfill(
        jsonResponse({
          status: 'empty',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'single_candidate_research',
          artifact_count: 0,
          criteria: ['The loop should keep advancing until it finds one actionable candidate or exhausts the queue.'],
          considered: ['KAYNES · first in queue'],
          freshness_state: 'unknown',
          empty_reason: 'requires_selection',
          research: null,
          loop_summary: discoveryPayload.loop_summary,
        }),
      )
    })

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/runs/research`, async route => {
      discoveryPayload.considered = ['KAYNES · keep_watch', 'HAVELLS · rejected', 'KPITTECH · actionable']
      discoveryPayload.artifact_count = 0
      discoveryPayload.candidates = [
        {
          ...discoveryPayload.candidates[0],
          lifecycle_state: 'keep_watch',
          last_researched_at: NOW,
          last_actionability: 'watch_only',
          last_thesis_confidence: 0.31,
          last_analysis_mode: 'stale_evidence',
          research_freshness: 'fresh',
          next_step: 'Keep on watch until a new trigger appears.',
        },
        {
          ...discoveryPayload.candidates[1],
          lifecycle_state: 'rejected',
          last_researched_at: NOW,
          last_actionability: 'blocked',
          last_thesis_confidence: 0.22,
          last_analysis_mode: 'insufficient_evidence',
          research_freshness: 'fresh',
          next_step: 'Rejected until a materially different trigger appears.',
        },
        {
          ...discoveryPayload.candidates[2],
          lifecycle_state: 'actionable',
          last_researched_at: NOW,
          last_actionability: 'actionable',
          last_thesis_confidence: 0.74,
          last_analysis_mode: 'fresh_evidence',
          research_freshness: 'fresh',
          next_step: 'Promote to proposal and preflight.',
        },
      ]
      discoveryPayload.loop_summary = {
        target_actionable_count: 1,
        actionable_found_count: 1,
        research_attempt_count: 3,
        attempted_candidates: ['KAYNES', 'HAVELLS', 'KPITTECH'],
        attempted_candidate_ids: ['candidate-kaynes', 'candidate-havells', 'candidate-kpit'],
        queue_exhausted: false,
        termination_reason: 'actionable_candidate_found',
        current_candidate_symbol: 'KPITTECH',
        current_candidate_id: 'candidate-kpit',
        latest_transition_reason: 'moved_kpittech_to_actionable',
        model_usage_by_phase: {
          research: { model: 'gpt-5.4', reasoning: 'medium' },
        },
        token_usage_by_phase: {
          research: { input_tokens: 640, output_tokens: 420 },
        },
        total_candidates_scanned: 3,
        promoted_actionable_symbols: ['KPITTECH'],
      }

      await route.fulfill(
        jsonResponse({
          status: 'ready',
          generated_at: NOW,
          last_generated_at: NOW,
          blockers: [],
          context_mode: 'single_candidate_research',
          artifact_count: 1,
          criteria: ['Research should stop once it finds one actionable buy candidate.'],
          considered: ['KAYNES · keep_watch', 'HAVELLS · rejected', 'KPITTECH · actionable'],
          freshness_state: 'fresh',
          empty_reason: null,
          loop_summary: discoveryPayload.loop_summary,
          research: {
            research_id: 'research-kpit',
            candidate_id: 'candidate-kpit',
            account_id: ACCOUNT_ID,
            symbol: 'KPITTECH',
            thesis: 'Fresh trigger plus relative-strength follow-through make this the actionable survivor.',
            evidence: ['Fresh trigger confirmed.', 'Relative strength improved.'],
            risks: ['Breakout can fail if follow-through disappears.'],
            invalidation: 'Close back into the base.',
            confidence: 0.78,
            screening_confidence: 0.79,
            thesis_confidence: 0.74,
            analysis_mode: 'fresh_evidence',
            actionability: 'actionable',
            classification: 'actionable_buy_candidate',
            what_changed_since_last_research: 'A new trigger and stronger tape reactivated the name.',
            external_evidence_status: 'fresh',
            why_now: 'The setup is now strong enough to promote.',
            source_summary: [],
            evidence_citations: [],
            market_data_freshness: {
              status: 'fresh',
              summary: 'Live quotes are available.',
              timestamp: NOW,
              provider: 'zerodha_kite',
              has_intraday_quote: true,
              has_historical_data: true,
            },
            blockers: [],
            warnings: [],
            next_step: 'Promote to proposal and preflight.',
            generated_at: NOW,
          },
        }),
      )
    })

    await page.goto('/paper-trading')
    await page.getByRole('button', { name: 'Run Research' }).click()

    const analyzedSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Carry-forward analyzed watchlist' }),
    }).first()
    const researchSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Research runs only when you ask for it' }),
    }).first()

    await expect(researchSection.getByText('Attempts 3')).toBeVisible()
    await expect(researchSection.getByText('Actionable 1/1')).toBeVisible()
    await expect(page.getByText('KPITTECH', { exact: true }).first()).toBeVisible()
    await expect(analyzedSection.getByRole('heading', { name: 'Actionable' })).toBeVisible()
    await expect(analyzedSection.getByRole('heading', { name: 'Keep watch' })).toBeVisible()
    await expect(analyzedSection.getByRole('heading', { name: 'Rejected' })).toBeVisible()
    await expect(analyzedSection.getByText('KAYNES', { exact: true }).first()).toBeVisible()
    await expect(analyzedSection.getByText('HAVELLS', { exact: true }).first()).toBeVisible()
    await expect(analyzedSection.getByText('KPITTECH', { exact: true }).first()).toBeVisible()
  })

  test('renders the first closed trade and live performance counters from current API shapes', async ({ page }) => {
    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/positions`, async route => {
      await route.fulfill(
        jsonResponse({
          positions: [
            {
              id: 'trade_a22a25e1',
              tradeId: 'trade_a22a25e1',
              symbol: 'RELIANCE',
              quantity: 5,
              avgPrice: 2650,
              entryPrice: 2650,
              ltp: 1369.2,
              currentPrice: 1369.2,
              pnl: -6404,
              pnlPercent: -48.33207547169811,
              currentValue: 6846,
              daysHeld: 96,
              markStatus: 'live',
              markTimestamp: NOW,
              strategy: 'Morning session trade',
              tradeType: 'buy',
              entryDate: '2025-12-26',
            },
          ],
          valuationStatus: 'live',
          valuationDetail: null,
        })
      )
    })

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/trades`, async route => {
      await route.fulfill(
        jsonResponse({
          trades: [
            {
              id: 'trade_101b8405',
              date: '2026-04-01T11:26:18.233615+00:00',
              symbol: 'HDFC',
              action: 'buy',
              entryPrice: 2750,
              exitPrice: 742.25,
              quantity: 5,
              holdTime: '96 days',
              pnl: -10038.75,
              pnlPercent: -73.00909090909092,
              strategy: 'Morning session trade',
              notes: 'Manual exit',
              status: 'closed',
            },
          ],
        })
      )
    })

    await page.route(`**/api/paper-trading/accounts/${ACCOUNT_ID}/performance?period=month`, async route => {
      await route.fulfill(
        jsonResponse({
          performance: {
            period: 'month',
            totalReturn: 0,
            totalReturnPercent: 0,
            winRate: 0,
            totalTrades: 3,
            winningTrades: 0,
            losingTrades: 1,
            avgWin: 0,
            avgLoss: -10038.75,
            profitFactor: 0,
            maxDrawdown: 10038.75,
            sharpeRatio: null,
            volatility: 0,
            benchmarkReturn: 0,
            alpha: 0,
          },
        })
      )
    })

    await page.goto('/paper-trading')

    await expect(page.getByRole('heading', { name: 'Trade History (1 trades)' })).toBeVisible()
    await expect(page.getByText('HDFC', { exact: true }).last()).toBeVisible()
    await expect(page.getByText('₹742.25')).toBeVisible()
    await expect(page.getByText('Losing Trades').locator('..').locator('..')).toContainText('1')
    await expect(page.getByText('Avg Loss').locator('..').locator('..')).toContainText('₹10,039')
    await expect(page.getByText('Application Error')).toHaveCount(0)
  })

  test('executes WebMCP tools with the current operator account context', async ({ page }) => {
    await page.goto('/health')

    await expect(page.getByText(/WebMCP ready \(\d+\)/)).toBeVisible()

    const accounts = await page.evaluate(async () => {
      const raw = await navigator.modelContextTesting?.executeTool('list_paper_accounts', '{}')
      return typeof raw === 'string' ? JSON.parse(raw) : raw
    })

    expect(accounts?.selected_account_id).toBe(ACCOUNT_ID)
    expect(accounts?.accounts).toHaveLength(1)
    expect(accounts?.accounts?.[0]?.account_id).toBe(ACCOUNT_ID)

    await page.evaluate(async (accountId) => {
      await navigator.modelContextTesting?.executeTool(
        'select_paper_account',
        JSON.stringify({ account_id: accountId }),
      )
    }, ACCOUNT_ID)

    const capability = await page.evaluate(async () => {
      const raw = await navigator.modelContextTesting?.executeTool('get_capability_snapshot', '{}')
      return typeof raw === 'string' ? JSON.parse(raw) : raw
    })

    expect(capability?.account_id).toBe(ACCOUNT_ID)
    expect(capability?.overall_status).toBe('ready')
  })
})

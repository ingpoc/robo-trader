import { useEffect, useRef, useState } from 'react'

import type { Account } from '@/contexts/AccountContext'

import { publishPaperTradingArtifactUpdate } from './useAgentArtifacts'
import type {
  DecisionEnvelope,
  DiscoveryEnvelope,
  PaperTradingOperatorSnapshot,
  ResearchEnvelope,
  ReviewEnvelope,
  WebMCPReadiness,
} from '../types'

type JsonRecord = Record<string, unknown>

interface UsePaperTradingWebMCPOptions {
  accounts: Account[]
  selectedAccountId?: string | null
  selectAccountById: (accountId: string) => Promise<void>
  refreshOperatorView: (options?: { accountId?: string | null; preserveContent?: boolean }) => Promise<void>
  getOperatorSnapshot: (accountId?: string | null) => Promise<PaperTradingOperatorSnapshot>
}

interface ToolContext extends UsePaperTradingWebMCPOptions {
  fetchJson: <T = unknown>(url: string, init?: RequestInit) => Promise<T>
}

type ToolContextGetter = () => ToolContext

function createAccountSchema(accounts: Account[]) {
  const schema: Record<string, unknown> = {
    type: 'string',
    description: 'Paper trading account to operate in the current operator session.',
  }

  if (accounts.length > 0) {
    schema.anyOf = accounts.map(account => ({
      const: account.account_id,
      title: `${account.account_name} (${account.strategy_type})`,
    }))
  }

  return schema
}

async function readJsonResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return await response.json()
  }

  const text = await response.text()
  return text ? { message: text } : null
}

function extractResponseError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object') {
    const record = payload as JsonRecord
    if (typeof record.error === 'string' && record.error.trim()) return record.error
    if (typeof record.message === 'string' && record.message.trim()) return record.message
    if (typeof record.detail === 'string' && record.detail.trim()) return record.detail
    if (Array.isArray(record.blockers) && record.blockers.length > 0) {
      const first = record.blockers.find(value => typeof value === 'string' && value.trim()) as string | undefined
      if (first) return first
    }
  }
  return fallback
}

function normalizeSymbol(value: unknown): string {
  return String(value ?? '').trim().toUpperCase()
}

function normalizeOrderType(value: unknown): 'MARKET' | 'LIMIT' {
  return String(value ?? 'MARKET').trim().toUpperCase() === 'LIMIT' ? 'LIMIT' : 'MARKET'
}

function normalizePositiveNumber(value: unknown, label: string): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue) || numberValue <= 0) {
    throw new Error(`${label} must be a positive number.`)
  }
  return numberValue
}

function createFetchJson() {
  return async function fetchJson<T = unknown>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, init)
    const payload = (await readJsonResponse(response)) as T
    if (!response.ok) {
      throw new Error(extractResponseError(payload, `Request failed with status ${response.status}.`))
    }
    return payload
  }
}

function normalizeAccountListPayload(payload: unknown): Account[] {
  if (!payload || typeof payload !== 'object') {
    return []
  }

  const record = payload as JsonRecord
  const accounts = Array.isArray(record.accounts) ? record.accounts : []
  return accounts
    .map((value): Account | null => {
      if (!value || typeof value !== 'object') {
        return null
      }

      const account = value as JsonRecord
      const accountId = String(account.account_id ?? account.accountId ?? '').trim()
      if (!accountId) {
        return null
      }

      return {
        account_id: accountId,
        account_name: String(account.account_name ?? account.accountName ?? accountId).trim(),
        account_type: String(account.account_type ?? account.accountType ?? '').trim(),
        strategy_type: String(account.strategy_type ?? account.accountType ?? '').trim(),
        risk_level: String(account.risk_level ?? account.riskLevel ?? 'moderate').trim(),
        balance: Number(account.balance ?? account.currentBalance ?? 0),
        buying_power: Number(account.buying_power ?? account.marginAvailable ?? 0),
        deployed_capital: Number(account.deployed_capital ?? account.totalInvested ?? 0),
        total_pnl: Number(account.total_pnl ?? 0),
        total_pnl_pct: Number(account.total_pnl_pct ?? 0),
        monthly_pnl: Number(account.monthly_pnl ?? 0),
        monthly_pnl_pct: Number(account.monthly_pnl_pct ?? 0),
        open_positions_count: Number(account.open_positions_count ?? 0),
        today_trades: Number(account.today_trades ?? 0),
        win_rate: Number(account.win_rate ?? 0),
        created_at: String(account.created_at ?? account.createdDate ?? new Date().toISOString()),
        reset_date: String(account.reset_date ?? ''),
      }
    })
    .filter((account): account is Account => account !== null)
}

const BLOCKED_WEBMCP_STATUS: WebMCPReadiness = {
  status: 'blocked',
  summary: 'WebMCP blocked',
  detail: 'Browser-native tool registration is unavailable in this Chrome session.',
  tool_count: 0,
  registered: false,
  testing_available: false,
  direct_execution_ready: false,
  probe_tool: null,
}

function parseTestingResult(value: unknown): JsonRecord {
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' ? (parsed as JsonRecord) : { value: parsed }
    } catch {
      return { value }
    }
  }

  if (value && typeof value === 'object') {
    return value as JsonRecord
  }

  return { value }
}

function buildTools(getContext: ToolContextGetter): WebMCPToolDefinition[] {
  const accountSchema = createAccountSchema(getContext().accounts)
  const fetchJson = async <T = unknown>(url: string, init?: RequestInit) => await getContext().fetchJson<T>(url, init)
  const getCurrentAccounts = () => getContext().accounts
  const getCurrentSelectedAccountId = () => getContext().selectedAccountId ?? null
  const getAvailableAccounts = async () => {
    const accounts = getCurrentAccounts()
    if (accounts.length > 0) {
      return accounts
    }
    return normalizeAccountListPayload(await fetchJson('/api/paper-trading/accounts'))
  }
  const selectAccountById = async (accountId: string) => await getContext().selectAccountById(accountId)
  const refreshOperatorView = async (options?: { accountId?: string | null; preserveContent?: boolean }) =>
    await getContext().refreshOperatorView(options)
  const getOperatorSnapshot = async (accountId?: string | null) => await getContext().getOperatorSnapshot(accountId)

  const resolveAccountId = (input?: JsonRecord, required = true): string | null => {
    const requested = String(input?.account_id ?? '').trim()
    const accountId = requested || getCurrentSelectedAccountId() || getCurrentAccounts()[0]?.account_id || ''
    if (!accountId) {
      if (!required) return null
      throw new Error('Select a paper trading account first or pass account_id explicitly.')
    }
    return accountId
  }

  const refreshAndSnapshot = async (accountId?: string | null) => {
    await refreshOperatorView({ accountId, preserveContent: true })
    return await getOperatorSnapshot(accountId)
  }

  const validateExecutionPreflight = async (accountId: string, payload: Record<string, unknown>) => {
    return await fetchJson(`/api/paper-trading/accounts/${accountId}/execution/preflight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  }

  const buildExecutionProposal = async (accountId: string, payload: Record<string, unknown>) => {
    return await fetchJson(`/api/paper-trading/accounts/${accountId}/execution/proposal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  }

  const refreshOperatorReadiness = async (accountId: string) => {
    return await fetchJson(`/api/paper-trading/accounts/${accountId}/operator/refresh-readiness`, {
      method: 'POST',
    })
  }

  const gatedMutationResult = async (
    accountId: string,
    preflightPayload: Record<string, unknown>,
    executeMutation: () => Promise<unknown>,
  ) => {
    const proposal = await buildExecutionProposal(accountId, preflightPayload)
    const proposalRecord = (proposal ?? {}) as JsonRecord
    if (proposalRecord.allowed !== true) {
      return {
        denied: true,
        proposal,
        operator_snapshot: await refreshAndSnapshot(accountId),
      }
    }

    const preflight = await validateExecutionPreflight(accountId, preflightPayload)
    const preflightRecord = (preflight ?? {}) as JsonRecord
    const proposalStateSignature = String(proposalRecord.state_signature ?? '')
    const preflightStateSignature = String(preflightRecord.state_signature ?? '')
    const proposalIdempotencyKey = String(proposalRecord.idempotency_key ?? '')
    const preflightIdempotencyKey = String(preflightRecord.idempotency_key ?? '')

    if (
      preflightRecord.allowed !== true ||
      !proposalStateSignature ||
      proposalStateSignature !== preflightStateSignature ||
      proposalIdempotencyKey !== preflightIdempotencyKey
    ) {
      return {
        denied: true,
        proposal,
        preflight,
        reason:
          preflightRecord.allowed !== true
            ? 'Execution was denied on the final preflight check.'
            : 'Execution proposal expired or no longer matches current backend state.',
        operator_snapshot: await refreshAndSnapshot(accountId),
      }
    }

    const result = await executeMutation()
    return {
      denied: false,
      proposal,
      preflight,
      result,
      operator_snapshot: await refreshAndSnapshot(accountId),
    }
  }

  return [
    {
      name: 'list_paper_accounts',
      description: 'List the paper trading accounts currently available in Robo Trader so the operator can choose one for monitoring or action.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => {
        const accounts = await getAvailableAccounts()
        return {
          generated_at: new Date().toISOString(),
          selected_account_id: getCurrentSelectedAccountId() ?? accounts[0]?.account_id ?? null,
          accounts: accounts.map(account => ({
          account_id: account.account_id,
          account_name: account.account_name,
          strategy_type: account.strategy_type,
          risk_level: account.risk_level,
        })),
        }
      },
    },
    {
      name: 'select_paper_account',
      description: 'Switch the operator session to a specific paper trading account and refresh the desk state before returning.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: accountSchema,
        },
        required: ['account_id'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        await selectAccountById(accountId)
        return await getOperatorSnapshot(accountId)
      },
    },
    {
      name: 'get_operator_snapshot',
      description: 'Retrieve the current operator snapshot for the selected paper account, including readiness, positions, trades, performance, discovery, and improvement data.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override. When omitted, the currently selected paper account is used.',
          },
        },
      },
      execute: async (input = {}) => await getOperatorSnapshot(resolveAccountId(input, false)),
    },
    {
      name: 'validate_operator_readiness',
      description: 'Refresh the selected paper account and return the current health, configuration, queue, and capability state before any operator action.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the readiness check.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input, false)
        const snapshot = await refreshAndSnapshot(accountId)
        return {
          generated_at: snapshot.generated_at,
          selected_account_id: snapshot.selected_account_id,
          health: snapshot.health,
          configuration_status: snapshot.configuration_status,
          queue_status: snapshot.queue_status,
          capability_snapshot: snapshot.capability_snapshot,
        }
      },
    },
    {
      name: 'refresh_operator_readiness',
      description:
        'Force a live operator-readiness refresh for the selected paper account and return the refreshed snapshot after AI validation and current backend checks.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the readiness refresh.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const refresh = await refreshOperatorReadiness(accountId)
        return {
          refresh,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'assert_queue_clean',
      description: 'Verify that no background queue work is pending or running so the manual-only operating contract remains intact.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => {
        const queueStatus = await fetchJson<Record<string, unknown>>('/api/queues/status')
        const stats = (queueStatus.stats as JsonRecord | undefined) ?? {}
        const pending = Number(stats.total_pending_tasks ?? 0)
        const running = Number(stats.total_active_tasks ?? 0)
        if (pending > 0 || running > 0) {
          throw new Error(`Queue cleanliness assertion failed: ${pending} pending and ${running} running task(s) remain.`)
        }
        return {
          generated_at: new Date().toISOString(),
          status: 'clean',
          queue_status: queueStatus,
        }
      },
    },
    {
      name: 'get_queue_statuses',
      description: 'Inspect queue state directly from the backend queue control plane, including totals, failed tasks, and per-queue counts.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => await fetchJson('/api/queues/status'),
    },
    {
      name: 'get_queue_history',
      description: 'Inspect recent scheduler task history so the operator can verify that no legacy background work is silently consuming resources.',
      inputSchema: {
        type: 'object',
        properties: {
          hours: {
            type: 'integer',
            minimum: 1,
            maximum: 168,
            description: 'Lookback window in hours.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 200,
            description: 'Maximum number of task-history rows to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const hours = input.hours == null ? 24 : Math.trunc(normalizePositiveNumber(input.hours, 'hours'))
        const limit = input.limit == null ? 100 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        return await fetchJson(`/api/queues/history?hours=${hours}&limit=${limit}`)
      },
    },
    {
      name: 'get_capability_snapshot',
      description: 'Fetch the current paper-trading capability snapshot for one account, including AI runtime, quote stream, market data, broker, and account readiness checks.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the capability snapshot.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input, false)
        if (!accountId) {
          throw new Error('Select a paper account before requesting a capability snapshot.')
        }
        return await fetchJson(`/api/paper-trading/capabilities?account_id=${encodeURIComponent(accountId)}`)
      },
    },
    {
      name: 'validate_ai_runtime_now',
      description: 'Force a live AI runtime validation against the paper-trading sidecar and return the runtime result plus the current capability snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for runtime validation.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input, false)
        const validation = await fetchJson(`/api/paper-trading/runtime/validate-ai${accountId ? `?account_id=${encodeURIComponent(accountId)}` : ''}`, {
          method: 'POST',
        })
        await refreshOperatorView({
          accountId,
          preserveContent: true,
        })
        const snapshot = await getOperatorSnapshot(accountId)
        return {
          validation,
          operator_snapshot: snapshot,
        }
      },
    },
    {
      name: 'get_operator_incidents',
      description: 'Return the current incident list for the selected paper account, including blocked capabilities, queue violations, and stale price marks.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for incident inspection.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/operator-incidents`)
      },
    },
    {
      name: 'repair_market_data_runtime',
      description: 'Re-subscribe the active paper-trading symbols to the market-data runtime, refresh live streaming state, and return both the repair result and the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for runtime market-data repair.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const result = await fetchJson(`/api/paper-trading/accounts/${accountId}/runtime/refresh-market-data`, {
          method: 'POST',
        })
        return {
          result,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'get_account_overview',
      description: 'Fetch the current capital, buying power, and exposure overview for the selected paper account.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for overview retrieval.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/overview`)
      },
    },
    {
      name: 'get_open_positions',
      description: 'Fetch the current open positions for the selected paper account, including mark freshness and unrealized PnL.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for positions retrieval.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/positions`)
      },
    },
    {
      name: 'get_closed_trades',
      description: 'Fetch recent closed paper trades for the selected account so the operator can inspect realized outcomes directly.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for trade retrieval.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 100,
            description: 'Maximum number of closed trades to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 20 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/trades?limit=${limit}`)
      },
    },
    {
      name: 'get_performance_metrics',
      description: 'Fetch paper-trading performance metrics for the selected account over a bounded period.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for performance retrieval.',
          },
          period: {
            type: 'string',
            enum: ['today', 'week', 'month', 'all-time'],
            description: 'Performance lookback period.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const period = typeof input.period === 'string' && input.period.trim() ? input.period.trim() : 'month'
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/performance?period=${encodeURIComponent(period)}`,
        )
      },
    },
    {
      name: 'run_discovery',
      description: 'Run a manual discovery pass for the selected paper account, refresh the desk, and return both the discovery envelope and the updated operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for discovery.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 25,
            description: 'Maximum number of discovery candidates to include in the refreshed operator snapshot.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? null : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        const query = limit ? `?limit=${limit}` : ''
        const envelope = await fetchJson<DiscoveryEnvelope>(`/api/paper-trading/accounts/${accountId}/runs/discovery${query}`, {
          method: 'POST',
        })
        publishPaperTradingArtifactUpdate('discovery', envelope)
        return {
          discovery: envelope,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'run_focused_research',
      description: 'Run a manual research pass for a candidate or symbol in the selected paper account and return the structured research packet plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for research.',
          },
          candidate_id: {
            type: 'string',
            description: 'Candidate identifier from the discovery watchlist.',
          },
          symbol: {
            type: 'string',
            description: 'Raw symbol text when candidate_id is not available.',
          },
        },
        anyOf: [{ required: ['candidate_id'] }, { required: ['symbol'] }],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const payload: Record<string, unknown> = {}
        if (typeof input.candidate_id === 'string' && input.candidate_id.trim()) {
          payload.candidate_id = input.candidate_id.trim()
        }
        if (typeof input.symbol === 'string' && input.symbol.trim()) {
          payload.symbol = normalizeSymbol(input.symbol)
        }
        const envelope = await fetchJson<ResearchEnvelope>(`/api/paper-trading/accounts/${accountId}/runs/research`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        publishPaperTradingArtifactUpdate('research', envelope)
        return {
          research: envelope,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'run_decision_review',
      description: 'Run a manual decision review for currently open positions in the selected paper account and return the bounded decision envelope plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for decision review.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 10,
            description: 'Maximum number of open-position decisions to include.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? null : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        const query = limit ? `?limit=${limit}` : ''
        const envelope = await fetchJson<DecisionEnvelope>(`/api/paper-trading/accounts/${accountId}/runs/decision-review${query}`, {
          method: 'POST',
        })
        publishPaperTradingArtifactUpdate('decisions', envelope)
        return {
          decisions: envelope,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'run_daily_review',
      description: 'Run the manual daily review for the selected paper account and return the review report plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for daily review.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const envelope = await fetchJson<ReviewEnvelope>(`/api/paper-trading/accounts/${accountId}/runs/daily-review`, {
          method: 'POST',
        })
        publishPaperTradingArtifactUpdate('review', envelope)
        return {
          review: envelope,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'run_exit_check',
      description: 'Run a bounded exit-check pass for the selected paper account and return the resulting decision envelope plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the exit check.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 10,
            description: 'Maximum number of exit-check decisions to include.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? null : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        const query = limit ? `?limit=${limit}` : ''
        const envelope = await fetchJson(`/api/paper-trading/accounts/${accountId}/runs/exit-check${query}`, {
          method: 'POST',
        })
        return {
          exit_check: envelope,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'get_manual_run_history',
      description: 'Retrieve recent manual-run audit history for the selected paper account, including status, duration, blockers, dependency state, and provider metadata.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for manual-run history.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 100,
            description: 'Maximum number of recent manual runs to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 20 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/runs/history?limit=${limit}`,
        )
      },
    },
    {
      name: 'get_run_history',
      description: 'Retrieve recent manual-run history for the selected paper account. Use this when the operator needs the latest discovery, research, decision, and review audit trail.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for run history.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 100,
            description: 'Maximum number of recent runs to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 20 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/runs/history?limit=${limit}`)
      },
    },
    {
      name: 'get_position_health',
      description: 'Inspect open-position health for the selected paper account, including mark freshness and degraded positions that should block autonomous action.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for position health.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/positions/health`)
      },
    },
    {
      name: 'validate_execution_preflight',
      description: 'Validate a proposed paper-trading mutation against deterministic gates before attempting execution.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for execution preflight.',
          },
          action: {
            type: 'string',
            enum: ['buy', 'sell', 'close', 'modify_risk'],
            anyOf: [
              { const: 'buy', title: 'Buy entry' },
              { const: 'sell', title: 'Sell entry' },
              { const: 'close', title: 'Close trade' },
              { const: 'modify_risk', title: 'Modify stop/target' },
            ],
            description: 'Mutation to validate.',
          },
          symbol: { type: 'string', description: 'Symbol for entry validation.' },
          trade_id: { type: 'string', description: 'Trade identifier for close or risk updates.' },
          quantity: { type: 'integer', minimum: 1, description: 'Quantity for entry validation.' },
          price: { type: 'number', description: 'Optional explicit execution price.' },
          stop_loss: { type: 'number', description: 'Proposed stop loss for risk updates.' },
          target_price: { type: 'number', description: 'Proposed target price for risk updates.' },
          dry_run: { type: 'boolean', description: 'Keep true when only validating intent.' },
        },
        required: ['action'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const payload: Record<string, unknown> = {
          action: String(input.action ?? '').trim(),
          dry_run: input.dry_run == null ? true : Boolean(input.dry_run),
        }
        if (input.symbol != null) payload.symbol = normalizeSymbol(input.symbol)
        if (input.trade_id != null) payload.trade_id = String(input.trade_id).trim()
        if (input.quantity != null) payload.quantity = Math.trunc(normalizePositiveNumber(input.quantity, 'quantity'))
        if (input.price != null) payload.price = normalizePositiveNumber(input.price, 'price')
        if (input.stop_loss != null) payload.stop_loss = normalizePositiveNumber(input.stop_loss, 'stop_loss')
        if (input.target_price != null) payload.target_price = normalizePositiveNumber(input.target_price, 'target_price')
        return await validateExecutionPreflight(accountId, payload)
      },
    },
    {
      name: 'build_execution_proposal',
      description:
        'Build a backend execution proposal for a paper-trading mutation, including the exact request payload and the state signature that must still match at execution time.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for execution proposal building.',
          },
          action: {
            type: 'string',
            enum: ['buy', 'sell', 'close', 'modify_risk'],
            description: 'Mutation to prepare without executing.',
          },
          symbol: { type: 'string', description: 'Symbol for entry proposals.' },
          trade_id: { type: 'string', description: 'Trade identifier for close or risk proposals.' },
          quantity: { type: 'integer', minimum: 1, description: 'Quantity for entry proposals.' },
          price: { type: 'number', description: 'Optional explicit execution price.' },
          stop_loss: { type: 'number', description: 'Proposed stop loss for risk updates.' },
          target_price: { type: 'number', description: 'Proposed target price for risk updates.' },
          dry_run: { type: 'boolean', description: 'Preserved for parity with execution preflight.' },
        },
        required: ['action'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const payload: Record<string, unknown> = {
          action: String(input.action ?? '').trim(),
          dry_run: input.dry_run == null ? true : Boolean(input.dry_run),
        }
        if (input.symbol != null) payload.symbol = normalizeSymbol(input.symbol)
        if (input.trade_id != null) payload.trade_id = String(input.trade_id).trim()
        if (input.quantity != null) payload.quantity = Math.trunc(normalizePositiveNumber(input.quantity, 'quantity'))
        if (input.price != null) payload.price = normalizePositiveNumber(input.price, 'price')
        if (input.stop_loss != null) payload.stop_loss = normalizePositiveNumber(input.stop_loss, 'stop_loss')
        if (input.target_price != null) payload.target_price = normalizePositiveNumber(input.target_price, 'target_price')
        return await buildExecutionProposal(accountId, payload)
      },
    },
    {
      name: 'create_session_retrospective',
      description: 'Persist a structured keep/remove/fix/improve retrospective for the selected paper account and queue any promotable improvements.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for retrospective creation.',
          },
          session_id: { type: 'string', description: 'Optional session identifier.' },
          keep: { type: 'array', items: { type: 'object' }, description: 'Items that should be preserved.' },
          remove: { type: 'array', items: { type: 'object' }, description: 'Items that should be removed.' },
          fix: { type: 'array', items: { type: 'object' }, description: 'Items that must be fixed.' },
          improve: { type: 'array', items: { type: 'object' }, description: 'Candidate improvements to evaluate or promote.' },
          evidence: { type: 'array', items: { type: 'object' }, description: 'Supporting evidence objects.' },
          owner: { type: 'string', description: 'Owner responsible for the retrospective outputs.' },
          promotion_state: { type: 'string', description: 'Default promotion state for queued improvements.' },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const payload = {
          session_id: typeof input.session_id === 'string' ? input.session_id.trim() : undefined,
          keep: Array.isArray(input.keep) ? input.keep : [],
          remove: Array.isArray(input.remove) ? input.remove : [],
          fix: Array.isArray(input.fix) ? input.fix : [],
          improve: Array.isArray(input.improve) ? input.improve : [],
          evidence: Array.isArray(input.evidence) ? input.evidence : [],
          owner: typeof input.owner === 'string' && input.owner.trim() ? input.owner.trim() : 'paper_trading_operator',
          promotion_state:
            typeof input.promotion_state === 'string' && input.promotion_state.trim()
              ? input.promotion_state.trim()
              : 'queued',
        }
        const retrospective = await fetchJson(`/api/paper-trading/accounts/${accountId}/retrospectives`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        return {
          retrospective,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'get_latest_session_retrospective',
      description: 'Fetch the latest persisted operator retrospective for the selected paper account.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for retrospective retrieval.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(`/api/paper-trading/accounts/${accountId}/retrospectives/latest`)
      },
    },
    {
      name: 'get_trade_outcome_lineage',
      description:
        'Return recent closed-trade outcome evaluations for the selected paper account, including research, decision, review, and prompt lineage.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for outcome lineage retrieval.',
          },
          symbol: {
            type: 'string',
            description: 'Optional symbol filter for recent closed-trade lineage.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 100,
            description: 'Maximum number of recent outcome evaluations to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const params = new URLSearchParams()
        const limit = input.limit == null ? 20 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        params.set('limit', String(limit))
        const symbol = normalizeSymbol(input.symbol)
        if (symbol) {
          params.set('symbol', symbol)
        }
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/learning/outcomes?${params.toString()}`,
        )
      },
    },
    {
      name: 'get_promotable_improvements',
      description:
        'Return the queued promotable improvements for the selected paper account, including outcome evidence, benchmark evidence, and guardrails.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for promotable improvement retrieval.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 100,
            description: 'Maximum number of queued improvements to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 20 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/learning/promotable-improvements?limit=${limit}`,
        )
      },
    },
    {
      name: 'decide_promotable_improvement',
      description:
        'Apply a promote, watch, or reject decision to a queued promotable improvement and return both the decision result and the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the improvement decision.',
          },
          improvement_id: {
            type: 'string',
            description: 'Promotable improvement identifier.',
          },
          decision: {
            type: 'string',
            enum: ['promote', 'watch', 'reject'],
            description: 'Decision to apply.',
          },
          owner: {
            type: 'string',
            description: 'Owner taking responsibility for the decision.',
          },
          reason: {
            type: 'string',
            description: 'Short explanation for the decision.',
          },
          benchmark_evidence: {
            type: 'array',
            items: { type: 'object' },
            description: 'Optional replay or benchmark evidence.',
          },
          guardrail: {
            type: 'string',
            description: 'Optional guardrail attached to the decision.',
          },
        },
        required: ['improvement_id', 'decision'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const improvementId = String(input.improvement_id ?? '').trim()
        if (!improvementId) {
          throw new Error('improvement_id is required to decide a promotable improvement.')
        }
        const payload = {
          decision: String(input.decision ?? '').trim().toLowerCase(),
          owner: typeof input.owner === 'string' && input.owner.trim() ? input.owner.trim() : 'paper_trading_operator',
          reason: typeof input.reason === 'string' ? input.reason.trim() : '',
          benchmark_evidence: Array.isArray(input.benchmark_evidence) ? input.benchmark_evidence : [],
          guardrail: typeof input.guardrail === 'string' ? input.guardrail.trim() : '',
        }
        const decision = await fetchJson(
          `/api/paper-trading/accounts/${accountId}/learning/promotable-improvements/${encodeURIComponent(improvementId)}/decision`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          },
        )
        return {
          decision,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'get_discovery_artifact',
      description: 'Fetch the latest stored discovery artifact for the selected paper account without triggering a new run.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for discovery retrieval.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 25,
            description: 'Maximum number of discovery candidates to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 10 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        const envelope = await fetchJson<DiscoveryEnvelope>(
          `/api/paper-trading/accounts/${accountId}/discovery?limit=${limit}`,
        )
        publishPaperTradingArtifactUpdate('discovery', envelope)
        return envelope
      },
    },
    {
      name: 'get_focused_research_artifact',
      description: 'Fetch the latest stored focused research packet for a candidate or symbol without triggering a new run.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for research retrieval.',
          },
          candidate_id: {
            type: 'string',
            description: 'Candidate identifier from the discovery watchlist.',
          },
          symbol: {
            type: 'string',
            description: 'Raw symbol text when candidate_id is not available.',
          },
        },
        anyOf: [{ required: ['candidate_id'] }, { required: ['symbol'] }],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const params = new URLSearchParams()
        if (typeof input.candidate_id === 'string' && input.candidate_id.trim()) {
          params.set('candidate_id', input.candidate_id.trim())
        }
        if (typeof input.symbol === 'string' && input.symbol.trim()) {
          params.set('symbol', normalizeSymbol(input.symbol))
        }
        const envelope = await fetchJson<ResearchEnvelope>(
          `/api/paper-trading/accounts/${accountId}/research?${params.toString()}`,
        )
        publishPaperTradingArtifactUpdate('research', envelope)
        return envelope
      },
    },
    {
      name: 'get_decision_artifact',
      description: 'Fetch the latest stored decision envelope for open positions in the selected paper account without triggering a new run.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for decision retrieval.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 10,
            description: 'Maximum number of position decisions to return.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const limit = input.limit == null ? 3 : Math.trunc(normalizePositiveNumber(input.limit, 'limit'))
        const envelope = await fetchJson<DecisionEnvelope>(
          `/api/paper-trading/accounts/${accountId}/decisions?limit=${limit}`,
        )
        publishPaperTradingArtifactUpdate('decisions', envelope)
        return envelope
      },
    },
    {
      name: 'get_daily_review_artifact',
      description: 'Fetch the latest stored daily review report for the selected paper account without triggering a new run.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for review retrieval.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const envelope = await fetchJson<ReviewEnvelope>(
          `/api/paper-trading/accounts/${accountId}/review`,
        )
        publishPaperTradingArtifactUpdate('review', envelope)
        return envelope
      },
    },
    {
      name: 'get_learning_summary',
      description: 'Fetch the current learning summary for the selected paper account to understand what the system should improve next.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the learning summary.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/learning-summary`,
        )
      },
    },
    {
      name: 'get_learning_readiness',
      description:
        'Fetch the current learning backlog for the selected paper account, including unevaluated closed trades and queued improvement decisions.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the learning readiness snapshot.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/learning/readiness`,
        )
      },
    },
    {
      name: 'evaluate_closed_trades',
      description:
        'Evaluate unevaluated closed paper trades for the selected account and persist outcome lineage back into the learning store.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for closed-trade evaluation.',
          },
          limit: {
            type: 'integer',
            minimum: 1,
            maximum: 500,
            description: 'Maximum number of closed trades to inspect.',
          },
          symbol: {
            type: 'string',
            description: 'Optional symbol filter for closed-trade evaluation.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const payload = {
          limit: input.limit == null ? 50 : Math.trunc(normalizePositiveNumber(input.limit, 'limit')),
          symbol: typeof input.symbol === 'string' && input.symbol.trim() ? normalizeSymbol(input.symbol) : undefined,
        }
        const evaluation = await fetchJson(`/api/paper-trading/accounts/${accountId}/learning/evaluate-closed-trades`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        return {
          evaluation,
          operator_snapshot: await refreshAndSnapshot(accountId),
        }
      },
    },
    {
      name: 'get_improvement_report',
      description: 'Fetch the current improvement report for the selected paper account so strategy changes remain benchmark-driven.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the improvement report.',
          },
        },
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        return await fetchJson(
          `/api/paper-trading/accounts/${accountId}/improvement-report`,
        )
      },
    },
    {
      name: 'buy_paper_position',
      description: 'Submit a manual paper buy order for the selected account using raw trading inputs and return the execution result plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the buy order.',
          },
          symbol: {
            type: 'string',
            description: 'Stock symbol exactly as the operator would type it.',
          },
          quantity: {
            type: 'integer',
            minimum: 1,
            description: 'Number of shares to buy.',
          },
          order_type: {
            type: 'string',
            enum: ['MARKET', 'LIMIT'],
            anyOf: [
              { const: 'MARKET', title: 'Market order' },
              { const: 'LIMIT', title: 'Limit order' },
            ],
            description: 'Use LIMIT only when the operator explicitly wants a limit price.',
          },
          price: {
            type: 'number',
            description: 'Limit price. Required when order_type is LIMIT.',
          },
        },
        required: ['symbol', 'quantity'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const orderType = normalizeOrderType(input.order_type)
        const payload: Record<string, unknown> = {
          symbol: normalizeSymbol(input.symbol),
          quantity: Math.trunc(normalizePositiveNumber(input.quantity, 'quantity')),
          order_type: orderType,
        }
        if (orderType === 'LIMIT') {
          payload.price = normalizePositiveNumber(input.price, 'price')
        }
        return await gatedMutationResult(
          accountId,
          {
            action: 'buy',
            symbol: payload.symbol,
            quantity: payload.quantity,
            price: payload.price,
            dry_run: false,
          },
          async () =>
            await fetchJson(`/api/paper-trading/accounts/${accountId}/trades/buy`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            }),
        )
      },
    },
    {
      name: 'sell_paper_position',
      description: 'Submit a manual paper sell order for the selected account using raw trading inputs and return the execution result plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the sell order.',
          },
          symbol: {
            type: 'string',
            description: 'Stock symbol exactly as the operator would type it.',
          },
          quantity: {
            type: 'integer',
            minimum: 1,
            description: 'Number of shares to sell.',
          },
          order_type: {
            type: 'string',
            enum: ['MARKET', 'LIMIT'],
            anyOf: [
              { const: 'MARKET', title: 'Market order' },
              { const: 'LIMIT', title: 'Limit order' },
            ],
            description: 'Use LIMIT only when the operator explicitly wants a limit price.',
          },
          price: {
            type: 'number',
            description: 'Limit price. Required when order_type is LIMIT.',
          },
        },
        required: ['symbol', 'quantity'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const orderType = normalizeOrderType(input.order_type)
        const payload: Record<string, unknown> = {
          symbol: normalizeSymbol(input.symbol),
          quantity: Math.trunc(normalizePositiveNumber(input.quantity, 'quantity')),
          order_type: orderType,
        }
        if (orderType === 'LIMIT') {
          payload.price = normalizePositiveNumber(input.price, 'price')
        }
        return await gatedMutationResult(
          accountId,
          {
            action: 'sell',
            symbol: payload.symbol,
            quantity: payload.quantity,
            price: payload.price,
            dry_run: false,
          },
          async () =>
            await fetchJson(`/api/paper-trading/accounts/${accountId}/trades/sell`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            }),
        )
      },
    },
    {
      name: 'close_paper_trade',
      description: 'Close an existing open paper trade at the live exit path and return the close result plus the refreshed operator snapshot.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the close action.',
          },
          trade_id: {
            type: 'string',
            description: 'Open trade identifier to close.',
          },
        },
        required: ['trade_id'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const tradeId = String(input.trade_id ?? '').trim()
        if (!tradeId) {
          throw new Error('trade_id is required to close a paper trade.')
        }
        return await gatedMutationResult(
          accountId,
          {
            action: 'close',
            trade_id: tradeId,
            dry_run: false,
          },
          async () =>
            await fetchJson(`/api/paper-trading/accounts/${accountId}/trades/${encodeURIComponent(tradeId)}/close`, {
              method: 'POST',
            }),
        )
      },
    },
    {
      name: 'modify_paper_trade_risk',
      description: 'Update the stop loss and or target price for an open paper trade, then refresh the desk before returning.',
      inputSchema: {
        type: 'object',
        properties: {
          account_id: {
            ...accountSchema,
            description: 'Optional account override for the risk update.',
          },
          trade_id: {
            type: 'string',
            description: 'Open trade identifier to update.',
          },
          stop_loss: {
            type: 'number',
            description: 'Updated stop loss price.',
          },
          target_price: {
            type: 'number',
            description: 'Updated target price.',
          },
        },
        required: ['trade_id'],
      },
      execute: async (input = {}) => {
        const accountId = resolveAccountId(input)!
        const tradeId = String(input.trade_id ?? '').trim()
        if (!tradeId) {
          throw new Error('trade_id is required to update trade risk levels.')
        }

        const payload: Record<string, unknown> = {}
        if (input.stop_loss != null) payload.stop_loss = normalizePositiveNumber(input.stop_loss, 'stop_loss')
        if (input.target_price != null) payload.target_price = normalizePositiveNumber(input.target_price, 'target_price')
        if (Object.keys(payload).length === 0) {
          throw new Error('Provide stop_loss, target_price, or both when updating trade risk levels.')
        }
        return await gatedMutationResult(
          accountId,
          {
            action: 'modify_risk',
            trade_id: tradeId,
            stop_loss: payload.stop_loss,
            target_price: payload.target_price,
            dry_run: false,
          },
          async () =>
            await fetchJson(`/api/paper-trading/accounts/${accountId}/trades/${encodeURIComponent(tradeId)}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            }),
        )
      },
    },
  ]
}

export function usePaperTradingWebMCP(options: UsePaperTradingWebMCPOptions) {
  const latestOptionsRef = useRef(options)
  latestOptionsRef.current = options

  const fetchJsonRef = useRef(createFetchJson())
  const [readiness, setReadiness] = useState<WebMCPReadiness>(BLOCKED_WEBMCP_STATUS)

  const getCurrentContext = () => ({
    ...latestOptionsRef.current,
    fetchJson: fetchJsonRef.current,
  })

  useEffect(() => {
    const modelContext = navigator.modelContext
    if (!modelContext?.registerTool) {
      setReadiness(BLOCKED_WEBMCP_STATUS)
      return
    }

    const controller = new AbortController()
    const tools = buildTools(getCurrentContext)

    for (const tool of tools) {
      try {
        modelContext.registerTool(tool, { signal: controller.signal })
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        // Vite hot reload can leave tools registered in the browser process briefly.
        // Ignore duplicate-name errors so the page stays usable during development.
        if (message.includes('Duplicate tool name')) {
          continue
        }
        throw error
      }
    }

    return () => controller.abort()
  }, [])

  useEffect(() => {
    let active = true

    const updateReadiness = (value: WebMCPReadiness) => {
      if (active) {
        setReadiness(value)
      }
    }

    const verifyReadiness = async () => {
      const modelContext = navigator.modelContext
      const testing = navigator.modelContextTesting

      if (!modelContext?.registerTool) {
        updateReadiness(BLOCKED_WEBMCP_STATUS)
        return
      }

      if (!testing?.listTools || !testing?.executeTool) {
        updateReadiness({
          status: 'blocked',
          summary: 'WebMCP testing unavailable',
          detail: 'navigator.modelContextTesting is missing, so direct browser-native execution cannot be proven.',
          tool_count: 0,
          registered: false,
          testing_available: false,
          direct_execution_ready: false,
          probe_tool: null,
        })
        return
      }

      try {
        const tools = await testing.listTools()
        const toolCount = Array.isArray(tools) ? tools.length : 0
        if (toolCount === 0) {
          updateReadiness({
            status: 'blocked',
            summary: 'WebMCP registered no tools',
            detail: 'navigator.modelContextTesting.listTools() returned zero registered tools for this page.',
            tool_count: 0,
            registered: false,
            testing_available: true,
            direct_execution_ready: false,
            probe_tool: null,
          })
          return
        }

        const accountsResult = parseTestingResult(await testing.executeTool('list_paper_accounts', '{}'))
        const accountCount = Array.isArray(accountsResult.accounts) ? accountsResult.accounts.length : 0
        if (accountCount === 0) {
          updateReadiness({
            status: 'blocked',
            summary: 'WebMCP tool context is stale',
            detail: 'Direct execution succeeded, but list_paper_accounts returned no accounts. Reload or re-register tools with current operator state.',
            tool_count: toolCount,
            registered: true,
            testing_available: true,
            direct_execution_ready: false,
            probe_tool: 'list_paper_accounts',
          })
          return
        }

        const selectedAccountId = latestOptionsRef.current.selectedAccountId ?? null
        if (selectedAccountId) {
          const capabilityResult = parseTestingResult(
            await testing.executeTool(
              'get_capability_snapshot',
              JSON.stringify({ account_id: selectedAccountId }),
            ),
          )
          if (
            capabilityResult.account_id !== selectedAccountId ||
            typeof capabilityResult.overall_status !== 'string'
          ) {
            updateReadiness({
              status: 'blocked',
              summary: 'WebMCP operator probe failed',
              detail: 'get_capability_snapshot did not return the selected account state, so direct operator execution is not trustworthy yet.',
              tool_count: toolCount,
              registered: true,
              testing_available: true,
              direct_execution_ready: false,
              probe_tool: 'get_capability_snapshot',
            })
            return
          }
        }

        updateReadiness({
          status: 'ready',
          summary: `WebMCP ready (${toolCount})`,
          detail: selectedAccountId
            ? `Direct execution verified via get_capability_snapshot for ${selectedAccountId}.`
            : 'Direct execution verified via list_paper_accounts.',
          tool_count: toolCount,
          registered: true,
          testing_available: true,
          direct_execution_ready: true,
          probe_tool: selectedAccountId ? 'get_capability_snapshot' : 'list_paper_accounts',
        })
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        updateReadiness({
          status: 'blocked',
          summary: 'WebMCP execution failed',
          detail: message,
          tool_count: 0,
          registered: true,
          testing_available: true,
          direct_execution_ready: false,
          probe_tool: 'list_paper_accounts',
        })
      }
    }

    void verifyReadiness()

    return () => {
      active = false
    }
  }, [options.accounts, options.selectedAccountId])

  return readiness
}

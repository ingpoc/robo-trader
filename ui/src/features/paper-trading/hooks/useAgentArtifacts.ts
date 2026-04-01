import { useCallback, useEffect, useMemo, useState } from 'react'

import type {
  AgentCandidate,
  DecisionEnvelope,
  DiscoveryEnvelope,
  ResearchEnvelope,
  ReviewEnvelope,
} from '../types'

export type ArtifactTab = 'discovery' | 'research' | 'decisions' | 'review'
export const PAPER_TRADING_ARTIFACT_EVENT = 'paper-trading-artifact-update'

type ArtifactEnvelope = DiscoveryEnvelope | ResearchEnvelope | DecisionEnvelope | ReviewEnvelope

interface ArtifactUpdateDetail {
  tab: ArtifactTab
  payload: ArtifactEnvelope
}

interface UseAgentArtifactsOptions {
  onRunComplete?: () => Promise<void> | void
}

interface AgentArtifactsState {
  discovery: DiscoveryEnvelope | null
  research: ResearchEnvelope | null
  decisions: DecisionEnvelope | null
  review: ReviewEnvelope | null
  isLoading: boolean
  activeRequest: ArtifactTab | null
  error: string | null
}

interface CandidateSelection {
  candidate_id?: string
  symbol?: string
}

const tabEndpointSuffix: Record<ArtifactTab, string> = {
  discovery: 'discovery',
  research: 'research',
  decisions: 'decisions',
  review: 'review',
}

export function publishPaperTradingArtifactUpdate(tab: ArtifactTab, payload: ArtifactEnvelope) {
  if (typeof window === 'undefined') return

  window.dispatchEvent(
    new CustomEvent<ArtifactUpdateDetail>(PAPER_TRADING_ARTIFACT_EVENT, {
      detail: { tab, payload },
    }),
  )
}

const emptyDiscovery: DiscoveryEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before loading discovery artifacts.'],
  context_mode: 'stateful_watchlist',
  artifact_count: 0,
  criteria: [],
  considered: [],
  candidates: [],
}

const emptyResearch: ResearchEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account and candidate before generating research.'],
  context_mode: 'single_candidate_research',
  artifact_count: 0,
  criteria: [],
  considered: [],
  research: null,
}

const emptyDecisions: DecisionEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before generating decision packets.'],
  context_mode: 'delta_position_review',
  artifact_count: 0,
  criteria: [],
  considered: [],
  decisions: [],
}

const emptyReview: ReviewEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before generating a review report.'],
  context_mode: 'delta_daily_review',
  artifact_count: 0,
  criteria: [],
  considered: [],
  review: null,
}

function buildResearchQuery(selection?: CandidateSelection) {
  const params = new URLSearchParams()
  if (selection?.candidate_id) params.set('candidate_id', selection.candidate_id)
  if (selection?.symbol) params.set('symbol', selection.symbol)
  const query = params.toString()
  return query ? `?${query}` : ''
}

async function readErrorMessage(response: Response, fallback: string) {
  const contentType = response.headers.get('content-type') ?? ''

  try {
    if (contentType.includes('application/json')) {
      const payload = await response.json()
      if (typeof payload?.error === 'string' && payload.error.trim()) return payload.error
      if (typeof payload?.detail === 'string' && payload.detail.trim()) return payload.detail
      if (Array.isArray(payload?.blockers) && payload.blockers.length > 0) {
        const firstBlocker = payload.blockers.find((value: unknown) => typeof value === 'string' && value.trim())
        if (typeof firstBlocker === 'string') return firstBlocker
      }
    } else {
      const body = await response.text()
      if (body.trim()) return body
    }
  } catch {
    // Use the fallback when the error payload cannot be parsed.
  }

  return fallback
}

export function useAgentArtifacts(
  accountId?: string,
  selectedCandidate?: AgentCandidate | null,
  options?: UseAgentArtifactsOptions,
) {
  const [state, setState] = useState<AgentArtifactsState>({
    discovery: null,
    research: null,
    decisions: null,
    review: null,
    isLoading: false,
    activeRequest: null,
    error: null,
  })

  const researchSelection = useMemo<CandidateSelection | undefined>(() => {
    if (!selectedCandidate) return undefined
    return {
      candidate_id: selectedCandidate.candidate_id,
      symbol: selectedCandidate.symbol,
    }
  }, [selectedCandidate])

  useEffect(() => {
    setState({
      discovery: null,
      research: null,
      decisions: null,
      review: null,
      isLoading: false,
      activeRequest: null,
      error: null,
    })
  }, [accountId])

  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleArtifactUpdate = (event: Event) => {
      const detail = (event as CustomEvent<ArtifactUpdateDetail>).detail
      if (!detail || typeof detail !== 'object') return

      setState(prev => ({
        ...prev,
        discovery: detail.tab === 'discovery' ? (detail.payload as DiscoveryEnvelope) : prev.discovery,
        research: detail.tab === 'research' ? (detail.payload as ResearchEnvelope) : prev.research,
        decisions: detail.tab === 'decisions' ? (detail.payload as DecisionEnvelope) : prev.decisions,
        review: detail.tab === 'review' ? (detail.payload as ReviewEnvelope) : prev.review,
        isLoading: false,
        activeRequest: null,
        error: null,
      }))
    }

    window.addEventListener(PAPER_TRADING_ARTIFACT_EVENT, handleArtifactUpdate as EventListener)
    return () => {
      window.removeEventListener(PAPER_TRADING_ARTIFACT_EVENT, handleArtifactUpdate as EventListener)
    }
  }, [])

  const clearTab = useCallback((tab: ArtifactTab) => {
    setState(prev => ({
      ...prev,
      discovery: tab === 'discovery' ? null : prev.discovery,
      research: tab === 'research' ? null : prev.research,
      decisions: tab === 'decisions' ? null : prev.decisions,
      review: tab === 'review' ? null : prev.review,
      activeRequest: prev.activeRequest === tab ? null : prev.activeRequest,
      error: null,
    }))
  }, [])

  const fetchEnvelope = useCallback(async (
    tab: ArtifactTab,
    selection?: CandidateSelection,
  ): Promise<ArtifactEnvelope> => {
    if (!accountId) {
      throw new Error('No paper trading account selected.')
    }

    const endpoint = tab === 'research'
      ? `/api/paper-trading/accounts/${accountId}/research${buildResearchQuery(selection)}`
      : `/api/paper-trading/accounts/${accountId}/${tabEndpointSuffix[tab]}`

    const response = await fetch(endpoint)
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, `Failed to fetch ${tab}`))
    }

    return await response.json() as ArtifactEnvelope
  }, [accountId])

  useEffect(() => {
    if (!accountId) return

    let cancelled = false

    void (async () => {
      setState(prev => ({ ...prev, isLoading: true, activeRequest: null, error: null }))

      try {
        const [discovery, research, decisions, review] = await Promise.all([
          fetchEnvelope('discovery'),
          fetchEnvelope('research', researchSelection),
          fetchEnvelope('decisions'),
          fetchEnvelope('review'),
        ])

        if (cancelled) return

        setState({
          discovery: discovery as DiscoveryEnvelope,
          research: research as ResearchEnvelope,
          decisions: decisions as DecisionEnvelope,
          review: review as ReviewEnvelope,
          isLoading: false,
          activeRequest: null,
          error: null,
        })
      } catch (error) {
        if (cancelled) return

        setState(prev => ({
          ...prev,
          isLoading: false,
          activeRequest: null,
          error: error instanceof Error ? error.message : 'Failed to load artifact stages',
        }))
      }
    })()

    return () => {
      cancelled = true
    }
  }, [accountId, fetchEnvelope, researchSelection])

  const requestTab = useCallback(async (
    tab: ArtifactTab,
    method: 'GET' | 'POST' = 'GET',
    selection?: CandidateSelection,
  ) => {
    if (!accountId) {
      setState(prev => ({
        ...prev,
        discovery: prev.discovery ?? emptyDiscovery,
        research: prev.research ?? emptyResearch,
        decisions: prev.decisions ?? emptyDecisions,
        review: prev.review ?? emptyReview,
        isLoading: false,
        activeRequest: null,
        error: null,
      }))
      return
    }

    if (method === 'POST' && tab === 'research' && !selection?.candidate_id && !selection?.symbol) {
      setState(prev => ({
        ...prev,
        research: {
          ...emptyResearch,
          blockers: ['Choose a discovery candidate before generating research.'],
          status: 'empty',
        },
        isLoading: false,
        activeRequest: null,
        error: null,
      }))
      return
    }

    setState(prev => ({ ...prev, isLoading: true, activeRequest: tab, error: null }))

    try {
      let endpoint = ''
      let init: RequestInit = { method }

      if (tab === 'discovery') endpoint = `/api/paper-trading/accounts/${accountId}/discovery`
      if (tab === 'research') endpoint = `/api/paper-trading/accounts/${accountId}/research${buildResearchQuery(selection)}`
      if (tab === 'decisions') endpoint = `/api/paper-trading/accounts/${accountId}/decisions`
      if (tab === 'review') endpoint = `/api/paper-trading/accounts/${accountId}/review`

      if (method === 'POST') {
        if (tab === 'discovery') endpoint = `/api/paper-trading/accounts/${accountId}/runs/discovery`
        if (tab === 'research') {
          endpoint = `/api/paper-trading/accounts/${accountId}/runs/research`
          init = {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(selection ?? {}),
          }
        }
        if (tab === 'decisions') endpoint = `/api/paper-trading/accounts/${accountId}/runs/decision-review`
        if (tab === 'review') endpoint = `/api/paper-trading/accounts/${accountId}/runs/daily-review`
      }

      const response = await fetch(endpoint, init)
      if (!response.ok) {
        throw new Error(
          await readErrorMessage(
            response,
            `Failed to ${method === 'POST' ? 'run' : 'fetch'} ${tab}`,
          ),
        )
      }

      const payload = await response.json()
      setState(prev => ({
        ...prev,
        discovery: tab === 'discovery' ? payload : prev.discovery,
        research: tab === 'research' ? payload : prev.research,
        decisions: tab === 'decisions' ? payload : prev.decisions,
        review: tab === 'review' ? payload : prev.review,
        isLoading: false,
        activeRequest: null,
        error: null,
      }))
      if (method === 'POST') {
        await options?.onRunComplete?.()
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        activeRequest: null,
        error: error instanceof Error ? error.message : `Failed to fetch ${tab}`,
      }))
    }
  }, [accountId, options, researchSelection])

  return {
    ...state,
    clearTab,
    refreshTab: (tab: ArtifactTab, selection?: CandidateSelection) => requestTab(tab, 'GET', selection),
    runTab: (tab: ArtifactTab, selection?: CandidateSelection) =>
      requestTab(tab, 'POST', selection ?? (tab === 'research' ? researchSelection : undefined)),
  }
}

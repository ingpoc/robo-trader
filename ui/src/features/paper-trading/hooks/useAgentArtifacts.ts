import { useCallback, useEffect, useMemo, useState } from 'react'

import type {
  AgentCandidate,
  DecisionEnvelope,
  DiscoveryEnvelope,
  ResearchEnvelope,
  ReviewEnvelope,
} from '../types'

export type ArtifactTab = 'discovery' | 'research' | 'decisions' | 'review'

interface AgentArtifactsState {
  discovery: DiscoveryEnvelope | null
  research: ResearchEnvelope | null
  decisions: DecisionEnvelope | null
  review: ReviewEnvelope | null
  isLoading: boolean
  error: string | null
}

interface CandidateSelection {
  candidate_id?: string
  symbol?: string
}

const emptyDiscovery: DiscoveryEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before loading discovery artifacts.'],
  context_mode: 'watchlist_only',
  artifact_count: 0,
  candidates: [],
}

const emptyResearch: ResearchEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account and candidate before generating research.'],
  context_mode: 'single_candidate_research',
  artifact_count: 0,
  research: null,
}

const emptyDecisions: DecisionEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before generating decision packets.'],
  context_mode: 'delta_position_review',
  artifact_count: 0,
  decisions: [],
}

const emptyReview: ReviewEnvelope = {
  status: 'blocked',
  generated_at: new Date(0).toISOString(),
  blockers: ['Select a paper trading account before generating a review report.'],
  context_mode: 'delta_daily_review',
  artifact_count: 0,
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
    // Fall back to the generic message when the error payload cannot be parsed.
  }

  return fallback
}

export function useAgentArtifacts(
  accountId?: string,
  activeTab?: ArtifactTab,
  selectedCandidate?: AgentCandidate | null,
) {
  const [state, setState] = useState<AgentArtifactsState>({
    discovery: null,
    research: null,
    decisions: null,
    review: null,
    isLoading: false,
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
      error: null,
    })
  }, [accountId])

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
        error: null,
      }))
      return
    }

    if (tab === 'research' && !selection?.candidate_id && !selection?.symbol) {
      setState(prev => ({
        ...prev,
        research: {
          ...emptyResearch,
          blockers: ['Choose a discovery candidate before generating research.'],
          status: 'empty',
        },
        isLoading: false,
        error: null,
      }))
      return
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }))

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
        error: null,
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : `Failed to fetch ${tab}`,
      }))
    }
  }, [accountId])

  useEffect(() => {
    if (!activeTab) return
    if (activeTab === 'research') return
    if (activeTab === 'discovery' && state.discovery) return
    if (activeTab === 'decisions' && state.decisions) return
    if (activeTab === 'review' && state.review) return
    void requestTab(activeTab, 'GET')
  }, [
    activeTab,
    requestTab,
    state.decisions,
    state.discovery,
    state.review,
  ])

  return {
    ...state,
    refreshTab: (tab: ArtifactTab, selection?: CandidateSelection) => requestTab(tab, 'GET', selection),
    runTab: (tab: ArtifactTab, selection?: CandidateSelection) => requestTab(tab, 'POST', selection),
  }
}

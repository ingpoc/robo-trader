import { useEffect, useState } from 'react'

import type {
  DecisionEnvelope,
  DiscoveryEnvelope,
  ResearchEnvelope,
  ReviewEnvelope,
} from '@/features/paper-trading/types'

interface OverviewArtifactsState {
  discovery: DiscoveryEnvelope | null
  research: ResearchEnvelope | null
  decisions: DecisionEnvelope | null
  review: ReviewEnvelope | null
  isLoading: boolean
  error: string | null
}

export function useOverviewArtifacts(accountId?: string | null) {
  const [state, setState] = useState<OverviewArtifactsState>({
    discovery: null,
    research: null,
    decisions: null,
    review: null,
    isLoading: false,
    error: null,
  })

  useEffect(() => {
    if (!accountId) {
      setState({
        discovery: null,
        research: null,
        decisions: null,
        review: null,
        isLoading: false,
        error: null,
      })
      return
    }

    let cancelled = false

    const load = async () => {
      setState(prev => ({ ...prev, isLoading: true, error: null }))

      try {
        const fetchArtifact = async (path: string) => {
          const response = await fetch(path)
          if (!response.ok) {
            throw new Error(`Failed to load ${path}`)
          }
          return response.json()
        }

        const [discovery, research, decisions, review] = await Promise.all([
          fetchArtifact(`/api/paper-trading/accounts/${accountId}/discovery`),
          fetchArtifact(`/api/paper-trading/accounts/${accountId}/research`),
          fetchArtifact(`/api/paper-trading/accounts/${accountId}/decisions`),
          fetchArtifact(`/api/paper-trading/accounts/${accountId}/review`),
        ])

        if (cancelled) return

        setState({
          discovery,
          research,
          decisions,
          review,
          isLoading: false,
          error: null,
        })
      } catch (error) {
        if (cancelled) return
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to load overview artifacts',
        }))
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [accountId])

  return state
}

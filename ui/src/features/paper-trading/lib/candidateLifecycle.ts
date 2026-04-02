import type { AgentCandidate } from '../types'

export type CandidateBucketKey = 'fresh_queue' | 'actionable' | 'keep_watch' | 'rejected'

export interface CandidateBucketDefinition {
  key: CandidateBucketKey
  title: string
  description: string
}

export const candidateBucketDefinitions: CandidateBucketDefinition[] = [
  {
    key: 'fresh_queue',
    title: 'Fresh queue',
    description: 'Names that still need fresh research or were reactivated by stale memory or a new trigger.',
  },
  {
    key: 'actionable',
    title: 'Actionable',
    description: 'Fresh actionable packets are ready to promote into proposal and preflight work.',
  },
  {
    key: 'keep_watch',
    title: 'Keep watch',
    description: 'Fresh watch-only packets stay here until new evidence or stale-memory refresh justifies another pass.',
  },
  {
    key: 'rejected',
    title: 'Rejected',
    description: 'Research ran, but evidence quality or runtime blockers made the setup unfit to advance.',
  },
]

export function hasFreshResearchMemory(candidate: AgentCandidate): boolean {
  return candidate.research_freshness === 'fresh' && Boolean(candidate.last_researched_at)
}

export function getCandidateBucket(candidate: AgentCandidate): CandidateBucketKey {
  if (candidate.lifecycle_state) {
    return candidate.lifecycle_state
  }
  if (!hasFreshResearchMemory(candidate)) {
    return 'fresh_queue'
  }
  if (candidate.last_actionability === 'actionable') {
    return 'actionable'
  }
  if (candidate.last_actionability === 'watch_only') {
    return 'keep_watch'
  }
  return 'rejected'
}

export function getCandidatesByBucket(candidates: AgentCandidate[]): Record<CandidateBucketKey, AgentCandidate[]> {
  return candidates.reduce<Record<CandidateBucketKey, AgentCandidate[]>>(
    (groups, candidate) => {
      groups[getCandidateBucket(candidate)].push(candidate)
      return groups
    },
    {
      fresh_queue: [],
      actionable: [],
      keep_watch: [],
      rejected: [],
    },
  )
}

export function getPreferredResearchCandidate(candidates: AgentCandidate[]): AgentCandidate | null {
  const groups = getCandidatesByBucket(candidates)
  return groups.fresh_queue[0] ?? groups.actionable[0] ?? groups.keep_watch[0] ?? groups.rejected[0] ?? null
}

export function getTrackedResearchCandidates(candidates: AgentCandidate[]): AgentCandidate[] {
  return candidates.filter(candidate => Boolean(candidate.last_researched_at))
}

export function getDiscoveryQueueCandidates(candidates: AgentCandidate[]): AgentCandidate[] {
  return candidates.filter(candidate => getCandidateBucket(candidate) === 'fresh_queue')
}

export function getAnalyzedCandidates(candidates: AgentCandidate[]): AgentCandidate[] {
  return candidates
    .filter(candidate => getCandidateBucket(candidate) !== 'fresh_queue')
    .sort((left, right) => {
      const leftTimestamp = left.last_researched_at ? new Date(left.last_researched_at).getTime() : 0
      const rightTimestamp = right.last_researched_at ? new Date(right.last_researched_at).getTime() : 0
      return rightTimestamp - leftTimestamp
    })
}

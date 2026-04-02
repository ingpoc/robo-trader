import { BookmarkCheck } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { candidateBucketDefinitions, getCandidateBucket } from '../lib/candidateLifecycle'
import type { AgentCandidate } from '../types'

interface AnalyzedWatchlistPanelProps {
  candidates: AgentCandidate[]
  selectedCandidateId?: string | null
  onSelectCandidate?: (candidate: AgentCandidate) => void
}

export function AnalyzedWatchlistPanel({
  candidates,
  selectedCandidateId,
  onSelectCandidate,
}: AnalyzedWatchlistPanelProps) {
  if (!candidates.length) return null

  const groupedCandidates = candidateBucketDefinitions
    .filter(bucket => bucket.key !== 'fresh_queue')
    .map(bucket => ({
      ...bucket,
      candidates: candidates.filter(candidate => getCandidateBucket(candidate) === bucket.key),
    }))
    .filter(bucket => bucket.candidates.length > 0)

  return (
    <section className="desk-panel">
      <header className="desk-panel-header">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <BookmarkCheck className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Analyzed Watchlist</p>
          </div>
          <h2 className="desk-heading">Carry-forward analyzed watchlist</h2>
          <p className="desk-copy max-w-3xl">
            Freshly analyzed names move here so the next session starts with memory instead of rediscovering the same symbols. Reopen a packet when you need the prior thesis, or rerun research if new evidence has changed the setup.
          </p>
        </div>
      </header>

      <div className="mt-2 space-y-6">
        {groupedCandidates.map((group) => (
          <section key={group.key} className="space-y-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-foreground">{group.title}</h3>
                <Badge variant="outline">{group.candidates.length}</Badge>
              </div>
              <p className="text-sm leading-6 text-muted-foreground">{group.description}</p>
            </div>

            <div className="space-y-3">
              {group.candidates.map((candidate) => {
                const isSelected = selectedCandidateId === candidate.candidate_id
                return (
                  <div
                    key={candidate.candidate_id}
                    className={`rounded-2xl border px-4 py-4 ${isSelected ? 'border-copper-400/60 bg-copper-50/60' : 'border-border/70 bg-white/70'}`}
                  >
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                      <div className="min-w-0 space-y-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-base font-semibold text-foreground">{candidate.symbol}</span>
                          {candidate.sector ? <Badge variant="subtle">{candidate.sector}</Badge> : null}
                          <Badge variant={candidateActionabilityVariant(candidate.last_actionability, getCandidateBucket(candidate))}>
                            {formatDecisionLabel(candidate.last_actionability, getCandidateBucket(candidate))}
                          </Badge>
                          {candidate.research_freshness ? (
                            <Badge variant="outline">{candidate.research_freshness} research</Badge>
                          ) : null}
                          {candidate.last_thesis_confidence !== undefined && candidate.last_thesis_confidence !== null ? (
                            <Badge variant="outline">Thesis {Math.round(candidate.last_thesis_confidence * 100)}%</Badge>
                          ) : null}
                          {candidate.last_analysis_mode ? (
                            <Badge variant="outline">{candidate.last_analysis_mode.replace(/_/g, ' ')}</Badge>
                          ) : null}
                          {candidate.last_trigger_type ? (
                            <Badge variant="outline">Trigger {candidate.last_trigger_type.replace(/_/g, ' ')}</Badge>
                          ) : null}
                        </div>

                        <p className="text-sm leading-6 text-muted-foreground">
                          {candidate.next_step}
                        </p>

                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>
                            {candidate.last_researched_at
                              ? `Last researched ${new Date(candidate.last_researched_at).toLocaleString()}`
                              : 'Research timestamp unavailable'}
                          </span>
                          <span>Primary {candidate.fresh_primary_source_count ?? 0}</span>
                          <span>External {candidate.fresh_external_source_count ?? 0}</span>
                          <span>Market {candidate.market_data_freshness ?? 'unknown'}</span>
                          <span>Technical {candidate.technical_context_available ? 'present' : 'missing'}</span>
                        </div>
                      </div>

                      {onSelectCandidate ? (
                        <Button
                          variant={isSelected ? 'secondary' : 'outline'}
                          size="sm"
                          onClick={() => onSelectCandidate(candidate)}
                        >
                          {isSelected ? 'Selected' : 'Open packet'}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  )
}

function formatDecisionLabel(
  actionability: AgentCandidate['last_actionability'],
  lifecycleState: ReturnType<typeof getCandidateBucket>,
) {
  if (lifecycleState === 'keep_watch' || actionability === 'watch_only') return 'Keep watch'
  if (lifecycleState === 'rejected' || actionability === 'blocked') return 'Rejected'
  if (lifecycleState === 'actionable' || actionability === 'actionable') return 'Actionable'
  return 'Stored'
}

function candidateActionabilityVariant(
  actionability: AgentCandidate['last_actionability'],
  lifecycleState: ReturnType<typeof getCandidateBucket>,
) {
  if (lifecycleState === 'actionable' || actionability === 'actionable') return 'success'
  if (lifecycleState === 'rejected' || actionability === 'blocked') return 'error'
  if (lifecycleState === 'keep_watch' || actionability === 'watch_only') return 'warning'
  return 'secondary'
}

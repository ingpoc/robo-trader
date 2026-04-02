import { useEffect, useState } from 'react'
import { ArrowUpRight, ChevronDown, ChevronRight, Compass, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import {
  candidateBucketDefinitions,
  getCandidateBucket,
  getCandidatesByBucket,
  hasFreshResearchMemory,
} from '../lib/candidateLifecycle'
import type { AgentCandidate, DiscoveryEnvelope } from '../types'

interface AgentDiscoveryPanelProps {
  envelope: DiscoveryEnvelope | null
  movedCandidateCount?: number
  isLoading?: boolean
  error?: string | null
  canRun?: boolean
  onRun?: () => void
  selectedCandidateId?: string | null
  onSelectCandidate?: (candidate: AgentCandidate) => void
}

export function AgentDiscoveryPanel({
  envelope,
  movedCandidateCount = 0,
  isLoading = false,
  error,
  canRun = false,
  onRun,
  selectedCandidateId,
  onSelectCandidate,
}: AgentDiscoveryPanelProps) {
  const [expandedCandidateIds, setExpandedCandidateIds] = useState<string[]>([])

  useEffect(() => {
    setExpandedCandidateIds(current => {
      const candidateIds = new Set(envelope?.candidates.map(candidate => candidate.candidate_id) ?? [])
      const next = current.filter(candidateId => candidateIds.has(candidateId))

      if (selectedCandidateId && candidateIds.has(selectedCandidateId) && !next.includes(selectedCandidateId)) {
        next.push(selectedCandidateId)
      }

      return next
    })
  }, [envelope?.candidates, selectedCandidateId])

  const toggleCandidate = (candidateId: string) => {
    setExpandedCandidateIds(current => (
      current.includes(candidateId)
        ? current.filter(id => id !== candidateId)
        : [...current, candidateId]
    ))
  }

  const groupedCandidates = getCandidatesByBucket(envelope?.candidates ?? [])

  return (
    <section className="desk-panel">
      <header className="desk-panel-header">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Discovery</p>
          </div>
          <h2 className="desk-heading">Stage only the names worth real research</h2>
          <p className="desk-copy max-w-2xl">
            Discovery should be cheap and selective. The system should surface a small dark-horse shortlist, not spend research tokens across a broad stock list.
          </p>
        </div>

        {onRun ? (
          <Button variant="primary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
            {isLoading ? 'Running discovery...' : 'Run Discovery'}
          </Button>
        ) : null}
      </header>

      <div className="desk-meta-row">
        <MetaItem label="Status" value={envelope?.status || 'idle'} />
        <MetaItem label="Context" value={envelope?.context_mode || 'stateful_watchlist'} />
        <MetaItem
          label="Generated"
          value={envelope ? new Date(envelope.generated_at).toLocaleString() : 'Not run yet'}
        />
        <MetaItem label="Candidates" value={String(envelope?.candidates.length || 0)} />
      </div>

      {envelope?.loop_summary ? (
        <div className="mt-4 rounded-2xl border border-border/70 bg-muted/15 px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">Attempts {envelope.loop_summary.research_attempt_count}</Badge>
            <Badge variant={envelope.loop_summary.actionable_found_count > 0 ? 'success' : 'secondary'}>
              Actionable {envelope.loop_summary.actionable_found_count}/{envelope.loop_summary.target_actionable_count}
            </Badge>
            {envelope.loop_summary.current_candidate_symbol ? (
              <Badge variant="outline">
                Current {envelope.loop_summary.current_candidate_symbol}
              </Badge>
            ) : null}
            <Badge variant={envelope.loop_summary.queue_exhausted ? 'warning' : 'info'}>
              {envelope.loop_summary.queue_exhausted ? 'Queue exhausted' : 'Loop active'}
            </Badge>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {formatLoopReason(envelope.loop_summary.termination_reason)}
            {envelope.loop_summary.latest_transition_reason
              ? ` Latest move: ${formatLoopReason(envelope.loop_summary.latest_transition_reason)}.`
              : ''}
          </p>
        </div>
      ) : null}

      {error ? (
        <p className="desk-error">{error}</p>
      ) : null}

      {envelope?.blockers.length ? (
        <ul className="desk-list mt-4 text-rose-700">
          {envelope.blockers.map(blocker => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}

      {!envelope && !isLoading ? (
        <EmptyState
          title="Discovery is idle"
          body="No discovery packet has been loaded. Run discovery when you want a fresh shortlist for the current account and market state."
        />
      ) : null}

      {isLoading && !envelope ? (
        <EmptyState
          title="Building shortlist"
          body="The system is screening the market and ranking a small set of dark-horse candidates."
        />
      ) : null}

      {envelope && envelope.candidates.length === 0 ? (
        <EmptyState
          title={movedCandidateCount > 0 ? 'Discovery queue is clear' : 'No candidates advanced'}
          body={movedCandidateCount > 0
            ? 'Every current candidate already has a fresh research packet. Review the analyzed watchlist or rerun discovery when new evidence appears.'
            : 'The current filters and market conditions did not justify a research shortlist. That is a valid outcome if the opportunity set is weak.'}
        />
      ) : null}

      {envelope?.candidates.length ? (
        <div className="mt-6 space-y-6">
          {candidateBucketDefinitions.map((bucket) => {
            const candidates = groupedCandidates[bucket.key]
            if (!candidates.length) return null

            return (
              <section key={bucket.key} className="desk-candidate-group">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-foreground">{bucket.title}</h3>
                    <Badge variant="outline">{candidates.length}</Badge>
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">{bucket.description}</p>
                </div>

                <div className="space-y-2">
                  <div className="candidate-row candidate-row--header">
                    <span>Candidate</span>
                    <span>Signal</span>
                    <span>Next step</span>
                    <span className="text-right">Action</span>
                  </div>

                  {candidates.map(candidate => {
                    const isSelected = selectedCandidateId === candidate.candidate_id
                    const isExpanded = expandedCandidateIds.includes(candidate.candidate_id)
                    const ToggleIcon = isExpanded ? ChevronDown : ChevronRight
                    const hasFreshResearch = hasFreshResearchMemory(candidate)

                    return (
                      <div
                        key={candidate.candidate_id}
                        className={`candidate-row ${isSelected ? 'candidate-row--selected' : ''}`}
                      >
                        <div className="xl:col-span-4">
                          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                            <button
                              type="button"
                              className="flex min-w-0 flex-1 items-start gap-3 text-left"
                              onClick={() => toggleCandidate(candidate.candidate_id)}
                              aria-expanded={isExpanded}
                              aria-controls={`candidate-panel-${candidate.candidate_id}`}
                            >
                              <ToggleIcon className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                              <div className="min-w-0 space-y-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-base font-semibold text-foreground">{candidate.symbol}</span>
                                  {candidate.sector ? <Badge variant="subtle">{candidate.sector}</Badge> : null}
                                  <Badge variant={priorityVariant(candidate.priority)}>{candidate.priority}</Badge>
                                  <Badge variant="outline">{Math.round(candidate.confidence * 100)}%</Badge>
                                  <Badge variant={bucketVariant(getCandidateBucket(candidate))}>
                                    {bucket.title}
                                  </Badge>
                                  {typeof candidate.dark_horse_score === 'number' ? (
                                    <Badge variant="outline">Dark horse {candidate.dark_horse_score}</Badge>
                                  ) : null}
                                  {typeof candidate.evidence_quality_score === 'number' ? (
                                    <Badge variant="outline">Evidence {candidate.evidence_quality_score}</Badge>
                                  ) : null}
                                  {candidate.last_actionability ? (
                                    <Badge variant={hasFreshResearch ? 'success' : 'secondary'}>
                                      {candidate.last_actionability.replace(/_/g, ' ')}
                                    </Badge>
                                  ) : null}
                                  {candidate.research_freshness && candidate.research_freshness !== 'unknown' ? (
                                    <Badge variant="outline">{candidate.research_freshness} research</Badge>
                                  ) : null}
                                  <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{candidate.source}</span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {candidate.company_name || 'Unnamed company'}
                                </p>
                              </div>
                            </button>

                            <div className="flex items-center justify-end gap-2">
                              {onSelectCandidate ? (
                                <Button
                                  variant={isSelected ? 'secondary' : 'outline'}
                                  size="sm"
                                  onClick={() => onSelectCandidate(candidate)}
                                >
                                  {isSelected ? 'Selected' : hasFreshResearch ? 'View Research' : 'Stage Research'}
                                  {!isSelected ? <ArrowUpRight className="ml-2 h-4 w-4" /> : null}
                                </Button>
                              ) : null}
                            </div>
                          </div>

                          {isExpanded ? (
                            <div
                              id={`candidate-panel-${candidate.candidate_id}`}
                              className="mt-4 grid gap-4 border-t border-border/70 pt-4 xl:grid-cols-[1.1fr_0.9fr]"
                            >
                              <div className="space-y-2">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Signal</p>
                                <p className="text-sm leading-6 text-foreground">{candidate.rationale}</p>
                              </div>

                              <div className="space-y-2">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Next step</p>
                                <p className="text-sm leading-6 text-foreground">{candidate.next_step}</p>
                              </div>

                              <div className="grid gap-4 xl:col-span-2 xl:grid-cols-[1fr_1fr]">
                                <div className="space-y-2">
                                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Stored research memory</p>
                                  <div className="flex flex-wrap gap-2">
                                    {candidate.last_researched_at ? (
                                      <Badge variant="outline">
                                        Last researched {new Date(candidate.last_researched_at).toLocaleString()}
                                      </Badge>
                                    ) : (
                                      <Badge variant="outline">No stored research</Badge>
                                    )}
                                    {candidate.last_thesis_confidence !== undefined && candidate.last_thesis_confidence !== null ? (
                                      <Badge variant="outline">
                                        Thesis {Math.round(candidate.last_thesis_confidence * 100)}%
                                      </Badge>
                                    ) : null}
                                    {candidate.last_analysis_mode ? (
                                      <Badge variant="outline">
                                        {candidate.last_analysis_mode.replace(/_/g, ' ')}
                                      </Badge>
                                    ) : null}
                                    {candidate.last_trigger_type ? (
                                      <Badge variant="outline">
                                        Trigger {candidate.last_trigger_type.replace(/_/g, ' ')}
                                      </Badge>
                                    ) : null}
                                    {candidate.reentry_reason ? (
                                      <Badge variant="outline">
                                        {candidate.reentry_reason}
                                      </Badge>
                                    ) : null}
                                  </div>
                                </div>

                                <div className="space-y-2 xl:col-span-2">
                                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Evidence provenance</p>
                                  <div className="flex flex-wrap gap-2">
                                    <Badge variant="outline">Primary {candidate.fresh_primary_source_count ?? 0}</Badge>
                                    <Badge variant="outline">External {candidate.fresh_external_source_count ?? 0}</Badge>
                                    <Badge variant="outline">Market {candidate.market_data_freshness ?? 'unknown'}</Badge>
                                    <Badge variant="outline">Technical {candidate.technical_context_available ? 'present' : 'missing'}</Badge>
                                    {candidate.evidence_mode ? (
                                      <Badge variant="outline">{candidate.evidence_mode.replace(/_/g, ' ')}</Badge>
                                    ) : null}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>
      ) : null}

      {envelope?.provider_metadata ? (
        <footer className="desk-footnote">
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Provider context: {String(envelope.provider_metadata.provider || 'local runtime')}</span>
        </footer>
      ) : null}
    </section>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="desk-kicker">{label}</p>
      <p className="text-sm text-foreground">{value}</p>
    </div>
  )
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-6 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-6">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
    </div>
  )
}

function priorityVariant(priority: AgentCandidate['priority']) {
  if (priority === 'high') return 'warning'
  if (priority === 'medium') return 'info'
  return 'secondary'
}

function bucketVariant(bucket: ReturnType<typeof getCandidateBucket>) {
  if (bucket === 'actionable') return 'success'
  if (bucket === 'keep_watch') return 'info'
  if (bucket === 'rejected') return 'warning'
  return 'secondary'
}

function formatLoopReason(reason: string) {
  return reason.replace(/_/g, ' ')
}

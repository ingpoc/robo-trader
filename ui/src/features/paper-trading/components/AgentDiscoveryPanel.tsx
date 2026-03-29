import { ArrowUpRight, Compass, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { AgentCandidate, DiscoveryEnvelope } from '../types'

interface AgentDiscoveryPanelProps {
  envelope: DiscoveryEnvelope | null
  isLoading?: boolean
  error?: string | null
  canRun?: boolean
  onRun?: () => void
  selectedCandidateId?: string | null
  onSelectCandidate?: (candidate: AgentCandidate) => void
}

export function AgentDiscoveryPanel({
  envelope,
  isLoading = false,
  error,
  canRun = false,
  onRun,
  selectedCandidateId,
  onSelectCandidate,
}: AgentDiscoveryPanelProps) {
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
          title="No candidates advanced"
          body="The current filters and market conditions did not justify a research shortlist. That is a valid outcome if the opportunity set is weak."
        />
      ) : null}

      {envelope?.candidates.length ? (
        <div className="mt-6 space-y-2">
          <div className="candidate-row candidate-row--header">
            <span>Candidate</span>
            <span>Signal</span>
            <span>Next step</span>
            <span className="text-right">Action</span>
          </div>

          {envelope.candidates.map(candidate => {
            const isSelected = selectedCandidateId === candidate.candidate_id
            return (
              <div
                key={candidate.candidate_id}
                className={`candidate-row ${isSelected ? 'candidate-row--selected' : ''}`}
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-semibold text-foreground">{candidate.symbol}</span>
                    {candidate.sector ? <Badge variant="subtle">{candidate.sector}</Badge> : null}
                    <Badge variant={priorityVariant(candidate.priority)}>{candidate.priority}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {candidate.company_name || 'Unnamed company'}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{Math.round(candidate.confidence * 100)}%</Badge>
                    <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{candidate.source}</span>
                  </div>
                  <p className="text-sm leading-6 text-foreground">{candidate.rationale}</p>
                </div>

                <div className="space-y-2">
                  <p className="text-sm leading-6 text-foreground">{candidate.next_step}</p>
                </div>

                <div className="flex items-center justify-end">
                  {onSelectCandidate ? (
                    <Button
                      variant={isSelected ? 'secondary' : 'outline'}
                      size="sm"
                      onClick={() => onSelectCandidate(candidate)}
                    >
                      {isSelected ? 'Selected' : 'Stage Research'}
                      {!isSelected ? <ArrowUpRight className="ml-2 h-4 w-4" /> : null}
                    </Button>
                  ) : null}
                </div>
              </div>
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

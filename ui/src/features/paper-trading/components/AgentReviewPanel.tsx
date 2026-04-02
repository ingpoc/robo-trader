import { Eye } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { ReviewEnvelope } from '../types'

interface AgentReviewPanelProps {
  envelope: ReviewEnvelope | null
  isLoading?: boolean
  error?: string | null
  canRun?: boolean
  onRun?: () => void
}

export function AgentReviewPanel({
  envelope,
  isLoading = false,
  error,
  canRun = false,
  onRun,
}: AgentReviewPanelProps) {
  return (
    <section className="desk-panel">
      <header className="desk-panel-header">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Daily Review</p>
          </div>
          <h2 className="desk-heading">Keep only lessons that change behavior</h2>
          <p className="desk-copy">
            Review should close the loop on executed ideas. If it does not improve future decisions or guardrails, it is wasted token spend.
          </p>
        </div>

        {onRun ? (
          <Button variant="outline" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
            {isLoading ? 'Running...' : 'Run Daily Review'}
          </Button>
        ) : null}
      </header>

      <div className="desk-meta-row">
        <MetaItem label="Status" value={envelope?.status || 'idle'} />
        <MetaItem label="Context" value={envelope?.context_mode || 'delta_daily_review'} />
        <MetaItem
          label="Generated"
          value={envelope?.review ? new Date(envelope.review.generated_at).toLocaleString() : 'Not run yet'}
        />
      </div>

      {error ? <p className="desk-error mt-4">{error}</p> : null}

      {envelope?.blockers.length ? (
        <ul className="desk-list mt-4 text-rose-700">
          {envelope.blockers.map(blocker => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}

      {!envelope?.review ? (
        <div className="mt-5 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-6">
          <p className="text-sm font-semibold text-foreground">No review report loaded</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Run a daily review when you want lessons, weaknesses, and guarded strategy proposals extracted from the latest paper-trading outcomes.
          </p>
        </div>
      ) : (
        <div className="mt-5 space-y-5">
          <section className="rounded-2xl border border-border/70 bg-white/75 px-4 py-4 dark:bg-warmgray-800/75">
            <p className="text-sm leading-6 text-foreground">{envelope.review.summary}</p>
          </section>

          <ReviewList title="Strengths" items={envelope.review.strengths} variant="success" />
          <ReviewList title="Weaknesses" items={envelope.review.weaknesses} variant="warning" />
          <ReviewList title="Risk Flags" items={envelope.review.risk_flags} variant="error" />
          <ReviewList title="Top Lessons" items={envelope.review.top_lessons} variant="info" />

          {envelope.review.strategy_proposals.length ? (
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-foreground">Guarded strategy proposals</h3>
              <div className="space-y-3">
                {envelope.review.strategy_proposals.map(proposal => (
                  <div key={proposal.proposal_id} className="rounded-2xl border border-border/70 bg-white/75 px-4 py-4 dark:bg-warmgray-800/75">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{proposal.title}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-foreground">{proposal.recommendation}</p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{proposal.rationale}</p>
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">Guardrail</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{proposal.guardrail}</p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </section>
  )
}

function ReviewList({
  title,
  items,
  variant,
}: {
  title: string
  items: string[]
  variant: 'success' | 'warning' | 'error' | 'info'
}) {
  if (!items.length) return null

  return (
    <section className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <ul className="desk-list">
        {items.map(item => (
          <li key={item} className="flex items-start gap-3">
            <Badge variant={variant} size="xs">
              {title.slice(0, 1)}
            </Badge>
            <span className="text-sm leading-6 text-foreground">{item}</span>
          </li>
        ))}
      </ul>
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

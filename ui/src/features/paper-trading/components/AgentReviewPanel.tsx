import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
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
  if (isLoading && !envelope) {
    return <Card><CardContent className="p-6 text-sm text-muted-foreground">Generating review…</CardContent></Card>
  }

  if (error) {
    return <Card><CardContent className="p-6 text-sm text-destructive">{error}</CardContent></Card>
  }

  if (!envelope) {
    return null
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-lg">Review</CardTitle>
              <CardDescription>
                Daily review is compressed into operator-grade takeaways and guarded strategy proposals instead of a full transcript dump.
              </CardDescription>
            </div>
            {onRun ? (
              <Button variant="tertiary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
                {isLoading ? 'Running...' : 'Run Daily Review'}
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <div>Status: <span className="font-medium text-foreground">{envelope.status}</span></div>
          <div>Context mode: <span className="font-medium text-foreground">{envelope.context_mode}</span></div>
          {envelope.blockers.length > 0 && (
            <ul className="list-disc pl-5 text-destructive">
              {envelope.blockers.map(blocker => <li key={blocker}>{blocker}</li>)}
            </ul>
          )}
        </CardContent>
      </Card>

      {envelope.review ? (
        <Card variant="compact">
          <CardContent className="space-y-5 p-5">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Generated {new Date(envelope.review.generated_at).toLocaleString()}</div>
              <p className="text-sm text-foreground">{envelope.review.summary}</p>
            </div>

            <ReviewList title="Strengths" items={envelope.review.strengths} variant="success" />
            <ReviewList title="Weaknesses" items={envelope.review.weaknesses} variant="warning" />
            <ReviewList title="Risk Flags" items={envelope.review.risk_flags} variant="error" />
            <ReviewList title="Top Lessons" items={envelope.review.top_lessons} variant="info" />

            {envelope.review.strategy_proposals.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-foreground">Strategy Proposals</h4>
                {envelope.review.strategy_proposals.map(proposal => (
                  <div key={proposal.proposal_id} className="rounded-lg border border-border/70 bg-muted/35 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Badge variant="outline">{proposal.title}</Badge>
                    </div>
                    <p className="text-sm text-foreground">{proposal.recommendation}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{proposal.rationale}</p>
                    <p className="mt-2 text-xs text-muted-foreground">Guardrail: {proposal.guardrail}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
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
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="space-y-2">
        {items.map(item => (
          <li key={item} className="flex items-start gap-2 text-sm text-foreground">
            <Badge variant={variant} size="xs">{title.slice(0, 1)}</Badge>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

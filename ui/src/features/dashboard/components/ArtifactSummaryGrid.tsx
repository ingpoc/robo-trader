import { ArrowRight } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import type {
  DecisionEnvelope,
  DiscoveryEnvelope,
  ResearchEnvelope,
  ReviewEnvelope,
} from '@/features/paper-trading/types'

interface ArtifactSummaryGridProps {
  accountLabel?: string
  discovery: DiscoveryEnvelope | null
  research: ResearchEnvelope | null
  decisions: DecisionEnvelope | null
  review: ReviewEnvelope | null
  isLoading?: boolean
  error?: string | null
  onOpenPaperTrading: () => void
}

export function ArtifactSummaryGrid({
  accountLabel,
  discovery,
  research,
  decisions,
  review,
  isLoading = false,
  error,
  onOpenPaperTrading,
}: ArtifactSummaryGridProps) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Latest Operator Artifacts</h2>
          <p className="text-sm text-muted-foreground">
            {accountLabel
              ? `Summaries are scoped to ${accountLabel}. Open Paper Trading for the full workflow.`
              : 'Select a paper trading account to load discovery, research, decisions, and review artifacts.'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onOpenPaperTrading}>
          Open Paper Trading
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>

      {error ? (
        <Card>
          <CardContent className="p-5 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4 md:grid-cols-2">
        <SummaryCard
          title="Discovery"
          description="Top candidate"
          isLoading={isLoading}
          body={
            discovery?.candidates[0]
              ? `${discovery.candidates[0].symbol}: ${discovery.candidates[0].next_step}`
              : fallbackCopy(discovery?.blockers, 'No discovery candidates are available.')
          }
          meta={discovery ? `Status: ${discovery.status}` : undefined}
        />
        <SummaryCard
          title="Research"
          description="Focused thesis"
          isLoading={isLoading}
          body={
            research?.research
              ? `${research.research.symbol}: ${research.research.thesis}`
              : fallbackCopy(research?.blockers, 'No research packet has been generated.')
          }
          meta={research ? `Status: ${research.status}` : undefined}
        />
        <SummaryCard
          title="Decisions"
          description="Current position guidance"
          isLoading={isLoading}
          body={
            decisions?.decisions[0]
              ? `${decisions.decisions[0].symbol}: ${decisions.decisions[0].next_step}`
              : fallbackCopy(decisions?.blockers, 'No decision packet is available.')
          }
          meta={decisions ? `Status: ${decisions.status}` : undefined}
        />
        <SummaryCard
          title="Review"
          description="Latest lessons"
          isLoading={isLoading}
          body={
            review?.review
              ? review.review.summary
              : fallbackCopy(review?.blockers, 'No review report is available.')
          }
          meta={review ? `Status: ${review.status}` : undefined}
        />
      </div>
    </section>
  )
}

function SummaryCard({
  title,
  description,
  body,
  meta,
  isLoading,
}: {
  title: string
  description: string
  body: string
  meta?: string
  isLoading?: boolean
}) {
  return (
    <Card className="h-full">
      <CardHeader className="space-y-1 pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-6 text-foreground">
          {isLoading ? 'Loading…' : body}
        </p>
        {meta ? <p className="text-xs uppercase tracking-wide text-muted-foreground">{meta}</p> : null}
      </CardContent>
    </Card>
  )
}

function fallbackCopy(blockers: string[] | undefined, emptyMessage: string) {
  if (blockers && blockers.length > 0) {
    return blockers[0]
  }
  return emptyMessage
}

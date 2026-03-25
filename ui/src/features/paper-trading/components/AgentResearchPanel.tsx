import type { ReactNode } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { AgentCandidate, ResearchEnvelope } from '../types'

interface AgentResearchPanelProps {
  envelope: ResearchEnvelope | null
  selectedCandidate?: AgentCandidate | null
  isLoading?: boolean
  error?: string | null
  canRun?: boolean
  onRun?: () => void
}

export function AgentResearchPanel({
  envelope,
  selectedCandidate,
  isLoading = false,
  error,
  canRun = false,
  onRun,
}: AgentResearchPanelProps) {
  if (isLoading && !envelope) {
    return <Card><CardContent className="p-6 text-sm text-muted-foreground">Generating focused research…</CardContent></Card>
  }

  if (error) {
    return <Card><CardContent className="p-6 text-sm text-destructive">{error}</CardContent></Card>
  }

  if (!envelope) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {selectedCandidate
            ? `Select "Run Research" to create a focused packet for ${selectedCandidate.symbol}.`
            : 'Choose a discovery candidate before generating research.'}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-lg">Research</CardTitle>
              <CardDescription>
                Research is generated one candidate at a time so the agent only receives the minimum context needed for a real thesis.
              </CardDescription>
            </div>
            {onRun ? (
              <Button variant="tertiary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
                {isLoading ? 'Running...' : 'Run Research'}
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <div>Status: <span className="font-medium text-foreground">{envelope.status}</span></div>
          <div>Context mode: <span className="font-medium text-foreground">{envelope.context_mode}</span></div>
          {selectedCandidate ? (
            <div>
              Candidate: <span className="font-medium text-foreground">{selectedCandidate.symbol}</span>
            </div>
          ) : null}
          {envelope.blockers.length > 0 && (
            <ul className="list-disc pl-5 text-destructive">
              {envelope.blockers.map(blocker => <li key={blocker}>{blocker}</li>)}
            </ul>
          )}
        </CardContent>
      </Card>

      {envelope.research ? (
        <Card variant="compact">
          <CardContent className="space-y-5 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-foreground">{envelope.research.symbol}</div>
                <div className="text-sm text-muted-foreground">
                  Generated {new Date(envelope.research.generated_at).toLocaleString()}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={actionabilityVariant(envelope.research.actionability)}>
                  {formatLabel(envelope.research.actionability)}
                </Badge>
                <Badge variant={analysisModeVariant(envelope.research.analysis_mode)}>
                  {formatLabel(envelope.research.analysis_mode)}
                </Badge>
                <Badge variant="outline">
                  Thesis {Math.round(envelope.research.thesis_confidence * 100)}%
                </Badge>
                <Badge variant="secondary">
                  Screening {Math.round(envelope.research.screening_confidence * 100)}%
                </Badge>
              </div>
            </div>

            <section className="grid gap-3 md:grid-cols-2">
              <SignalCard
                title="Why Now"
                body={envelope.research.why_now || 'No explicit why-now context was produced.'}
              />
              <SignalCard
                title="Market Data Freshness"
                body={envelope.research.market_data_freshness.summary || 'Market data freshness was not reported.'}
                meta={
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={freshnessVariant(envelope.research.market_data_freshness.status)}>
                      {formatLabel(envelope.research.market_data_freshness.status)}
                    </Badge>
                    {envelope.research.market_data_freshness.provider ? (
                      <Badge variant="outline">{envelope.research.market_data_freshness.provider}</Badge>
                    ) : null}
                  </div>
                }
              />
            </section>

            <section className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">Thesis</h4>
              <p className="text-sm text-foreground">{envelope.research.thesis}</p>
            </section>

            <ArtifactList title="Evidence" items={envelope.research.evidence} tone="info" />
            <ArtifactList title="Risks" items={envelope.research.risks} tone="warning" />

            <section className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">Invalidation</h4>
              <p className="text-sm text-foreground">{envelope.research.invalidation}</p>
            </section>

            <section className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">Next Step</h4>
              <p className="text-sm text-muted-foreground">{envelope.research.next_step}</p>
            </section>

            <section className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">Evidence Provenance</h4>
              {envelope.research.source_summary.length > 0 ? (
                <div className="space-y-2">
                  {envelope.research.source_summary.map(source => (
                    <div
                      key={`${source.source_type}-${source.label}-${source.timestamp}`}
                      className="rounded-2xl border border-border/70 bg-background/80 px-4 py-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="text-sm font-medium text-foreground">{source.label}</div>
                        <Badge variant={freshnessVariant(source.freshness)} size="xs">
                          {formatLabel(source.freshness)}
                        </Badge>
                      </div>
                      {source.detail ? (
                        <div className="mt-1 text-sm text-muted-foreground">{source.detail}</div>
                      ) : null}
                      {source.timestamp ? (
                        <div className="mt-1 text-xs text-muted-foreground">
                          {new Date(source.timestamp).toLocaleString()}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No source provenance was captured.</p>
              )}
            </section>

            <section className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">Evidence Citations</h4>
              {envelope.research.evidence_citations.length > 0 ? (
                <ul className="space-y-2">
                  {envelope.research.evidence_citations.map(citation => (
                    <li
                      key={`${citation.reference}-${citation.label}`}
                      className="rounded-2xl border border-border/70 bg-background/80 px-4 py-3 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-foreground">{citation.label}</span>
                        <Badge variant={freshnessVariant(citation.freshness)} size="xs">
                          {formatLabel(citation.freshness)}
                        </Badge>
                      </div>
                      <div className="mt-1 text-muted-foreground">{citation.reference}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No structured citations were emitted.</p>
              )}
            </section>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}

function ArtifactList({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: 'info' | 'warning'
}) {
  if (!items.length) return null

  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="space-y-2">
        {items.map(item => (
          <li key={item} className="flex items-start gap-2 text-sm text-foreground">
            <Badge variant={tone} size="xs">{title.slice(0, 1)}</Badge>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function SignalCard({
  title,
  body,
  meta,
}: {
  title: string
  body: string
  meta?: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-foreground">{title}</h4>
        {meta}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </div>
  )
}

function formatLabel(value: string) {
  return value.replace(/_/g, ' ')
}

function actionabilityVariant(actionability: string) {
  if (actionability === 'actionable') return 'success'
  if (actionability === 'blocked') return 'error'
  return 'warning'
}

function analysisModeVariant(mode: string) {
  if (mode === 'fresh_evidence') return 'success'
  if (mode === 'insufficient_evidence') return 'error'
  return 'warning'
}

function freshnessVariant(freshness: string) {
  if (freshness === 'fresh') return 'success'
  if (freshness === 'delayed') return 'warning'
  if (freshness === 'stale' || freshness === 'missing') return 'error'
  return 'secondary'
}

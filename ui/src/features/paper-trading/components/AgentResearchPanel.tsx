import type { ReactNode } from 'react'
import { BookText, Clock3, DatabaseZap, Sparkles } from 'lucide-react'

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
  const research = envelope?.research
  const loopSummary = envelope?.loop_summary
  const renderedSymbol = research?.symbol || selectedCandidate?.symbol || 'No candidate selected'
  const renderedSector = research?.source_summary.find(source => source.source_type === 'screening')?.label || selectedCandidate?.sector
  const packetMatchesSelection = Boolean(
    !selectedCandidate ||
      !research ||
      research.candidate_id === selectedCandidate.candidate_id ||
      research.symbol === selectedCandidate.symbol,
  )

  return (
    <section className="desk-panel desk-panel--featured">
      <header className="desk-panel-header">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <BookText className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Focused Research</p>
          </div>
          <h2 className="desk-heading">Research runs only when you ask for it</h2>
          <p className="desk-copy max-w-2xl">
            The loop keeps advancing through the fresh queue until it finds one actionable buy candidate or exhausts the eligible list. Weak packets should stop fast and move into memory instead of burning more context.
          </p>
        </div>

        {onRun ? (
          <Button variant="primary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
            {isLoading ? 'Running research...' : selectedCandidate ? 'Run Research' : 'Run Loop'}
          </Button>
        ) : null}
      </header>

      <div className="desk-meta-row">
        <MetaItem label="Candidate" value={renderedSymbol} />
        <MetaItem label="Sector" value={renderedSector || 'Unspecified'} />
        <MetaItem label="Status" value={envelope?.status || 'idle'} />
        <MetaItem label="Generated" value={research ? new Date(research.generated_at).toLocaleString() : 'Not run yet'} />
      </div>

      {loopSummary ? (
        <div className="mt-4 rounded-2xl border border-border/70 bg-muted/15 px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">Attempts {loopSummary.research_attempt_count}</Badge>
            <Badge variant={loopSummary.actionable_found_count > 0 ? 'success' : 'secondary'}>
              Actionable {loopSummary.actionable_found_count}/{loopSummary.target_actionable_count}
            </Badge>
            {loopSummary.current_candidate_symbol ? (
              <Badge variant="outline">Current {loopSummary.current_candidate_symbol}</Badge>
            ) : null}
            <Badge variant={loopSummary.queue_exhausted ? 'warning' : 'info'}>
              {loopSummary.queue_exhausted ? 'Queue exhausted' : 'Loop active'}
            </Badge>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {formatLabel(loopSummary.termination_reason)}
            {loopSummary.latest_transition_reason ? ` Latest move: ${formatLabel(loopSummary.latest_transition_reason)}.` : ''}
          </p>
        </div>
      ) : null}

      {selectedCandidate ? (
        <div className="rounded-2xl border border-border/70 bg-muted/15 px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-foreground">Staged candidate</span>
            <Badge variant="subtle">{selectedCandidate.symbol}</Badge>
            {selectedCandidate.sector ? <Badge variant="outline">{selectedCandidate.sector}</Badge> : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedCandidate.rationale}</p>
        </div>
      ) : (
        <EmptyState
          title="No candidate staged"
          body="Run discovery first, then stage a candidate before spending tokens on research."
        />
      )}

      {error ? <p className="desk-error mt-5">{error}</p> : null}

      {envelope?.blockers.length ? (
        <ul className="desk-list mt-5 text-rose-700">
          {envelope.blockers.map(blocker => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}

      {!research ? (
        selectedCandidate ? (
          <EmptyState
            title="Research is idle"
            body={`The system is staged for ${selectedCandidate.symbol}. Run research to produce a single thesis packet with evidence, risks, invalidation, and next step.`}
          />
        ) : null
      ) : (
        <div className="mt-6 space-y-6">
          {!packetMatchesSelection ? (
            <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Displayed packet is for {research.symbol}, but the currently staged candidate is {selectedCandidate?.symbol}. Run research again to replace it.
            </p>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <SignalBlock
              icon={Sparkles}
              title="Why now"
              body={research.why_now}
              meta={(
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={analysisModeVariant(research.analysis_mode)}>{formatLabel(research.analysis_mode)}</Badge>
                  <Badge variant={actionabilityVariant(research.actionability)}>{formatLabel(research.actionability)}</Badge>
                  {research.classification ? (
                    <Badge variant={classificationVariant(research.classification)}>{formatLabel(research.classification)}</Badge>
                  ) : null}
                </div>
              )}
            />
            <SignalBlock
              icon={DatabaseZap}
              title="Thesis"
              body={research.thesis}
              meta={(
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Screening {Math.round(research.screening_confidence * 100)}%</span>
                  <span>·</span>
                  <span>Thesis {Math.round(research.thesis_confidence * 100)}%</span>
                </div>
              )}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
            <div className="space-y-5">
              <SignalBlock title="Next step" body={research.next_step} />
              {research.what_changed_since_last_research ? (
                <SignalBlock title="What changed since last research" body={research.what_changed_since_last_research} />
              ) : null}
              <SignalBlock title="Invalidation" body={research.invalidation} />
              <ArtifactList title="Evidence" items={research.evidence} tone="info" />
              <ArtifactList title="Risks" items={research.risks} tone="warning" />
            </div>

            <div className="space-y-5">
              <section className="space-y-3">
                <div className="flex items-center gap-2">
                  <Clock3 className="h-4 w-4 text-primary" />
                  <h3 className="text-base font-semibold text-foreground">Evidence Provenance</h3>
                </div>
                {research.source_summary.length ? (
                  <div className="divide-y divide-border/70 rounded-2xl border border-border/70 bg-white/75 dark:bg-warmgray-800/75">
                    {research.source_summary.map(source => (
                      <div key={`${source.source_type}-${source.label}-${source.timestamp}`} className="grid gap-2 px-4 py-3 sm:grid-cols-[0.8fr_0.8fr_1.4fr]">
                        <div>
                          <p className="desk-kicker">{source.source_type}</p>
                          <p className="text-sm font-medium text-foreground">{source.label}</p>
                        </div>
                        <div>
                          <Badge variant={freshnessVariant(source.freshness)} size="xs">
                            {formatLabel(source.freshness)}
                          </Badge>
                          <p className="mt-2 text-xs text-muted-foreground">
                            {new Date(source.timestamp).toLocaleString()}
                          </p>
                        </div>
                        <p className="text-sm leading-6 text-muted-foreground">{source.detail}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No source summary was emitted.</p>
                )}
              </section>

              <section className="space-y-3">
                <h3 className="text-base font-semibold text-foreground">Evidence Citations</h3>
                {research.evidence_citations.length ? (
                  <div className="space-y-2">
                    {research.evidence_citations.map(citation => (
                      <div key={`${citation.reference}-${citation.label}`} className="rounded-2xl border border-border/70 bg-muted/15 px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-foreground">{citation.label}</span>
                          <Badge variant={freshnessVariant(citation.freshness)} size="xs">
                            {formatLabel(citation.freshness)}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(citation.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">{citation.reference}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No structured citations were emitted.</p>
                )}
              </section>

              <section className="rounded-2xl border border-border/70 bg-white/75 px-4 py-4 dark:bg-warmgray-800/75">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-base font-semibold text-foreground">Market Data Freshness</h3>
                  <Badge variant={freshnessVariant(research.market_data_freshness.status)} size="xs">
                    {formatLabel(research.market_data_freshness.status)}
                  </Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {research.market_data_freshness.summary}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Provider: {research.market_data_freshness.provider} · Intraday quote: {research.market_data_freshness.has_intraday_quote ? 'yes' : 'no'} · Historical data: {research.market_data_freshness.has_historical_data ? 'yes' : 'no'}
                </p>
              </section>
            </div>
          </div>
        </div>
      )}
    </section>
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
    <section className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <ul className="desk-list">
        {items.map(item => (
          <li key={item} className="flex items-start gap-3">
            <Badge variant={tone === 'info' ? 'info' : 'warning'} size="xs">
              {title.slice(0, 1)}
            </Badge>
            <span className="text-sm leading-6 text-foreground">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-5 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-6">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
    </div>
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

function SignalBlock({
  icon: Icon,
  title,
  body,
  meta,
}: {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  body: string
  meta?: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-border/70 bg-white/75 px-4 py-4 dark:bg-warmgray-800/75">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {Icon ? <Icon className="h-4 w-4 text-primary" /> : null}
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
        </div>
        {meta}
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{body}</p>
    </section>
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

function classificationVariant(classification: string) {
  if (classification === 'actionable_buy_candidate') return 'success'
  if (classification === 'rejected') return 'error'
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

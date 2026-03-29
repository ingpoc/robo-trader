import { ClipboardList } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { DecisionEnvelope } from '../types'

interface AgentDecisionPanelProps {
  envelope: DecisionEnvelope | null
  isLoading?: boolean
  error?: string | null
  canRun?: boolean
  onRun?: () => void
}

const decisionVariant: Record<string, 'hold' | 'warning' | 'negative' | 'positive'> = {
  hold: 'hold',
  review_exit: 'warning',
  tighten_stop: 'negative',
  take_profit: 'positive',
}

export function AgentDecisionPanel({
  envelope,
  isLoading = false,
  error,
  canRun = false,
  onRun,
}: AgentDecisionPanelProps) {
  return (
    <section className="desk-panel">
      <header className="desk-panel-header">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Decision Review</p>
          </div>
          <h2 className="desk-heading">Position-level next actions</h2>
          <p className="desk-copy">
            This step reviews open paper positions only. It should stay narrow and tied to current exposure, not become a background analysis loop.
          </p>
        </div>

        {onRun ? (
          <Button variant="outline" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
            {isLoading ? 'Running...' : 'Run Decision Review'}
          </Button>
        ) : null}
      </header>

      <div className="desk-meta-row">
        <MetaItem label="Status" value={envelope?.status || 'idle'} />
        <MetaItem label="Context" value={envelope?.context_mode || 'delta_position_review'} />
        <MetaItem label="Packets" value={String(envelope?.decisions.length || 0)} />
      </div>

      {error ? <p className="desk-error mt-4">{error}</p> : null}

      {envelope?.blockers.length ? (
        <ul className="desk-list mt-4 text-rose-700">
          {envelope.blockers.map(blocker => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}

      {!envelope?.decisions.length ? (
        <div className="mt-5 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-6">
          <p className="text-sm font-semibold text-foreground">No decision packets loaded</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Run a position review when you want fresh exit or stop-tightening guidance for the current open positions.
          </p>
        </div>
      ) : (
        <div className="mt-5 divide-y divide-border/70 rounded-2xl border border-border/70 bg-white/75 dark:bg-warmgray-800/75">
          {envelope.decisions.map(decision => (
            <div key={decision.decision_id} className="space-y-3 px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold text-foreground">{decision.symbol}</span>
                    <Badge variant={decisionVariant[decision.action] || 'secondary'} size="xs">
                      {decision.action}
                    </Badge>
                    <Badge variant="outline" size="xs">
                      {Math.round(decision.confidence * 100)}%
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Generated {new Date(decision.generated_at).toLocaleString()}
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">{decision.next_step}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <p className="text-sm leading-6 text-foreground">
                  <span className="font-semibold">Thesis:</span> {decision.thesis}
                </p>
                <p className="text-sm leading-6 text-muted-foreground">
                  <span className="font-semibold text-foreground">Invalidation:</span> {decision.invalidation}
                </p>
              </div>

              <p className="text-sm leading-6 text-muted-foreground">{decision.risk_note}</p>
            </div>
          ))}
        </div>
      )}
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

import { Badge } from '@/components/ui/Badge'

interface StageCriteriaPanelProps {
  stageLabel: string
  criteria: string[]
  considered: string[]
  status?: string | null
  statusReason?: string | null
  freshnessState?: string | null
  emptyReason?: string | null
}

export function StageCriteriaPanel({
  stageLabel,
  criteria,
  considered,
  status,
  statusReason,
  freshnessState,
  emptyReason,
}: StageCriteriaPanelProps) {
  return (
    <aside className="desk-criteria-panel">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="desk-kicker">Current Criteria</p>
          {status ? <Badge variant={statusVariant(status)} size="xs">{status}</Badge> : null}
        </div>
        <h3 className="text-lg font-semibold text-foreground">{stageLabel} control surface</h3>
        <p className="text-sm leading-6 text-muted-foreground">
          This is the explicit rule set and in-scope work the dashboard is using right now.
        </p>
        {statusReason ? <p className="text-sm leading-6 text-foreground">{statusReason}</p> : null}
        {(freshnessState || emptyReason) ? (
          <div className="flex flex-wrap gap-2">
            {freshnessState ? <Badge variant="outline" size="xs">Freshness {freshnessState.replace(/_/g, ' ')}</Badge> : null}
            {emptyReason ? <Badge variant="outline" size="xs">Empty reason {emptyReason.replace(/_/g, ' ')}</Badge> : null}
          </div>
        ) : null}
      </div>

      <CriteriaSection
        title="Rules in force"
        emptyText="No explicit criteria are currently published for this stage."
        items={criteria}
        badgeVariant="secondary"
      />

      <CriteriaSection
        title="Currently considered"
        emptyText="Nothing is currently in scope for this stage."
        items={considered}
        badgeVariant="outline"
      />
    </aside>
  )
}

function CriteriaSection({
  title,
  items,
  emptyText,
  badgeVariant,
}: {
  title: string
  items: string[]
  emptyText: string
  badgeVariant: 'secondary' | 'outline'
}) {
  return (
    <section className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</h4>
      {items.length ? (
        <ul className="desk-list">
          {items.map(item => (
            <li key={item} className="flex items-start gap-3">
              <Badge variant={badgeVariant} size="xs">
                {title === 'Rules in force' ? 'R' : 'C'}
              </Badge>
              <span className="text-sm leading-6 text-foreground">{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm leading-6 text-muted-foreground">{emptyText}</p>
      )}
    </section>
  )
}

function statusVariant(status: string): 'success' | 'warning' | 'error' | 'secondary' {
  if (status === 'ready') return 'success'
  if (status === 'blocked') return 'error'
  if (status === 'empty') return 'warning'
  return 'secondary'
}

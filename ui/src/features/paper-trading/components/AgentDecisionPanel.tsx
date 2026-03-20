import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
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
  if (isLoading && !envelope) {
    return <Card><CardContent className="p-6 text-sm text-muted-foreground">Generating decision packets…</CardContent></Card>
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
              <CardTitle className="text-lg">Decisions</CardTitle>
              <CardDescription>
                This view only renders compact decision packets for current positions. It does not expose raw prompts or full history by default.
              </CardDescription>
            </div>
            {onRun ? (
              <Button variant="tertiary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
                {isLoading ? 'Running...' : 'Run Decision Review'}
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

      {envelope.decisions.map(decision => (
        <Card key={decision.decision_id} variant="compact">
          <CardContent className="space-y-3 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-foreground">{decision.symbol}</div>
                <div className="text-sm text-muted-foreground">Generated {new Date(decision.generated_at).toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={decisionVariant[decision.action] || 'secondary'}>{decision.action}</Badge>
                <Badge variant="outline">{Math.round(decision.confidence * 100)}% confidence</Badge>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <p><span className="font-medium text-foreground">Thesis:</span> {decision.thesis}</p>
              <p><span className="font-medium text-foreground">Invalidation:</span> {decision.invalidation}</p>
              <p><span className="font-medium text-foreground">Next step:</span> {decision.next_step}</p>
              <p className="text-muted-foreground">{decision.risk_note}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

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
              <Badge variant="outline">
                {Math.round(envelope.research.confidence * 100)}% confidence
              </Badge>
            </div>

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

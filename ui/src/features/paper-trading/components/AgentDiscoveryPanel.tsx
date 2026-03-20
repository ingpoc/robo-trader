import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
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
  if (isLoading && !envelope) {
    return <Card><CardContent className="p-6 text-sm text-muted-foreground">Loading discovery candidates…</CardContent></Card>
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
              <CardTitle className="text-lg">Discovery</CardTitle>
              <CardDescription>
                Progressive disclosure starts with a compact candidate list. Open research only for names worth spending context on.
              </CardDescription>
            </div>
            {onRun ? (
              <Button variant="tertiary" size="sm" onClick={onRun} disabled={!canRun || isLoading}>
                {isLoading ? 'Running...' : 'Run Discovery'}
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

      {envelope.candidates.length === 0 && (
        <Card variant="compact">
          <CardContent className="p-5 text-sm text-muted-foreground">
            No ranked candidates are available yet. Run discovery again once the watchlist or upstream research inputs change.
          </CardContent>
        </Card>
      )}

      {envelope.candidates.map(candidate => (
        <Card key={candidate.candidate_id} variant="compact">
          <CardContent className="space-y-3 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-foreground">{candidate.symbol}</div>
                <div className="text-sm text-muted-foreground">
                  {candidate.company_name || 'Unnamed company'}
                  {candidate.sector ? ` · ${candidate.sector}` : ''}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={candidate.priority === 'high' ? 'warning' : candidate.priority === 'medium' ? 'info' : 'secondary'}>
                  {candidate.priority}
                </Badge>
                <Badge variant="outline">{Math.round(candidate.confidence * 100)}% confidence</Badge>
              </div>
            </div>
            <p className="text-sm text-foreground">{candidate.rationale}</p>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">{candidate.next_step}</p>
              {onSelectCandidate ? (
                <Button
                  variant={selectedCandidateId === candidate.candidate_id ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => onSelectCandidate(candidate)}
                >
                  {selectedCandidateId === candidate.candidate_id ? 'Research Selected' : 'Open Research'}
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

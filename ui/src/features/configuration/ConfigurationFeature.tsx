import React from 'react'
import { RefreshCw, Save, Settings, SlidersHorizontal, Wallet } from 'lucide-react'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useAccount } from '@/contexts/AccountContext'
import { AIAgentConfigComponent } from './components/AIAgentConfig'
import { GlobalSettingsPanel } from './components/GlobalSettingsPanel'
import { useConfiguration } from './hooks/useConfiguration'
import { StageCriteriaPanel } from '@/features/paper-trading/components/StageCriteriaPanel'

const ConfigurationFeature: React.FC = () => {
  const { selectedAccount } = useAccount()
  const {
    aiAgents,
    globalSettings,
    accountPolicy,
    operatorSnapshot,
    isLoading,
    isSaving,
    error,
    loadConfiguration,
    saveConfiguration,
    updateAIAgent,
    updateGlobalSetting,
    updateAccountPolicy,
  } = useConfiguration({
    accountId: selectedAccount?.account_id ?? null,
  })

  const discoveryEnvelope = normalizeStageEnvelope(operatorSnapshot?.discovery)
  const researchEnvelope = normalizeStageEnvelope(operatorSnapshot?.research)
  const decisionEnvelope = normalizeStageEnvelope(operatorSnapshot?.decisions)
  const reviewEnvelope = normalizeStageEnvelope(operatorSnapshot?.review)

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-4">
          <Breadcrumb items={[{ label: 'Configuration' }]} />
          <PageHeader
            title="Configuration"
            description="Policy only. Live runtime state, broker readiness, and runtime identity live in Health."
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => void loadConfiguration()} isLoading={isLoading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Reload policy
          </Button>
          <Button variant="primary" onClick={() => void saveConfiguration()} isLoading={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            Save changes
          </Button>
        </div>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Alert>
        <AlertDescription>
          This tab owns editable defaults and guardrails only. If you need runtime truth, broker state, quote health, or runtime identity, use the Health tab.
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Global Policy</CardTitle>
            <CardDescription>Editable defaults that apply across operator accounts and runtime lanes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <GlobalSettingsPanel
              globalSettings={globalSettings}
              isLoading={isLoading}
              onUpdateSetting={updateGlobalSetting}
            />
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-foreground">Agent runtime defaults</h3>
                <p className="text-sm leading-6 text-muted-foreground">
                  These roles control discovery, research, decision, and review generation behavior when the runtime is ready.
                </p>
              </div>
              <AIAgentConfigComponent
                aiAgents={aiAgents}
                isLoading={isLoading}
                onUpdateAgent={updateAIAgent}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account Policy</CardTitle>
            <CardDescription>Selected-account execution posture and risk guardrails.</CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedAccount ? (
              <p className="text-sm leading-6 text-muted-foreground">Select a paper account to edit account policy.</p>
            ) : !accountPolicy ? (
              <p className="text-sm leading-6 text-muted-foreground">Account policy is not available for the selected account.</p>
            ) : (
              <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
                <FieldBlock label="Execution mode">
                  <Select
                    value={accountPolicy.execution_mode}
                    onValueChange={(value) => updateAccountPolicy('execution_mode', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual_only">Manual only</SelectItem>
                      <SelectItem value="observe">Observe</SelectItem>
                      <SelectItem value="propose">Propose</SelectItem>
                      <SelectItem value="operator_confirmed_execution">Operator confirmed</SelectItem>
                    </SelectContent>
                  </Select>
                </FieldBlock>

                <FieldBlock label="Risk level">
                  <Select
                    value={accountPolicy.risk_level}
                    onValueChange={(value) => updateAccountPolicy('risk_level', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="moderate">Moderate</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                  </Select>
                </FieldBlock>

                <FieldBlock label="Max open positions">
                  <Input
                    type="number"
                    min="1"
                    value={accountPolicy.max_open_positions}
                    onChange={(event) => updateAccountPolicy('max_open_positions', parseInt(event.target.value, 10) || 1)}
                  />
                </FieldBlock>

                <FieldBlock label="Max new entries / day">
                  <Input
                    type="number"
                    min="1"
                    value={accountPolicy.max_new_entries_per_day}
                    onChange={(event) => updateAccountPolicy('max_new_entries_per_day', parseInt(event.target.value, 10) || 1)}
                  />
                </FieldBlock>

                <FieldBlock label="Per-trade exposure %">
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={accountPolicy.per_trade_exposure_pct}
                    onChange={(event) => updateAccountPolicy('per_trade_exposure_pct', parseFloat(event.target.value) || 1)}
                  />
                </FieldBlock>

                <FieldBlock label="Max portfolio risk %">
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={accountPolicy.max_portfolio_risk_pct}
                    onChange={(event) => updateAccountPolicy('max_portfolio_risk_pct', parseFloat(event.target.value) || 1)}
                  />
                </FieldBlock>

                <FieldBlock label="Max deployed capital %">
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={accountPolicy.max_deployed_capital_pct}
                    onChange={(event) => updateAccountPolicy('max_deployed_capital_pct', parseFloat(event.target.value) || 1)}
                  />
                </FieldBlock>

                <FieldBlock label="Default stop-loss %">
                  <Input
                    type="number"
                    min="0.1"
                    step="0.1"
                    value={accountPolicy.default_stop_loss_pct}
                    onChange={(event) => updateAccountPolicy('default_stop_loss_pct', parseFloat(event.target.value) || 0.1)}
                  />
                </FieldBlock>

                <FieldBlock label="Default target %">
                  <Input
                    type="number"
                    min="0.1"
                    step="0.1"
                    value={accountPolicy.default_target_pct}
                    onChange={(event) => updateAccountPolicy('default_target_pct', parseFloat(event.target.value) || 0.1)}
                  />
                </FieldBlock>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Stage Criteria and Guardrails</CardTitle>
            <CardDescription>Read-only criteria and in-scope items for the current selected-account operator workflow.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {!selectedAccount ? (
              <p className="text-sm leading-6 text-muted-foreground">Select a paper account to inspect current stage criteria.</p>
            ) : (
              <>
                <section className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
                  <StageCriteriaPanel
                    stageLabel="Discovery"
                    criteria={discoveryEnvelope.criteria}
                    considered={discoveryEnvelope.considered}
                    status={discoveryEnvelope.status}
                    statusReason={discoveryEnvelope.status_reason}
                    freshnessState={discoveryEnvelope.freshness_state}
                    emptyReason={discoveryEnvelope.empty_reason}
                  />
                  <div className="rounded-3xl border border-border/70 bg-background/70 p-5">
                    <div className="flex items-center gap-2">
                      <Wallet className="h-4 w-4 text-primary" />
                      <p className="desk-kicker">Guardrail snapshot</p>
                    </div>
                    <div className="mt-4 space-y-3">
                      <StatusRow label="Execution mode" value={accountPolicy?.execution_mode ?? operatorSnapshot?.execution_mode ?? 'unknown'} />
                      <StatusRow label="Per-trade exposure" value={`${accountPolicy?.per_trade_exposure_pct ?? 0}%`} />
                      <StatusRow label="Max open positions" value={String(accountPolicy?.max_open_positions ?? 0)} />
                    </div>
                  </div>
                </section>

                <section className="grid gap-6 xl:grid-cols-3">
                  <StageCriteriaPanel
                    stageLabel="Focused Research"
                    criteria={researchEnvelope.criteria}
                    considered={researchEnvelope.considered}
                    status={researchEnvelope.status}
                    statusReason={researchEnvelope.status_reason}
                    freshnessState={researchEnvelope.freshness_state}
                    emptyReason={researchEnvelope.empty_reason}
                  />
                  <StageCriteriaPanel
                    stageLabel="Decision Review"
                    criteria={decisionEnvelope.criteria}
                    considered={decisionEnvelope.considered}
                    status={decisionEnvelope.status}
                    statusReason={decisionEnvelope.status_reason}
                    freshnessState={decisionEnvelope.freshness_state}
                    emptyReason={decisionEnvelope.empty_reason}
                  />
                  <StageCriteriaPanel
                    stageLabel="Daily Review"
                    criteria={reviewEnvelope.criteria}
                    considered={reviewEnvelope.considered}
                    status={reviewEnvelope.status}
                    statusReason={reviewEnvelope.status_reason}
                    freshnessState={reviewEnvelope.freshness_state}
                    emptyReason={reviewEnvelope.empty_reason}
                  />
                </section>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function FieldBlock({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  )
}

function StatusRow({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold text-foreground">{value}</p>
    </div>
  )
}

function normalizeStageEnvelope(envelope: unknown): {
  criteria: string[]
  considered: string[]
  status: string | null
  status_reason: string | null
  freshness_state: string | null
  empty_reason: string | null
} {
  if (!envelope || typeof envelope !== 'object') {
    return {
      criteria: [],
      considered: [],
      status: null,
      status_reason: null,
      freshness_state: null,
      empty_reason: null,
    }
  }

  const record = envelope as Record<string, unknown>
  return {
    criteria: Array.isArray(record.criteria) ? record.criteria.filter((value): value is string => typeof value === 'string') : [],
    considered: Array.isArray(record.considered) ? record.considered.filter((value): value is string => typeof value === 'string') : [],
    status: typeof record.status === 'string' ? record.status : null,
    status_reason: typeof record.status_reason === 'string' ? record.status_reason : null,
    freshness_state: typeof record.freshness_state === 'string' ? record.freshness_state : null,
    empty_reason: typeof record.empty_reason === 'string' ? record.empty_reason : null,
  }
}

export default ConfigurationFeature

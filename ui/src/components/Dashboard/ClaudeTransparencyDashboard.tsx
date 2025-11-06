/**
 * Claude Transparency Dashboard
 *
 * Comprehensive UI for viewing AI trading transparency and learning progress
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import {
  Brain,
  Search,
  TrendingUp,
  Activity,
  Target,
  BookOpen,
  BarChart3,
  Clock,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  Calendar,
  DollarSign,
  Zap,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { useClaudeTransparency } from '@/hooks/useClaudeTransparency'

export function ClaudeTransparencyDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null)

  const {
    researchActivity,
    analysisActivity,
    executionActivity,
    dailyEvaluation,
    dailySummary,
    strategyEvolution,
    isLoading,
    error,
    refetchAll,
  } = useClaudeTransparency()

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">AI Transparency Dashboard</h1>
            <p className="text-muted-foreground">See how Claude learns and trades</p>
          </div>
          <Button disabled>
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            Loading...
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-muted rounded w-full"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6 p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load AI transparency data: {error}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Eye className="w-8 h-8 text-copper-500" />
            AI Transparency Dashboard
          </h1>
          <p className="text-muted-foreground">Complete visibility into Claude's learning and trading process</p>
        </div>
        <Button onClick={refetchAll} variant="tertiary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh Data
        </Button>
      </div>

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Brain className="w-4 h-4 text-blue-500" />
              Research Sessions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{researchActivity?.total_sessions || 0}</div>
            <p className="text-xs text-muted-foreground">
              {researchActivity?.symbols_analyzed || 0} symbols analyzed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Target className="w-4 h-4 text-green-500" />
              Trade Decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysisActivity?.total_decisions || 0}</div>
            <p className="text-xs text-muted-foreground">
              {analysisActivity?.avg_confidence ? `${(analysisActivity.avg_confidence * 100).toFixed(1)}%` : '0%'} avg confidence
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-500" />
              Execution Success
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {executionActivity?.success_rate ? `${(executionActivity.success_rate * 100).toFixed(1)}%` : '0%'}
            </div>
            <p className="text-xs text-muted-foreground">
              {executionActivity?.avg_slippage ? `${executionActivity.avg_slippage.toFixed(1)} bps` : '0 bps'} avg slippage
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              Strategy Learning
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dailyEvaluation?.strategies_evaluated || 0}</div>
            <p className="text-xs text-muted-foreground">
              {dailyEvaluation?.refinements_recommended || 0} refinements recommended
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="research">Research</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="execution">Execution</TabsTrigger>
          <TabsTrigger value="learning">Learning</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  Today's Summary
                </CardTitle>
                <CardDescription>
                  {dailySummary?.date ? new Date(dailySummary.date).toLocaleDateString() : 'No data available'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {dailySummary ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Day Rating</span>
                      <Badge variant={
                        dailySummary.day_rating === 'excellent' ? 'default' :
                        dailySummary.day_rating === 'good' ? 'secondary' :
                        dailySummary.day_rating === 'neutral' ? 'outline' : 'destructive'
                      }>
                        {dailySummary.day_rating}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Trades Executed</p>
                        <p className="font-bold">{dailySummary.trades_executed}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Total P&L</p>
                        <p className={`font-bold ${dailySummary.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ₹{dailySummary.total_pnl.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div>
                      <p className="text-sm font-medium mb-2">Key Achievements</p>
                      <ul className="text-sm space-y-1">
                        {dailySummary.key_achievements.slice(0, 3).map((achievement, index) => (
                          <li key={index} className="flex items-center gap-2">
                            <CheckCircle className="w-3 h-3 text-green-500" />
                            {achievement}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="text-sm font-medium mb-2">Tomorrow's Plan</p>
                      <ul className="text-sm space-y-1">
                        {dailySummary.planned_activities.slice(0, 3).map((activity, index) => (
                          <li key={index} className="flex items-center gap-2">
                            <Clock className="w-3 h-3 text-blue-500" />
                            {activity}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </>
                ) : (
                  <p className="text-muted-foreground text-center py-4">No daily summary available</p>
                )}
              </CardContent>
            </Card>

            {/* Strategy Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Strategy Performance
                </CardTitle>
                <CardDescription>Today's evaluation results</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {dailyEvaluation?.performance_summary ? (
                  Object.entries(dailyEvaluation.performance_summary).map(([strategy, metrics]: [string, any]) => (
                    <div key={strategy} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium capitalize">
                          {strategy.replace('_', ' ')}
                        </span>
                        <Badge variant="tertiary">
                          {metrics.win_rate ? `${(metrics.win_rate * 100).toFixed(1)}%` : '0%'} win rate
                        </Badge>
                      </div>
                      <Progress
                        value={metrics.win_rate ? metrics.win_rate * 100 : 0}
                        className="h-2"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>P&L: ₹{metrics.total_return ? metrics.total_return.toLocaleString() : '0'}</span>
                        <span>Trades: {metrics.total_trades || 0}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground text-center py-4">No strategy evaluation data available</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Key Insights */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="w-5 h-5" />
                Key Insights from Today
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">What Claude Learned</h4>
                  <ul className="text-sm space-y-1">
                    {dailyEvaluation?.key_insights?.slice(0, 3).map((insight, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                        {insight}
                      </li>
                    )) || <li className="text-muted-foreground">No insights available</li>}
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Research Findings</h4>
                  <ul className="text-sm space-y-1">
                    {researchActivity?.key_findings?.slice(0, 3).map((finding, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                        {finding}
                      </li>
                    )) || <li className="text-muted-foreground">No research findings available</li>}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Research Tab */}
        <TabsContent value="research" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  Research Activity
                </CardTitle>
                <CardDescription>What Claude has been researching</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {researchActivity?.total_sessions || 0}
                    </div>
                    <div className="text-sm text-muted-foreground">Research Sessions</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {researchActivity?.symbols_analyzed || 0}
                    </div>
                    <div className="text-sm text-muted-foreground">Symbols Analyzed</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Data Sources Used</h4>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Market Data API</Badge>
                    <Badge variant="secondary">News Feeds</Badge>
                    <Badge variant="secondary">Technical Indicators</Badge>
                    <Badge variant="secondary">Fundamental Data</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Research Sessions</CardTitle>
                <CardDescription>Latest market analysis activities</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {researchActivity?.recent_sessions?.slice(0, 5).map((session: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{session.research_type}</p>
                        <p className="text-sm text-muted-foreground">
                          {session.symbols_analyzed?.length || 0} symbols analyzed
                        </p>
                      </div>
                      <Badge variant="tertiary">
                        {session.confidence_score ? `${(session.confidence_score * 100).toFixed(0)}%` : '0%'}
                      </Badge>
                    </div>
                  )) || (
                    <p className="text-muted-foreground text-center py-4">No recent research sessions</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Analysis Tab */}
        <TabsContent value="analysis" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  Analysis Activity
                </CardTitle>
                <CardDescription>Claude's decision-making process</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {analysisActivity?.total_decisions || 0}
                    </div>
                    <div className="text-sm text-muted-foreground">Decisions Made</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-orange-600">
                      {analysisActivity?.avg_confidence ? `${(analysisActivity.avg_confidence * 100).toFixed(1)}%` : '0%'}
                    </div>
                    <div className="text-sm text-muted-foreground">Avg Confidence</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Analysis Methods Used</h4>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Technical Analysis</Badge>
                    <Badge variant="secondary">Fundamental Analysis</Badge>
                    <Badge variant="secondary">Risk Assessment</Badge>
                    <Badge variant="secondary">Market Sentiment</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Decisions</CardTitle>
                <CardDescription>Latest trade analysis and decisions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysisActivity?.recent_decisions?.slice(0, 5).map((decision: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{decision.symbol} - {decision.action}</p>
                        <p className="text-sm text-muted-foreground">
                          {decision.strategy_rationale}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge variant={decision.executed ? "default" : "outline"}>
                          {decision.executed ? "Executed" : "Analyzed"}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          {decision.confidence_score ? `${(decision.confidence_score * 100).toFixed(0)}%` : '0%'} confidence
                        </p>
                      </div>
                    </div>
                  )) || (
                    <p className="text-muted-foreground text-center py-4">No recent decisions</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Execution Tab */}
        <TabsContent value="execution" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Execution Quality
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold text-emerald-600">
                    {executionActivity?.success_rate ? `${(executionActivity.success_rate * 100).toFixed(1)}%` : '0%'}
                  </div>
                  <div className="text-sm text-muted-foreground">Success Rate</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Risk Compliance</span>
                    <span>{executionActivity?.risk_compliance ? `${(executionActivity.risk_compliance * 100).toFixed(1)}%` : '0%'}</span>
                  </div>
                  <Progress value={executionActivity?.risk_compliance ? executionActivity.risk_compliance * 100 : 0} className="h-2" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Slippage Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {executionActivity?.avg_slippage ? `${executionActivity.avg_slippage.toFixed(1)}` : '0'}
                  </div>
                  <div className="text-sm text-muted-foreground">Avg Slippage (bps)</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Cost Efficiency</span>
                    <span>{executionActivity?.avg_cost ? `${executionActivity.avg_cost.toFixed(2)}%` : '0%'}</span>
                  </div>
                  <Progress
                    value={executionActivity?.avg_cost ? Math.max(0, 100 - executionActivity.avg_cost * 10) : 100}
                    className="h-2"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Executions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {executionActivity?.recent_executions?.slice(0, 4).map((execution: any, index: number) => (
                    <div key={index} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{execution.symbol}</span>
                        <Badge variant={execution.success ? "default" : "destructive"}>
                          {execution.success ? "Success" : "Failed"}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <p>Qty: {execution.quantity} @ ₹{execution.entry_price}</p>
                        {execution.slippage_analysis && (
                          <p>Slippage: {execution.slippage_analysis.slippage_bps?.toFixed(1)} bps</p>
                        )}
                      </div>
                    </div>
                  )) || (
                    <p className="text-muted-foreground text-center py-4">No recent executions</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Learning Tab */}
        <TabsContent value="learning" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5" />
                  Strategy Learning Progress
                </CardTitle>
                <CardDescription>How Claude is improving strategies</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-indigo-600">
                      {dailyEvaluation?.strategies_evaluated || 0}
                    </div>
                    <div className="text-sm text-muted-foreground">Strategies Evaluated</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-teal-600">
                      {dailyEvaluation?.refinements_recommended || 0}
                    </div>
                    <div className="text-sm text-muted-foreground">Refinements Made</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Learning Confidence</h4>
                  <Progress
                    value={dailyEvaluation?.confidence_score ? dailyEvaluation.confidence_score * 100 : 0}
                    className="h-3"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {dailyEvaluation?.confidence_score ? `${(dailyEvaluation.confidence_score * 100).toFixed(1)}%` : '0%'} confidence in refinements
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Strategy Evolution</CardTitle>
                <CardDescription>Select a strategy to see its evolution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {['rsi_momentum', 'macd_divergence', 'bollinger_mean_reversion', 'breakout_momentum'].map((strategy) => (
                    <Button
                      key={strategy}
                      variant={selectedStrategy === strategy ? "default" : "outline"}
                      className="w-full justify-start"
                      onClick={() => setSelectedStrategy(selectedStrategy === strategy ? null : strategy)}
                    >
                      <BarChart3 className="w-4 h-4 mr-2" />
                      {strategy.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Button>
                  ))}
                </div>

                {selectedStrategy && strategyEvolution && (
                  <div className="mt-4 p-3 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">{selectedStrategy.replace('_', ' ')} Evolution</h4>
                    <div className="text-sm space-y-1">
                      <p>Total Evaluations: {strategyEvolution.total_evaluations}</p>
                      <p>Avg Win Rate: {strategyEvolution.avg_win_rate ? `${(strategyEvolution.avg_win_rate * 100).toFixed(1)}%` : '0%'}</p>
                      <p>Total Refinements: {strategyEvolution.total_refinements}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Strategy Refinements */}
          <Card>
            <CardHeader>
              <CardTitle>Recommended Strategy Refinements</CardTitle>
              <CardDescription>AI-suggested improvements to trading strategies</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {dailyEvaluation?.refinements_recommended?.slice(0, 5).map((refinement: any, index: number) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium">{refinement.strategy_name.replace('_', ' ')}</h4>
                      <div className="flex gap-2">
                        <Badge variant={
                          refinement.implementation_priority === 'high' ? 'destructive' :
                          refinement.implementation_priority === 'medium' ? 'default' : 'secondary'
                        }>
                          {refinement.implementation_priority}
                        </Badge>
                        <Badge variant="tertiary">
                          {refinement.confidence_score ? `${(refinement.confidence_score * 100).toFixed(0)}%` : '0%'}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{refinement.description}</p>
                    <div className="text-sm">
                      <p><strong>Current:</strong> {refinement.current_value}</p>
                      <p><strong>Proposed:</strong> {refinement.proposed_value}</p>
                      <p className="text-muted-foreground"><strong>Impact:</strong> {refinement.expected_impact}</p>
                    </div>
                  </div>
                )) || (
                  <p className="text-muted-foreground text-center py-4">No refinements recommended today</p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
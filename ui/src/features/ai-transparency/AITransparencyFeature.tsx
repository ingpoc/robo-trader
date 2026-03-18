/**
 * AI Transparency Feature
 * Complete visibility into Claude's learning and trading process
 */

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Eye, Brain, TrendingUp, Shield, BookOpen, MessageSquare, BarChart3, Clock, Database } from 'lucide-react'
import { useAITransparency } from './hooks/useAITransparency'
import { TradeDecisionLog } from './components/TradeDecisionLog'
import { StrategyReflections } from './components/StrategyReflections'
import { RecommendationAudit } from './components/RecommendationAudit'
import { SessionTranscripts } from './components/SessionTranscripts'
import { PerformanceAttribution } from './components/PerformanceAttribution'
import { DataPipelineAnalysis, PromptOptimizationHistory } from './components'

interface AITransparencyFeatureProps {
  embedded?: boolean
}

export const AITransparencyFeature: React.FC<AITransparencyFeatureProps> = ({ embedded = false }) => {
  const { tradeLogs, reflections, sessions, isLoading } = useAITransparency()
  const [selectedPromptId, setSelectedPromptId] = useState<string | undefined>(undefined)

  return (
    <div className={embedded ? 'space-y-6' : 'page-wrapper'}>
      <div className="flex flex-col gap-6">
        {!embedded ? <Breadcrumb /> : null}

        {!embedded ? (
          <PageHeader
            title="AI Transparency"
            description="Review the real research, decision, execution, and learning traces produced by the Claude trading runtime."
            icon={<Eye className="h-5 w-5" />}
          />
        ) : null}

        {/* Tabs Section */}
        <Tabs defaultValue="trades" className="w-full">
          <TabsList className="mb-6 grid w-full grid-cols-6 rounded-xl border border-border bg-muted/50 p-1">
            <TabsTrigger value="trades" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              <span className="hidden sm:inline">Trades</span>
            </TabsTrigger>
            <TabsTrigger value="reflections" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <Brain className="w-4 h-4" />
              <span className="hidden sm:inline">Reflections</span>
            </TabsTrigger>
            <TabsTrigger value="recommendations" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">Recommendations</span>
            </TabsTrigger>
            <TabsTrigger value="sessions" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">Sessions</span>
            </TabsTrigger>
            <TabsTrigger value="data-quality" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <Database className="w-4 h-4" />
              <span className="hidden sm:inline">Data Quality</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="text-sm font-semibold rounded-md flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Analytics</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="trades" className="space-y-4">
            <TradeDecisionLog trades={tradeLogs} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="reflections" className="space-y-4">
            <StrategyReflections reflections={reflections} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="recommendations" className="space-y-4">
            <RecommendationAudit />
          </TabsContent>

          <TabsContent value="sessions" className="space-y-4">
            <SessionTranscripts sessions={sessions} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="data-quality" className="space-y-6">
            {/* Introduction Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-6 w-6 text-muted-foreground" />
                  Claude's Prompt Optimization System
                </CardTitle>
                <CardDescription>
                  Watch Claude self-optimize its data fetching prompts in real-time. Claude analyzes data quality
                  from Perplexity API, identifies missing or redundant elements, and iteratively improves prompts
                  to get better trading insights.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-lg border border-border bg-muted/40 p-4">
                    <h4 className="mb-2 font-semibold text-foreground">Quality Analysis</h4>
                    <p className="text-sm text-muted-foreground">
                      Claude rates data quality (1-10) and identifies what's missing or redundant
                    </p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/40 p-4">
                    <h4 className="mb-2 font-semibold text-foreground">Iterative Improvement</h4>
                    <p className="text-sm text-muted-foreground">
                      Up to 3 optimization attempts per data fetch until quality threshold is met
                    </p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/40 p-4">
                    <h4 className="mb-2 font-semibold text-foreground">Continuous Learning</h4>
                    <p className="text-sm text-muted-foreground">
                      Optimized prompts are saved and reused, improving over time
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Real-time Data Pipeline Analysis */}
            <DataPipelineAnalysis />

            {/* Prompt Optimization History Viewer */}
            {selectedPromptId && (
              <Card>
                <CardHeader>
                  <CardTitle>Optimization History Details</CardTitle>
                  <CardDescription>
                    Step-by-step view of how Claude improved this specific prompt
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PromptOptimizationHistory promptId={selectedPromptId} />
                </CardContent>
              </Card>
            )}

            {!selectedPromptId && (
              <Card>
                <CardContent className="py-8">
                  <p className="text-center text-muted-foreground">
                    Click on any prompt in the optimization history above to see detailed improvement steps
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <PerformanceAttribution />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default AITransparencyFeature

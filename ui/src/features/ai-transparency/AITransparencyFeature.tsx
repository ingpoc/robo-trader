/**
 * AI Transparency Feature
 * Complete visibility into Claude's learning and trading process
 */

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Eye, Brain, TrendingUp, Shield, BookOpen, MessageSquare, BarChart3, Clock, Database } from 'lucide-react'
import { useAITransparency } from './hooks/useAITransparency'
import { TradeDecisionLog } from './components/TradeDecisionLog'
import { StrategyReflections } from './components/StrategyReflections'
import { RecommendationAudit } from './components/RecommendationAudit'
import { SessionTranscripts } from './components/SessionTranscripts'
import { PerformanceAttribution } from './components/PerformanceAttribution'
import { DataPipelineAnalysis, PromptOptimizationHistory } from './components'

export const AITransparencyFeature: React.FC = () => {
  const { tradeLogs, reflections, sessions, isLoading } = useAITransparency()
  const [selectedPromptId, setSelectedPromptId] = useState<string | undefined>(undefined)

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4 animate-fade-in-luxury">
        <Breadcrumb />

        {/* Header */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-copper-100 dark:bg-copper-950 rounded-lg">
              <Eye className="w-6 h-6 text-copper-600 dark:text-copper-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-warmgray-900 dark:text-warmgray-100">
                AI Transparency
              </h1>
              <p className="text-sm text-warmgray-600 dark:text-warmgray-400 mt-1">
                Real-time view of Claude's decisions and learning
              </p>
            </div>
          </div>
        </div>

        {/* Tabs Section */}
        <Tabs defaultValue="trades" className="w-full">
          <TabsList className="grid w-full grid-cols-6 mb-6 p-1.5 bg-warmgray-100 dark:bg-warmgray-800 rounded-lg border border-warmgray-300 dark:border-warmgray-700 shadow-sm">
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
                  <Database className="w-6 h-6 text-copper-600 dark:text-copper-400" />
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
                  <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h4 className="font-semibold mb-2 text-blue-900 dark:text-blue-100">Quality Analysis</h4>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      Claude rates data quality (1-10) and identifies what's missing or redundant
                    </p>
                  </div>
                  <div className="p-4 bg-purple-50 dark:bg-purple-950 rounded-lg border border-purple-200 dark:border-purple-800">
                    <h4 className="font-semibold mb-2 text-purple-900 dark:text-purple-100">Iterative Improvement</h4>
                    <p className="text-sm text-purple-700 dark:text-purple-300">
                      Up to 3 optimization attempts per data fetch until quality threshold is met
                    </p>
                  </div>
                  <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
                    <h4 className="font-semibold mb-2 text-green-900 dark:text-green-100">Continuous Learning</h4>
                    <p className="text-sm text-green-700 dark:text-green-300">
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

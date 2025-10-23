/**
 * AI Transparency Feature
 * Complete visibility into Claude's learning and trading process
 */

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Eye, Brain, TrendingUp, Shield, BookOpen, MessageSquare, BarChart3, Clock } from 'lucide-react'
import { useAITransparency } from './hooks/useAITransparency'
import { TradeDecisionLog } from './components/TradeDecisionLog'
import { StrategyReflections } from './components/StrategyReflections'
import { RecommendationAudit } from './components/RecommendationAudit'
import { SessionTranscripts } from './components/SessionTranscripts'
import { PerformanceAttribution } from './components/PerformanceAttribution'

export const AITransparencyFeature: React.FC = () => {
  const { tradeLogs, reflections, sessions, isLoading } = useAITransparency()

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
              <h1 className="text-4xl lg:text-5xl font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">
                AI Transparency Center
              </h1>
              <p className="text-lg text-warmgray-600 dark:text-warmgray-400 mt-2">
                Complete visibility into Claude's learning and trading process
              </p>
            </div>
          </div>

          {/* Feature Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Brain className="w-5 h-5 text-blue-500" />
                  Research Tracking
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  See what data sources Claude uses, which symbols it analyzes, and key market insights discovered.
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-purple-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-500" />
                  Decision Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Understand Claude's step-by-step reasoning process, confidence levels, and trade decision logic.
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-emerald-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Shield className="w-5 h-5 text-emerald-500" />
                  Execution Monitoring
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Monitor trade execution quality, slippage analysis, and risk compliance in real-time.
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-orange-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-orange-500" />
                  Learning Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Track how Claude evaluates strategies daily, implements refinements, and improves over time.
                </CardDescription>
              </CardContent>
            </Card>
          </div>

          {/* Trust Statement */}
          <Card className="bg-gradient-to-r from-copper-50/50 to-emerald-50/50 dark:from-copper-950/50 dark:to-emerald-950/50 border-copper-200 dark:border-copper-800">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-copper-100 dark:bg-copper-900 rounded-lg flex-shrink-0">
                  <Shield className="w-6 h-6 text-copper-600 dark:text-copper-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100 mb-2">
                    Transparency You Can Trust
                  </h3>
                  <p className="text-warmgray-600 dark:text-warmgray-400">
                    Every decision Claude makes is logged and explained. You can see exactly how it analyzes markets,
                    evaluates strategies, executes trades, and learns from experience. No black boxes - just clear,
                    comprehensive visibility into the AI's complete trading process.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs Section */}
        <Tabs defaultValue="trades" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-6 p-1.5 bg-warmgray-100 dark:bg-warmgray-800 rounded-lg border border-warmgray-300 dark:border-warmgray-700 shadow-sm">
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

          <TabsContent value="analytics" className="space-y-4">
            <PerformanceAttribution />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default AITransparencyFeature

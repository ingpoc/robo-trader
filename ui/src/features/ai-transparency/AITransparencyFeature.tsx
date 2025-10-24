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

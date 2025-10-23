/**
 * Claude Transparency Page
 *
 * Main page for viewing AI trading transparency and learning progress
 */

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ClaudeTransparencyDashboard } from '@/components/Dashboard/ClaudeTransparencyDashboard'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Eye, Brain, TrendingUp, Shield, BookOpen } from 'lucide-react'

export function ClaudeTransparency() {
  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4">
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

        {/* Main Transparency Dashboard */}
        <ClaudeTransparencyDashboard />
      </div>
    </div>
  )
}

export default ClaudeTransparency
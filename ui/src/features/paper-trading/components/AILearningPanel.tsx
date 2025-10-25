/**
 * AI Learning Panel Component
 * Displays Claude's AI learning progress and strategy effectiveness
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TrendingUp, Lightbulb, Target, Zap } from 'lucide-react'

export interface DailyReflection {
  date: string
  what_worked: string[]
  what_didnt_work: string[]
  tomorrow_focus: string[]
  tokens_used: number
  max_tokens: number
}

export interface StrategyInsight {
  strategy: string
  win_rate: number
  avg_return: number
  total_trades: number
}

export interface AILearningPanelProps {
  dailyReflection: DailyReflection | null
  strategyInsights: StrategyInsight[]
  isLoading?: boolean
}

export const AILearningPanel: React.FC<AILearningPanelProps> = ({
  dailyReflection,
  strategyInsights,
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-500" />
            AI Learning & Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          AI Learning & Insights
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Daily Reflection Section */}
        {dailyReflection && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">Today's Reflection</h3>
              <span className="text-xs text-muted-foreground">
                {new Date(dailyReflection.date).toLocaleDateString('en-IN')}
              </span>
            </div>

            {/* What Worked */}
            {dailyReflection.what_worked.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <CheckIcon className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-600">What Worked</span>
                </div>
                <div className="space-y-1 ml-6">
                  {dailyReflection.what_worked.map((item, idx) => (
                    <div key={idx} className="text-sm text-muted-foreground">✓ {item}</div>
                  ))}
                </div>
              </div>
            )}

            {/* What Didn't Work */}
            {dailyReflection.what_didnt_work.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <XIcon className="w-4 h-4 text-red-600" />
                  <span className="text-sm font-medium text-red-600">What Didn't Work</span>
                </div>
                <div className="space-y-1 ml-6">
                  {dailyReflection.what_didnt_work.map((item, idx) => (
                    <div key={idx} className="text-sm text-muted-foreground">✗ {item}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Tomorrow's Focus */}
            {dailyReflection.tomorrow_focus.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-600">Tomorrow's Focus</span>
                </div>
                <div className="space-y-1 ml-6">
                  {dailyReflection.tomorrow_focus.map((item, idx) => (
                    <div key={idx} className="text-sm text-muted-foreground">→ {item}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Token Usage */}
            <div className="pt-2 border-t">
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted-foreground">Token Usage</span>
                <span className="font-medium">
                  {dailyReflection.tokens_used} / {dailyReflection.max_tokens}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${(dailyReflection.tokens_used / dailyReflection.max_tokens) * 100}%`
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Strategy Effectiveness */}
        {strategyInsights.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">Strategy Effectiveness</h3>
              <Zap className="w-4 h-4 text-amber-500" />
            </div>

            <div className="space-y-3">
              {strategyInsights.map((insight, idx) => (
                <div key={idx} className="bg-muted p-3 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{insight.strategy}</span>
                    <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 px-2 py-1 rounded">
                      {insight.total_trades} trades
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground text-xs">Win Rate</span>
                      <div className={`font-semibold ${
                        insight.win_rate >= 60 ? 'text-emerald-600' :
                        insight.win_rate >= 50 ? 'text-amber-600' :
                        'text-red-600'
                      }`}>
                        {insight.win_rate.toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs">Avg Return</span>
                      <div className={`font-semibold ${insight.avg_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {insight.avg_return >= 0 ? '+' : ''}{insight.avg_return.toFixed(2)}%
                      </div>
                    </div>
                  </div>

                  {/* Win Rate Progress Bar */}
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-3 h-3 text-emerald-600" />
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          insight.win_rate >= 60 ? 'bg-emerald-600' :
                          insight.win_rate >= 50 ? 'bg-amber-600' :
                          'bg-red-600'
                        }`}
                        style={{ width: `${insight.win_rate}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!dailyReflection && strategyInsights.length === 0 && (
          <div className="text-center py-8">
            <Lightbulb className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">
              AI learning insights will appear here as you execute trades
            </p>
          </div>
        )}

        {/* Last Updated */}
        {dailyReflection && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              Last updated: {new Date(dailyReflection.date).toLocaleTimeString('en-IN')}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Helper Components for Icons
const CheckIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
)

const XIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
)

export default AILearningPanel

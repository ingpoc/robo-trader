/**
 * AI Insights Summary Component
 * Displays AI agent insights and recommendations
 */

import React from 'react'
import { AIInsights } from '@/components/Dashboard/AIInsights'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { ArrowRight } from 'lucide-react'

export interface AIInsightsSummaryProps {
  onNavigate?: (path: string) => void
}

export const AIInsightsSummary: React.FC<AIInsightsSummaryProps> = ({ onNavigate }) => {
  return (
    <div className="space-y-6 animate-slide-in-up-luxury">
      <div style={{ animationDelay: '100ms' }} className="animate-slide-in-up-luxury">
        <AIInsights status="operational" />
      </div>
      <div style={{ animationDelay: '200ms' }} className="animate-slide-in-up-luxury">
        <Card className="border-l-4 border-l-copper-500/40 dark:border-l-copper-500/30 hover:shadow-md transition-all duration-300 backdrop-blur-sm">
          <CardContent className="pt-8 pb-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100 mb-2">
                  AI Trading Intelligence
                </h3>
                <p className="text-sm text-warmgray-600 dark:text-warmgray-400">
                  Explore detailed AI agent performance metrics and trading recommendations
                </p>
              </div>
              <Button
                variant="primary"
                onClick={() => onNavigate?.('/ai-transparency')}
                className="whitespace-nowrap font-semibold transition-all duration-300 hover:shadow-lg hover:shadow-copper-500/20"
              >
                View AI Details
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default AIInsightsSummary

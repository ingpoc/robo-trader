/**
 * AI Insights Summary Component
 * Displays AI agent insights and recommendations
 */

import React from 'react'
import { AIInsights } from '@/components/Dashboard/AIInsights'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { ArrowRight } from 'lucide-react'
import type { AIStatus } from '@/types/api'

export interface AIInsightsSummaryProps {
  onNavigate?: (path: string) => void
  status?: AIStatus
}

export const AIInsightsSummary: React.FC<AIInsightsSummaryProps> = ({ onNavigate, status }) => {
  return (
    <div className="space-y-6">
      <div>
        <AIInsights status={status} />
      </div>
      <div>
        <Card className="border-border bg-card shadow-sm">
          <CardContent className="pt-8 pb-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="mb-2 text-lg font-semibold text-card-foreground">
                  AI Trading Intelligence
                </h3>
                <p className="text-sm text-muted-foreground">
                  Inspect current agent activity, decision context, and execution blockers inside the paper-trading workflow.
                </p>
              </div>
              <Button
                variant="outline"
                onClick={() => onNavigate?.('/paper-trading')}
                className="whitespace-nowrap font-semibold"
              >
                Open Paper Trading Review
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

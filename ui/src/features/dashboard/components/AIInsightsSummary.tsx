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
    <div className="space-y-4">
      <AIInsights status="operational" />
      <Card>
        <CardContent className="pt-6">
          <Button
            variant="primary"
            onClick={() => onNavigate?.('/agents')}
            className="w-full sm:w-auto"
          >
            View AI Agent Details
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default AIInsightsSummary

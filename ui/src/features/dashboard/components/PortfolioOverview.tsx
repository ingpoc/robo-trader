/**
 * Portfolio Overview Component
 * Displays portfolio holdings and position details
 */

import React from 'react'
import { HoldingsTable } from '@/components/Dashboard/HoldingsTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

export interface PortfolioOverviewProps {
  portfolio: any | null
  detailed?: boolean
}

export const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ portfolio, detailed = false }) => {
  if (!portfolio || !portfolio.holdings || portfolio.holdings.length === 0) {
    return (
      <div>
        <Card className="border-border bg-card shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-card-foreground">
              Portfolio Holdings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <svg className="w-6 h-6 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m0 0h6m-6-6h6m0 0h6" />
                </svg>
              </div>
              <p className="text-muted-foreground">No active positions</p>
              <p className="mt-2 text-sm text-muted-foreground">Start trading to see your portfolio here</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center justify-between text-lg font-semibold text-card-foreground">
            <span>
              {detailed ? 'All Holdings' : 'Recent Holdings'} <span className="ml-2 font-bold text-muted-foreground">({portfolio.holdings.length})</span>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <HoldingsTable holdings={portfolio.holdings} totalExposure={portfolio.exposure_total || 0} />
        </CardContent>
      </Card>
    </div>
  )
}

export default PortfolioOverview

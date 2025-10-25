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
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-warmgray-500">No active positions</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {detailed ? 'All Holdings' : 'Recent Holdings'} ({portfolio.holdings.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <HoldingsTable holdings={portfolio.holdings} />
      </CardContent>
    </Card>
  )
}

export default PortfolioOverview

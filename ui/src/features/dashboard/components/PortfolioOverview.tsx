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
      <div className="animate-slide-in-up-luxury">
        <Card className="border-l-4 border-l-warmgray-300 dark:border-l-warmgray-600 hover:shadow-md transition-all duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-warmgray-700 dark:text-warmgray-300">
              Portfolio Holdings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <div className="w-12 h-12 bg-warmgray-100 dark:bg-warmgray-800 rounded-full flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-warmgray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m0 0h6m-6-6h6m0 0h6" />
                </svg>
              </div>
              <p className="text-warmgray-500 dark:text-warmgray-400">No active positions</p>
              <p className="text-sm text-warmgray-400 dark:text-warmgray-500 mt-2">Start trading to see your portfolio here</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="animate-slide-in-up-luxury">
      <Card className="border-l-4 border-l-copper-500/40 dark:border-l-copper-500/30 hover:shadow-md transition-all duration-300">
        <CardHeader className="pb-4 border-b border-warmgray-100 dark:border-warmgray-700">
          <CardTitle className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100 flex items-center justify-between">
            <span>
              {detailed ? 'All Holdings' : 'Recent Holdings'} <span className="ml-2 text-copper-600 dark:text-copper-400 font-bold">({portfolio.holdings.length})</span>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <HoldingsTable holdings={portfolio.holdings} />
        </CardContent>
      </Card>
    </div>
  )
}

export default PortfolioOverview

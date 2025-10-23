/**
 * Strategy Reflections Component
 * Displays daily learning reflections and strategy improvements
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonCard } from '@/components/common/SkeletonLoader'
import { TrendingUp, TrendingDown, Lightbulb } from 'lucide-react'

export interface StrategyReflectionsProps {
  reflections: any[]
  isLoading: boolean
}

export const StrategyReflections: React.FC<StrategyReflectionsProps> = ({ reflections, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4">
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} className="h-56" />
        ))}
      </div>
    )
  }

  if (!reflections || reflections.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">No strategy reflections available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {reflections.map((reflection, index) => (
        <Card key={index}>
          <CardHeader>
            <CardTitle className="text-lg">
              {new Date(reflection.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* What Worked */}
            {reflection.what_worked && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  <h4 className="font-semibold text-warmgray-900">What Worked</h4>
                </div>
                <p className="text-sm text-warmgray-600 ml-7">{reflection.what_worked}</p>
              </div>
            )}

            {/* What Didn't Work */}
            {reflection.what_didnt_work && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-red-600" />
                  <h4 className="font-semibold text-warmgray-900">What Didn't Work</h4>
                </div>
                <p className="text-sm text-warmgray-600 ml-7">{reflection.what_didnt_work}</p>
              </div>
            )}

            {/* Tomorrow's Focus */}
            {reflection.tomorrow_focus && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-amber-600" />
                  <h4 className="font-semibold text-warmgray-900">Tomorrow's Focus</h4>
                </div>
                <p className="text-sm text-warmgray-600 ml-7">{reflection.tomorrow_focus}</p>
              </div>
            )}

            {/* Stats */}
            {reflection.win_rate !== undefined && (
              <div className="flex gap-4 pt-3 border-t text-sm">
                <div>
                  <p className="text-warmgray-600">Win Rate</p>
                  <p className="font-semibold">{reflection.win_rate.toFixed(1)}%</p>
                </div>
                {reflection.trades_executed !== undefined && (
                  <div>
                    <p className="text-warmgray-600">Trades</p>
                    <p className="font-semibold">{reflection.trades_executed}</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default StrategyReflections

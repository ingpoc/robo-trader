import { memo } from 'react'
import { Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatDate } from '@/utils/format'
import type { UpcomingEarnings } from '@/types/domain'

interface UpcomingEarningsProps {
  earnings: UpcomingEarnings[]
  portfolioSymbols: string[]
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
}

export const UpcomingEarnings = memo<UpcomingEarningsProps>(({
  earnings,
  portfolioSymbols,
  isLoading,
  error,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📅 Upcoming Earnings Calendar
          </CardTitle>
          <p className="text-slate-600 dark:text-slate-400">
            Next earnings reports for your portfolio stocks (next 60 days)
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 dark:text-slate-400">Loading upcoming earnings...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📅 Upcoming Earnings Calendar
          </CardTitle>
          <p className="text-slate-600 dark:text-slate-400">
            Next earnings reports for your portfolio stocks (next 60 days)
          </p>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md mx-auto">
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Unable to load upcoming earnings</h3>
              <p className="text-red-700 dark:text-red-300 text-sm mb-4">{error}</p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Filter earnings for portfolio symbols and sort by date
  const portfolioEarnings = earnings
    .filter(earnings => portfolioSymbols.includes(earnings.symbol))
    .sort((a, b) => new Date(a.next_earnings_date).getTime() - new Date(b.next_earnings_date).getTime())

  if (!portfolioEarnings || portfolioEarnings.length === 0) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📅 Upcoming Earnings Calendar
          </CardTitle>
          <p className="text-slate-600 dark:text-slate-400">
            Next earnings reports for your portfolio stocks (next 60 days)
          </p>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">📅</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Upcoming Earnings</h3>
            <p className="text-slate-600 dark:text-slate-400">
              No earnings reports scheduled for your portfolio stocks in the next 60 days.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
      <CardHeader className="pb-4">
        <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
          📅 Upcoming Earnings Calendar
        </CardTitle>
        <p className="text-slate-600 dark:text-slate-400">
          Next earnings reports for your portfolio stocks (next 60 days)
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {portfolioEarnings.map((earnings, index) => (
            <article
              key={index}
              className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-700 rounded-lg bg-gradient-to-r from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-center gap-4">
                <div className="bg-blue-100 dark:bg-blue-900 rounded-full w-12 h-12 flex items-center justify-center">
                  <Calendar className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h4 className="font-bold text-lg text-slate-900 dark:text-slate-100">
                    {earnings.symbol}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {earnings.fiscal_period}
                  </p>
                  {earnings.guidance && (
                    <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 max-w-md truncate">
                      {earnings.guidance}
                    </p>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {formatDate(earnings.next_earnings_date)}
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  {earnings.days_until} days
                </div>
              </div>
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  )
})

UpcomingEarnings.displayName = 'UpcomingEarnings'
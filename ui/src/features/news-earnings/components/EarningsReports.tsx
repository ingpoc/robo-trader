import { memo } from 'react'
import { Calendar, Target } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatDate } from '@/utils/format'
import type { EarningsReport } from '@/types/domain'

interface EarningsReportsProps {
  earnings: EarningsReport[]
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
}

export const EarningsReports = memo<EarningsReportsProps>(({
  earnings,
  isLoading,
  error,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📊 Earnings Reports
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 dark:text-slate-400">Loading earnings data...</p>
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
            📊 Earnings Reports
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md mx-auto">
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Unable to load earnings data</h3>
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

  if (!earnings || earnings.length === 0) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📊 Earnings Reports
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">📊</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Earnings Data</h3>
            <p className="text-slate-600 dark:text-slate-400">No earnings reports found for the selected stock</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
      <CardHeader className="pb-4">
        <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
          📊 Earnings Reports
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {earnings.map((report) => (
            <article
              key={report.id}
              className="border border-slate-200 dark:border-slate-700 rounded-xl p-6 bg-gradient-to-r from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 hover:shadow-lg transition-all duration-300"
            >
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Period Info */}
                <div className="lg:col-span-1">
                  <h4 className="font-bold text-xl text-slate-900 dark:text-slate-100 mb-2">
                    {report.fiscal_period}
                  </h4>
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400 mb-3">
                    <Calendar className="w-4 h-4" />
                    <time dateTime={report.report_date}>
                      {formatDate(report.report_date)}
                    </time>
                  </div>
                  {report.surprise_pct !== undefined && report.surprise_pct !== null && (
                    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${
                      Math.abs(report.surprise_pct) > 10
                        ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        : Math.abs(report.surprise_pct) > 5
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                        : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
                    }`}>
                      <Target className="w-4 h-4" />
                      {report.surprise_pct >= 0 ? '+' : ''}{report.surprise_pct.toFixed(1)}% Surprise
                    </div>
                  )}
                </div>

                {/* EPS Data */}
                <div className="space-y-3">
                  <h5 className="font-semibold text-slate-900 dark:text-slate-100">EPS Performance</h5>
                  <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                    <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                      {report.eps_actual ? `$${report.eps_actual.toFixed(2)}` : 'N/A'}
                    </div>
                    {report.eps_estimated && (
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        Est: ${report.eps_estimated.toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Revenue Data */}
                <div className="space-y-3">
                  <h5 className="font-semibold text-slate-900 dark:text-slate-100">Revenue</h5>
                  <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                    {report.revenue_actual ? (
                      <>
                        <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                          ${(report.revenue_actual / 1000000).toFixed(0)}M
                        </div>
                        {report.revenue_estimated && (
                          <div className="text-sm text-slate-600 dark:text-slate-400">
                            Est: ${(report.revenue_estimated / 1000000).toFixed(0)}M
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-slate-500 dark:text-slate-400">N/A</div>
                    )}
                  </div>
                </div>

                {/* Next Earnings */}
                <div className="space-y-3">
                  <h5 className="font-semibold text-slate-900 dark:text-slate-100">Next Report</h5>
                  <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                    {report.next_earnings_date ? (
                      <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                        {formatDate(report.next_earnings_date)}
                      </div>
                    ) : (
                      <div className="text-slate-500 dark:text-slate-400">TBD</div>
                    )}
                  </div>
                </div>
              </div>

              {report.guidance && (
                <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
                  <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Management Guidance</h5>
                  <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <p className="text-blue-900 dark:text-blue-100">{report.guidance}</p>
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  )
})

EarningsReports.displayName = 'EarningsReports'
import { formatCurrency, formatNumber, formatPercent } from '@/utils/format'
import type { Holding } from '@/types/api'

interface HoldingsTableProps {
  holdings: Holding[]
  totalExposure: number
}

export function HoldingsTable({ holdings, totalExposure }: HoldingsTableProps) {
  return (
    <div className="flex flex-col gap-2 bg-white/80 backdrop-blur-sm border border-gray-200/50 card-shadow rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-200/50">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Holdings</div>
        <div className="text-11 text-gray-500">
          {holdings.length} {holdings.length === 1 ? 'position' : 'positions'}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-full table-fixed">
          <colgroup>
            <col style={{ width: '20%' }} />
            <col style={{ width: '12%' }} />
            <col style={{ width: '16%' }} />
            <col style={{ width: '16%' }} />
            <col style={{ width: '20%' }} />
            <col style={{ width: '16%' }} />
          </colgroup>
          <thead className="bg-gray-50/80 border-b border-gray-200/50">
            <tr>
              <th className="px-4 py-3 text-left text-11 font-semibold text-gray-600 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-4 py-3 text-right text-11 font-semibold text-gray-600 uppercase tracking-wider">
                Quantity
              </th>
              <th className="px-4 py-3 text-right text-11 font-semibold text-gray-600 uppercase tracking-wider">
                Avg Price
              </th>
              <th className="px-4 py-3 text-right text-11 font-semibold text-gray-600 uppercase tracking-wider">
                Last Price
              </th>
              <th className="px-4 py-3 text-right text-11 font-semibold text-gray-600 uppercase tracking-wider">
                P&L
              </th>
              <th className="px-4 py-3 text-right text-11 font-semibold text-gray-600 uppercase tracking-wider">
                Allocation
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {holdings.map((holding, index) => {
              const allocation = totalExposure > 0 ? (holding.exposure / totalExposure) * 100 : 0

              return (
                <tr key={index} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-gray-900">
                        {holding.symbol}
                      </span>
                      {holding.risk_tags.length > 0 && (
                        <span className="text-11 text-gray-500 uppercase tracking-wider mt-0.5">
                          {holding.risk_tags[0]}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-900 tabular-nums font-medium">
                    {formatNumber(holding.qty, 0)}
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-900 tabular-nums">
                    {formatCurrency(holding.avg_price)}
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-900 tabular-nums">
                    {formatCurrency(holding.last_price)}
                  </td>
                  <td className="px-4 py-4 text-right">
                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={`text-sm tabular-nums font-semibold ${
                          holding.pnl_abs > 0
                            ? 'text-success'
                            : holding.pnl_abs < 0
                              ? 'text-error'
                              : 'text-gray-500'
                        }`}
                      >
                        {formatCurrency(holding.pnl_abs)}
                      </span>
                      <span
                        className={`text-11 tabular-nums ${
                          holding.pnl_abs > 0 ? 'text-success-dark' : 'text-gray-500'
                        }`}
                      >
                        {formatPercent(holding.pnl_pct)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-900 tabular-nums font-medium">
                    {formatNumber(allocation, 1)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {holdings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 px-4">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500 text-center">No holdings to display</p>
        </div>
      )}
    </div>
  )
}

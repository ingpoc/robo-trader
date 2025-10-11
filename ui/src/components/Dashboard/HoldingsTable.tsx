import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'
import { formatCurrency, formatNumber, formatPercent } from '@/utils/format'
import type { Holding } from '@/types/api'

interface HoldingsTableProps {
  holdings: Holding[]
  totalExposure: number
}

export function HoldingsTable({ holdings, totalExposure }: HoldingsTableProps) {
  const parentRef = useRef<HTMLDivElement>(null)

  const rowVirtualizer = useVirtualizer({
    count: holdings.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 5,
  })

  return (
    <div className="flex flex-col gap-2 bg-white border border-gray-200 card-shadow">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Holdings</div>
        <div className="text-11 text-gray-500">
          {holdings.length} {holdings.length === 1 ? 'position' : 'positions'}
        </div>
      </div>

      <div ref={parentRef} className="overflow-auto" style={{ maxHeight: '400px' }}>
        <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
          <table className="w-full table-fixed">
            <colgroup>
              <col style={{ width: '20%' }} />
              <col style={{ width: '10%' }} />
              <col style={{ width: '15%' }} />
              <col style={{ width: '15%' }} />
              <col style={{ width: '25%' }} />
              <col style={{ width: '15%' }} />
            </colgroup>
            <thead className="sticky top-0 bg-gray-50 border-b border-gray-200 z-10">
              <tr>
                <th className="px-4 py-1.5 text-left text-11 font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-4 py-1.5 text-right text-11 font-medium text-gray-500 uppercase tracking-wider">
                  Qty
                </th>
                <th className="px-4 py-1.5 text-right text-11 font-medium text-gray-500 uppercase tracking-wider">
                  Avg Price
                </th>
                <th className="px-4 py-1.5 text-right text-11 font-medium text-gray-500 uppercase tracking-wider">
                  Last Price
                </th>
                <th className="px-4 py-1.5 text-right text-11 font-medium text-gray-500 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-4 py-1.5 text-right text-11 font-medium text-gray-500 uppercase tracking-wider">
                  Allocation
                </th>
              </tr>
            </thead>
            <tbody>
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const holding = holdings[virtualRow.index]
                const allocation =
                  totalExposure > 0 ? (holding.exposure / totalExposure) * 100 : 0

                return (
                  <tr
                    key={virtualRow.index}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-900">
                          {holding.symbol}
                        </span>
                        {holding.risk_tags.length > 0 && (
                          <span className="text-11 text-gray-500 uppercase tracking-wider">
                            {holding.risk_tags[0]}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-13 text-gray-900 tabular-nums">
                      {formatNumber(holding.qty, 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-13 text-gray-900 tabular-nums">
                      {formatCurrency(holding.avg_price)}
                    </td>
                    <td className="px-4 py-3 text-right text-13 text-gray-900 tabular-nums">
                      {formatCurrency(holding.last_price)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col items-end">
                        <span
                          className={`text-13 tabular-nums ${
                            holding.pnl_abs > 0
                              ? 'text-success font-semibold'
                              : holding.pnl_abs < 0
                                ? 'text-gray-600 font-medium'
                                : 'text-gray-500 font-medium'
                          }`}
                        >
                          {formatCurrency(holding.pnl_abs)}
                        </span>
                        <span className={`text-11 tabular-nums ${holding.pnl_abs > 0 ? 'text-success-dark' : 'text-gray-500'}`}>
                          {formatPercent(holding.pnl_pct)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-13 text-gray-900 tabular-nums">
                      {formatNumber(allocation, 1)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

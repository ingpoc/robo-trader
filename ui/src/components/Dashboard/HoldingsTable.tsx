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
    <div className="flex flex-col gap-3 bg-white border border-gray-200 rounded">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Holdings</h3>
        <div className="text-sm text-gray-600">
          {holdings.length} {holdings.length === 1 ? 'position' : 'positions'}
        </div>
      </div>

      <div ref={parentRef} className="overflow-auto" style={{ maxHeight: '400px' }}>
        <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
          <table className="w-full">
            <thead className="sticky top-0 bg-gray-50 border-b border-gray-200 z-10">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                  Symbol
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-600">
                  Qty
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-600">
                  Avg Price
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-600">
                  Last Price
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-600">
                  P&L
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-600">
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
                    className="border-b border-gray-100"
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-900">
                          {holding.symbol}
                        </span>
                        {holding.risk_tags.length > 0 && (
                          <span className="text-xs text-gray-500">
                            {holding.risk_tags[0]}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-900">
                      {formatNumber(holding.qty, 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-900">
                      {formatCurrency(holding.avg_price)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-900">
                      {formatCurrency(holding.last_price)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col items-end">
                        <span
                          className={`text-sm font-medium ${
                            holding.pnl_abs > 0
                              ? 'text-gray-900'
                              : holding.pnl_abs < 0
                                ? 'text-gray-600'
                                : 'text-gray-500'
                          }`}
                        >
                          {formatCurrency(holding.pnl_abs)}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatPercent(holding.pnl_pct)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-900">
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

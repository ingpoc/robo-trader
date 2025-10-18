import { useState, useMemo } from 'react'
import { formatCurrency, formatNumber, formatPercent } from '@/utils/format'
import type { Holding } from '@/types/api'
import { Input } from '@/components/ui/Input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronUp, ChevronDown, Search, MoreHorizontal, TrendingUp, TrendingDown, Edit } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

interface HoldingsTableProps {
  holdings: Holding[]
  totalExposure: number
  onBuy?: (symbol: string) => void
  onSell?: (symbol: string) => void
  onEdit?: (symbol: string) => void
}

type SortField = 'symbol' | 'qty' | 'last_price' | 'exposure' | 'pnl_abs' | 'pnl_pct'
type SortDirection = 'asc' | 'desc'

export function HoldingsTable({ holdings, totalExposure, onBuy, onSell, onEdit }: HoldingsTableProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState<SortField>('symbol')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // Filter holdings based on search term
  const filteredHoldings = useMemo(() => {
    return holdings.filter(holding =>
      holding.symbol.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [holdings, searchTerm])

  // Sort holdings
  const sortedHoldings = useMemo(() => {
    return [...filteredHoldings].sort((a, b) => {
      let aValue: string | number
      let bValue: string | number

      switch (sortField) {
        case 'symbol':
          aValue = a.symbol.toLowerCase()
          bValue = b.symbol.toLowerCase()
          break
        case 'qty':
          aValue = a.qty
          bValue = b.qty
          break
        case 'last_price':
          aValue = a.last_price
          bValue = b.last_price
          break
        case 'exposure':
          aValue = a.exposure
          bValue = b.exposure
          break
        case 'pnl_abs':
          aValue = a.pnl_abs
          bValue = b.pnl_abs
          break
        case 'pnl_pct':
          aValue = a.pnl_pct
          bValue = b.pnl_pct
          break
        default:
          return 0
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue)
      }

      if (sortDirection === 'asc') {
        return (aValue as number) - (bValue as number)
      } else {
        return (bValue as number) - (aValue as number)
      }
    })
  }, [filteredHoldings, sortField, sortDirection])

  // Paginate holdings
  const totalPages = Math.ceil(sortedHoldings.length / itemsPerPage)
  const paginatedHoldings = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return sortedHoldings.slice(startIndex, startIndex + itemsPerPage)
  }, [sortedHoldings, currentPage, itemsPerPage])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
    setCurrentPage(1) // Reset to first page when sorting
  }

  const SortableHeader = ({
    field,
    children,
    className
  }: {
    field: SortField
    children: React.ReactNode
    className?: string
  }) => (
    <TableHead
      className={cn(
        "cursor-pointer select-none hover:bg-warmgray-50/50 transition-colors",
        className
      )}
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        <div className="flex flex-col">
          <ChevronUp
            className={cn(
              "w-3 h-3 -mb-1",
              sortField === field && sortDirection === 'asc'
                ? "text-warmgray-900"
                : "text-warmgray-300"
            )}
          />
          <ChevronDown
            className={cn(
              "w-3 h-3 -mt-1",
              sortField === field && sortDirection === 'desc'
                ? "text-warmgray-900"
                : "text-warmgray-300"
            )}
          />
        </div>
      </div>
    </TableHead>
  )

  return (
    <div className="flex flex-col gap-4 bg-gradient-to-br from-white/95 to-warmgray-50/70 backdrop-blur-sm border-0 shadow-md rounded-xl overflow-hidden hover:shadow-lg transition-all duration-300 ring-1 ring-warmgray-300/50 animate-scale-in">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-warmgray-300/30 bg-gradient-to-r from-warmgray-50/80 to-white/60">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-copper-100 to-copper-200 rounded-xl shadow-sm">
            <TrendingUp className="w-6 h-6 text-copper-700" />
          </div>
          <div>
            <div className="text-lg font-bold text-warmgray-900 font-serif uppercase tracking-wider">
              Holdings
            </div>
            <div className="text-sm text-warmgray-600 mt-0.5 font-medium">
              Portfolio positions and performance
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 bg-gradient-to-r from-copper-100 to-copper-200 text-copper-800 text-sm font-bold rounded-full border border-copper-300 shadow-sm">
            {filteredHoldings.length} {filteredHoldings.length === 1 ? 'position' : 'positions'}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-warmgray-500" />
          <Input
            type="text"
            placeholder="Search symbols..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1) // Reset to first page when searching
            }}
            className="pl-12 h-12 border-warmgray-300 focus:border-copper-500 focus:ring-copper-500/20 rounded-xl shadow-sm bg-white/80 backdrop-blur-sm font-medium"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-gradient-to-r from-warmgray-50/90 to-white/60 border-b border-warmgray-300/40">
            <TableRow>
              <SortableHeader field="symbol" className="text-left">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-warmgray-800">Symbol</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Stock ticker symbol (e.g., AAPL, GOOGL)</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="qty" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-warmgray-800">Quantity</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Number of shares you own</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="last_price" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-warmgray-800">Current Price</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Latest market price per share</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="exposure" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-warmgray-800">Market Value</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Total value of your position (price × quantity)</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="pnl_abs" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-gray-800">P&L</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Profit and Loss in dollar amount</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="pnl_pct" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-gray-800">P&L %</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Profit and Loss as a percentage</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <TableHead className="w-12">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="font-bold text-gray-800">Actions</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Quick actions for this position</p>
                  </TooltipContent>
                </Tooltip>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-gray-100/60">
            {paginatedHoldings.map((holding, index) => {
              const allocation = totalExposure > 0 ? (holding.exposure / totalExposure) * 100 : 0

              return (
                <TableRow key={index} className="hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-indigo-50/30 transition-all duration-200 group border-b border-gray-50/50">
                  <TableCell className="font-medium py-4">
                    <div className="flex flex-col">
                      <span className="text-base font-bold text-gray-900">
                        {holding.symbol}
                      </span>
                      {holding.risk_tags.length > 0 && (
                        <span className="text-xs text-gray-600 uppercase tracking-wider mt-1 font-semibold bg-gray-100 px-2 py-0.5 rounded-full inline-block w-fit">
                          {holding.risk_tags[0]}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-bold text-gray-800 py-4">
                    {formatNumber(holding.qty, 0)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-semibold text-gray-700 py-4">
                    {formatCurrency(holding.last_price)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-bold text-gray-900 py-4">
                    {formatCurrency(holding.exposure)}
                  </TableCell>
                  <TableCell className="text-right py-4">
                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={cn(
                          "text-base tabular-nums font-black",
                          holding.pnl_abs > 0
                            ? 'text-profit'
                            : holding.pnl_abs < 0
                              ? 'text-loss'
                              : 'text-neutral'
                        )}
                      >
                        {formatCurrency(holding.pnl_abs)}
                      </span>
                      <span
                        className={cn(
                          "text-sm tabular-nums font-semibold",
                          holding.pnl_abs > 0 ? 'text-profit' : 'text-neutral'
                        )}
                      >
                        {formatPercent(holding.pnl_pct)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-bold text-gray-800 py-4">
                    {formatNumber(allocation, 1)}%
                  </TableCell>
                  <TableCell className="text-right py-4">
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        className="h-10 w-10 p-0 hover:bg-gradient-to-r hover:from-gray-100 hover:to-gray-200 rounded-lg transition-all duration-200 shadow-sm border border-gray-200"
                        aria-label={`Actions for ${holding.symbol}`}
                      >
                        <MoreHorizontal className="h-5 w-5 text-gray-600" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40">
                        {onBuy && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <DropdownMenuItem
                                onClick={() => onBuy(holding.symbol)}
                                className="cursor-pointer"
                              >
                                <TrendingUp className="mr-2 h-4 w-4 text-green-600" />
                                Buy
                              </DropdownMenuItem>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Add more shares of {holding.symbol}</p>
                            </TooltipContent>
                          </Tooltip>
                        )}
                        {onSell && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <DropdownMenuItem
                                onClick={() => onSell(holding.symbol)}
                                className="cursor-pointer"
                              >
                                <TrendingDown className="mr-2 h-4 w-4 text-red-600" />
                                Sell
                              </DropdownMenuItem>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Sell shares of {holding.symbol}</p>
                            </TooltipContent>
                          </Tooltip>
                        )}
                        {onEdit && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <DropdownMenuItem
                                onClick={() => onEdit(holding.symbol)}
                                className="cursor-pointer"
                              >
                                <Edit className="mr-2 h-4 w-4 text-blue-600" />
                                Edit
                              </DropdownMenuItem>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Modify position settings for {holding.symbol}</p>
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-5 border-t border-gray-200/40 bg-gradient-to-r from-gray-50/60 to-white/40">
          <div className="text-sm text-gray-700 font-bold">
            Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, sortedHoldings.length)} of {sortedHoldings.length} entries
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-5 py-2.5 text-sm font-bold border border-gray-300 rounded-xl hover:bg-white hover:shadow-professional disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-all duration-200 bg-white/80"
            >
              Previous
            </button>
            <span className="text-sm text-gray-800 font-black px-4 py-2.5 bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl border border-blue-200 shadow-sm">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="px-5 py-2.5 text-sm font-bold border border-gray-300 rounded-xl hover:bg-white hover:shadow-professional disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-all duration-200 bg-white/80"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredHoldings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 px-6 animate-scale-in">
          <div className="w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mb-6 shadow-professional">
            <Search className="w-10 h-10 text-gray-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-3">
            {searchTerm ? 'No matches found' : 'No holdings yet'}
          </h3>
          <p className="text-base text-gray-600 text-center max-w-md leading-relaxed">
            {searchTerm
              ? `No holdings match "${searchTerm}". Try adjusting your search terms.`
              : 'Start building your portfolio by making your first trade.'
            }
          </p>
        </div>
      )}
    </div>
  )
}
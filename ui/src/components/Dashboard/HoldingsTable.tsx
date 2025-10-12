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
        "cursor-pointer select-none hover:bg-gray-50/50 transition-colors",
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
                ? "text-gray-900"
                : "text-gray-300"
            )}
          />
          <ChevronDown
            className={cn(
              "w-3 h-3 -mt-1",
              sortField === field && sortDirection === 'desc'
                ? "text-gray-900"
                : "text-gray-300"
            )}
          />
        </div>
      </div>
    </TableHead>
  )

  return (
    <div className="flex flex-col gap-4 bg-white/80 backdrop-blur-sm border border-gray-200/50 card-shadow rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200/50">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">
          Holdings
        </div>
        <div className="text-11 text-gray-500">
          {filteredHoldings.length} {filteredHoldings.length === 1 ? 'position' : 'positions'}
        </div>
      </div>

      {/* Search */}
      <div className="px-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search symbols..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1) // Reset to first page when searching
            }}
            className="pl-10"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-gray-50/80 border-b border-gray-200/50">
            <TableRow>
              <SortableHeader field="symbol" className="text-left">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>Symbol</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Stock ticker symbol (e.g., AAPL, GOOGL)</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="qty" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>Quantity</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Number of shares you own</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="last_price" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>Current Price</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Latest market price per share</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="exposure" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>Market Value</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Total value of your position (price × quantity)</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="pnl_abs" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>P&L</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Profit and Loss in dollar amount</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <SortableHeader field="pnl_pct" className="text-right">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>P&L %</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Profit and Loss as a percentage</p>
                  </TooltipContent>
                </Tooltip>
              </SortableHeader>
              <TableHead className="w-10">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>Actions</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Quick actions for this position</p>
                  </TooltipContent>
                </Tooltip>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-gray-100">
            {paginatedHoldings.map((holding, index) => {
              const allocation = totalExposure > 0 ? (holding.exposure / totalExposure) * 100 : 0

              return (
                <TableRow key={index} className="hover:bg-gray-50/50 transition-colors">
                  <TableCell className="font-medium">
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
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {formatNumber(holding.qty, 0)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(holding.last_price)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {formatCurrency(holding.exposure)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={cn(
                          "text-sm tabular-nums font-semibold",
                          holding.pnl_abs > 0
                            ? 'text-success'
                            : holding.pnl_abs < 0
                              ? 'text-error'
                              : 'text-gray-500'
                        )}
                      >
                        {formatCurrency(holding.pnl_abs)}
                      </span>
                      <span
                        className={cn(
                          "text-11 tabular-nums",
                          holding.pnl_abs > 0 ? 'text-success-dark' : 'text-gray-500'
                        )}
                      >
                        {formatPercent(holding.pnl_pct)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {formatNumber(allocation, 1)}%
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        className="h-8 w-8 p-0 hover:bg-gray-100 rounded-md transition-colors"
                        aria-label={`Actions for ${holding.symbol}`}
                      >
                        <MoreHorizontal className="h-4 w-4 text-gray-500" />
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
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200/50">
          <div className="text-sm text-gray-500">
            Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, sortedHoldings.length)} of {sortedHoldings.length} entries
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredHoldings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 px-4">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
            <Search className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-sm text-gray-500 text-center">
            {searchTerm ? 'No holdings match your search.' : 'No holdings to display'}
          </p>
        </div>
      )}
    </div>
  )
}
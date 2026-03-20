import { useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, MoreHorizontal, Search } from 'lucide-react'

import type { Holding } from '@/types/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/utils/cn'
import { formatCurrency, formatNumber, formatPercent } from '@/utils/format'

interface HoldingsTableProps {
  holdings: Holding[]
  totalExposure: number
  onBuy?: (symbol: string) => void
  onSell?: (symbol: string) => void
  onEdit?: (symbol: string) => void
}

type SortField = 'symbol' | 'qty' | 'last_price' | 'exposure' | 'pnl_abs' | 'pnl_pct'
type SortDirection = 'asc' | 'desc'

const ITEMS_PER_PAGE = 10

export function HoldingsTable({
  holdings,
  totalExposure,
  onBuy,
  onSell,
  onEdit,
}: HoldingsTableProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState<SortField>('symbol')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [page, setPage] = useState(1)

  const filteredHoldings = useMemo(() => {
    return holdings.filter((holding) =>
      holding.symbol.toLowerCase().includes(searchTerm.toLowerCase().trim())
    )
  }, [holdings, searchTerm])

  const sortedHoldings = useMemo(() => {
    return [...filteredHoldings].sort((left, right) => {
      const direction = sortDirection === 'asc' ? 1 : -1
      const a = left[sortField]
      const b = right[sortField]

      if (typeof a === 'string' && typeof b === 'string') {
        return a.localeCompare(b) * direction
      }

      return ((Number(a) || 0) - (Number(b) || 0)) * direction
    })
  }, [filteredHoldings, sortDirection, sortField])

  const totalPages = Math.max(1, Math.ceil(sortedHoldings.length / ITEMS_PER_PAGE))

  const paginatedHoldings = useMemo(() => {
    const start = (page - 1) * ITEMS_PER_PAGE
    return sortedHoldings.slice(start, start + ITEMS_PER_PAGE)
  }, [page, sortedHoldings])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }

    setSortField(field)
    setSortDirection('asc')
  }

  const SortableHeader = ({
    field,
    label,
    align = 'left',
  }: {
    field: SortField
    label: string
    align?: 'left' | 'right'
  }) => {
    const active = sortField === field
    const Icon = active && sortDirection === 'desc' ? ChevronDown : ChevronUp

    return (
      <TableHead className={align === 'right' ? 'text-right' : ''}>
        <button
          type="button"
          onClick={() => toggleSort(field)}
          className={cn(
            'inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground',
            align === 'right' && 'ml-auto'
          )}
        >
          <span>{label}</span>
          <Icon className={cn('h-3.5 w-3.5', !active && 'opacity-30')} />
        </button>
      </TableHead>
    )
  }

  if (holdings.length === 0) {
    return (
      <div className="flex min-h-[18rem] flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 px-6 text-center">
        <div className="mb-3 rounded-full bg-muted p-3 text-muted-foreground">
          <Search className="h-5 w-5" />
        </div>
        <h3 className="text-base font-semibold text-foreground">No active positions</h3>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
          Open paper-trading positions will appear here with live mark-to-market values and unrealized P&amp;L.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground">Open positions</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {holdings.length} holding{holdings.length === 1 ? '' : 's'} · {formatCurrency(totalExposure)} deployed
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value)
              setPage(1)
            }}
            placeholder="Search symbol"
            className="pl-9"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <Table>
          <TableHeader className="bg-muted/35">
            <TableRow>
              <SortableHeader field="symbol" label="Symbol" />
              <SortableHeader field="qty" label="Qty" align="right" />
              <SortableHeader field="last_price" label="LTP" align="right" />
              <SortableHeader field="exposure" label="Market Value" align="right" />
              <SortableHeader field="pnl_abs" label="P&L" align="right" />
              <SortableHeader field="pnl_pct" label="P&L %" align="right" />
              <TableHead className="w-[52px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedHoldings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-sm text-muted-foreground">
                  No holdings match the current filter.
                </TableCell>
              </TableRow>
            ) : (
              paginatedHoldings.map((holding) => {
                const pnlPositive = holding.pnl_abs >= 0

                return (
                  <TableRow key={`${holding.symbol}-${holding.qty}`} className="hover:bg-muted/20">
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-semibold text-foreground">{holding.symbol}</span>
                        <span className="text-xs text-muted-foreground">
                          {totalExposure > 0 ? formatPercent((holding.exposure / totalExposure) * 100, 1) : '0.0%'} of deployed capital
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium text-foreground">
                      {formatNumber(holding.qty, 0)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {formatCurrency(holding.last_price)}
                    </TableCell>
                    <TableCell className="text-right font-medium text-foreground">
                      {formatCurrency(holding.exposure)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-semibold',
                        pnlPositive ? 'text-emerald-700' : 'text-rose-700'
                      )}
                    >
                      {formatCurrency(holding.pnl_abs)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-semibold',
                        pnlPositive ? 'text-emerald-700' : 'text-rose-700'
                      )}
                    >
                      {formatPercent(holding.pnl_pct, 2)}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {onBuy ? (
                            <DropdownMenuItem onClick={() => onBuy(holding.symbol)}>
                              Buy more
                            </DropdownMenuItem>
                          ) : null}
                          {onSell ? (
                            <DropdownMenuItem onClick={() => onSell(holding.symbol)}>
                              Close / sell
                            </DropdownMenuItem>
                          ) : null}
                          {onEdit ? (
                            <DropdownMenuItem onClick={() => onEdit(holding.symbol)}>
                              Edit risk settings
                            </DropdownMenuItem>
                          ) : null}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {paginatedHoldings.length === 0 ? 0 : (page - 1) * ITEMS_PER_PAGE + 1}-
          {Math.min(page * ITEMS_PER_PAGE, sortedHoldings.length)} of {sortedHoldings.length}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <div className="rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground">
            Page {page} of {totalPages}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page === totalPages}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

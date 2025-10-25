import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, ChevronsUpDown, TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { symbolsAPI } from '@/api/endpoints'
import type { SymbolData } from '@/types/api'

interface SymbolComboboxProps {
  value?: string
  onValueChange: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

const RECENT_SYMBOLS_KEY = 'recent-symbols'
const MAX_RECENT_SYMBOLS = 5

export function SymbolCombobox({
  value,
  onValueChange,
  placeholder = "Search symbols...",
  className,
  disabled = false
}: SymbolComboboxProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [recentSymbols, setRecentSymbols] = useState<SymbolData[]>([])

  // Fetch symbols from API
  const { data: symbolsData, isLoading } = useQuery({
    queryKey: ['symbols', searchQuery],
    queryFn: async () => {
      const response = await symbolsAPI.searchSymbols(searchQuery, 20)
      return response
    },
    staleTime: 60000, // 1 minute
    enabled: open, // Only fetch when dropdown is open
  })

  const symbols = symbolsData?.symbols || []

  // Load recent symbols from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(RECENT_SYMBOLS_KEY)
    if (stored) {
      try:
        setRecentSymbols(JSON.parse(stored))
      } catch (error) {
        console.error('Failed to parse recent symbols:', error)
      }
    }
  }, [])

  // Save recent symbols to localStorage
  const saveRecentSymbols = (symbols: SymbolData[]) => {
    localStorage.setItem(RECENT_SYMBOLS_KEY, JSON.stringify(symbols))
    setRecentSymbols(symbols)
  }

  // Add symbol to recent list
  const addToRecent = (symbol: SymbolData) => {
    const filtered = recentSymbols.filter(s => s.symbol !== symbol.symbol)
    const updated = [symbol, ...filtered].slice(0, MAX_RECENT_SYMBOLS)
    saveRecentSymbols(updated)
  }

  const selectedSymbol = symbols.find(symbol => symbol.symbol === value) ||
                         recentSymbols.find(symbol => symbol.symbol === value)

  const handleSelect = (symbolValue: string) => {
    const symbol = symbols.find(s => s.symbol === symbolValue) ||
                   recentSymbols.find(s => s.symbol === symbolValue)
    if (symbol) {
      addToRecent(symbol)
      onValueChange(symbolValue)
      setOpen(false)
    }
  }

  const formatPrice = (price: number) => `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const formatChange = (change: number, changePercent: number) => {
    const isPositive = change >= 0
    const sign = isPositive ? '+' : ''
    return `${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn("w-full justify-between", className)}
          disabled={disabled}
        >
          {selectedSymbol ? (
            <div className="flex items-center gap-2 truncate">
              <span className="font-medium">{selectedSymbol.symbol}</span>
              <span className="text-sm text-warmgray-500 truncate">{selectedSymbol.name}</span>
            </div>
          ) : (
            <span className="text-warmgray-500">{placeholder}</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[500px] p-0" align="start">
        <Command>
          <CommandInput
            placeholder="Search symbols..."
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
            {isLoading ? (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="h-6 w-6 animate-spin text-warmgray-400" />
                <span className="ml-2 text-sm text-warmgray-500">Loading symbols...</span>
              </div>
            ) : (
              <>
                <CommandEmpty>No symbols found.</CommandEmpty>

                {/* Recent Symbols */}
                {recentSymbols.length > 0 && !searchQuery && (
                  <CommandGroup heading="Recent">
                    {recentSymbols.map((symbol) => (
                      <CommandItem
                        key={`recent-${symbol.symbol}`}
                        value={symbol.symbol}
                        onSelect={() => handleSelect(symbol.symbol)}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              value === symbol.symbol ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <div>
                            <div className="font-medium">{symbol.symbol}</div>
                            <div className="text-sm text-warmgray-500 truncate max-w-[200px]">{symbol.name}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">{formatPrice(symbol.price)}</div>
                          <div className={cn(
                            "text-sm flex items-center gap-1",
                            symbol.change >= 0 ? "text-green-600" : "text-red-600"
                          )}>
                            {symbol.change >= 0 ? (
                              <TrendingUp className="h-3 w-3" />
                            ) : (
                              <TrendingDown className="h-3 w-3" />
                            )}
                            {formatChange(symbol.change, symbol.changePercent)}
                          </div>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                )}

                {/* Search Results */}
                <CommandGroup heading={searchQuery ? "Search Results" : "Popular Symbols"}>
                  {symbols.map((symbol) => (
                    <CommandItem
                      key={symbol.symbol}
                      value={symbol.symbol}
                      onSelect={() => handleSelect(symbol.symbol)}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            value === symbol.symbol ? "opacity-100" : "opacity-0"
                          )}
                        />
                        <div>
                          <div className="font-medium">{symbol.symbol}</div>
                          <div className="text-sm text-warmgray-500 truncate max-w-[200px]">{symbol.name}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">{formatPrice(symbol.price)}</div>
                        <div className={cn(
                          "text-sm flex items-center gap-1",
                          symbol.change >= 0 ? "text-emerald-600" : "text-rose-600"
                        )}>
                          {symbol.change >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {formatChange(symbol.change, symbol.changePercent)}
                        </div>
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

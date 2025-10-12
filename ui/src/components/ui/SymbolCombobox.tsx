import { useState, useEffect, useMemo } from 'react'
import { Check, ChevronsUpDown, TrendingUp, TrendingDown } from 'lucide-react'
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

// Mock data for demonstration - in real app this would come from API
const mockSymbols: SymbolData[] = [
  { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', price: 2456.75, change: 23.45, changePercent: 0.96 },
  { symbol: 'TCS', name: 'Tata Consultancy Services Ltd', price: 3876.20, change: -12.30, changePercent: -0.32 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', price: 1654.80, change: 8.90, changePercent: 0.54 },
  { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', price: 987.65, change: -5.40, changePercent: -0.54 },
  { symbol: 'INFY', name: 'Infosys Ltd', price: 1432.10, change: 15.75, changePercent: 1.11 },
  { symbol: 'ITC', name: 'ITC Ltd', price: 432.85, change: 2.15, changePercent: 0.50 },
  { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank Ltd', price: 1789.45, change: -7.20, changePercent: -0.40 },
  { symbol: 'LT', name: 'Larsen & Toubro Ltd', price: 3456.90, change: 28.60, changePercent: 0.84 },
  { symbol: 'MARUTI', name: 'Maruti Suzuki India Ltd', price: 12345.60, change: -45.30, changePercent: -0.37 },
  { symbol: 'WIPRO', name: 'Wipro Ltd', price: 567.80, change: 3.25, changePercent: 0.58 },
]

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

  // Load recent symbols from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(RECENT_SYMBOLS_KEY)
    if (stored) {
      try {
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

  // Filter symbols based on search query
  const filteredSymbols = useMemo(() => {
    if (!searchQuery) return mockSymbols.slice(0, 10) // Show first 10 when no search

    const query = searchQuery.toLowerCase()
    return mockSymbols.filter(symbol =>
      symbol.symbol.toLowerCase().includes(query) ||
      symbol.name.toLowerCase().includes(query)
    )
  }, [searchQuery])

  const selectedSymbol = mockSymbols.find(symbol => symbol.symbol === value)

  const handleSelect = (symbolValue: string) => {
    const symbol = mockSymbols.find(s => s.symbol === symbolValue)
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
              <span className="text-sm text-gray-500 truncate">{selectedSymbol.name}</span>
            </div>
          ) : (
            <span className="text-gray-500">{placeholder}</span>
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
                        <div className="text-sm text-gray-500 truncate max-w-[200px]">{symbol.name}</div>
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
              {filteredSymbols.map((symbol) => (
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
                      <div className="text-sm text-gray-500 truncate max-w-[200px]">{symbol.name}</div>
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
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
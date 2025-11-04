import { memo } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { BarChart3 } from 'lucide-react'

interface SymbolSelectorProps {
  selectedSymbol: string
  portfolioSymbols: string[]
  onSymbolChange: (symbol: string) => void
  onRefresh?: () => void
  isLoading?: boolean
}

export const SymbolSelector = memo<SymbolSelectorProps>(({
  selectedSymbol,
  portfolioSymbols,
  onSymbolChange,
  onRefresh,
  isLoading = false,
}) => {
  return (
    <Card className="shadow-lg border-0 bg-white/80 dark:bg-warmgray-800/80 backdrop-blur-sm">
      <CardContent className="p-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
          <div className="flex-1 min-w-0">
            <label
              htmlFor="symbol-select"
              className="block text-sm font-semibold text-warmgray-700 dark:text-warmgray-300 mb-2"
            >
              Select Portfolio Stock
            </label>
            <Select
              value={selectedSymbol}
              onValueChange={onSymbolChange}
              disabled={isLoading}
            >
              <SelectTrigger className="w-full bg-white dark:bg-warmgray-800 border-warmgray-300 dark:border-warmgray-600">
                <SelectValue placeholder={isLoading ? 'Loading stocks...' : 'Choose a stock to analyze...'} />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-warmgray-800 border-warmgray-300 dark:border-warmgray-600">
                {portfolioSymbols.map((symbol) => (
                  <SelectItem
                    key={symbol}
                    value={symbol}
                    className="text-warmgray-900 dark:text-warmgray-100 hover:bg-warmgray-100 dark:hover:bg-warmgray-700 focus:bg-warmgray-100 dark:focus:bg-warmgray-700"
                  >
                    {symbol}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-3">
            {onRefresh && (
              <Button
                variant="outline"
                onClick={onRefresh}
                disabled={isLoading}
                className="flex items-center gap-2"
                aria-label="Refresh data"
              >
                <BarChart3 className="w-4 h-4" />
                Refresh
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
})

SymbolSelector.displayName = 'SymbolSelector'
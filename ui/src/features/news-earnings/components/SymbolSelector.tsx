import { memo } from 'react'
import { Select } from '@/components/ui/Select'
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
              id="symbol-select"
              value={selectedSymbol}
              onChange={(e) => onSymbolChange(e.target.value)}
              disabled={isLoading}
              className="w-full"
            >
              <option value="">
                {isLoading ? 'Loading stocks...' : 'Choose a stock to analyze...'}
              </option>
              {portfolioSymbols.map((symbol) => (
                <option key={symbol} value={symbol}>
                  {symbol}
                </option>
              ))}
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
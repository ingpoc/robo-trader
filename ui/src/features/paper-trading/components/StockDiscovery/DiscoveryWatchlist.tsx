/**
 * Discovery Watchlist Component
 * Displays stocks discovered by the AI
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/Table'
import {
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  Filter
} from 'lucide-react'
import type {
  DiscoveryWatchlistResponse,
  DiscoveryWatchlistItem
} from './types'

interface DiscoveryWatchlistProps {
  watchlist: DiscoveryWatchlistResponse | null
  isLoading: boolean
  onRefresh: (limit?: number) => Promise<void>
}

export const DiscoveryWatchlist: React.FC<DiscoveryWatchlistProps> = ({
  watchlist,
  isLoading,
  onRefresh
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSector, setSelectedSector] = useState<string>('all')
  const [selectedRecommendation, setSelectedRecommendation] = useState<string>('all')

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'BUY':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
      case 'SELL':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
    }
  }

  const getRecommendationIcon = (recommendation: string) => {
    switch (recommendation) {
      case 'BUY':
        return <TrendingUp className="w-4 h-4" />
      case 'SELL':
        return <TrendingDown className="w-4 h-4" />
      default:
        return <Minus className="w-4 h-4" />
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600 dark:text-green-400'
    if (score >= 0.5) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const filteredWatchlist = watchlist?.watchlist.filter(stock => {
    const matchesSearch = stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         stock.company_name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesSector = selectedSector === 'all' || stock.sector === selectedSector
    const matchesRecommendation = selectedRecommendation === 'all' ||
                                 stock.recommendation === selectedRecommendation
    return matchesSearch && matchesSector && matchesRecommendation
  }) || []

  const sectors = [...new Set(watchlist?.watchlist.map(s => s.sector) || [])]

  const handleRefresh = () => {
    onRefresh(100) // Load more items on refresh
  }

  if (isLoading && !watchlist) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  if (!watchlist || watchlist.watchlist.length === 0) {
    return (
      <Card className="p-6 text-center">
        <div className="text-gray-500 dark:text-gray-400">
          <Search className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <h3 className="text-lg font-medium mb-1">No stocks discovered yet</h3>
          <p className="text-sm mb-4">Run a discovery session to find potential trading opportunities</p>
          <Button onClick={handleRefresh} variant="outline">
            Trigger Discovery
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">
          Discovery Watchlist ({filteredWatchlist.length} stocks)
        </h3>
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={isLoading}
        >
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search stocks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <select
          value={selectedSector}
          onChange={(e) => setSelectedSector(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Sectors</option>
          {sectors.map(sector => (
            <option key={sector} value={sector}>{sector}</option>
          ))}
        </select>
        <select
          value={selectedRecommendation}
          onChange={(e) => setSelectedRecommendation(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Recommendations</option>
          <option value="BUY">Buy</option>
          <option value="HOLD">Hold</option>
          <option value="SELL">Sell</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Stock</TableHead>
              <TableHead>Sector</TableHead>
              <TableHead>Recommendation</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Discovered</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredWatchlist.map((stock) => (
              <TableRow key={stock.symbol}>
                <TableCell>
                  <div>
                    <div className="font-medium">{stock.symbol}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {stock.company_name}
                    </div>
                  </div>
                </TableCell>
                <TableCell>{stock.sector}</TableCell>
                <TableCell>
                  <Badge
                    className={`flex items-center gap-1 w-fit ${getRecommendationColor(stock.recommendation)}`}
                  >
                    {getRecommendationIcon(stock.recommendation)}
                    {stock.recommendation}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${getConfidenceColor(stock.confidence_score)}`}>
                      {(stock.confidence_score * 100).toFixed(0)}%
                    </span>
                    <div className="w-16 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          stock.confidence_score >= 0.7 ? 'bg-green-500' :
                          stock.confidence_score >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${stock.confidence_score * 100}%` }}
                      />
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {stock.current_price ? (
                    <span>₹{stock.current_price.toFixed(2)}</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={stock.status === 'ACTIVE' ? 'default' : 'secondary'}
                  >
                    {stock.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {new Date(stock.discovery_date).toLocaleDateString()}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {filteredWatchlist.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Filter className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No stocks match your filters</p>
        </div>
      )}
    </Card>
  )
}
export interface SymbolData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume?: number
  marketCap?: number
}

export interface SymbolSearchResult {
  symbols: SymbolData[]
  total: number
}
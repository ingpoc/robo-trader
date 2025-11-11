/**
 * Real-Time Trading Hook
 * Manages WebSocket connections and real-time trading data
 */

import { useState, useEffect, useRef, useCallback } from 'react'

interface RealTimeQuote {
  symbol: string
  last_price: number
  change: number
  change_percent: number
  volume: number
  timestamp: string
}

interface RealTimePosition {
  symbol: string
  quantity: number
  average_price: number
  last_price: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  pnl_percent: number
  updated_at: string
}

interface RealTimeTradingState {
  isConnected: boolean
  quotes: Record<string, RealTimeQuote>
  positions: Record<string, RealTimePosition>
  lastUpdate: string | null
  error: string | null
}

interface UseRealTimeTradingOptions {
  accountId?: string
  symbols?: string[]
  autoConnect?: boolean
  reconnectInterval?: number
}

export const useRealTimeTrading = (options: UseRealTimeTradingOptions = {}) => {
  const {
    accountId = 'paper_swing_main',
    symbols = [],
    autoConnect = true,
    reconnectInterval = 5000
  } = options

  const [state, setState] = useState<RealTimeTradingState>({
    isConnected: false,
    quotes: {},
    positions: {},
    lastUpdate: null,
    error: null
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const connectWebSocket = useCallback(() => {
    try {
      // Create WebSocket connection
      const wsUrl = `ws://localhost:8000/ws/trading?account_id=${accountId}`
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected for real-time trading')
        setState(prev => ({
          ...prev,
          isConnected: true,
          error: null
        }))

        // Subscribe to symbols
        if (symbols.length > 0) {
          wsRef.current?.send(JSON.stringify({
            type: 'subscribe',
            data: { symbols }
          }))
        }

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          switch (message.type) {
            case 'connection_established':
              setState(prev => ({ ...prev, isConnected: true }))
              break

            case 'quote_update':
              const quote = message.data
              setState(prev => ({
                ...prev,
                quotes: {
                  ...prev.quotes,
                  [quote.symbol]: quote
                },
                lastUpdate: new Date().toISOString()
              }))
              break

            case 'position_update':
              const position = message.data
              setState(prev => ({
                ...prev,
                positions: {
                  ...prev.positions,
                  [`${position.symbol}_${position.product_type}`]: position
                },
                lastUpdate: new Date().toISOString()
              }))
              break

            case 'portfolio_update':
              // Handle portfolio-level updates
              setState(prev => ({
                ...prev,
                lastUpdate: new Date().toISOString()
              }))
              break

            case 'pong':
              // Heartbeat response
              break

            case 'error':
              setState(prev => ({
                ...prev,
                error: message.data.message
              }))
              break

            default:
              console.log('Unknown message type:', message.type)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
          setState(prev => ({
            ...prev,
            error: 'Failed to parse real-time data'
          }))
        }
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setState(prev => ({
          ...prev,
          isConnected: false
        }))

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current)
          heartbeatIntervalRef.current = null
        }

        // Attempt reconnection
        if (autoConnect) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...')
            connectWebSocket()
          }, reconnectInterval)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState(prev => ({
          ...prev,
          error: 'WebSocket connection error'
        }))
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setState(prev => ({
        ...prev,
        error: 'Failed to connect to real-time data'
      }))
    }
  }, [accountId, symbols, autoConnect, reconnectInterval])

  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setState(prev => ({
      ...prev,
      isConnected: false
    }))
  }, [])

  const subscribeToSymbols = useCallback((newSymbols: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        data: { symbols: newSymbols }
      }))
    }
  }, [])

  const unsubscribeFromSymbols = useCallback((removeSymbols: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        data: { symbols: removeSymbols }
      }))
    }
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && !wsRef.current) {
      connectWebSocket()
    }

    return () => {
      disconnectWebSocket()
    }
  }, [autoConnect, connectWebSocket, disconnectWebSocket])

  // Reconnect when symbols change
  useEffect(() => {
    if (state.isConnected && symbols.length > 0) {
      subscribeToSymbols(symbols)
    }
  }, [symbols, state.isConnected, subscribeToSymbols])

  const getQuote = useCallback((symbol: string) => {
    return state.quotes[symbol] || null
  }, [state.quotes])

  const getPosition = useCallback((symbol: string, productType: string = 'CNC') => {
    return state.positions[`${symbol}_${productType}`] || null
  }, [state.positions])

  const getAllQuotes = useCallback(() => {
    return Object.values(state.quotes)
  }, [state.quotes])

  const getAllPositions = useCallback(() => {
    return Object.values(state.positions)
  }, [state.positions])

  const executeTrade = useCallback(async (tradeData: {
    symbol: string
    action: 'BUY' | 'SELL'
    quantity: number
    order_type?: string
    product?: string
    price?: number
  }) => {
    try {
      const response = await fetch('/api/mcp/execute-trade', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tool: tradeData.action === 'BUY' ? 'execute_buy_order' : 'execute_sell_order',
          arguments: {
            symbol: tradeData.symbol,
            quantity: tradeData.quantity,
            order_type: tradeData.order_type || 'MARKET',
            product: tradeData.product || 'CNC',
            price: tradeData.price,
            account_id: accountId
          }
        })
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || 'Trade execution failed')
      }

      return result
    } catch (error) {
      console.error('Trade execution error:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Trade execution failed'
      }))
      throw error
    }
  }, [accountId])

  const closePosition = useCallback(async (symbol: string, quantity?: number) => {
    try {
      const response = await fetch('/api/mcp/close-position', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tool: 'close_position',
          arguments: {
            symbol,
            quantity,
            account_id: accountId
          }
        })
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || 'Position close failed')
      }

      return result
    } catch (error) {
      console.error('Position close error:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Position close failed'
      }))
      throw error
    }
  }, [accountId])

  return {
    // State
    isConnected: state.isConnected,
    quotes: state.quotes,
    positions: state.positions,
    lastUpdate: state.lastUpdate,
    error: state.error,

    // Actions
    connect: connectWebSocket,
    disconnect: disconnectWebSocket,
    subscribeToSymbols,
    unsubscribeFromSymbols,

    // Data getters
    getQuote,
    getPosition,
    getAllQuotes,
    getAllPositions,

    // Trading actions
    executeTrade,
    closePosition
  }
}

export type UseRealTimeTradingReturn = ReturnType<typeof useRealTimeTrading>
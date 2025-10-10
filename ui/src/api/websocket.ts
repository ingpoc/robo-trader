import type { DashboardData } from '@/types/api'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

type WebSocketCallback = (data: DashboardData) => void
type ErrorCallback = (error: Event) => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private callbacks: Set<WebSocketCallback> = new Set()
  private errorCallbacks: Set<ErrorCallback> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private reconnectTimer: number | null = null
  private shouldReconnect = true
  private isConnecting = false

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(WS_URL)

      this.ws.onopen = () => {
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.reconnectDelay = 1000
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as DashboardData
          this.callbacks.forEach((callback) => callback(data))
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        this.isConnecting = false
        this.errorCallbacks.forEach((callback) => callback(error))
      }

      this.ws.onclose = () => {
        this.isConnecting = false
        this.ws = null
        this.scheduleReconnect()
      }
    } catch (error) {
      this.isConnecting = false
      console.error('Failed to create WebSocket connection:', error)
      this.scheduleReconnect()
    }
  }

  private cleanup() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect) return

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.cleanup()

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000
    )

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  subscribe(callback: WebSocketCallback) {
    this.callbacks.add(callback)
    return () => this.callbacks.delete(callback)
  }

  onError(callback: ErrorCallback) {
    this.errorCallbacks.add(callback)
    return () => this.errorCallbacks.delete(callback)
  }

  disconnect() {
    this.shouldReconnect = false
    this.cleanup()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.callbacks.clear()
    this.errorCallbacks.clear()
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsClient = new WebSocketClient()

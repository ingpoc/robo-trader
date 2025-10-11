import type { DashboardData } from '@/types/api'

const WS_URL = 'ws://localhost:8000/ws'

type WebSocketCallback = (data: DashboardData) => void
type ErrorCallback = (error: Event) => void
type ConnectionCallback = () => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private callbacks: Set<WebSocketCallback> = new Set()
  private errorCallbacks: Set<ErrorCallback> = new Set()
  private connectionCallbacks: Set<ConnectionCallback> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private reconnectTimer: number | null = null
  private shouldReconnect = true
  private isConnecting = false
  private connectionId: string

  constructor() {
    this.connectionId = `ws_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(WS_URL)

      // Store bound handlers to ensure proper cleanup
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onerror = this.handleError.bind(this)
      this.ws.onclose = this.handleClose.bind(this)

    } catch (error) {
      this.isConnecting = false
      console.error(`[${this.connectionId}] Failed to create WebSocket connection:`, error)
      this.scheduleReconnect()
    }
  }

  private handleOpen = () => {
    this.isConnecting = false
    this.reconnectAttempts = 0
    this.reconnectDelay = 1000
    // Notify connection callbacks that connection is successful
    this.connectionCallbacks.forEach((callback) => callback())
  }

  private handleMessage = (event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data)
      // Any message received means we're connected - pass data to callbacks
      this.callbacks.forEach((callback) => callback(message as DashboardData))
    } catch (error) {
      console.error(`Failed to parse WebSocket message:`, error)
    }
  }

  private handleError = (error: Event) => {
    console.warn(`[${this.connectionId}] WebSocket connection error:`, error)
    this.isConnecting = false
    // Only notify error callbacks on first attempt to avoid spam
    if (this.reconnectAttempts === 0) {
      this.errorCallbacks.forEach((callback) => callback(error))
    }
  }

  private handleClose = (event: CloseEvent) => {
    const wasClean = event.wasClean
    const code = event.code
    const reason = event.reason

    console.log(`[${this.connectionId}] WebSocket closed: clean=${wasClean}, code=${code}, reason="${reason}"`)

    this.isConnecting = false
    this.ws = null

    // Only reconnect on unexpected closures
    // 1000 = normal closure, 1001 = going away, 1005 = no status code
    if (!wasClean || (code !== 1000 && code !== 1001)) {
      console.log(`[${this.connectionId}] Unexpected closure, scheduling reconnect`)
      this.scheduleReconnect()
    } else {
      console.log(`[${this.connectionId}] Clean closure, not reconnecting`)
    }
  }

  private cleanup() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // Clear all event handlers to prevent memory leaks
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onerror = null
      this.ws.onclose = null
    }
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect) {
      console.log(`[${this.connectionId}] Reconnection disabled`)
      return
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`[${this.connectionId}] Max reconnection attempts (${this.maxReconnectAttempts}) reached`)
      return
    }

    this.cleanup()

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds
    )

    console.log(`[${this.connectionId}] Scheduling reconnect attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts} in ${delay}ms`)

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

  onConnect(callback: ConnectionCallback) {
    this.connectionCallbacks.add(callback)
    return () => this.connectionCallbacks.delete(callback)
  }

  disconnect() {
    console.log(`[${this.connectionId}] Disconnecting WebSocket client`)
    this.shouldReconnect = false
    this.cleanup()

    if (this.ws) {
      try {
        // Only close if not already closed/closing
        if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
          this.ws.close(1000, 'Client disconnect') // 1000 = normal closure
        }
      } catch (error) {
        console.warn(`[${this.connectionId}] Error closing WebSocket:`, error)
      }
      this.ws = null
    }

    this.callbacks.clear()
    this.errorCallbacks.clear()
    this.connectionCallbacks.clear()
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected'
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'closed'
      default: return 'unknown'
    }
  }

  getConnectionInfo(): {
    id: string
    state: string
    reconnectAttempts: number
    isReconnecting: boolean
  } {
    return {
      id: this.connectionId,
      state: this.getConnectionState(),
      reconnectAttempts: this.reconnectAttempts,
      isReconnecting: this.shouldReconnect && !this.isConnected()
    }
  }
}

export const wsClient = new WebSocketClient()

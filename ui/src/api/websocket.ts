import type { DashboardData } from '@/types/api'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

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
  private hasConnected = false  // Track if we've ever connected
  private connectionId: string
  private isChromium: boolean
  private lastProcessedTime: number = 0
  private throttleInterval: number
  private messageQueue: any[] = []  // Queue messages when not connected

  constructor() {
    this.connectionId = `ws_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    this.isChromium = this.detectChromium()
    this.throttleInterval = this.isChromium ? 5000 : 1500 // 5s for Chromium, 1.5s for others
  }

  connect() {
    // Check if we already have a healthy connection
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log(`[${this.connectionId}] WebSocket already connected`)
      return
    }

    // Prevent multiple concurrent connection attempts
    if (this.isConnecting) {
      console.log(`[${this.connectionId}] WebSocket connection already in progress`)
      return
    }

    // Force cleanup of any existing connection
    this.forceCleanup()

    this.isConnecting = true
    console.log(`[${this.connectionId}] Attempting to connect to ${WS_URL}`)

    try {
      this.ws = new WebSocket(WS_URL)

      // Store bound handlers to ensure proper cleanup
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onerror = this.handleError.bind(this)
      this.ws.onclose = this.handleClose.bind(this)

      // Set connection timeout
      setTimeout(() => {
        if (this.isConnecting && this.ws?.readyState === WebSocket.CONNECTING) {
          console.warn(`[${this.connectionId}] WebSocket connection timeout`)
          this.ws.close()
        }
      }, 10000) // 10 second timeout

    } catch (error) {
      this.isConnecting = false
      console.error(`[${this.connectionId}] Failed to create WebSocket connection:`, error)
      this.scheduleReconnect()
    }
  }

  private forceCleanup() {
    // Clean up any existing connection forcefully
    if (this.ws) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[${this.connectionId}] Force cleaning up existing WebSocket connection`)
      }
      try {
        // Remove all event listeners first
        this.ws.onopen = null
        this.ws.onmessage = null
        this.ws.onerror = null
        this.ws.onclose = null

        // Close the connection
        if (this.ws.readyState !== WebSocket.CLOSED) {
          this.ws.close(1000, 'Force cleanup')
        }
      } catch (error) {
        console.warn(`[${this.connectionId}] Error during force cleanup:`, error)
      }
      this.ws = null
    }

    // Reset state
    this.isConnecting = false
    this.messageQueue.length = 0
  }

  private handleOpen = () => {
    this.isConnecting = false
    this.hasConnected = true
    this.reconnectAttempts = 0
    this.reconnectDelay = 1000

    if (process.env.NODE_ENV === 'development') {
      console.log(`[${this.connectionId}] WebSocket connected successfully`)
    }

    // Notify connection callbacks that connection is successful
    this.connectionCallbacks.forEach((callback) => callback())

    // Process any queued messages
    if (this.messageQueue.length > 0) {
      console.log(`[${this.connectionId}] Processing ${this.messageQueue.length} queued messages`)
      const queuedMessages = this.messageQueue.splice(0) // Clear queue
      queuedMessages.forEach(message => {
        this.callbacks.forEach((callback) => callback(message))
      })
    }
  }

  private handleMessage = (event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data)

      // Log received message for debugging (reduced verbosity)
      if (message.type !== 'system_health_update' || process.env.NODE_ENV === 'development') {
        console.log(`[${this.connectionId}] Received WebSocket message:`, message.type)
      }

      // Validate message structure
      if (typeof message === 'object' && message !== null) {
        // Apply throttling for Chromium browsers to prevent excessive processing
        const now = Date.now()
        if (this.isChromium && now - this.lastProcessedTime < this.throttleInterval) {
          console.log(`[${this.connectionId}] Throttling message processing for Chromium browser (last processed ${now - this.lastProcessedTime}ms ago)`)
          return
        }

        this.lastProcessedTime = now

        // If we have callbacks, process immediately
        if (this.callbacks.size > 0) {
          this.callbacks.forEach((callback) => callback(message as DashboardData))
        } else {
          // Queue messages until callbacks are registered
          if (this.messageQueue.length < 100) { // Prevent unlimited queue growth
            this.messageQueue.push(message)
          }
        }
      } else {
        console.warn(`[${this.connectionId}] Received invalid message format:`, message)
      }
    } catch (error) {
      console.error(`[${this.connectionId}] Failed to parse WebSocket message:`, error, 'Raw data:', event.data)
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

    // Clear all callbacks and message queue
    this.callbacks.clear()
    this.errorCallbacks.clear()
    this.connectionCallbacks.clear()
    this.messageQueue.length = 0  // Clear message queue
    this.hasConnected = false
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

  private detectChromium(): boolean {
    const userAgent = navigator.userAgent
    // Check for Chromium-based browsers (Chrome, Edge, Opera, etc.)
    // This includes browsers that use Chromium engine, including Comet
    return /Chrome|Chromium|Edg|OPR/.test(userAgent) && !/Safari/.test(userAgent)
  }

  getConnectionInfo(): {
    id: string
    state: string
    reconnectAttempts: number
    isReconnecting: boolean
    isChromium: boolean
    throttleInterval: number
    hasConnected: boolean
    callbackCount: number
    queuedMessages: number
  } {
    return {
      id: this.connectionId,
      state: this.getConnectionState(),
      reconnectAttempts: this.reconnectAttempts,
      isReconnecting: this.shouldReconnect && !this.isConnected(),
      isChromium: this.isChromium,
      throttleInterval: this.throttleInterval,
      hasConnected: this.hasConnected,
      callbackCount: this.callbacks.size,
      queuedMessages: this.messageQueue.length
    }
  }
}

export const wsClient = new WebSocketClient()

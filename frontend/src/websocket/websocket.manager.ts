/**
 * WebSocket Manager
 * ================
 * Production-grade WebSocket manager with:
 * - Auto reconnection with exponential backoff
 * - Heartbeat system
 * - Connection state tracking
 * - Message queueing for offline recovery
 * - Event batching and deduplication
 * - Reconnection replay
 */

import { io, Socket } from 'socket.io-client'
import type {
  ConnectionStatus,
  WebSocketState,
  ReconnectOptions,
  HeartbeatOptions,
  MarketTickPayload,
  OrderUpdatePayload,
  PositionUpdatePayload,
  PnLUpdatePayload,
  AISignalPayload,
  NotificationPayload,
  StrategyUpdatePayload,
  MarketStatusPayload,
} from './websocket.types'

type EventHandler<T = unknown> = (data: T) => void

interface QueuedMessage {
  event: string
  data?: unknown
  timestamp: number
}

export class WebSocketManager {
  private socket: Socket | null = null
  private state: WebSocketState
  private reconnectOptions: ReconnectOptions
  private heartbeatOptions: HeartbeatOptions
  private eventHandlers: Map<string, Set<EventHandler>> = new Map()
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null
  private messageQueue: QueuedMessage[] = []
  private processedMessageIds: Set<string> = new Set()
  private lastReconnectTime: number = 0
  private currentToken: string | null = null

  private readonly WS_URL: string
  private readonly MAX_QUEUE_SIZE = 100
  private readonly MESSAGE_DEDUP_WINDOW = 5000

  constructor() {
    this.WS_URL = this.getWebSocketUrl()

    this.state = {
      status: 'disconnected',
      connectedAt: null,
      lastHeartbeat: null,
      reconnectAttempts: 0,
      error: null,
      subscribedSymbols: new Set(),
      subscribedStrategies: new Set(),
    }

    this.reconnectOptions = {
      maxAttempts: 10,
      initialDelay: 1000,
      maxDelay: 30000,
      backoffMultiplier: 1.5,
    }

    this.heartbeatOptions = {
      interval: 30000,
      timeout: 10000,
    }

    this.setupOfflineDetection()
  }

  private getWebSocketUrl(): string {
    const envUrl = import.meta.env.VITE_WS_URL
    if (envUrl) return envUrl

    const isProduction = import.meta.env.PROD
    if (isProduction) {
      return window.location.origin.replace(/^http/, 'ws')
    }

    return 'http://localhost:5000'
  }

  private setupOfflineDetection(): void {
    if (typeof window === 'undefined') return

    window.addEventListener('online', () => {
      console.log('[WS] Network online - attempting reconnection')
      if (this.currentToken && this.state.status !== 'connected') {
        this.handleReconnect()
      }
    })

    window.addEventListener('offline', () => {
      console.log('[WS] Network offline')
      this.setState({ status: 'disconnected' })
      this.stopHeartbeat()
    })
  }

  connect(token?: string): void {
    if (token) {
      this.currentToken = token
    }

    if (this.socket?.connected) {
      console.log('[WS] Already connected')
      return
    }

    if (this.state.status === 'connecting') {
      console.log('[WS] Connection in progress')
      return
    }

    this.setState({ status: 'connecting', error: null })

    this.socket = io(this.WS_URL, {
      transports: ['websocket', 'polling'],
      auth: { token: this.currentToken || '' },
      reconnection: false,
      reconnectionAttempts: 0,
      timeout: 20000,
      forceNew: true,
      withCredentials: true,
    })

    this.setupEventListeners()
  }

  private setupEventListeners(): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('[WS] Connected')
      this.setState({
        status: 'connected',
        connectedAt: new Date().toISOString(),
        reconnectAttempts: 0,
        error: null,
      })
      this.startHeartbeat()
      this.emitStateEvent('connected', { connected: true })
      this.flushMessageQueue()
      this.resubscribe()
    })

    this.socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason)
      this.setState({ status: 'disconnected' })
      this.stopHeartbeat()
      this.emitStateEvent('disconnected', { reason })

      if (reason !== 'io client disconnect' && this.currentToken) {
        this.scheduleReconnect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('[WS] Connection error:', error.message)
      this.setState({
        status: 'error',
        error: error.message,
      })
      this.scheduleReconnect()
    })

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`[WS] Reconnected after ${attemptNumber} attempts`)
      this.setState({ status: 'connected', reconnectAttempts: 0 })
      this.resubscribe()
      this.emitStateEvent('reconnected', { attempts: attemptNumber })
    })

    this.socket.on('reconnect_failed', () => {
      console.error('[WS] Reconnection failed')
      this.setState({
        status: 'error',
        error: 'Failed to reconnect after max attempts',
      })
      this.emitStateEvent('reconnect_failed', { attempts: this.state.reconnectAttempts })
    })

    this.setupMarketHandlers()
    this.setupTradingHandlers()
    this.setupNotificationHandlers()
    this.setupSystemHandlers()
  }

  private setupMarketHandlers(): void {
    if (!this.socket) return

    this.socket.on('market_tick', (data: MarketTickPayload) => {
      this.emitWithDedup(`market_tick_${data.symbol}`, data, () => {
        this.emit('market_tick', data)
      })
    })

    this.socket.on('market:tick', (data: MarketTickPayload) => {
      this.emitWithDedup(`market:tick_${data.symbol}`, data, () => {
        this.emit('market:tick', data)
      })
    })

    this.socket.on('market:depth', (data: unknown) => {
      this.emit('market:depth', data)
    })

    this.socket.on('market:candle', (data: unknown) => {
      this.emit('market:candle', data)
    })

    this.socket.on('index:nifty', (data: { value: number; change: number }) => {
      this.emit('index_update', { index: 'NIFTY', ...data })
    })

    this.socket.on('index:sensex', (data: { value: number; change: number }) => {
      this.emit('index_update', { index: 'SENSEX', ...data })
    })

    this.socket.on('index:banknifty', (data: { value: number; change: number }) => {
      this.emit('index_update', { index: 'BANKNIFTY', ...data })
    })

    this.socket.on('market_status', (data: MarketStatusPayload) => {
      this.emit('market_status', data)
    })

    this.socket.on('ai_signal', (data: AISignalPayload) => {
      this.emit('ai_signal', data)
    })
  }

  private setupTradingHandlers(): void {
    if (!this.socket) return

    this.socket.on('order_update', (data: OrderUpdatePayload) => {
      this.emitWithDedup(`order_${data.order_id}`, data, () => {
        this.emit('order_update', data)
      })
    })

    this.socket.on('order_created', (data: OrderUpdatePayload) => {
      this.emit('order_created', data)
    })

    this.socket.on('order_executed', (data: OrderUpdatePayload) => {
      this.emit('order_executed', data)
    })

    this.socket.on('order_cancelled', (data: OrderUpdatePayload) => {
      this.emit('order_cancelled', data)
    })

    this.socket.on('position_update', (data: PositionUpdatePayload) => {
      this.emitWithDedup(`position_${data.position_id}`, data, () => {
        this.emit('position_update', data)
      })
    })

    this.socket.on('position_opened', (data: PositionUpdatePayload) => {
      this.emit('position_opened', data)
    })

    this.socket.on('position_closed', (data: PositionUpdatePayload) => {
      this.emit('position_closed', data)
    })

    this.socket.on('pnl_update', (data: PnLUpdatePayload) => {
      this.emit('pnl_update', data)
    })

    this.socket.on('trade_executed', (data: unknown) => {
      this.emit('trade_executed', data)
    })
  }

  private setupNotificationHandlers(): void {
    if (!this.socket) return

    this.socket.on('notification', (data: NotificationPayload) => {
      this.emit('notification', data)
    })

    this.socket.on('strategy_update', (data: StrategyUpdatePayload) => {
      this.emit('strategy_update', data)
    })

    this.socket.on('signal:new', (data: AISignalPayload) => {
      this.emit('signal_new', data)
    })
  }

  private setupSystemHandlers(): void {
    if (!this.socket) return

    this.socket.on('connected', (data: { status: string }) => {
      console.log('[WS] Server confirmed connection')
    })

    this.socket.on('auth_success', (data: { user_id: string }) => {
      console.log('[WS] Authentication successful:', data.user_id)
    })

    this.socket.on('auth_error', (data: { message: string }) => {
      console.error('[WS] Auth error:', data.message)
      this.setState({ error: data.message })
    })

    this.socket.on('subscription_success', (data: { action: string; symbols?: string[] }) => {
      console.log('[WS] Subscription success:', data)
    })

    this.socket.on('heartbeat', (data: { timestamp: string }) => {
      this.setState({ lastHeartbeat: data.timestamp })
      if (this.heartbeatTimeout) {
        clearTimeout(this.heartbeatTimeout)
        this.heartbeatTimeout = null
      }
    })

    this.socket.on('error', (data: { message: string }) => {
      console.error('[WS] Server error:', data.message)
    })
  }

  private emitWithDedup(messageId: string, data: unknown, emitFn: () => void): void {
    const now = Date.now()
    
    if (this.processedMessageIds.has(messageId)) {
      return
    }

    this.processedMessageIds.add(messageId)
    emitFn()

    setTimeout(() => {
      this.processedMessageIds.delete(messageId)
    }, this.MESSAGE_DEDUP_WINDOW)
  }

  private scheduleReconnect(): void {
    const { reconnectAttempts, maxAttempts } = this.state
    const { initialDelay, maxDelay, backoffMultiplier } = this.reconnectOptions

    if (reconnectAttempts >= maxAttempts) {
      console.error('[WS] Max reconnection attempts reached')
      this.setState({
        status: 'error',
        error: 'Failed to reconnect after maximum attempts',
      })
      return
    }

    const now = Date.now()
    if (now - this.lastReconnectTime < 1000) {
      console.log('[WS] Reconnecting too soon, waiting...')
      return
    }

    this.setState({ status: 'reconnecting' })

    const delay = Math.min(
      initialDelay * Math.pow(backoffMultiplier, reconnectAttempts),
      maxDelay
    )

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxAttempts})`)

    this.lastReconnectTime = now

    this.reconnectTimeout = setTimeout(() => {
      if (this.currentToken) {
        this.setState({ reconnectAttempts: this.state.reconnectAttempts + 1 })
        this.connect(this.currentToken)
      }
    }, delay)
  }

  private handleReconnect(): void {
    this.scheduleReconnect()
  }

  private resubscribe(): void {
    const symbols = Array.from(this.state.subscribedSymbols)
    if (symbols.length > 0) {
      this.subscribeMarket(symbols)
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping')
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('[WS] Heartbeat timeout - disconnecting')
          this.socket?.disconnect()
        }, this.heartbeatOptions.timeout)
      }
    }, this.heartbeatOptions.interval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  private flushMessageQueue(): void {
    const queue = [...this.messageQueue]
    this.messageQueue = []

    queue.forEach((msg) => {
      if (this.socket?.connected) {
        this.socket.emit(msg.event, msg.data)
      }
    })
  }

  private queueMessage(event: string, data?: unknown): void {
    if (this.messageQueue.length >= this.MAX_QUEUE_SIZE) {
      this.messageQueue.shift()
    }
    this.messageQueue.push({
      event,
      data,
      timestamp: Date.now(),
    })
  }

  private setState(partial: Partial<WebSocketState>): void {
    this.state = { ...this.state, ...partial }
  }

  private emit(event: string, data: unknown): void {
    const handlers = this.eventHandlers.get(event)
    if (!handlers) return

    handlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        console.error(`[WS] Error in handler for ${event}:`, error)
      }
    })
  }

  private emitStateEvent(event: string, data: unknown): void {
    this.emit(event, data)
  }

  public authenticate(token: string): void {
    this.currentToken = token
    this.socket?.emit('authenticate', { token })
  }

  public subscribeMarket(symbols: string[]): void {
    if (symbols.length === 0) return

    if (this.socket?.connected) {
      this.socket.emit('subscribe_market', { symbols })
      symbols.forEach(s => this.state.subscribedSymbols.add(s.toUpperCase()))
    } else {
      this.queueMessage('subscribe_market', { symbols })
    }
  }

  public unsubscribeMarket(symbols: string[]): void {
    if (symbols.length === 0) return

    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_market', { symbols })
      symbols.forEach(s => this.state.subscribedSymbols.delete(s.toUpperCase()))
    } else {
      this.queueMessage('unsubscribe_market', { symbols })
    }
  }

  public subscribeWatchlist(watchlistId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_watchlist', { watchlist_id: watchlistId })
    } else {
      this.queueMessage('subscribe_watchlist', { watchlist_id: watchlistId })
    }
  }

  public subscribeUser(channels: string[] = ['orders', 'positions', 'pnl']): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_user', { channels })
    } else {
      this.queueMessage('subscribe_user', { channels })
    }
  }

  public placeOrder(order: {
    order_type: string
    product: string
    symbol: string
    exchange: string
    side: string
    quantity: number
    price?: number
    trigger_price?: number
  }): void {
    if (this.socket?.connected) {
      this.socket.emit('place_order', { order })
    } else {
      this.queueMessage('place_order', { order })
    }
  }

  public cancelOrder(orderId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('cancel_order', { order_id: orderId })
    } else {
      this.queueMessage('cancel_order', { order_id: orderId })
    }
  }

  public startStrategy(strategyId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('start_strategy', { strategy_id: strategyId })
      this.state.subscribedStrategies.add(strategyId)
    } else {
      this.queueMessage('start_strategy', { strategy_id: strategyId })
    }
  }

  public stopStrategy(strategyId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('stop_strategy', { strategy_id: strategyId })
      this.state.subscribedStrategies.delete(strategyId)
    } else {
      this.queueMessage('stop_strategy', { strategy_id: strategyId })
    }
  }

  public getSubscribedSymbols(): string[] {
    return Array.from(this.state.subscribedSymbols)
  }

  public on<T = unknown>(event: string, handler: EventHandler<T>): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler as EventHandler)

    return () => {
      this.eventHandlers.get(event)?.delete(handler as EventHandler)
    }
  }

  public off(event: string, handler: EventHandler): void {
    this.eventHandlers.get(event)?.delete(handler)
  }

  public disconnect(): void {
    this.stopHeartbeat()
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.setState({
      status: 'disconnected',
      connectedAt: null,
      subscribedSymbols: new Set(),
      subscribedStrategies: new Set(),
    })
    this.messageQueue = []
  }

  public getStatus(): ConnectionStatus {
    return this.state.status
  }

  public isConnected(): boolean {
    return this.state.status === 'connected'
  }

  public getState(): Readonly<WebSocketState> {
    return { ...this.state }
  }

  public emit(event: string, data?: unknown): void {
    if (this.socket?.connected) {
      this.socket.emit(event, data)
    } else {
      this.queueMessage(event, data)
    }
  }

  public setReconnectOptions(options: Partial<ReconnectOptions>): void {
    this.reconnectOptions = { ...this.reconnectOptions, ...options }
  }

  public setHeartbeatOptions(options: Partial<HeartbeatOptions>): void {
    this.heartbeatOptions = { ...this.heartbeatOptions, ...options }
  }
}

export const wsManager = new WebSocketManager()
export default wsManager
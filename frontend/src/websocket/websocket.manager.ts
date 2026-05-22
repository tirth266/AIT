/**
 * WebSocket Manager
 * ================
 * Production-grade WebSocket manager with:
 * - JWT authentication using existing login token
 * - Auto reconnection with exponential backoff
 * - Heartbeat system
 * - Connection state tracking
 * - Message queueing for offline recovery
 * - StrictMode-safe singleton lifecycle
 * - No token fetching - uses existing JWT only
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

interface BatchedEvents {
  ticks: Record<string, MarketTickPayload>
  positions: Record<string, PositionUpdatePayload>
  orders: Record<string, OrderUpdatePayload>
  pnl: PnLUpdatePayload | null
}

let wsManagerInstance: WebSocketManager | null = null

class WebSocketManager {
  private socket: Socket | null = null
  private state: WebSocketState
  private reconnectOptions: ReconnectOptions
  private heartbeatOptions: HeartbeatOptions
  private eventHandlers: Map<string, Set<EventHandler>> = new Map()
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null
  private messageQueue: QueuedMessage[] = []
  private lastReconnectTime: number = 0
  private listenersAttached = false
  private isIntentionalDisconnect = false
  private isConnecting = false

  private batchedEvents: BatchedEvents = {
    ticks: {},
    positions: {},
    orders: {},
    pnl: null,
  }
  private batchTimeout: ReturnType<typeof setTimeout> | null = null
  private readonly BATCH_INTERVAL = 50

  private readonly WS_URL: string
  private readonly MAX_QUEUE_SIZE = 100

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
      initialDelay: 2000,
      maxDelay: 30000,
      backoffMultiplier: 2,
    }

    this.heartbeatOptions = {
      interval: 25000,
      timeout: 10000,
    }

    this.setupOfflineDetection()
  }

  private getWebSocketUrl(): string {
    const envUrl = import.meta.env.VITE_WS_URL
    if (envUrl && envUrl !== '') return envUrl.replace(/\/$/, '')

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000'
    const normalized = apiUrl.replace(/\/$/, '').replace(/\/api\/v1$/, '').replace(/\/api$/, '')
    return normalized
  }

  private getToken(): string | null {
    const angelToken = localStorage.getItem('angel_jwt_token');
    const accessToken = localStorage.getItem('access_token');
    const token = angelToken || accessToken;

    if (token) {
      console.log('[WS] Token loaded from storage');
      return token;
    }

    if (import.meta.env.DEV) {
      console.log('[WS] DEV mode: using placeholder token for development');
      const devToken = 'dev_token_placeholder';
      localStorage.setItem('access_token', devToken);
      return devToken;
    }

    console.warn('[WS] No access token found - please login first');
    return null;
  }

  public initAuth(token: string): void {
    localStorage.setItem('access_token', token)
    console.log('[WS] Token stored in localStorage')
  }

  private setupOfflineDetection(): void {
    if (typeof window === 'undefined') return

    window.addEventListener('online', () => {
      console.log('[WS] Network online')
      if (this.state.status === 'disconnected' && !this.isIntentionalDisconnect) {
        this.attemptReconnect()
      }
    })

    window.addEventListener('offline', () => {
      console.log('[WS] Network offline')
      this.setState({ status: 'disconnected' })
      this.stopHeartbeat()
    })
  }

  connect(): void {
    if (this.isConnecting) {
      console.log('[WS] Connection already in progress, skipping')
      return
    }

    if (this.socket?.connected) {
      console.log('[WS] Already connected, skipping')
      return
    }

    if (wsManagerInstance && wsManagerInstance !== this) {
      console.log('[WS] Using existing manager instance, skipping')
      return
    }

    const token = this.getToken()
    if (!token) {
      console.warn('[WS] No access token - cannot connect. Please login first.')
      this.setState({
        status: 'error',
        error: 'No access token. Please login to enable WebSocket.',
      })
      return
    }

    wsManagerInstance = this
    this.isIntentionalDisconnect = false
    this.isConnecting = true

    this.setState({ status: 'connecting', error: null })

    console.log('[WS] Attempting WebSocket connection with existing JWT...')

    try {
      this.socket = io(this.WS_URL, {
        transports: ['websocket', 'polling'],
        autoConnect: false,
        reconnection: true,
        reconnectionAttempts: this.reconnectOptions.maxAttempts,
        reconnectionDelay: this.reconnectOptions.initialDelay,
        reconnectionDelayMax: this.reconnectOptions.maxDelay,
        timeout: 20000,
        withCredentials: true,
        forceNew: true,
        multiplex: false,
        auth: { token },
      })

      this.setupEventListeners()
      this.socket.connect()
    } catch (error) {
      console.error('[WS] Failed to create socket:', error)
      this.isConnecting = false
      this.setState({ status: 'error', error: 'Failed to create connection' })
    }
  }

  private setupEventListeners(): void {
    if (!this.socket || this.listenersAttached) return
    this.listenersAttached = true

    this.socket.on('connect', () => {
      console.log('[WS] Socket connected', this.socket?.id)
      this.isConnecting = false
      this.setState({
        status: 'connected',
        connectedAt: new Date().toISOString(),
        reconnectAttempts: 0,
        error: null,
      })
      this.startHeartbeat()
      this.emitStateEvent('connected', { connected: true, sid: this.socket?.id })
    })

    this.socket.on('disconnect', (reason) => {
      console.log('[WS] Socket disconnected:', reason)
      this.isConnecting = false
      this.setState({ status: 'disconnected' })
      this.stopHeartbeat()
      this.emitStateEvent('disconnected', { reason })

      if (!this.isIntentionalDisconnect && reason !== 'io client disconnect') {
        this.scheduleReconnect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('[WS] Connection error:', error.message)
      this.isConnecting = false

      if (error.message.includes('401') || error.message.includes('Invalid token') || error.message.includes('jwt')) {
        localStorage.removeItem('access_token')
        this.setState({
          status: 'error',
          error: 'Authentication failed. Please login again.',
        })
      } else {
        this.setState({
          status: 'error',
          error: error.message,
        })

        if (this.state.reconnectAttempts < this.reconnectOptions.maxAttempts) {
          this.scheduleReconnect()
        }
      }
    })

    this.setupMarketHandlers()
    this.setupSystemHandlers()
  }

  private setupMarketHandlers(): void {
    if (!this.socket) return

    this.socket.on('market_tick', (data: MarketTickPayload) => {
      this.batchEvent('ticks', data.symbol, data)
    })

    this.socket.on('market:tick', (data: MarketTickPayload) => {
      this.batchEvent('ticks', data.symbol, data)
    })

    this.socket.on('position_update', (data: PositionUpdatePayload) => {
      this.batchEvent('positions', data.position_id, data)
    })

    this.socket.on('order_update', (data: OrderUpdatePayload) => {
      this.batchEvent('orders', data.order_id, data)
    })

    this.socket.on('pnl_update', (data: PnLUpdatePayload) => {
      this.batchedEvents.pnl = data
      this.scheduleBatchFlush()
    })

    this.socket.on('market:depth', (data: unknown) => this.emitInternal('market:depth', data))
    this.socket.on('market:candle', (data: unknown) => this.emitInternal('market:candle', data))
    this.socket.on('market_status', (data: MarketStatusPayload) => this.emitInternal('market_status', data))
    this.socket.on('ai_signal', (data: AISignalPayload) => this.emitInternal('ai_signal', data))
    this.socket.on('notification', (data: NotificationPayload) => this.emitInternal('notification', data))
    this.socket.on('strategy_update', (data: StrategyUpdatePayload) => this.emitInternal('strategy_update', data))
    this.socket.on('signal:new', (data: AISignalPayload) => this.emitInternal('signal_new', data))
    this.socket.on('trade_executed', (data: unknown) => this.emitInternal('trade_executed', data))
    this.socket.on('position_opened', (data: PositionUpdatePayload) => this.emitInternal('position_opened', data))
    this.socket.on('position_closed', (data: PositionUpdatePayload) => this.emitInternal('position_closed', data))
  }

  private batchEvent(type: 'ticks' | 'positions' | 'orders', id: string, data: unknown): void {
    this.batchedEvents[type][id] = data as never
    this.scheduleBatchFlush()
  }

  private scheduleBatchFlush(): void {
    if (this.batchTimeout) return

    this.batchTimeout = setTimeout(() => {
      this.flushBatchedEvents()
    }, this.BATCH_INTERVAL)
  }

  private flushBatchedEvents(): void {
    this.batchTimeout = null

    if (Object.keys(this.batchedEvents.ticks).length > 0) {
      this.emitInternal('batched_ticks', Object.values(this.batchedEvents.ticks))
      this.batchedEvents.ticks = {}
    }

    if (Object.keys(this.batchedEvents.positions).length > 0) {
      this.emitInternal('batched_positions', Object.values(this.batchedEvents.positions))
      this.batchedEvents.positions = {}
    }

    if (Object.keys(this.batchedEvents.orders).length > 0) {
      this.emitInternal('batched_orders', Object.values(this.batchedEvents.orders))
      this.batchedEvents.orders = {}
    }

    if (this.batchedEvents.pnl) {
      this.emitInternal('pnl_update', this.batchedEvents.pnl)
      this.batchedEvents.pnl = null
    }
  }

  private setupSystemHandlers(): void {
    if (!this.socket) return

    this.socket.on('auth_success', (data: { user_id: string }) => {
      console.log('[WS] Auth success:', data.user_id)
      this.setState({ error: null })
      this.emitStateEvent('auth_success', data)
      this.flushMessageQueue()
      this.resubscribe()
    })

    this.socket.on('auth_error', (data: { message: string }) => {
      console.error('[WS] Auth error:', data.message)
      this.setState({ error: data.message })
      this.emitStateEvent('auth_error', data)
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

    this.socket.on('connected', (data: { status: string; session_id: string }) => {
      console.log('[WS] Server acknowledged:', data.session_id)
    })
  }

  private scheduleReconnect(): void {
    const { reconnectAttempts } = this.state
    const { initialDelay, maxDelay, backoffMultiplier, maxAttempts } = this.reconnectOptions

    if (reconnectAttempts >= maxAttempts) {
      console.error('[WS] Max reconnection attempts reached')
      this.setState({
        status: 'error',
        error: 'Failed to reconnect after maximum attempts',
      })
      return
    }

    const now = Date.now()
    if (now - this.lastReconnectTime < 3000) {
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
      this.setState({ reconnectAttempts: this.state.reconnectAttempts + 1 })
      this.connect()
    }, delay)
  }

  private attemptReconnect(): void {
    if (this.socket?.connected) return
    this.setState({ reconnectAttempts: 0 })
    this.connect()
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
          console.warn('[WS] Heartbeat timeout')
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

  private emitInternal(event: string, data: unknown): void {
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
    this.emitInternal(event, data)
  }

  public authenticate(token: string): void {
    localStorage.setItem('access_token', token)

    if (this.socket?.connected) {
      console.log('[WS] Sending authenticate event')
      this.socket.emit('authenticate', { token })
    } else {
      console.log('[WS] Queueing authenticate event')
      this.queueMessage('authenticate', { token })
    }
  }

  public subscribeMarket(symbols: string[]): void {
    if (symbols.length === 0) return

    const upperSymbols = symbols.map(s => s.toUpperCase())

    if (this.socket?.connected) {
      this.socket.emit('subscribe_market', { symbols: upperSymbols })
      upperSymbols.forEach(s => this.state.subscribedSymbols.add(s))
    } else {
      this.queueMessage('subscribe_market', { symbols: upperSymbols })
    }
  }

  public unsubscribeMarket(symbols: string[]): void {
    if (symbols.length === 0) return

    const upperSymbols = symbols.map(s => s.toUpperCase())

    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_market', { symbols: upperSymbols })
      upperSymbols.forEach(s => this.state.subscribedSymbols.delete(s))
    } else {
      this.queueMessage('unsubscribe_market', { symbols: upperSymbols })
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
    this.isIntentionalDisconnect = true

    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout)
      this.batchTimeout = null
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
      this.listenersAttached = false
    }

    this.setState({
      status: 'disconnected',
      connectedAt: null,
      subscribedSymbols: new Set(),
      subscribedStrategies: new Set(),
    })
    this.messageQueue = []
    console.log('[WS] Disconnected and cleaned up')
  }

  public forceDisconnect(): void {
    this.disconnect()
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

function getWsManager(): WebSocketManager {
  if (!wsManagerInstance) {
    wsManagerInstance = new WebSocketManager()
  }
  return wsManagerInstance
}

export const wsManager = getWsManager()
export default wsManager
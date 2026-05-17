/**
 * WebSocket Event Types
 * ====================
 * TypeScript types for WebSocket communication
 */

// Connection States
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'

// Event Payloads
export interface MarketTickPayload {
  symbol: string
  last_price: number
  change: number
  change_percent: number
  volume: number
  open?: number
  high?: number
  low?: number
  prev_close?: number
  value?: number
  vwap?: number
  timestamp: string
}

export interface MarketDepthPayload {
  symbol: string
  exchange: string
  timestamp: string
  buy_orders: OrderBookEntry[]
  sell_orders: OrderBookEntry[]
  total_buy_quantity: number
  total_sell_quantity: number
}

export interface OrderBookEntry {
  price: number
  quantity: number
  orders: number
}

export interface OrderUpdatePayload {
  order_id: string
  status: 'PENDING' | 'OPEN' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'REJECTED'
  filled_quantity: number
  average_price: number | null
  message: string
  timestamp: string
}

export interface PositionUpdatePayload {
  position_id: string
  symbol: string
  quantity: number
  current_price: number
  unrealized_pnl: number
  pnl_percent: number
  day_pnl: number
  timestamp: string
}

export interface PnLUpdatePayload {
  total_pnl: number
  day_pnl: number
  unrealized_pnl: number
  realized_pnl: number
  margin_used: number
  available_cash: number
  timestamp: string
}

export interface AISignalPayload {
  signal_id: string
  symbol: string
  action: 'BUY' | 'SELL'
  confidence: number
  target_price: number
  stop_loss: number
  reasoning: string
  timeframe: string
  indicators?: {
    rsi?: number
    macd?: string
    volume_ratio?: number
  }
  timestamp: string
}

export interface NotificationPayload {
  notification_id: string
  type: 'ORDER_FILLED' | 'ORDER_CANCELLED' | 'ORDER_REJECTED' | 'POSITION_OPENED' | 'POSITION_CLOSED' | 'SIGNAL' | 'ALERT' | 'SYSTEM' | 'INFO' | 'WARNING' | 'ERROR'
  title: string
  message: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  timestamp: string
}

export interface StrategyUpdatePayload {
  strategy_id: string
  status: 'STARTING' | 'RUNNING' | 'STOPPING' | 'STOPPED' | 'PAUSED' | 'ERROR'
  signal?: {
    action: 'BUY' | 'SELL'
    symbol: string
    price: number
    quantity: number
    confidence: number
  }
  message: string
  timestamp: string
}

export interface MarketStatusPayload {
  exchange: string
  status: 'OPEN' | 'CLOSED'
  session: 'PRE-MARKET' | 'REGULAR' | 'POST-MARKET'
  next_session: string
  timestamp: string
}

export interface ConnectionPayload {
  status: 'connected' | 'disconnected'
  session_id?: string
  timestamp: string
}

export interface AuthSuccessPayload {
  user_id: string
  message: string
  timestamp: string
}

export interface AuthErrorPayload {
  message: string
  timestamp: string
}

export interface SubscriptionPayload {
  action: 'subscribe_market' | 'unsubscribe_market' | 'subscribe_watchlist' | 'subscribe_user'
  symbols?: string[]
  watchlist_id?: string
  channels?: string[]
  timestamp: string
}

export interface HeartbeatPayload {
  timestamp: string
}

// Client Event Types
export interface AuthenticateEvent {
  type: 'authenticate'
  token: string
}

export interface SubscribeMarketEvent {
  type: 'subscribe_market'
  symbols: string[]
  channel?: 'quotes' | 'depth' | 'candles'
}

export interface UnsubscribeMarketEvent {
  type: 'unsubscribe_market'
  symbols: string[]
}

export interface SubscribeWatchlistEvent {
  type: 'subscribe_watchlist'
  watchlist_id: string
}

export interface SubscribeUserEvent {
  type: 'subscribe_user'
  user_id: string
  channels: ('orders' | 'positions' | 'pnl')[]
}

export interface PlaceOrderEvent {
  type: 'place_order'
  order: {
    order_type: string
    product: string
    symbol: string
    exchange: string
    side: string
    quantity: number
    price?: number
    trigger_price?: number
  }
}

export interface CancelOrderEvent {
  type: 'cancel_order'
  order_id: string
}

export interface StartStrategyEvent {
  type: 'start_strategy'
  strategy_id: string
}

export interface StopStrategyEvent {
  type: 'stop_strategy'
  strategy_id: string
}

export interface PingEvent {
  type: 'ping'
}

// WebSocket State
export interface WebSocketState {
  status: ConnectionStatus
  connectedAt: string | null
  lastHeartbeat: string | null
  reconnectAttempts: number
  error: string | null
  subscribedSymbols: Set<string>
  subscribedStrategies: Set<string>
}

// Event Handler Type
export type EventHandler<T = unknown> = (data: T) => void

// Subscription Manager Types
export interface SubscriptionManager {
  subscribe: (symbols: string[]) => void
  unsubscribe: (symbols: string[]) => void
  subscribeWatchlist: (watchlistId: string) => void
  subscribeUser: (channels: string[]) => void
  getSubscribedSymbols: () => string[]
}

// Reconnection Options
export interface ReconnectOptions {
  maxAttempts: number
  initialDelay: number
  maxDelay: number
  backoffMultiplier: number
}

// Heartbeat Options
export interface HeartbeatOptions {
  interval: number
  timeout: number
}
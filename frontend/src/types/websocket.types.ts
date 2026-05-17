// WebSocket Event Types
export interface WSEvent<T = unknown> {
  event: string
  data: T
  timestamp: string
}

// Market Events
export interface MarketTickData {
  symbol: string
  last_price: number
  change: number
  change_percent: number
  volume: number
  timestamp: string
}

export interface MarketDepthData {
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

export interface MarketIndicesData {
  nifty_50: { value: number; change: number }
  sensex: { value: number; change: number }
  bank_nifty: { value: number; change: number }
}

// Trading Events
export interface OrderUpdateData {
  order_id: string
  status: 'PENDING' | 'EXECUTED' | 'CANCELLED' | 'REJECTED' | 'MODIFIED'
  filled_quantity: number
  average_price: number | null
  message: string
  timestamp: string
}

export interface PositionUpdateData {
  position_id: string
  symbol: string
  quantity: number
  current_price: number
  unrealized_pnl: number
  pnl_percent: number
  day_pnl: number
  timestamp: string
}

export interface PnLUpdateData {
  total_pnl: number
  day_pnl: number
  unrealized_pnl: number
  realized_pnl: number
  margin_used: number
  available_cash: number
  timestamp: string
}

export interface TradeExecutedData {
  trade_id: string
  order_id: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  timestamp: string
}

// Notification Events
export interface NotificationData {
  notification_id: string
  type: string
  title: string
  message: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  timestamp: string
}

// Strategy Events
export interface StrategyUpdateData {
  strategy_id: string
  status: 'ACTIVE' | 'PAUSED' | 'RUNNING' | 'STOPPED'
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

// AI Signal Events
export interface AISignalData {
  signal_id: string
  symbol: string
  action: 'BUY' | 'SELL'
  confidence: number
  target_price: number
  stop_loss: number
  reasoning: string
  timestamp: string
}

// Market Status Events
export interface MarketStatusData {
  exchange: string
  status: 'OPEN' | 'CLOSED'
  session: 'PRE-MARKET' | 'REGULAR' | 'POST-MARKET'
  next_session: string
  closes_in_seconds: number
  timestamp: string
}

// Client Events
export interface SubscribeMarketEvent {
  type: 'subscribe_market'
  symbols: string[]
  channel: 'quotes' | 'depth' | 'candles'
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

// WebSocket Connection State
export type WSConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface WSState {
  status: WSConnectionStatus
  connectedAt?: string
  lastHeartbeat?: string
  reconnectAttempts: number
  error?: string
}

// Event Handlers Map
export interface WSEventHandlers {
  'ws:connected': (data: { connected: boolean }) => void
  'ws:disconnected': (data: { reason: string }) => void
  'ws:failed': (data: { message: string }) => void
  'market:tick': (data: MarketTickData) => void
  'market:depth': (data: MarketDepthData) => void
  'market:indices': (data: MarketIndicesData) => void
  'order:created': (data: OrderUpdateData) => void
  'order:updated': (data: OrderUpdateData) => void
  'order:filled': (data: OrderUpdateData) => void
  'order:cancelled': (data: OrderUpdateData) => void
  'position:opened': (data: PositionUpdateData) => void
  'position:updated': (data: PositionUpdateData) => void
  'position:closed': (data: PositionUpdateData) => void
  'pnl:update': (data: PnLUpdateData) => void
  'trade:executed': (data: TradeExecutedData) => void
  'notification:new': (data: NotificationData) => void
  'signal:new': (data: AISignalData) => void
  'strategy:update': (data: StrategyUpdateData) => void
  'market_status': (data: MarketStatusData) => void
}
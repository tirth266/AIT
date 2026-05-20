// API Response Types
export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
  timestamp: string
  pagination?: Pagination
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: Pagination
}

export interface Pagination {
  page: number
  limit: number
  total: number
  pages: number
}

export interface ErrorResponse {
  success: false
  message: string
  errors: ValidationError[]
  timestamp: string
}

export interface ValidationError {
  field: string
  message: string
}

// User Types
export interface User {
  user_id: string
  email: string
  full_name: string
  phone?: string
  role: 'admin' | 'trader' | 'viewer'
  broker?: string
  twofa_enabled: boolean
  email_verified: boolean
  kyc_status: 'pending' | 'verified' | 'rejected'
  created_at: string
  last_login?: string
}

export interface UserProfile {
  user_id: string
  email: string
  full_name: string
  phone: string
  role: string
  broker: {
    name: string
    connected: boolean
    account_id?: string
  }
  preferences: UserPreferences
  limits: UserLimits
  created_at: string
}

export interface UserPreferences {
  default_product: 'MIS' | 'CNC' | 'CO'
  default_order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
  default_exchange: 'NSE' | 'BSE'
  theme: 'dark' | 'light'
}

export interface UserLimits {
  max_daily_loss: number
  max_positions: number
  max_orders_per_minute: number
}

// Auth Types
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  token_type: string
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RefreshTokenResponse {
  access_token: string
  expires_in: number
  token_type: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  phone: string
  pan_number?: string
  broker?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
  confirm_password: string
}

// Market Types
export interface Quote {
  symbol: string
  exchange: string
  last_price: number
  change: number
  change_percent: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  value: number
  vwap: number
  high_52w: number
  low_52w: number
  avg_volume_20d: number
  timestamp: string
}

export interface MarketDepth {
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

export interface Candle {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  value: number
  trades: number
}

export interface CandleData {
  symbol: string
  exchange: string
  timeframe: string
  candles: Candle[]
  count: number
}

export interface Index {
  value: number
  change: number
  change_percent: number
  timestamp: string
}

export interface MarketOverview {
  indices: {
    nifty_50: Index
    sensex: Index
    bank_nifty: Index
  }
  market_status: {
    trading_session: 'PRE-MARKET' | 'REGULAR' | 'POST-MARKET' | 'CLOSED'
    next_session: string
    session_start: string
    session_end: string
  }
  top_movers: {
    gainers: TopMover[]
    losers: TopMover[]
  }
}

export interface TopMover {
  symbol: string
  change_percent: number
}

// Order Types
export interface Order {
  order_id: string
  order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
  product: 'MIS' | 'CNC' | 'CO'
  symbol: string
  exchange: 'NSE' | 'BSE'
  side: 'BUY' | 'SELL'
  quantity: number
  price: number | null
  trigger_price: number | null
  status: 'PENDING' | 'EXECUTED' | 'CANCELLED' | 'REJECTED'
  filled_quantity: number
  average_price: number | null
  order_timestamp: string
  exchange_order_id?: string
  filled_timestamp?: string
  cancelled_timestamp?: string
  rejected_reason?: string
  tags?: string[]
}

export interface CreateOrderRequest {
  order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
  product: 'MIS' | 'CNC' | 'CO'
  symbol: string
  exchange: 'NSE' | 'BSE'
  side: 'BUY' | 'SELL'
  quantity: number
  price?: number
  trigger_price?: number
  disclosed_quantity?: number
  validity?: 'DAY' | 'IOC' | 'GTD' | 'GTC'
  after_market_order?: boolean
}

export interface ModifyOrderRequest {
  price?: number
  quantity?: number
  trigger_price?: number
  validity?: string
}

export interface OrderStats {
  total_orders: number
  executed: number
  cancelled: number
  rejected: number
  total_volume: number
}

// Position Types
export interface Position {
  position_id: string
  symbol: string
  exchange: string
  product: 'MIS' | 'CNC'
  side: 'BUY' | 'SELL'
  quantity: number
  avg_price: number
  current_price: number
  last_updated: string
  pnl: number
  pnl_percent: number
  day_pnl?: number
  unrealized_pnl?: number
  m2m?: number
  status: 'OPEN' | 'CLOSED'
  opened_at: string
  closed_at?: string
  exit_reason?: string
  holding_period?: number
}

export interface PositionSummary {
  total_positions: number
  total_value: number
  total_pnl: number
  day_pnl: number
}

// Trade Types
export interface Trade {
  trade_id: string
  order_id: string
  symbol: string
  exchange: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  value: number
  order_type: string
  product: string
  brokerage: number
  gst: number
  stamp_duty: number
  sebi_charges: number
  total_charges: number
  net_value: number
  trade_timestamp: string
  exchange_trade_id: string
}

export interface DailyTradeSummary {
  date: string
  total_trades: number
  buy_trades: number
  sell_trades: number
  total_volume: number
  total_brokerage: number
  trades: Trade[]
}

// Funds Types
export interface Funds {
  account_id: string
  broker: string
  balance: {
    available_cash: number
    used_margin: number
    total_balance: number
    currency: string
  }
  margin: {
    available_margin: number
    used_margin: number
    span_margin: number
    exposure_margin: number
    total_margin_used: number
  }
  limits: {
    daily_buy_power: number
    daily_sell_power: number
  }
  last_updated: string
}

export interface Transaction {
  transaction_id: string
  type: 'CREDIT' | 'DEBIT'
  amount: number
  balance_after: number
  description: string
  reference: string
  timestamp: string
}

export interface Holding {
  symbol: string
  quantity: number
  avg_buy_price: number
  ltp: number
  current_value: number
  pnl: number
  pnl_percent: number
  day_change: number
  day_change_percent: number
  exchange: string
}

export interface HoldingsSummary {
  total_invested: number
  total_current_value: number
  total_pnl: number
  total_pnl_percent: number
}

// Strategy Types
export interface Strategy {
  strategy_id: string
  name: string
  description?: string
  symbol: string
  exchange: string
  timeframe: string
  mode: 'PAPER' | 'LIVE'
  status: 'ACTIVE' | 'PAUSED'
  parameters: StrategyParameters
  risk_settings: RiskSettings
  statistics?: StrategyStatistics
  created_at: string
  updated_at?: string
  last_run?: string
}

export interface StrategyParameters {
  indicator?: string
  rsi_period?: number
  fast_period?: number
  slow_period?: number
  period?: number
  oversold?: number
  overbought?: number
  lookback?: number
  multiplier?: number
  min_confidence?: number
  entry_condition?: string
  exit_condition?: string
  [key: string]: unknown
}

export interface RiskSettings {
  max_position_size: number
  stop_loss_percent: number
  target_percent: number
  max_daily_loss: number
  position_size_percent?: number
  max_positions?: number
  trailing_stop_enabled?: boolean
  trailing_stop_percent?: number
  min_risk_reward_ratio?: number
  max_trades_per_day?: number
}

export interface StrategyStatistics {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_pnl: number
  total_pnl: number
}

export interface CreateStrategyRequest {
  name: string
  description?: string
  symbol: string
  exchange: string
  timeframe: string
  mode?: 'PAPER' | 'LIVE'
  parameters: StrategyParameters
  risk_settings: RiskSettings
}

export interface StrategySignal {
  signal_id: string
  strategy_id: string
  symbol: string
  action: 'BUY' | 'SELL'
  price: number
  quantity: number
  confidence: number
  reasoning: string
  timestamp: string
  executed: boolean
  order_id?: string
}

// AI Signal Types
export interface Signal {
  signal_id: string
  symbol: string
  exchange: string
  action: 'BUY' | 'SELL'
  confidence: number
  target_price: number
  stop_loss: number
  entry_range: {
    min: number
    max: number
  }
  reasoning: string
  indicators: {
    rsi?: number
    rsi_14?: number
    macd?: string
    macd_line?: number
    signal_line?: number
    sma_20?: number
    sma_50?: number
    sma_200?: number
    volume_ratio?: number
    atr?: number
    bb_upper?: number
    bb_middle?: number
    bb_lower?: number
  }
  timeframe: string
  generated_at: string
  expires_at: string
  status: 'ACTIVE' | 'EXPIRED' | 'EXECUTED'
}

export interface LiveSignalsSummary {
  total_signals: number
  buy_signals: number
  sell_signals: number
  avg_confidence: number
}

export interface SignalGenerationRequest {
  symbols: string[]
  timeframe?: string
  analysis_type?: 'QUICK' | 'FULL'
}

export interface SignalJob {
  job_id: string
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED'
  symbols: string[]
  estimated_completion: string
}

// Notification Types
export interface Notification {
  notification_id: string
  type: 'ORDER_FILLED' | 'ORDER_CANCELLED' | 'ORDER_REJECTED' | 'POSITION_OPENED' | 'POSITION_CLOSED' | 'SIGNAL' | 'ALERT' | 'SYSTEM' | 'INFO' | 'WARNING' | 'ERROR'
  title: string
  message: string
  read: boolean
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  data?: Record<string, unknown>
  created_at: string
}

// Dashboard Types
export interface DashboardSummary {
  account: {
    total_balance: number
    available_cash: number
    used_margin: number
    currency: string
  }
  today: {
    pnl: number
    pnl_percent: number
    trades: number
    buy_trades: number
    sell_trades: number
    winning_trades: number
    losing_trades: number
    win_rate: number
  }
  positions: {
    open: number
    total_value: number
    unrealized_pnl: number
  }
  orders: {
    pending: number
    executed_today: number
  }
  strategies: {
    active: number
    paused: number
  }
  alerts: {
    critical: number
    warnings: number
  }
}

export interface PerformanceData {
  period: 'TODAY' | 'WEEK' | 'MONTH' | 'YEAR' | 'ALL'
  summary: {
    total_pnl: number
    total_pnl_percent: number
    total_trades: number
    winning_trades: number
    losing_trades: number
    win_rate: number
    avg_trade_pnl: number
    avg_win: number
    avg_loss: number
    profit_factor: number
    sharpe_ratio: number
    max_drawdown: number
    max_drawdown_percent: number
  }
  daily_breakdown: DailyPerformance[]
  by_symbol: SymbolPerformance[]
}

export interface DailyPerformance {
  date: string
  pnl: number
  pnl_percent: number
  trades: number
  win_rate: number
}

export interface SymbolPerformance {
  symbol: string
  pnl: number
  trades: number
  win_rate: number
}

// Watchlist Types
export interface Watchlist {
  watchlist_id: string
  name: string
  description?: string
  symbols: string[]
  created_at: string
  updated_at: string
  is_default: boolean
}

export interface CreateWatchlistRequest {
  name: string
  description?: string
  symbols?: string[]
}

export interface UpdateWatchlistRequest {
  name?: string
  description?: string
}

export interface AddStocksRequest {
  symbols: string[]
}

// Settings Types
export interface Settings {
  trading: {
    default_product: 'MIS' | 'CNC' | 'CO'
    default_order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
    default_exchange: 'NSE' | 'BSE'
    default_validity: 'DAY' | 'IOC' | 'GTD' | 'GTC'
    auto_square_off: boolean
    square_off_time: string
  }
  notifications: {
    order_filled: boolean
    order_cancelled: boolean
    order_rejected: boolean
    position_opened: boolean
    position_closed: boolean
    stop_loss_hit: boolean
    target_hit: boolean
    daily_summary: boolean
    ai_signals: boolean
    email_notifications: boolean
    sms_notifications: boolean
    push_notifications: boolean
  }
  display: {
    theme: 'DARK' | 'LIGHT'
    language: string
    price_format: string
    show_volume: boolean
    chart_type: string
  }
  api_access: {
    enabled: boolean
    api_key?: string
    webhook_url?: string
    rate_limit: number
  }
  risk_management: {
    max_daily_loss: number
    max_single_trade_loss: number
    max_positions: number
    max_orders_per_minute: number
    position_size_percent: number
  }
  updated_at: string
}

export interface UpdateSettingsRequest {
  trading?: Partial<Settings['trading']>
  notifications?: Partial<Settings['notifications']>
  display?: Partial<Settings['display']>
  risk_management?: Partial<Settings['risk_management']>
}

export interface StrategyConfig {
  strategy_id: string
  strategy_name: string
  strategy_type: StrategyType
  description?: string
  symbol: string
  exchange: string
  timeframe: string
  mode: 'paper' | 'live'
  status: StrategyStatus
  parameters: StrategyParameters
  risk_settings: RiskSettings
  execution_settings?: ExecutionSettings
  indicators?: IndicatorConfig[]
  entry_conditions?: Condition[]
  exit_conditions?: Condition[]
  is_active: boolean
  created_at: string
  updated_at?: string
  last_run?: string
  statistics?: StrategyStatistics
}

export type StrategyType =
  | 'ema_crossover'
  | 'rsi_reversal'
  | 'breakout'
  | 'scalping'
  | 'supertrend'
  | 'ai_strategy'
  | 'custom'

export type StrategyStatus = 'created' | 'running' | 'paused' | 'stopped' | 'error'

export interface ExecutionSettings {
  order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
  allow_partial_fills: boolean
  retry_on_failure: boolean
  max_retries: number
}

export interface IndicatorConfig {
  name: string
  type: string
  period?: number
  params?: Record<string, number>
}

export interface Condition {
  type: 'indicator' | 'price' | 'time'
  indicator?: string
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte' | 'crosses'
  value: number
  connector?: 'AND' | 'OR'
}

export interface StrategyStatisticsV2 {
  total_trades: number
  winning_trades: number
  losing_trades: number
  total_pnl: number
  win_rate: number
  avg_pnl: number
  avg_win?: number
  avg_loss?: number
  profit_factor?: number
}

export interface CreateStrategyRequestV2 {
  strategy_name: string
  strategy_type: StrategyType
  description?: string
  symbol: string
  exchange: string
  timeframe: string
  mode?: 'paper' | 'live'
  parameters?: StrategyParameters
  risk_settings?: RiskSettings
  execution_settings?: ExecutionSettings
}

export interface UpdateStrategyRequest {
  strategy_name?: string
  description?: string
  parameters?: Record<string, unknown>
  risk_settings?: Record<string, unknown>
  execution_settings?: Record<string, unknown>
  is_active?: boolean
}

export interface StrategySignalV2 {
  signal_id: string
  strategy_id: string
  strategy_name?: string
  symbol: string
  exchange?: string
  action: 'BUY' | 'SELL' | 'HOLD'
  entry_price: number
  stop_loss?: number
  target_price?: number
  quantity?: number
  confidence: number
  reasoning: string
  indicators: Record<string, unknown>
  timeframe: string
  timestamp: string
  executed?: boolean
  order_id?: string
}

export interface EngineStatus {
  status: 'stopped' | 'starting' | 'running' | 'paused' | 'error'
  metrics: EngineMetrics
  strategies: StrategyInstanceStatus[]
}

export interface EngineMetrics {
  total_strategies: number
  active_strategies: number
  signals_generated: number
  signals_executed: number
  total_pnl: number
  uptime_seconds: number
  errors_count: number
}

export interface StrategyInstanceStatus {
  strategy_id: string
  name: string
  status: StrategyStatus
  symbol: string
  timeframe: string
  trades_count: number
  last_signal_time?: string
}

export interface BacktestResult {
  backtest_id?: string
  strategy_id: string
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  final_capital: number
  total_return: number
  total_return_percent: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  max_drawdown: number
  max_drawdown_percent: number
  sharpe_ratio: number
  trades?: BacktestTrade[]
  equity_curve?: { date: string; equity: number }[]
}

export interface BacktestTrade {
  entry_date: string
  exit_date: string
  symbol: string
  side: 'BUY' | 'SELL'
  entry_price: number
  exit_price: number
  quantity: number
  pnl: number
  pnl_percent: number
  holding_period: number
  exit_reason?: string
}

export interface BacktestRequest {
  strategy_id: string
  symbol: string
  start_date: string
  end_date: string
  initial_capital?: number
}

export interface PaperPortfolio {
  portfolio_id?: string
  user_id: string
  cash: number
  initial_capital: number
  total_pnl?: number
  open_positions: number
  created_at: string
  updated_at?: string
}

export interface PaperTrade {
  trade_id: string
  user_id: string
  strategy_id?: string
  symbol: string
  exchange: string
  side: 'BUY' | 'SELL'
  quantity: number
  entry_price: number
  exit_price?: number
  stop_loss?: number
  target?: number
  status: 'open' | 'closed'
  pnl?: number
  pnl_percent?: number
  opened_at: string
  closed_at?: string
  exit_reason?: string
}

export interface PaperPerformance {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  current_capital: number
  return_percent: number
  avg_pnl: number
}

export interface RiskSummary {
  daily_pnl: number
  open_positions: number
  trades_today: number
  risk_status: 'normal' | 'warning' | 'danger'
}
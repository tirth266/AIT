import { Position, Trade, Strategy, Bot } from '../store/trading'
import type { Quote, CandleData } from '../types'

export const mockStrategies: Strategy[] = [
  {
    _id: 'strat_001',
    strategy_name: 'Nifty Breakout',
    symbol: 'RELIANCE',
    timeframe: '15min',
    mode: 'paper',
    broker: 'zerodha',
    is_active: true,
    indicators: [
      { name: 'RSI', params: { period: 14 }, enabled: true },
      { name: 'EMA', params: { period: 9 }, enabled: true },
      { name: 'EMA', params: { period: 21 }, enabled: true },
    ],
    entry_conditions: [
      { indicator_name: 'RSI', operator: 'greater_than', value: 60, logic: 'AND' },
      { indicator_name: 'EMA_9', operator: 'crosses_above', value: 'EMA_21', logic: 'AND' },
    ],
    exit_conditions: [
      { indicator_name: 'RSI', operator: 'greater_than', value: 80, logic: 'OR' },
    ],
    risk_settings: {
      stop_loss_percent: 1.0,
      take_profit_percent: 2.0,
      trailing_stop_enabled: true,
      trailing_stop_percent: 0.5,
      position_size_type: 'calculated',
      position_size_percent: 10,
    },
    last_evaluated_at: '2024-01-15T10:00:00Z',
    created_at: '2024-01-10T08:00:00Z',
    total_trades: 45,
    total_pnl: 3250.50,
  },
  {
    _id: 'strat_002',
    strategy_name: 'Bank Nifty Momentum',
    symbol: 'ICICIBANK',
    timeframe: '5min',
    mode: 'live',
    broker: 'zerodha',
    is_active: false,
    indicators: [
      { name: 'EMA', params: { period: 9 }, enabled: true },
      { name: 'EMA', params: { period: 21 }, enabled: true },
      { name: 'EMA', params: { period: 50 }, enabled: true },
    ],
    entry_conditions: [
      { indicator_name: 'EMA_9', operator: 'crosses_above', value: 'EMA_21', logic: 'AND' },
    ],
    exit_conditions: [
      { indicator_name: 'EMA_9', operator: 'crosses_below', value: 'EMA_21', logic: 'OR' },
      { indicator_name: 'EMA_21', operator: 'crosses_below', value: 'EMA_50', logic: 'OR' },
    ],
    risk_settings: {
      stop_loss_percent: 1.5,
      take_profit_percent: 3.0,
      trailing_stop_enabled: false,
      trailing_stop_percent: 0,
      position_size_type: 'fixed',
      position_size: 100,
    },
    created_at: '2024-01-05T12:00:00Z',
    total_trades: 120,
    total_pnl: -502.25,
  },
  {
    _id: 'strat_003',
    strategy_name: 'F&O Swing',
    symbol: 'INFY',
    timeframe: '1h',
    mode: 'paper',
    broker: 'upstox',
    is_active: true,
    indicators: [
      { name: 'Bollinger_Bands', params: { period: 20, std_dev: 2 }, enabled: true },
      { name: 'RSI', params: { period: 14 }, enabled: true },
    ],
    entry_conditions: [
      { indicator_name: 'BB_lower', operator: 'greater_than', value: 'price', logic: 'AND' },
      { indicator_name: 'RSI', operator: 'less_than', value: 35, logic: 'AND' },
    ],
    exit_conditions: [
      { indicator_name: 'BB_upper', operator: 'less_than', value: 'price', logic: 'OR' },
      { indicator_name: 'RSI', operator: 'greater_than', value: 70, logic: 'OR' },
    ],
    risk_settings: {
      stop_loss_percent: 2.0,
      take_profit_percent: 4.0,
      trailing_stop_enabled: true,
      trailing_stop_percent: 1.0,
      position_size_type: 'calculated',
      position_size_percent: 15,
    },
    created_at: '2024-01-12T06:00:00Z',
    total_trades: 28,
    total_pnl: 1568.80,
  },
]

export const mockPositions: Position[] = [
  {
    _id: 'pos_001',
    strategy_name: 'Nifty Breakout',
    symbol: 'RELIANCE',
    side: 'BUY',
    entry_price: 2950.00,
    quantity: 100,
    current_price: 2985.00,
    unrealized_pnl: 3500.00,
    unrealized_pnl_percent: 1.186,
    stop_loss: 2920.50,
    take_profit: 3010.00,
    mode: 'paper',
    opened_at: '2024-01-15T08:30:00Z',
  },
  {
    _id: 'pos_002',
    strategy_name: 'F&O Swing',
    symbol: 'INFY',
    side: 'BUY',
    entry_price: 1680.00,
    quantity: 150,
    current_price: 1695.50,
    unrealized_pnl: 2325.00,
    unrealized_pnl_percent: 0.922,
    stop_loss: 1656.00,
    take_profit: 1747.20,
    mode: 'paper',
    opened_at: '2024-01-15T09:15:00Z',
  },
]

export const mockTrades: Trade[] = [
  {
    _id: 'trade_001',
    strategy_name: 'Nifty Breakout',
    symbol: 'RELIANCE',
    side: 'BUY',
    entry_price: 2900.00,
    exit_price: 2950.00,
    quantity: 100,
    pnl: 5000.00,
    pnl_percent: 1.72,
    commission: 50.00,
    mode: 'paper',
    status: 'CLOSED',
    entry_time: '2024-01-15T08:30:00Z',
    exit_time: '2024-01-15T10:30:00Z',
    exit_reason: 'take_profit',
    duration_minutes: 120,
  },
  {
    _id: 'trade_002',
    strategy_name: 'F&O Swing',
    symbol: 'INFY',
    side: 'SELL',
    entry_price: 1720.00,
    exit_price: 1695.00,
    quantity: 150,
    pnl: -3750.00,
    pnl_percent: -1.45,
    commission: 45.00,
    mode: 'paper',
    status: 'CLOSED',
    entry_time: '2024-01-14T14:00:00Z',
    exit_time: '2024-01-14T18:30:00Z',
    exit_reason: 'stop_loss',
    duration_minutes: 270,
  },
  {
    _id: 'trade_003',
    strategy_name: 'Bank Nifty Momentum',
    symbol: 'ICICIBANK',
    side: 'BUY',
    entry_price: 1020.00,
    exit_price: 1045.00,
    quantity: 300,
    pnl: 7500.00,
    pnl_percent: 2.45,
    commission: 60.00,
    mode: 'live',
    status: 'CLOSED',
    entry_time: '2024-01-14T10:00:00Z',
    exit_time: '2024-01-14T16:00:00Z',
    exit_reason: 'take_profit',
    duration_minutes: 360,
  },
  {
    _id: 'trade_004',
    strategy_name: 'Nifty Breakout',
    symbol: 'RELIANCE',
    side: 'SELL',
    entry_price: 2980.00,
    exit_price: 2955.00,
    quantity: 100,
    pnl: -2500.00,
    pnl_percent: -0.84,
    commission: 50.00,
    mode: 'paper',
    status: 'CLOSED',
    entry_time: '2024-01-13T20:00:00Z',
    exit_time: '2024-01-14T02:00:00Z',
    exit_reason: 'stop_loss',
    duration_minutes: 360,
  },
  {
    _id: 'trade_005',
    strategy_name: 'F&O Swing',
    symbol: 'TCS',
    side: 'BUY',
    entry_price: 4050.00,
    exit_price: 4120.00,
    quantity: 50,
    pnl: 3500.00,
    pnl_percent: 1.73,
    commission: 35.00,
    mode: 'paper',
    status: 'CLOSED',
    entry_time: '2024-01-13T12:00:00Z',
    exit_time: '2024-01-13T15:00:00Z',
    exit_reason: 'signal',
    duration_minutes: 180,
  },
]

export const mockBots: Bot[] = [
  {
    strategy_id: 'strat_001',
    strategy_name: 'Nifty Breakout',
    status: 'running',
    mode: 'paper',
    last_signal: 'BUY',
    last_signal_time: '2024-01-15T10:30:00Z',
    trades_today: 3,
    pnl_today: 5250.00,
    uptime_seconds: 3600,
  },
  {
    strategy_id: 'strat_003',
    strategy_name: 'F&O Swing',
    status: 'running',
    mode: 'paper',
    last_signal: 'BUY',
    last_signal_time: '2024-01-15T09:15:00Z',
    trades_today: 1,
    pnl_today: 2325.00,
    uptime_seconds: 7200,
  },
]

export const mockPrices: Record<string, MarketPrice> = {
  'RELIANCE': { symbol: 'RELIANCE', price: 2985.00, change_24h: 35.00, change_percent_24h: 1.19, high_24h: 2995.00, low_24h: 2940.00, volume_24h: 3500000, bid: 2984.50, ask: 2985.50, timestamp: Date.now() },
  'TCS': { symbol: 'TCS', price: 4120.00, change_24h: 45.00, change_percent_24h: 1.10, high_24h: 4150.00, low_24h: 4080.00, volume_24h: 1500000, bid: 4119.50, ask: 4120.50, timestamp: Date.now() },
  'INFY': { symbol: 'INFY', price: 1695.50, change_24h: -5.50, change_percent_24h: -0.32, high_24h: 1710.00, low_24h: 1685.00, volume_24h: 2500000, bid: 1695.00, ask: 1696.00, timestamp: Date.now() },
  'HDFCBANK': { symbol: 'HDFCBANK', price: 1725.00, change_24h: 15.00, change_percent_24h: 0.88, high_24h: 1735.00, low_24h: 1710.00, volume_24h: 5000000, bid: 1724.50, ask: 1725.50, timestamp: Date.now() },
  'ICICIBANK': { symbol: 'ICICIBANK', price: 1045.00, change_24h: 8.50, change_percent_24h: 0.82, high_24h: 1055.00, low_24h: 1035.00, volume_24h: 8000000, bid: 1044.50, ask: 1045.50, timestamp: Date.now() },
  'SBIN': { symbol: 'SBIN', price: 645.00, change_24h: 12.50, change_percent_24h: 1.98, high_24h: 650.00, low_24h: 630.00, volume_24h: 12000000, bid: 644.50, ask: 645.50, timestamp: Date.now() },
  'ITC': { symbol: 'ITC', price: 425.50, change_24h: -2.50, change_percent_24h: -0.58, high_24h: 430.00, low_24h: 422.00, volume_24h: 4000000, bid: 425.00, ask: 426.00, timestamp: Date.now() },
  'NIFTY': { symbol: 'NIFTY', price: 24500.00, change_24h: 125.00, change_percent_24h: 0.51, high_24h: 24600.00, low_24h: 24350.00, volume_24h: 0, bid: 24499.00, ask: 24501.00, timestamp: Date.now() },
  'SENSEX': { symbol: 'SENSEX', price: 82000.00, change_24h: 245.00, change_percent_24h: 0.30, high_24h: 82250.00, low_24h: 81700.00, volume_24h: 0, bid: 81995.00, ask: 82005.00, timestamp: Date.now() },
  'BANKNIFTY': { symbol: 'BANKNIFTY', price: 52000.00, change_24h: 380.00, change_percent_24h: 0.74, high_24h: 52200.00, low_24h: 51500.00, volume_24h: 0, bid: 51995.00, ask: 52005.00, timestamp: Date.now() },
}

export const mockWatchlist = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', price: 2985.00, change: 1.19, volume: 3.5 },
  { symbol: 'TCS', name: 'Tata Consultancy', price: 4120.00, change: 1.10, volume: 1.5 },
  { symbol: 'INFY', name: 'Infosys', price: 1695.50, change: -0.32, volume: 2.5 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', price: 1725.00, change: 0.88, volume: 5.0 },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', price: 1045.00, change: 0.82, volume: 8.0 },
  { symbol: 'SBIN', name: 'State Bank', price: 645.00, change: 1.98, volume: 12.0 },
  { symbol: 'ITC', name: 'ITC Ltd', price: 425.50, change: -0.58, volume: 4.0 },
  { symbol: 'LT', name: 'Larsen & Toubro', price: 3850.00, change: 0.65, volume: 1.2 },
  { symbol: 'WIPRO', name: 'Wipro Ltd', price: 525.00, change: 0.38, volume: 3.0 },
  { symbol: 'AXISBANK', name: 'Axis Bank', price: 1125.00, change: 1.15, volume: 2.8 },
]

export function generateCandleData(symbol: string, count: number = 100): Candle[] {
  const basePrice = symbol === 'RELIANCE' ? 2950 : symbol === 'TCS' ? 4100 : symbol === 'INFY' ? 1680 : symbol === 'HDFCBANK' ? 1700 : 1000
  const candles: Candle[] = []
  let currentTime = new Date()
  currentTime.setHours(currentTime.getHours() - count)

  for (let i = 0; i < count; i++) {
    const volatility = basePrice * 0.015
    const open = basePrice + (Math.random() - 0.5) * volatility
    const close = open + (Math.random() - 0.5) * volatility
    const high = Math.max(open, close) + Math.random() * volatility * 0.5
    const low = Math.min(open, close) - Math.random() * volatility * 0.5
    const volume = Math.random() * 100000 + 50000

    candles.push({
      timestamp: currentTime.toISOString(),
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
      volume: Number(volume.toFixed(2)),
    })

    currentTime.setHours(currentTime.getHours() + 1)
  }

  return candles
}

export const mockDashboardData = {
  mode: 'paper',
  global_mode: 'paper',
  account: {
    paper_balance: 500000.00,
    live_balance: 250000.00,
    total_equity: 750000.00,
    available_margin: 450000.00,
    used_margin: 50000.00,
  },
  today: {
    pnl: 12825.00,
    pnl_percent: 2.57,
    trades: 3,
    win_rate: 66.6,
  },
  positions: 2,
  active_bots: 2,
  recent_trades: mockTrades.slice(0, 5),
  performance: {
    daily: [
      { date: '2024-01-15', pnl: 12825.00 },
      { date: '2024-01-14', pnl: -5230.00 },
      { date: '2024-01-13', pnl: 18580.00 },
      { date: '2024-01-12', pnl: 4850.00 },
      { date: '2024-01-11', pnl: -2320.00 },
      { date: '2024-01-10', pnl: 12310.00 },
      { date: '2024-01-09', pnl: 7840.00 },
    ],
    weekly: [
      { date: '2024-W02', pnl: 41280.00 },
      { date: '2024-W01', pnl: 28520.00 },
    ],
    monthly: [
      { date: '2024-01', pnl: 135050.00 },
      { date: '2023-12', pnl: 98030.00 },
      { date: '2023-11', pnl: 142010.00 },
    ],
  },
}

export const mockOrders = [
  {
    _id: 'ord_001',
    symbol: 'RELIANCE',
    side: 'BUY',
    order_type: 'LIMIT',
    quantity: 100,
    price: 2950.00,
    filled: 0,
    status: 'PENDING',
    created_at: '2024-01-15T11:00:00Z',
    exchange: 'NSE',
    product: 'CNC',
  },
  {
    _id: 'ord_002',
    symbol: 'INFY',
    side: 'SELL',
    order_type: 'MARKET',
    quantity: 150,
    price: 1695.00,
    filled: 150,
    status: 'COMPLETED',
    created_at: '2024-01-15T10:30:00Z',
    exchange: 'NSE',
    product: 'CNC',
  },
  {
    _id: 'ord_003',
    symbol: 'TCS',
    side: 'BUY',
    order_type: 'SL',
    quantity: 50,
    price: 4100.00,
    trigger_price: 4080.00,
    filled: 50,
    status: 'COMPLETED',
    created_at: '2024-01-15T09:45:00Z',
    exchange: 'NSE',
    product: 'MIS',
  },
]

export const mockLogs = [
  { _id: 'log_001', level: 'INFO', category: 'ORDER', message: 'Buy order placed for RELIANCE', metadata: { symbol: 'RELIANCE', quantity: 100, price: 2950 }, created_at: '2024-01-15T10:30:00Z' },
  { _id: 'log_002', level: 'INFO', category: 'MARKET', message: 'Price update: RELIANCE @ 2985.00', metadata: { symbol: 'RELIANCE' }, created_at: '2024-01-15T10:30:00Z' },
  { _id: 'log_003', level: 'WARNING', category: 'SIGNAL', message: 'RSI near overbought zone: 68', metadata: { strategy_id: 'strat_001' }, created_at: '2024-01-15T10:29:00Z' },
  { _id: 'log_004', level: 'ERROR', category: 'BROKER', message: 'Order rejection: Insufficient margin', metadata: { broker: 'zerodha' }, created_at: '2024-01-15T10:25:00Z' },
  { _id: 'log_005', level: 'INFO', category: 'STRATEGY', message: 'Strategy executed: Nifty Breakout', metadata: { strategy_id: 'strat_001', signal: 'BUY' }, created_at: '2024-01-15T10:20:00Z' },
  { _id: 'log_006', level: 'INFO', category: 'ORDER', message: 'Sell order completed for INFY', metadata: { order_id: 'ord_002', price: 1695 }, created_at: '2024-01-15T10:15:00Z' },
  { _id: 'log_007', level: 'INFO', category: 'STRATEGY', message: 'Strategy evaluated: Bank Nifty Momentum', metadata: { strategy_id: 'strat_002', signal: 'NONE' }, created_at: '2024-01-15T10:10:00Z' },
]

export const mockNotifications = [
  { _id: 'notif_001', type: 'order_filled', title: 'Order Filled', message: 'Bought 100 RELIANCE @ ₹2,985', read: false, created_at: '2024-01-15T10:30:00Z' },
  { _id: 'notif_002', type: 'price_alert', title: 'Price Alert', message: 'INFY crossed ₹1,700', read: false, created_at: '2024-01-15T10:25:00Z' },
  { _id: 'notif_003', type: 'order_triggered', title: 'Stop Loss Triggered', message: 'INFY sell order executed at ₹1,695', read: false, created_at: '2024-01-15T10:20:00Z' },
  { _id: 'notif_004', type: 'margin_alert', title: 'Margin Alert', message: 'Available margin below ₹1 lakh', read: true, created_at: '2024-01-15T10:15:00Z' },
  { _id: 'notif_005', type: 'daily_summary', title: 'Daily Summary', message: 'P&L: +₹12,825 | 3 trades', read: true, created_at: '2024-01-15T06:00:00Z' },
]

export const mockBacktestResults = {
  total_return: 25.0,
  annual_return: 25.0,
  total_trades: 150,
  winning_trades: 90,
  losing_trades: 60,
  win_rate: 60.0,
  sharpe_ratio: 1.5,
  max_drawdown: 8.5,
  profit_factor: 1.8,
  avg_trade_duration: 240,
  trades: mockTrades,
  equity_curve: mockDashboardData.performance.daily.map((d, i) => ({
    date: d.date,
    value: 500000 + (i * 5000) + Math.random() * 10000,
  })),
}

export const mockSettings = {
  default_mode: 'paper',
  timezone: 'Asia/Kolkata',
  telegram_enabled: true,
  telegram_chat_id: '123456789',
  notifications: {
    order_filled: true,
    price_alert: true,
    sl_hit: true,
    tp_hit: true,
    margin_alert: true,
    daily_summary: true,
  },
  risk_defaults: {
    max_daily_loss_percent: 5.0,
    risk_per_trade_percent: 1.0,
    max_open_positions: 3,
    max_consecutive_losses: 3,
    max_drawdown_percent: 10.0,
    trade_cooldown_minutes: 5,
  },
  brokers: {
    zerodha: { is_connected: true, testnet_enabled: true },
    upstox: { is_connected: false, testnet_enabled: false },
    angelone: { is_connected: false, testnet_enabled: false },
  },
}

export const mockIndices = {
  NIFTY: { value: 24500.00, change: 125.00, change_percent: 0.51, high: 24600.00, low: 24350.00 },
  SENSEX: { value: 82000.00, change: 245.00, change_percent: 0.30, high: 82250.00, low: 81700.00 },
  BANKNIFTY: { value: 52000.00, change: 380.00, change_percent: 0.74, high: 52200.00, low: 51500.00 },
  FINNIFTY: { value: 21500.00, change: 85.00, change_percent: 0.40, high: 21650.00, low: 21400.00 },
  INDIAVIX: { value: 14.25, change: -0.35, change_percent: -2.40, high: 15.00, low: 13.80 },
}
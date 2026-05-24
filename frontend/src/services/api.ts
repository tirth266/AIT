import { apiClient as api } from '../api/axios'

export { api }

export const watchlistApi = {
  list: (params?: { page?: number; limit?: number }) => api.get('/watchlists', { params }),
  get: (id: string) => api.get(`/watchlists/${id}`),
  create: (data: { name: string; description?: string; symbols?: string[] }) =>
    api.post('/watchlists', data),
  update: (id: string, data: { name?: string; description?: string }) =>
    api.put(`/watchlists/${id}`, data),
  delete: (id: string) => api.delete(`/watchlists/${id}`),
  addStocks: (id: string, data: { symbols: string[] }) => api.post(`/watchlists/${id}/stocks`, data),
  removeStock: (id: string, symbol: string) => api.delete(`/watchlists/${id}/stocks/${symbol}`),
}

export const ordersApi = {
  list: (params?: { status?: string; product?: string; from_date?: string; to_date?: string; symbol?: string; page?: number; limit?: number }) =>
    api.get('/orders', { params }),
  get: (id: string) => api.get(`/orders/${id}`),
  create: (data: {
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
  }) => api.post('/orders', data),
  cancel: (id: string) => api.put(`/orders/${id}/cancel`),
  modify: (id: string, data: { price?: number; quantity?: number; trigger_price?: number }) =>
    api.put(`/orders/${id}/modify`, data),
  history: (params?: { from_date?: string; to_date?: string; page?: number; limit?: number }) =>
    api.get('/orders/history', { params }),
  stats: () => api.get('/orders/stats'),
}

export const tradesApi = {
  list: (params?: { from_date?: string; to_date?: string; symbol?: string; order_id?: string; page?: number; limit?: number }) =>
    api.get('/trades', { params }),
  get: (id: string) => api.get(`/trades/${id}`),
  daily: (params?: { date?: string }) => api.get('/trades/daily', { params }),
}

export const positionsApi = {
  list: (params?: { status?: string; product?: string; page?: number; limit?: number }) => api.get('/positions', { params }),
  get: (id: string) => api.get(`/positions/${id}`),
  open: () => api.get('/positions/open'),
  history: (params?: { from_date?: string; to_date?: string; page?: number; limit?: number }) => api.get('/positions/history', { params }),
  exit: (id: string, data?: { order_type?: string; limit_price?: number }) => api.put(`/positions/${id}/exit`, data),
}

export const signalsApi = {
  list: (params?: { symbol?: string; action?: string; from_date?: string; to_date?: string; page?: number; limit?: number }) =>
    api.get('/signals', { params }),
  get: (id: string) => api.get(`/signals/${id}`),
  live: () => api.get('/signals/live'),
  generate: (data: { symbols: string[]; timeframe?: string; analysis_type?: string }) =>
    api.post('/signals/generate', data),
}

export const fundsApi = {
  get: () => api.get('/funds'),
  ledger: (params?: { from_date?: string; to_date?: string; transaction_type?: string; page?: number; limit?: number }) =>
    api.get('/funds/ledger', { params }),
  add: (data: { amount: number; payment_method?: string; reference?: string }) =>
    api.post('/funds/add', data),
  holdings: () => api.get('/funds/holdings'),
}

export const notificationsApi = {
  list: (params?: { type?: string; is_read?: boolean; priority?: string; limit?: number; skip?: number }) =>
    api.get('/notifications', { params }),
  get: (id: string) => api.get(`/notifications/${id}`),
  create: (data: { type?: string; title: string; message?: string; priority?: string; metadata?: object }) =>
    api.post('/notifications', data),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
  delete: (id: string) => api.delete(`/notifications/${id}`),
  clear: (clearType?: 'read' | 'all') => api.delete('/notifications/clear', { data: { clear_type: clearType } }),
  unreadCount: () => api.get('/notifications/unread-count'),
}

export const engineApi = {
  status: () => api.get('/engine/status'),
  getSignals: (params?: { limit?: number }) => api.get('/engine/signals', { params }),
  generateSignal: (strategyId: string) => api.post('/engine/signals', { strategy_id: strategyId }),
  runBacktest: (data: {
    strategy_id: string
    symbol: string
    start_date: string
    end_date: string
    initial_capital?: number
  }) => api.post('/engine/backtest', data),
  getPaperPortfolio: () => api.get('/engine/paper-trading/portfolio'),
  getPaperTrades: (params?: { status?: string; limit?: number }) =>
    api.get('/engine/paper-trading/trades', { params }),
  getPaperPerformance: (params?: { days?: number }) =>
    api.get('/engine/paper-trading/performance', { params }),
  resetPaperPortfolio: () => api.post('/engine/paper-trading/reset'),
  getRiskSummary: () => api.get('/engine/risk/summary'),
}

export const strategiesApi = {
  list: (params?: { mode?: string; status?: string; symbol?: string; page?: number; limit?: number }) =>
    api.get('/strategies', { params }),
  get: (id: string) => api.get(`/strategies/${id}`),
  create: (data: {
    name: string
    description?: string
    symbol: string
    exchange: string
    timeframe: string
    mode?: 'PAPER' | 'LIVE'
    parameters?: object
    risk_settings?: object
  }) => api.post('/strategies', data),
  update: (id: string, data: object) => api.put(`/strategies/${id}`, data),
  delete: (id: string) => api.delete(`/strategies/${id}`),
  start: (id: string, data?: { mode?: string }) => api.post(`/strategies/${id}/start`, data),
  stop: (id: string) => api.post(`/strategies/${id}/stop`),
  signals: (id: string, params?: { from_date?: string; to_date?: string; page?: number; limit?: number }) =>
    api.get(`/strategies/${id}/signals`, { params }),
}

export const botApi = {
  start: (strategyId: string) => api.post('/bot/start', { strategy_id: strategyId }),
  stop: (strategyId: string) => api.post('/bot/stop', { strategy_id: strategyId }),
  status: () => api.get('/bot/status'),
  mode: (mode: 'paper' | 'live') => api.post('/bot/mode', { mode }),
}

export const brokerApi = {
  connect: (data: { broker: string; api_key: string; api_secret: string; testnet: boolean }) =>
    api.post('/broker/connect', data),
  status: (broker: string) => api.get('/broker/status', { params: { broker } }),
  disconnect: (broker: string) => api.delete('/broker/disconnect', { data: { broker } }),
  balance: (broker: string, mode: string) => api.get('/broker/balance', { params: { broker, mode } }),
}

export const marketApi = {
  quotes: (symbols: string) => api.get('/market/quotes', { params: { symbols } }),
  quote: (symbol: string) => api.get(`/market/quote/${symbol}`),
  depth: (symbol: string) => api.get(`/market/depth/${symbol}`),
  candles: (params: { symbol: string; timeframe: string; from?: string; to?: string; limit?: number }) =>
    api.get('/market/candles', { params }),
  currentCandle: (params: { symbol: string; timeframe: string }) =>
    api.get('/market/current-candle', { params }),
  indicators: (symbol: string) => api.get(`/market/indicators/${symbol}`),
  symbols: (params?: { type?: string }) => api.get('/market/symbols', { params }),
  symbolInfo: (symbol: string) => api.get(`/market/symbol-info/${symbol}`),
  status: () => api.get('/market/status'),
  overview: () => api.get('/market/overview'),
  watchlist: () => api.get('/market/watchlist'),
}

export const backtestApi = {
  run: (data: {
    strategy_id: string
    symbol: string
    timeframe: string
    start_date: string
    end_date: string
    initial_capital: number
    commission_percent?: number
    slippage_percent?: number
  }) => api.post('/backtest/run', data),
  status: (id: string) => api.get(`/backtest/${id}`),
  results: (id: string) => api.get(`/backtest/${id}/results`),
  history: (strategyId?: string) => api.get('/backtest/history', { params: { strategy_id: strategyId } }),
}

export const dashboardApi = {
  summary: () => api.get('/dashboard'),
  performance: (params?: { period?: string }) => api.get('/dashboard/performance', { params }),
  watchlist: (params?: { watchlist_id?: string }) => api.get('/dashboard/watchlist', { params }),
  marketOverview: () => api.get('/dashboard/market-overview'),
}

export const settingsApi = {
  get: () => api.get('/settings'),
  update: (data: object) => api.put('/settings', data),
  user: {
    get: () => api.get('/users/me'),
    update: (data: object) => api.put('/users/me', data),
  },
}

export const logsApi = {
  list: (params?: { level?: string; category?: string; start_date?: string; end_date?: string; limit?: number }) =>
    api.get('/logs', { params }),
}

export const healthApi = {
  health: () => api.get('/health'),
  status: () => api.get('/health/status'),
  ready: () => api.get('/health/ready'),
}

export const tradingApi = {
  engineStatus: () => api.get('/trading/engine/status'),
  
  createOrder: (data: {
    symbol: string
    transaction_type: 'BUY' | 'SELL'
    order_type?: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
    quantity: number
    price?: number
    trigger_price?: number
    product_type?: 'MIS' | 'CNC' | 'NRML'
    exchange?: 'NSE' | 'BSE'
    validity?: 'DAY' | 'IOC' | 'GTD' | 'GTC'
    mode?: 'paper' | 'live'
    disclosed_quantity?: number
    strategy_id?: string
  }) => api.post('/trading/order/create', data),
  
  getOrder: (orderId: string) => api.get(`/trading/order/${orderId}`),
  cancelOrder: (orderId: string, reason?: string) => api.post(`/trading/order/${orderId}/cancel`, { reason }),
  modifyOrder: (orderId: string, data: { price?: number; quantity?: number; trigger_price?: number }) => 
    api.put(`/trading/order/${orderId}/modify`, data),
  
  listOrders: (params?: { status?: string; order_type?: string; symbol?: string; mode?: string; limit?: number }) =>
    api.get('/trading/orders', { params }),
  
  listPositions: (params?: { status?: string; symbol?: string; mode?: string }) =>
    api.get('/trading/positions', { params }),
  getOpenPositions: (params?: { mode?: string }) => api.get('/trading/positions/open', { params }),
  getPosition: (positionId: string) => api.get(`/trading/positions/${positionId}`),
  exitPosition: (positionId: string, data?: { exit_price?: number; quantity?: number }) =>
    api.post(`/trading/positions/${positionId}/exit`, data),
  
  getPnL: (params?: { mode?: string }) => api.get('/trading/pnl', { params }),
  getDayPnL: (params?: { mode?: string }) => api.get('/trading/pnl/day', { params }),
  
  getMargin: () => api.get('/trading/margin'),
  
  getPortfolio: (params?: { mode?: string }) => api.get('/trading/portfolio', { params }),
  getHoldings: (params?: { mode?: string }) => api.get('/trading/portfolio/holdings', { params }),
  
  getTrades: (params?: { symbol?: string; limit?: number }) => api.get('/trading/trades', { params }),
  
  getMarketQuotes: (symbols?: string) => api.get('/trading/market/quotes', { params: { symbols } }),
  getMarketDepth: (symbol: string) => api.get(`/trading/market/depth/${symbol}`),
  
  getRiskEvents: (params?: { limit?: number }) => api.get('/trading/risk/checks', { params }),
  
  runReconciliation: () => api.get('/trading/reconciliation'),
  
  initEngine: () => api.post('/trading/init'),
}

export default api

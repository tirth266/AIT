import { create } from 'zustand'
import { dashboardApi, fundsApi, positionsApi, ordersApi } from '../services/api'
import type { DashboardSummary, PerformanceData, Funds, Position, Order } from '../types'
import { 
  normalizePositions, 
  normalizeOrders, 
  normalizeFunds,
  normalizePnL,
  safeNumber,
  safeTimestamp,
  safeString
} from '../utils/normalization'

export const DEFAULT_DASHBOARD_SUMMARY: DashboardSummary = {
  account: {
    total_balance: 0,
    available_cash: 0,
    used_margin: 0,
    currency: 'INR',
  },
  today: {
    pnl: 0,
    pnl_percent: 0,
    trades: 0,
    buy_trades: 0,
    sell_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
  },
  positions: {
    open: 0,
    total_value: 0,
    unrealized_pnl: 0,
  },
  orders: {
    pending: 0,
    executed_today: 0,
  },
  strategies: {
    active: 0,
    paused: 0,
  },
  alerts: {
    critical: 0,
    warnings: 0,
  },
};

export const normalizeDashboardSummary = (raw: any): DashboardSummary => {
  return {
    account: {
      total_balance: safeNumber(raw?.account?.total_balance),
      available_cash: safeNumber(raw?.account?.available_cash),
      used_margin: safeNumber(raw?.account?.used_margin),
      currency: safeString(raw?.account?.currency, 'INR'),
    },
    today: {
      pnl: safeNumber(raw?.today?.pnl),
      pnl_percent: safeNumber(raw?.today?.pnl_percent),
      trades: safeNumber(raw?.today?.trades),
      buy_trades: safeNumber(raw?.today?.buy_trades),
      sell_trades: safeNumber(raw?.today?.sell_trades),
      winning_trades: safeNumber(raw?.today?.winning_trades),
      losing_trades: safeNumber(raw?.today?.losing_trades),
      win_rate: safeNumber(raw?.today?.win_rate),
    },
    positions: {
      open: safeNumber(raw?.positions?.open),
      total_value: safeNumber(raw?.positions?.total_value),
      unrealized_pnl: safeNumber(raw?.positions?.unrealized_pnl),
    },
    orders: {
      pending: safeNumber(raw?.orders?.pending),
      executed_today: safeNumber(raw?.orders?.executed_today),
    },
    strategies: {
      active: safeNumber(raw?.strategies?.active),
      paused: safeNumber(raw?.strategies?.paused),
    },
    alerts: {
      critical: safeNumber(raw?.alerts?.critical),
      warnings: safeNumber(raw?.alerts?.warnings),
    },
  };
};

export const DEFAULT_PERFORMANCE_DATA: PerformanceData = {
  period: 'WEEK',
  summary: {
    total_pnl: 0,
    total_pnl_percent: 0,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    avg_trade_pnl: 0,
    avg_win: 0,
    avg_loss: 0,
    profit_factor: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
    max_drawdown_percent: 0,
  },
  daily_breakdown: [],
  by_symbol: [],
};

export const normalizePerformanceData = (raw: any): PerformanceData => {
  return {
    period: (raw?.period || 'WEEK').toUpperCase() as any,
    summary: {
      total_pnl: safeNumber(raw?.summary?.total_pnl),
      total_pnl_percent: safeNumber(raw?.summary?.total_pnl_percent),
      total_trades: safeNumber(raw?.summary?.total_trades),
      winning_trades: safeNumber(raw?.summary?.winning_trades),
      losing_trades: safeNumber(raw?.summary?.losing_trades),
      win_rate: safeNumber(raw?.summary?.win_rate),
      avg_trade_pnl: safeNumber(raw?.summary?.avg_trade_pnl),
      avg_win: safeNumber(raw?.summary?.avg_win),
      avg_loss: safeNumber(raw?.summary?.avg_loss),
      profit_factor: safeNumber(raw?.summary?.profit_factor),
      sharpe_ratio: safeNumber(raw?.summary?.sharpe_ratio),
      max_drawdown: safeNumber(raw?.summary?.max_drawdown),
      max_drawdown_percent: safeNumber(raw?.summary?.max_drawdown_percent),
    },
    daily_breakdown: Array.isArray(raw?.daily_breakdown) ? raw.daily_breakdown.map((d: any) => ({
      date: safeTimestamp(d.date),
      pnl: safeNumber(d.pnl),
      pnl_percent: safeNumber(d.pnl_percent),
      trades: safeNumber(d.trades),
      win_rate: safeNumber(d.win_rate),
    })) : [],
    by_symbol: Array.isArray(raw?.by_symbol) ? raw.by_symbol.map((s: any) => ({
      symbol: safeString(s.symbol).toUpperCase(),
      pnl: safeNumber(s.pnl),
      trades: safeNumber(s.trades),
      win_rate: safeNumber(s.win_rate),
    })) : [],
  };
};

export const DEFAULT_FUNDS: Funds = {
  account_id: '',
  broker: '',
  balance: {
    available_cash: 0,
    used_margin: 0,
    total_balance: 0,
    currency: 'INR',
  },
  margin: {
    available_margin: 0,
    used_margin: 0,
    span_margin: 0,
    exposure_margin: 0,
    total_margin_used: 0,
  },
  limits: {
    daily_buy_power: 0,
    daily_sell_power: 0,
  },
  last_updated: new Date(0).toISOString(),
};

interface DashboardState {
  summary: DashboardSummary
  performance: PerformanceData
  funds: Funds
  positions: Position[]
  pendingOrders: Order[]
  isLoading: boolean
  error: string | null
  lastUpdated: string

  fetchSummary: () => Promise<void>
  fetchPerformance: (period?: string) => Promise<void>
  fetchFunds: () => Promise<void>
  fetchPositions: () => Promise<void>
  fetchPendingOrders: () => Promise<void>
  refreshDashboard: () => Promise<void>
  setError: (error: string | null) => void
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  summary: DEFAULT_DASHBOARD_SUMMARY,
  performance: DEFAULT_PERFORMANCE_DATA,
  funds: DEFAULT_FUNDS,
  positions: [],
  pendingOrders: [],
  isLoading: false,
  error: null,
  lastUpdated: new Date(0).toISOString(),

  fetchSummary: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await dashboardApi.summary()
      set({ 
        summary: normalizeDashboardSummary(response.data.data) || DEFAULT_DASHBOARD_SUMMARY, 
        isLoading: false, 
        lastUpdated: new Date().toISOString() 
      })
    } catch (error) {
      console.error('Failed to fetch dashboard summary:', error)
      set({ error: 'Failed to fetch dashboard data', isLoading: false })
    }
  },

  fetchPerformance: async (period = 'WEEK') => {
    try {
      const response = await dashboardApi.performance({ period })
      set({ performance: normalizePerformanceData(response.data.data) || DEFAULT_PERFORMANCE_DATA })
    } catch (error) {
      console.error('Failed to fetch performance:', error)
    }
  },

  fetchFunds: async () => {
    try {
      const response = await fundsApi.get()
      set({ funds: normalizeFunds(response.data.data) || DEFAULT_FUNDS })
    } catch (error) {
      console.error('Failed to fetch funds:', error)
    }
  },

  fetchPositions: async () => {
    try {
      const response = await positionsApi.open()
      set({ positions: normalizePositions(response.data.data) })
    } catch (error) {
      console.error('Failed to fetch positions:', error)
    }
  },

  fetchPendingOrders: async () => {
    try {
      const response = await ordersApi.list({ status: 'PENDING', limit: 10 })
      set({ pendingOrders: normalizeOrders(response.data.data) })
    } catch (error) {
      console.error('Failed to fetch pending orders:', error)
    }
  },

  refreshDashboard: async () => {
    const { fetchSummary, fetchFunds, fetchPositions, fetchPendingOrders, fetchPerformance } = get()
    set({ isLoading: true })
    await Promise.all([
      fetchSummary(),
      fetchFunds(),
      fetchPositions(),
      fetchPendingOrders(),
      fetchPerformance('WEEK'),
    ])
    set({ isLoading: false })
  },

  setError: (error) => set({ error }),
}))

export default useDashboardStore
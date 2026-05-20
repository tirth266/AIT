import { create } from 'zustand'
import { engineApi } from '../services/api'
import type {
  EngineStatus,
  EngineMetrics,
  StrategySignal,
  BacktestResult,
  PaperPortfolio,
  PaperTrade,
  PaperPerformance,
  RiskSummary,
} from '../types'
import { 
  safeNumber, 
  safeString, 
  safeTimestamp, 
  normalizeSymbol 
} from '../utils/normalization'

export const DEFAULT_ENGINE_METRICS: EngineMetrics = {
  total_strategies: 0,
  active_strategies: 0,
  signals_generated: 0,
  signals_executed: 0,
  total_pnl: 0,
  uptime_seconds: 0,
  errors_count: 0,
};

export const DEFAULT_ENGINE_STATUS: EngineStatus = {
  status: 'stopped',
  metrics: DEFAULT_ENGINE_METRICS,
  strategies: [],
};

export const normalizeEngineStatus = (raw: any): EngineStatus => {
  return {
    status: (raw?.status || 'stopped') as any,
    metrics: {
      total_strategies: safeNumber(raw?.metrics?.total_strategies),
      active_strategies: safeNumber(raw?.metrics?.active_strategies),
      signals_generated: safeNumber(raw?.metrics?.signals_generated),
      signals_executed: safeNumber(raw?.metrics?.signals_executed),
      total_pnl: safeNumber(raw?.metrics?.total_pnl),
      uptime_seconds: safeNumber(raw?.metrics?.uptime_seconds),
      errors_count: safeNumber(raw?.metrics?.errors_count),
    },
    strategies: Array.isArray(raw?.strategies) ? raw.strategies.map((s: any) => ({
      strategy_id: safeString(s.strategy_id),
      name: safeString(s.name),
      status: safeString(s.status) as any,
      symbol: normalizeSymbol(s.symbol),
      timeframe: safeString(s.timeframe),
      trades_count: safeNumber(s.trades_count),
      last_signal_time: s.last_signal_time ? safeTimestamp(s.last_signal_time) : undefined,
    })) : [],
  };
};

export const DEFAULT_PAPER_PORTFOLIO: PaperPortfolio = {
  user_id: '',
  cash: 0,
  initial_capital: 0,
  open_positions: 0,
  created_at: new Date(0).toISOString(),
};

export const normalizePaperPortfolio = (raw: any): PaperPortfolio => {
  return {
    portfolio_id: raw?.portfolio_id ? safeString(raw.portfolio_id) : undefined,
    user_id: safeString(raw?.user_id),
    cash: safeNumber(raw?.cash),
    initial_capital: safeNumber(raw?.initial_capital),
    total_pnl: raw?.total_pnl ? safeNumber(raw.total_pnl) : undefined,
    open_positions: safeNumber(raw?.open_positions),
    created_at: safeTimestamp(raw?.created_at),
    updated_at: raw?.updated_at ? safeTimestamp(raw.updated_at) : undefined,
  };
};

export const DEFAULT_PAPER_PERFORMANCE: PaperPerformance = {
  total_trades: 0,
  winning_trades: 0,
  losing_trades: 0,
  win_rate: 0,
  total_pnl: 0,
  current_capital: 0,
  return_percent: 0,
  avg_pnl: 0,
};

export const normalizePaperPerformance = (raw: any): PaperPerformance => {
  return {
    total_trades: safeNumber(raw?.total_trades),
    winning_trades: safeNumber(raw?.winning_trades),
    losing_trades: safeNumber(raw?.losing_trades),
    win_rate: safeNumber(raw?.win_rate),
    total_pnl: safeNumber(raw?.total_pnl),
    current_capital: safeNumber(raw?.current_capital),
    return_percent: safeNumber(raw?.return_percent),
    avg_pnl: safeNumber(raw?.avg_pnl),
  };
};

export const DEFAULT_RISK_SUMMARY: RiskSummary = {
  daily_pnl: 0,
  open_positions: 0,
  trades_today: 0,
  risk_status: 'normal',
};

export const normalizeRiskSummary = (raw: any): RiskSummary => {
  return {
    daily_pnl: safeNumber(raw?.daily_pnl),
    open_positions: safeNumber(raw?.open_positions),
    trades_today: safeNumber(raw?.trades_today),
    risk_status: (raw?.risk_status || 'normal') as any,
  };
};

export const normalizeStrategySignal = (raw: any): StrategySignal => {
  return {
    signal_id: safeString(raw?.signal_id),
    strategy_id: safeString(raw?.strategy_id),
    symbol: normalizeSymbol(raw?.symbol),
    action: (raw?.action || 'BUY').toUpperCase() as any,
    price: safeNumber(raw?.price),
    quantity: safeNumber(raw?.quantity),
    confidence: safeNumber(raw?.confidence),
    reasoning: safeString(raw?.reasoning),
    timestamp: safeTimestamp(raw?.timestamp),
    executed: !!raw?.executed,
    order_id: raw?.order_id ? safeString(raw.order_id) : undefined,
  };
};

interface EngineState {
  status: EngineStatus
  signals: StrategySignal[]
  backtestResults: BacktestResult[]
  paperPortfolio: PaperPortfolio
  paperTrades: PaperTrade[]
  paperPerformance: PaperPerformance
  riskSummary: RiskSummary
  isLoading: boolean
  isRunningBacktest: boolean
  error: string | null

  fetchEngineStatus: () => Promise<void>
  fetchSignals: (limit?: number) => Promise<void>
  generateSignal: (strategyId: string) => Promise<StrategySignal | null>
  runBacktest: (data: {
    strategy_id: string
    symbol: string
    start_date: string
    end_date: string
    initial_capital?: number
  }) => Promise<BacktestResult | null>
  fetchPaperPortfolio: () => Promise<void>
  fetchPaperTrades: (status?: string, limit?: number) => Promise<void>
  fetchPaperPerformance: (days?: number) => Promise<void>
  resetPaperPortfolio: () => Promise<boolean>
  fetchRiskSummary: () => Promise<void>
  clearError: () => void
  updateSignalFromWS: (signal: StrategySignal) => void
}

export const useEngineStore = create<EngineState>((set, get) => ({
  status: DEFAULT_ENGINE_STATUS,
  signals: [],
  backtestResults: [],
  paperPortfolio: DEFAULT_PAPER_PORTFOLIO,
  paperTrades: [],
  paperPerformance: DEFAULT_PAPER_PERFORMANCE,
  riskSummary: DEFAULT_RISK_SUMMARY,
  isLoading: false,
  isRunningBacktest: false,
  error: null,

  fetchEngineStatus: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await engineApi.status()
      set({ status: normalizeEngineStatus(response.data) || DEFAULT_ENGINE_STATUS, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch engine status:', error)
      set({ error: 'Failed to fetch engine status', isLoading: false })
    }
  },

  fetchSignals: async (limit = 50) => {
    try {
      const response = await engineApi.getSignals({ limit })
      const signals = Array.isArray(response.data.signals) 
        ? response.data.signals.map(normalizeStrategySignal) 
        : [];
      set({ signals })
    } catch (error) {
      console.error('Failed to fetch signals:', error)
    }
  },

  generateSignal: async (strategyId: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await engineApi.generateSignal(strategyId)
      if (response.data.signal) {
        const signal = normalizeStrategySignal(response.data.signal)
        set((state) => ({
          signals: [signal, ...state.signals],
          isLoading: false,
        }))
        return signal
      }
      set({ isLoading: false })
      return null
    } catch (error) {
      console.error('Failed to generate signal:', error)
      set({ error: 'Failed to generate signal', isLoading: false })
      return null
    }
  },

  runBacktest: async (data) => {
    set({ isRunningBacktest: true, error: null })
    try {
      const response = await engineApi.runBacktest(data)
      const result = response.data.backtest
      if (result) {
        set((state) => ({
          backtestResults: [result, ...state.backtestResults],
          isRunningBacktest: false,
        }))
        return result
      }
      set({ isRunningBacktest: false })
      return null
    } catch (error) {
      console.error('Failed to run backtest:', error)
      set({ error: 'Failed to run backtest', isRunningBacktest: false })
      return null
    }
  },

  fetchPaperPortfolio: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await engineApi.getPaperPortfolio()
      set({ paperPortfolio: normalizePaperPortfolio(response.data.portfolio) || DEFAULT_PAPER_PORTFOLIO, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch paper portfolio:', error)
      set({ error: 'Failed to fetch paper portfolio', isLoading: false })
    }
  },

  fetchPaperTrades: async (status = 'all', limit = 50) => {
    try {
      const response = await engineApi.getPaperTrades({ status, limit })
      const paperTrades = Array.isArray(response.data.trades) ? response.data.trades.map((t: any) => ({
        ...t,
        symbol: normalizeSymbol(t.symbol),
        quantity: safeNumber(t.quantity),
        entry_price: safeNumber(t.entry_price),
        pnl: safeNumber(t.pnl),
        opened_at: safeTimestamp(t.opened_at),
      })) : [];
      set({ paperTrades })
    } catch (error) {
      console.error('Failed to fetch paper trades:', error)
    }
  },

  fetchPaperPerformance: async (days = 30) => {
    try {
      const response = await engineApi.getPaperPerformance({ days })
      set({ paperPerformance: normalizePaperPerformance(response.data.performance) || DEFAULT_PAPER_PERFORMANCE })
    } catch (error) {
      console.error('Failed to fetch paper performance:', error)
    }
  },

  resetPaperPortfolio: async () => {
    set({ isLoading: true, error: null })
    try {
      await engineApi.resetPaperPortfolio()
      set({ isLoading: false })
      await get().fetchPaperPortfolio()
      return true
    } catch (error) {
      console.error('Failed to reset paper portfolio:', error)
      set({ error: 'Failed to reset paper portfolio', isLoading: false })
      return false
    }
  },

  fetchRiskSummary: async () => {
    try {
      const response = await engineApi.getRiskSummary()
      set({ riskSummary: normalizeRiskSummary(response.data.risk) || DEFAULT_RISK_SUMMARY })
    } catch (error) {
      console.error('Failed to fetch risk summary:', error)
    }
  },

  clearError: () => set({ error: null }),

  updateSignalFromWS: (signal) => {
    const normalized = normalizeStrategySignal(signal)
    set((state) => ({
      signals: [normalized, ...state.signals.filter(s => s.signal_id !== normalized.signal_id)],
    }))
  },
}))

export default useEngineStore

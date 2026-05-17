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

interface EngineState {
  status: EngineStatus | null
  signals: StrategySignal[]
  backtestResults: BacktestResult[]
  paperPortfolio: PaperPortfolio | null
  paperTrades: PaperTrade[]
  paperPerformance: PaperPerformance | null
  riskSummary: RiskSummary | null
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
  status: null,
  signals: [],
  backtestResults: [],
  paperPortfolio: null,
  paperTrades: [],
  paperPerformance: null,
  riskSummary: null,
  isLoading: false,
  isRunningBacktest: false,
  error: null,

  fetchEngineStatus: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await engineApi.status()
      set({ status: response.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch engine status:', error)
      set({ error: 'Failed to fetch engine status', isLoading: false })
    }
  },

  fetchSignals: async (limit = 50) => {
    try {
      const response = await engineApi.getSignals({ limit })
      set({ signals: response.data.signals || [] })
    } catch (error) {
      console.error('Failed to fetch signals:', error)
    }
  },

  generateSignal: async (strategyId: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await engineApi.generateSignal(strategyId)
      if (response.data.signal) {
        const signal = response.data.signal
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
      set({ paperPortfolio: response.data.portfolio, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch paper portfolio:', error)
      set({ error: 'Failed to fetch paper portfolio', isLoading: false })
    }
  },

  fetchPaperTrades: async (status = 'all', limit = 50) => {
    try {
      const response = await engineApi.getPaperTrades({ status, limit })
      set({ paperTrades: response.data.trades || [] })
    } catch (error) {
      console.error('Failed to fetch paper trades:', error)
    }
  },

  fetchPaperPerformance: async (days = 30) => {
    try {
      const response = await engineApi.getPaperPerformance({ days })
      set({ paperPerformance: response.data.performance })
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
      set({ riskSummary: response.data.risk })
    } catch (error) {
      console.error('Failed to fetch risk summary:', error)
    }
  },

  clearError: () => set({ error: null }),

  updateSignalFromWS: (signal) => {
    set((state) => ({
      signals: [signal, ...state.signals.filter(s => s.signal_id !== signal.signal_id)],
    }))
  },
}))

export default useEngineStore
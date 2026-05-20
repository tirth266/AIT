import { create } from 'zustand'
import { strategiesApi } from '../services/api'
import type { Strategy, CreateStrategyRequest } from '../types'
import { 
  safeNumber, 
  safeString, 
  safeTimestamp, 
  normalizeSymbol,
  normalizeStrategy,
  normalizeStrategies
} from '../utils/normalization'

export const DEFAULT_STRATEGY: Strategy = {
  strategy_id: '',
  name: '',
  symbol: '',
  exchange: 'NSE',
  timeframe: '5m',
  mode: 'PAPER',
  status: 'PAUSED',
  parameters: {},
  risk_settings: {
    max_position_size: 0,
    stop_loss_percent: 0,
    target_percent: 0,
    max_daily_loss: 0,
  },
  created_at: new Date(0).toISOString(),
};

export const DEFAULT_PAGINATION = {
  page: 1,
  limit: 20,
  total: 0,
  pages: 0,
};

interface StrategiesState {
  strategies: Strategy[]
  selectedStrategy: Strategy
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }

  fetchStrategies: (params?: { mode?: string; status?: string; symbol?: string; page?: number; limit?: number }) => Promise<void>
  fetchStrategy: (id: string) => Promise<void>
  createStrategy: (data: CreateStrategyRequest) => Promise<Strategy | null>
  updateStrategy: (id: string, data: object) => Promise<void>
  deleteStrategy: (id: string) => Promise<void>
  startStrategy: (id: string, mode?: string) => Promise<void>
  stopStrategy: (id: string) => Promise<void>
  updateStrategyFromWS: (strategy: { strategy_id: string; status: string }) => void
  setSelectedStrategy: (strategy: Strategy) => void
  clearError: () => void
}

export const useStrategiesStore = create<StrategiesState>((set, get) => ({
  strategies: [],
  selectedStrategy: DEFAULT_STRATEGY,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: DEFAULT_PAGINATION,

  fetchStrategies: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await strategiesApi.list(params)
      const rawPagination = response.data.pagination;
      set({
        strategies: normalizeStrategies(response.data.data),
        pagination: {
          page: safeNumber(rawPagination?.page, 1),
          limit: safeNumber(rawPagination?.limit, 20),
          total: safeNumber(rawPagination?.total, 0),
          pages: safeNumber(rawPagination?.pages, 0),
        } || DEFAULT_PAGINATION,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch strategies:', error)
      set({ error: 'Failed to fetch strategies', isLoading: false })
    }
  },

  fetchStrategy: async (id) => {
    set({ isLoading: true })
    try {
      const response = await strategiesApi.get(id)
      set({ selectedStrategy: normalizeStrategy(response.data.data) || DEFAULT_STRATEGY, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch strategy:', error)
      set({ error: 'Failed to fetch strategy details', isLoading: false })
    }
  },

  createStrategy: async (data) => {
    set({ isSubmitting: true, error: null })
    try {
      const response = await strategiesApi.create(data)
      const newStrategy = normalizeStrategy(response.data.data)
      set((state) => ({
        strategies: [newStrategy, ...state.strategies],
        isSubmitting: false,
      }))
      return newStrategy
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } }
      const errorMessage = err.response?.data?.message || 'Failed to create strategy'
      console.error('Failed to create strategy:', error)
      set({ error: errorMessage, isSubmitting: false })
      return null
    }
  },

  updateStrategy: async (id, data) => {
    set({ isSubmitting: true })
    try {
      await strategiesApi.update(id, data)
      set((state) => ({
        strategies: state.strategies.map((s) =>
          s.strategy_id === id ? { ...s, ...data } : s
        ),
        selectedStrategy: state.selectedStrategy.strategy_id === id
          ? { ...state.selectedStrategy, ...data }
          : state.selectedStrategy,
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to update strategy:', error)
      set({ error: 'Failed to update strategy', isSubmitting: false })
    }
  },

  deleteStrategy: async (id) => {
    try {
      await strategiesApi.delete(id)
      set((state) => ({
        strategies: state.strategies.filter((s) => s.strategy_id !== id),
        selectedStrategy: state.selectedStrategy.strategy_id === id ? DEFAULT_STRATEGY : state.selectedStrategy,
      }))
    } catch (error) {
      console.error('Failed to delete strategy:', error)
      set({ error: 'Failed to delete strategy' })
    }
  },

  startStrategy: async (id, mode = 'PAPER') => {
    set({ isSubmitting: true })
    try {
      await strategiesApi.start(id, { mode })
      set((state) => ({
        strategies: state.strategies.map((s) =>
          s.strategy_id === id ? { ...s, status: 'ACTIVE' as const, mode: mode as 'PAPER' | 'LIVE' } : s
        ),
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to start strategy:', error)
      set({ error: 'Failed to start strategy', isSubmitting: false })
    }
  },

  stopStrategy: async (id) => {
    set({ isSubmitting: true })
    try {
      await strategiesApi.stop(id)
      set((state) => ({
        strategies: state.strategies.map((s) =>
          s.strategy_id === id ? { ...s, status: 'PAUSED' as const } : s
        ),
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to stop strategy:', error)
      set({ error: 'Failed to stop strategy', isSubmitting: false })
    }
  },

  updateStrategyFromWS: (data) => {
    set((state) => ({
      strategies: state.strategies.map((s) =>
        s.strategy_id === data.strategy_id
          ? { ...s, status: data.status as 'ACTIVE' | 'PAUSED' }
          : s
      ),
    }))
  },

  setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy || DEFAULT_STRATEGY }),

  clearError: () => set({ error: null }),
}))

export default useStrategiesStore
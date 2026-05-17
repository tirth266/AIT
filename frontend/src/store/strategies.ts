import { create } from 'zustand'
import { strategiesApi } from '../services/api'
import type { Strategy, CreateStrategyRequest } from '../types'

interface StrategiesState {
  strategies: Strategy[]
  selectedStrategy: Strategy | null
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
  setSelectedStrategy: (strategy: Strategy | null) => void
  clearError: () => void
}

export const useStrategiesStore = create<StrategiesState>((set, get) => ({
  strategies: [],
  selectedStrategy: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: { page: 1, limit: 20, total: 0, pages: 0 },

  fetchStrategies: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await strategiesApi.list(params)
      set({
        strategies: response.data.data,
        pagination: response.data.pagination || { page: 1, limit: 20, total: 0, pages: 0 },
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
      set({ selectedStrategy: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch strategy:', error)
      set({ error: 'Failed to fetch strategy details', isLoading: false })
    }
  },

  createStrategy: async (data) => {
    set({ isSubmitting: true, error: null })
    try {
      const response = await strategiesApi.create(data)
      const newStrategy = response.data.data
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
        selectedStrategy: state.selectedStrategy?.strategy_id === id
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
        selectedStrategy: state.selectedStrategy?.strategy_id === id ? null : state.selectedStrategy,
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

  setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy }),

  clearError: () => set({ error: null }),
}))

export default useStrategiesStore
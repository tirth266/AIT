import { create } from 'zustand'
import { positionsApi } from '../services/api'
import type { Position, PositionSummary } from '../types'
import { normalizePosition, normalizePositions, safeNumber } from '../utils/normalization'

export const DEFAULT_POSITION_SUMMARY: PositionSummary = {
  total_positions: 0,
  total_value: 0,
  total_pnl: 0,
  day_pnl: 0,
};

export const DEFAULT_PAGINATION = {
  page: 1,
  limit: 50,
  total: 0,
  pages: 0,
};

export const normalizePositionSummary = (raw: any): PositionSummary => {
  return {
    total_positions: safeNumber(raw?.total_positions),
    total_value: safeNumber(raw?.total_value),
    total_pnl: safeNumber(raw?.total_pnl),
    day_pnl: safeNumber(raw?.day_pnl),
  };
};

interface PositionsState {
  positions: Position[]
  historyPositions: Position[]
  selectedPosition: Position | null
  summary: PositionSummary
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }

  fetchPositions: (params?: { status?: string; product?: string; page?: number; limit?: number }) => Promise<void>
  fetchOpenPositions: () => Promise<void>
  fetchPosition: (id: string) => Promise<void>
  fetchHistory: (params?: { from_date?: string; to_date?: string; page?: number; limit?: number }) => Promise<void>
  exitPosition: (id: string, data?: { order_type?: string; limit_price?: number }) => Promise<void>
  updatePositionFromWS: (position: Position) => void
  removePositionFromWS: (id: string) => void
  setSelectedPosition: (position: Position | null) => void
  clearError: () => void
}

export const usePositionsStore = create<PositionsState>((set, get) => ({
  positions: [],
  historyPositions: [],
  selectedPosition: null,
  summary: DEFAULT_POSITION_SUMMARY,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: DEFAULT_PAGINATION,

  fetchPositions: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await positionsApi.list(params)
      const rawPagination = response.data.pagination;
      set({
        positions: normalizePositions(response.data.data),
        summary: normalizePositionSummary(response.data.summary) || DEFAULT_POSITION_SUMMARY,
        pagination: {
          page: safeNumber(rawPagination?.page, 1),
          limit: safeNumber(rawPagination?.limit, 50),
          total: safeNumber(rawPagination?.total, 0),
          pages: safeNumber(rawPagination?.pages, 0),
        } || DEFAULT_PAGINATION,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch positions:', error)
      set({ error: 'Failed to fetch positions', isLoading: false })
    }
  },

  fetchOpenPositions: async () => {
    set({ isLoading: true })
    try {
      const response = await positionsApi.open()
      set({
        positions: normalizePositions(response.data.data),
        summary: normalizePositionSummary(response.data.summary) || DEFAULT_POSITION_SUMMARY,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch open positions:', error)
      set({ error: 'Failed to fetch open positions', isLoading: false })
    }
  },

  fetchPosition: async (id) => {
    set({ isLoading: true })
    try {
      const response = await positionsApi.get(id)
      set({ selectedPosition: normalizePosition(response.data.data), isLoading: false })
    } catch (error) {
      console.error('Failed to fetch position:', error)
      set({ error: 'Failed to fetch position details', isLoading: false })
    }
  },

  fetchHistory: async (params = {}) => {
    set({ isLoading: true })
    try {
      const response = await positionsApi.history(params)
      const rawPagination = response.data.pagination;
      set({
        historyPositions: normalizePositions(response.data.data),
        pagination: {
          page: safeNumber(rawPagination?.page, 1),
          limit: safeNumber(rawPagination?.limit, 50),
          total: safeNumber(rawPagination?.total, 0),
          pages: safeNumber(rawPagination?.pages, 0),
        } || DEFAULT_PAGINATION,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch position history:', error)
      set({ error: 'Failed to fetch position history', isLoading: false })
    }
  },

  exitPosition: async (id, data) => {
    set({ isSubmitting: true })
    try {
      await positionsApi.exit(id, data)
      set((state) => ({
        positions: state.positions.filter((p) => p.position_id !== id),
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to exit position:', error)
      set({ error: 'Failed to exit position', isSubmitting: false })
    }
  },

  updatePositionFromWS: (position) => {
    const normalizedPosition = normalizePosition(position)
    set((state) => ({
      positions: state.positions.map((p) =>
        p.position_id === normalizedPosition.position_id ? normalizedPosition : p
      ),
      selectedPosition: state.selectedPosition?.position_id === normalizedPosition.position_id ? normalizedPosition : state.selectedPosition,
    }))
  },

  removePositionFromWS: (id) => {
    set((state) => ({
      positions: state.positions.filter((p) => p.position_id !== id),
      selectedPosition: state.selectedPosition?.position_id === id ? null : state.selectedPosition,
    }))
  },

  setSelectedPosition: (position) => set({ selectedPosition: position ? normalizePosition(position) : null }),

  clearError: () => set({ error: null }),
}))

export default usePositionsStore
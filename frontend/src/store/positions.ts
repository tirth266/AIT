import { create } from 'zustand'
import { positionsApi } from '../services/api'
import type { Position, PositionSummary } from '../types'

interface PositionsState {
  positions: Position[]
  historyPositions: Position[]
  selectedPosition: Position | null
  summary: PositionSummary | null
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
  summary: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: { page: 1, limit: 50, total: 0, pages: 0 },

  fetchPositions: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await positionsApi.list(params)
      set({
        positions: response.data.data,
        summary: response.data.summary,
        pagination: response.data.pagination || { page: 1, limit: 50, total: 0, pages: 0 },
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
        positions: response.data.data,
        summary: response.data.summary,
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
      set({ selectedPosition: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch position:', error)
      set({ error: 'Failed to fetch position details', isLoading: false })
    }
  },

  fetchHistory: async (params = {}) => {
    set({ isLoading: true })
    try {
      const response = await positionsApi.history(params)
      set({
        historyPositions: response.data.data,
        pagination: response.data.pagination || { page: 1, limit: 50, total: 0, pages: 0 },
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
    set((state) => ({
      positions: state.positions.map((p) =>
        p.position_id === position.position_id ? position : p
      ),
      selectedPosition: state.selectedPosition?.position_id === position.position_id ? position : state.selectedPosition,
    }))
  },

  removePositionFromWS: (id) => {
    set((state) => ({
      positions: state.positions.filter((p) => p.position_id !== id),
      selectedPosition: state.selectedPosition?.position_id === id ? null : state.selectedPosition,
    }))
  },

  setSelectedPosition: (position) => set({ selectedPosition: position }),

  clearError: () => set({ error: null }),
}))

export default usePositionsStore
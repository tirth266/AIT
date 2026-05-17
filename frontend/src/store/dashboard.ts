import { create } from 'zustand'
import { dashboardApi, fundsApi, positionsApi, ordersApi } from '../services/api'
import type { DashboardSummary, PerformanceData, Funds, Position, Order } from '../types'

interface DashboardState {
  summary: DashboardSummary | null
  performance: PerformanceData | null
  funds: Funds | null
  positions: Position[]
  pendingOrders: Order[]
  isLoading: boolean
  error: string | null
  lastUpdated: string | null

  fetchSummary: () => Promise<void>
  fetchPerformance: (period?: string) => Promise<void>
  fetchFunds: () => Promise<void>
  fetchPositions: () => Promise<void>
  fetchPendingOrders: () => Promise<void>
  refreshDashboard: () => Promise<void>
  setError: (error: string | null) => void
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  summary: null,
  performance: null,
  funds: null,
  positions: [],
  pendingOrders: [],
  isLoading: false,
  error: null,
  lastUpdated: null,

  fetchSummary: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await dashboardApi.summary()
      set({ summary: response.data.data, isLoading: false, lastUpdated: new Date().toISOString() })
    } catch (error) {
      console.error('Failed to fetch dashboard summary:', error)
      set({ error: 'Failed to fetch dashboard data', isLoading: false })
    }
  },

  fetchPerformance: async (period = 'WEEK') => {
    try {
      const response = await dashboardApi.performance({ period })
      set({ performance: response.data.data })
    } catch (error) {
      console.error('Failed to fetch performance:', error)
    }
  },

  fetchFunds: async () => {
    try {
      const response = await fundsApi.get()
      set({ funds: response.data.data })
    } catch (error) {
      console.error('Failed to fetch funds:', error)
    }
  },

  fetchPositions: async () => {
    try {
      const response = await positionsApi.open()
      set({ positions: response.data.data })
    } catch (error) {
      console.error('Failed to fetch positions:', error)
    }
  },

  fetchPendingOrders: async () => {
    try {
      const response = await ordersApi.list({ status: 'PENDING', limit: 10 })
      set({ pendingOrders: response.data.data })
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
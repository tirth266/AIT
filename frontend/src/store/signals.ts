import { create } from 'zustand'
import { signalsApi } from '../services/api'
import type { Signal, LiveSignalsSummary, SignalGenerationRequest } from '../types'

interface SignalsState {
  signals: Signal[]
  liveSignals: Signal[]
  liveSummary: LiveSignalsSummary | null
  selectedSignal: Signal | null
  isLoading: boolean
  isGenerating: boolean
  error: string | null
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }

  fetchSignals: (params?: { symbol?: string; action?: string; from_date?: string; to_date?: string; page?: number; limit?: number }) => Promise<void>
  fetchLiveSignals: () => Promise<void>
  fetchSignal: (id: string) => Promise<void>
  generateSignals: (data: SignalGenerationRequest) => Promise<void>
  addSignalFromWS: (signal: Signal) => void
  setSelectedSignal: (signal: Signal | null) => void
  clearError: () => void
}

export const useSignalsStore = create<SignalsState>((set, get) => ({
  signals: [],
  liveSignals: [],
  liveSummary: null,
  selectedSignal: null,
  isLoading: false,
  isGenerating: false,
  error: null,
  pagination: { page: 1, limit: 20, total: 0, pages: 0 },

  fetchSignals: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await signalsApi.list(params)
      set({
        signals: response.data.data,
        pagination: response.data.pagination || { page: 1, limit: 20, total: 0, pages: 0 },
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch signals:', error)
      set({ error: 'Failed to fetch signals', isLoading: false })
    }
  },

  fetchLiveSignals: async () => {
    set({ isLoading: true })
    try {
      const response = await signalsApi.live()
      set({
        liveSignals: response.data.data,
        liveSummary: response.data.summary,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch live signals:', error)
      set({ error: 'Failed to fetch live signals', isLoading: false })
    }
  },

  fetchSignal: async (id) => {
    set({ isLoading: true })
    try {
      const response = await signalsApi.get(id)
      set({ selectedSignal: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch signal:', error)
      set({ error: 'Failed to fetch signal details', isLoading: false })
    }
  },

  generateSignals: async (data) => {
    set({ isGenerating: true, error: null })
    try {
      await signalsApi.generate(data)
      await get().fetchLiveSignals()
      set({ isGenerating: false })
    } catch (error) {
      console.error('Failed to generate signals:', error)
      set({ error: 'Failed to generate signals', isGenerating: false })
    }
  },

  addSignalFromWS: (signal) => {
    set((state) => ({
      liveSignals: [signal, ...state.liveSignals.filter((s) => s.signal_id !== signal.signal_id)],
    }))
  },

  setSelectedSignal: (signal) => set({ selectedSignal: signal }),

  clearError: () => set({ error: null }),
}))

export default useSignalsStore
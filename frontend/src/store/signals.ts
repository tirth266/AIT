import { create } from 'zustand'
import { signalsApi } from '../services/api'
import type { Signal, LiveSignalsSummary, SignalGenerationRequest } from '../types'
import { safeNumber, safeString, safeTimestamp, normalizeSymbol } from '../utils/normalization'

export const DEFAULT_LIVE_SIGNALS_SUMMARY: LiveSignalsSummary = {
  total_signals: 0,
  buy_signals: 0,
  sell_signals: 0,
  avg_confidence: 0,
};

export const normalizeSignal = (raw: any): Signal => {
  return {
    signal_id: safeString(raw?.signal_id),
    symbol: normalizeSymbol(raw?.symbol),
    exchange: safeString(raw?.exchange, 'NSE'),
    action: (raw?.action || 'BUY').toUpperCase() as any,
    confidence: safeNumber(raw?.confidence),
    target_price: safeNumber(raw?.target_price),
    stop_loss: safeNumber(raw?.stop_loss),
    entry_range: {
      min: safeNumber(raw?.entry_range?.min),
      max: safeNumber(raw?.entry_range?.max),
    },
    reasoning: safeString(raw?.reasoning),
    indicators: raw?.indicators || {},
    timeframe: safeString(raw?.timeframe),
    generated_at: safeTimestamp(raw?.generated_at),
    expires_at: safeTimestamp(raw?.expires_at),
    status: (raw?.status || 'ACTIVE').toUpperCase() as any,
  };
};

export const normalizeSignals = (rawArray: any): Signal[] => {
  if (!Array.isArray(rawArray)) return [];
  return rawArray.map(normalizeSignal);
};

export const normalizeLiveSignalsSummary = (raw: any): LiveSignalsSummary => {
  return {
    total_signals: safeNumber(raw?.total_signals),
    buy_signals: safeNumber(raw?.buy_signals),
    sell_signals: safeNumber(raw?.sell_signals),
    avg_confidence: safeNumber(raw?.avg_confidence),
  };
};

interface SignalsState {
  signals: Signal[]
  liveSignals: Signal[]
  liveSummary: LiveSignalsSummary
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
  liveSummary: DEFAULT_LIVE_SIGNALS_SUMMARY,
  selectedSignal: null,
  isLoading: false,
  isGenerating: false,
  error: null,
  pagination: { page: 1, limit: 20, total: 0, pages: 0 },

  fetchSignals: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await signalsApi.list(params)
      const rawPagination = response.data.pagination;
      set({
        signals: normalizeSignals(response.data.data),
        pagination: {
          page: safeNumber(rawPagination?.page, 1),
          limit: safeNumber(rawPagination?.limit, 20),
          total: safeNumber(rawPagination?.total, 0),
          pages: safeNumber(rawPagination?.pages, 0),
        },
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
        liveSignals: normalizeSignals(response.data.data),
        liveSummary: normalizeLiveSignalsSummary(response.data.summary) || DEFAULT_LIVE_SIGNALS_SUMMARY,
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
      set({ selectedSignal: normalizeSignal(response.data.data), isLoading: false })
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
    const normalized = normalizeSignal(signal)
    set((state) => ({
      liveSignals: [normalized, ...state.liveSignals.filter((s) => s.signal_id !== normalized.signal_id)],
    }))
  },

  setSelectedSignal: (signal) => set({ selectedSignal: signal ? normalizeSignal(signal) : null }),

  clearError: () => set({ error: null }),
}))

export default useSignalsStore

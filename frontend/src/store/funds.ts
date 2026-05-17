import { create } from 'zustand'
import { fundsApi } from '../services/api'
import type { Funds as FundsData, Transaction, Holding, HoldingsSummary } from '../types'

interface FundsState {
  funds: FundsData | null
  transactions: Transaction[]
  holdings: Holding[]
  holdingsSummary: HoldingsSummary | null
  isLoading: boolean
  error: string | null

  fetchFunds: () => Promise<void>
  fetchLedger: (params?: { from_date?: string; to_date?: string; transaction_type?: string; page?: number; limit?: number }) => Promise<void>
  addFunds: (data: { amount: number; payment_method?: string; reference?: string }) => Promise<boolean>
  fetchHoldings: () => Promise<void>
  setError: (error: string | null) => void
}

export const useFundsStore = create<FundsState>((set) => ({
  funds: null,
  transactions: [],
  holdings: [],
  holdingsSummary: null,
  isLoading: false,
  error: null,

  fetchFunds: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fundsApi.get()
      set({ funds: response.data.data, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch funds', isLoading: false })
      console.error('Failed to fetch funds:', error)
    }
  },

  fetchLedger: async (params = {}) => {
    set({ isLoading: true })
    try {
      const response = await fundsApi.ledger(params)
      set({ transactions: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch ledger:', error)
      set({ isLoading: false })
    }
  },

  addFunds: async (data) => {
    set({ isLoading: true, error: null })
    try {
      await fundsApi.add(data)
      await useFundsStore.getState().fetchFunds()
      set({ isLoading: false })
      return true
    } catch (error) {
      set({ error: 'Failed to add funds', isLoading: false })
      console.error('Failed to add funds:', error)
      return false
    }
  },

  fetchHoldings: async () => {
    try {
      const response = await fundsApi.holdings()
      set({
        holdings: response.data.data,
        holdingsSummary: response.data.summary,
      })
    } catch (error) {
      console.error('Failed to fetch holdings:', error)
    }
  },

  setError: (error) => set({ error }),
}))
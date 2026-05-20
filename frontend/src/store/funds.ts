import { create } from 'zustand'
import { fundsApi } from '../services/api'
import type { Funds as FundsData, Transaction, Holding, HoldingsSummary } from '../types'
import { 
  normalizeFunds, 
  safeNumber, 
  safeString, 
  safeTimestamp,
  normalizeSymbol,
  normalizeExchange
} from '../utils/normalization'

export const DEFAULT_FUNDS: FundsData = {
  account_id: '',
  broker: '',
  balance: {
    available_cash: 0,
    used_margin: 0,
    total_balance: 0,
    currency: 'INR',
  },
  margin: {
    available_margin: 0,
    used_margin: 0,
    span_margin: 0,
    exposure_margin: 0,
    total_margin_used: 0,
  },
  limits: {
    daily_buy_power: 0,
    daily_sell_power: 0,
  },
  last_updated: new Date(0).toISOString(),
};

export const DEFAULT_HOLDINGS_SUMMARY: HoldingsSummary = {
  total_invested: 0,
  total_current_value: 0,
  total_pnl: 0,
  total_pnl_percent: 0,
};

export const normalizeTransaction = (raw: any): Transaction => {
  return {
    transaction_id: safeString(raw.transaction_id || raw._id),
    type: (raw.type || 'CREDIT').toUpperCase() as 'CREDIT' | 'DEBIT',
    amount: safeNumber(raw.amount),
    balance_after: safeNumber(raw.balance_after),
    description: safeString(raw.description),
    reference: safeString(raw.reference),
    timestamp: safeTimestamp(raw.timestamp),
  };
};

export const normalizeHolding = (raw: any): Holding => {
  return {
    symbol: normalizeSymbol(raw.symbol),
    quantity: safeNumber(raw.quantity),
    avg_buy_price: safeNumber(raw.avg_buy_price || raw.average_price),
    ltp: safeNumber(raw.ltp || raw.current_price),
    current_value: safeNumber(raw.current_value || raw.value),
    pnl: safeNumber(raw.pnl),
    pnl_percent: safeNumber(raw.pnl_percent),
    day_change: safeNumber(raw.day_change),
    day_change_percent: safeNumber(raw.day_change_percent),
    exchange: normalizeExchange(raw.exchange),
  };
};

interface FundsState {
  funds: FundsData
  transactions: Transaction[]
  holdings: Holding[]
  holdingsSummary: HoldingsSummary
  isLoading: boolean
  error: string | null

  fetchFunds: () => Promise<void>
  fetchLedger: (params?: { from_date?: string; to_date?: string; transaction_type?: string; page?: number; limit?: number }) => Promise<void>
  addFunds: (data: { amount: number; payment_method?: string; reference?: string }) => Promise<boolean>
  fetchHoldings: () => Promise<void>
  setError: (error: string | null) => void
}

export const useFundsStore = create<FundsState>((set) => ({
  funds: DEFAULT_FUNDS,
  transactions: [],
  holdings: [],
  holdingsSummary: DEFAULT_HOLDINGS_SUMMARY,
  isLoading: false,
  error: null,

  fetchFunds: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fundsApi.get()
      set({ funds: normalizeFunds(response.data.data) || DEFAULT_FUNDS, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch funds', isLoading: false })
      console.error('Failed to fetch funds:', error)
    }
  },

  fetchLedger: async (params = {}) => {
    set({ isLoading: true })
    try {
      const response = await fundsApi.ledger(params)
      const transactions = Array.isArray(response.data.data) 
        ? response.data.data.map(normalizeTransaction) 
        : [];
      set({ transactions, isLoading: false })
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
      const rawSummary = response.data.summary;
      set({
        holdings: Array.isArray(response.data.data) ? response.data.data.map(normalizeHolding) : [],
        holdingsSummary: {
          total_invested: safeNumber(rawSummary?.total_invested),
          total_current_value: safeNumber(rawSummary?.total_current_value),
          total_pnl: safeNumber(rawSummary?.total_pnl),
          total_pnl_percent: safeNumber(rawSummary?.total_pnl_percent),
        } || DEFAULT_HOLDINGS_SUMMARY,
      })
    } catch (error) {
      console.error('Failed to fetch holdings:', error)
    }
  },

  setError: (error) => set({ error }),
}))

export default useFundsStore
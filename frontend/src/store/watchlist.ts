import { create } from 'zustand'
import { watchlistApi, marketApi } from '../services/api'
import type { Watchlist, Quote } from '../types'
import { 
  safeString, 
  safeTimestamp, 
  normalizeSymbol, 
  safeNumber,
  normalizeTick
} from '../utils/normalization'

export const DEFAULT_WATCHLIST: Watchlist = {
  watchlist_id: '',
  name: '',
  symbols: [],
  created_at: new Date(0).toISOString(),
  updated_at: new Date(0).toISOString(),
  is_default: false,
};

export const normalizeWatchlist = (raw: any): Watchlist => {
  return {
    watchlist_id: safeString(raw?.watchlist_id || raw?._id),
    name: safeString(raw?.name),
    symbols: Array.isArray(raw?.symbols) ? raw.symbols.map(normalizeSymbol) : [],
    is_default: !!raw?.is_default,
    created_at: safeTimestamp(raw?.created_at),
    updated_at: safeTimestamp(raw?.updated_at),
  };
};

interface WatchlistState {
  watchlists: Watchlist[]
  activeWatchlist: Watchlist
  quotes: Record<string, Quote>
  isLoading: boolean
  error: string | null

  fetchWatchlists: () => Promise<void>
  setActiveWatchlist: (id: string) => Promise<void>
  createWatchlist: (data: { name: string; description?: string; symbols?: string[] }) => Promise<void>
  updateWatchlist: (id: string, data: { name?: string; description?: string }) => Promise<void>
  deleteWatchlist: (id: string) => Promise<void>
  addStocks: (id: string, symbols: string[]) => Promise<void>
  removeStock: (id: string, symbol: string) => Promise<void>
  fetchQuotes: (symbols: string[]) => Promise<void>
  updateQuote: (symbol: string, price: number, change: number, changePercent: number) => void
  clearError: () => void
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  watchlists: [],
  activeWatchlist: DEFAULT_WATCHLIST,
  quotes: {},
  isLoading: false,
  error: null,

  fetchWatchlists: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await watchlistApi.list()
      const watchlists = Array.isArray(response.data.data) 
        ? response.data.data.map(normalizeWatchlist) 
        : [];
      set({ watchlists, isLoading: false })

      if (watchlists.length > 0 && get().activeWatchlist.watchlist_id === '') {
        const defaultList = watchlists.find((w: Watchlist) => w.is_default) || watchlists[0]
        set({ activeWatchlist: defaultList })
        if (defaultList.symbols.length > 0) {
          get().fetchQuotes(defaultList.symbols)
        }
      }
    } catch (error) {
      console.error('Failed to fetch watchlists:', error)
      set({ error: 'Failed to fetch watchlists', isLoading: false })
    }
  },

  setActiveWatchlist: async (id: string) => {
    const watchlist = get().watchlists.find(w => w.watchlist_id === id)
    if (watchlist) {
      set({ activeWatchlist: watchlist })
      if (watchlist.symbols.length > 0) {
        await get().fetchQuotes(watchlist.symbols)
      } else {
        set({ quotes: {} })
      }
    }
  },

  createWatchlist: async (data) => {
    set({ isLoading: true })
    try {
      await watchlistApi.create(data)
      await get().fetchWatchlists()
    } catch (error) {
      console.error('Failed to create watchlist:', error)
      set({ error: 'Failed to create watchlist', isLoading: false })
    }
  },

  updateWatchlist: async (id, data) => {
    try {
      await watchlistApi.update(id, data)
      await get().fetchWatchlists()
    } catch (error) {
      console.error('Failed to update watchlist:', error)
      set({ error: 'Failed to update watchlist' })
    }
  },

  deleteWatchlist: async (id) => {
    try {
      await watchlistApi.delete(id)
      if (get().activeWatchlist.watchlist_id === id) {
        set({ activeWatchlist: DEFAULT_WATCHLIST })
      }
      await get().fetchWatchlists()
    } catch (error) {
      console.error('Failed to delete watchlist:', error)
      set({ error: 'Failed to delete watchlist' })
    }
  },

  addStocks: async (id, symbols) => {
    try {
      await watchlistApi.addStocks(id, { symbols })
      await get().fetchWatchlists()
      if (get().activeWatchlist.watchlist_id === id) {
        await get().fetchQuotes(symbols)
      }
    } catch (error) {
      console.error('Failed to add stocks:', error)
      set({ error: 'Failed to add stocks' })
    }
  },

  removeStock: async (id, symbol) => {
    try {
      await watchlistApi.removeStock(id, symbol)
      const newQuotes = { ...get().quotes }
      delete newQuotes[normalizeSymbol(symbol)]
      set({ quotes: newQuotes })
      await get().fetchWatchlists()
    } catch (error) {
      console.error('Failed to remove stock:', error)
      set({ error: 'Failed to remove stock' })
    }
  },

  fetchQuotes: async (symbols) => {
    if (symbols.length === 0) return
    try {
      const response = await marketApi.quotes(symbols.join(','))
      const newQuotes: Record<string, Quote> = { ...get().quotes }
      if (Array.isArray(response.data.data)) {
        response.data.data.forEach((quote: any) => {
          const normalized = normalizeTick(quote)
          if (normalized?.symbol) {
            newQuotes[normalized.symbol] = normalized as any
          }
        })
      }
      set({ quotes: newQuotes })
    } catch (error) {
      console.error('Failed to fetch quotes:', error)
    }
  },

  updateQuote: (symbol, price, change, changePercent) => {
    const normSymbol = normalizeSymbol(symbol)
    const currentQuote = get().quotes[normSymbol]
    if (currentQuote) {
      const newQuotes = { ...get().quotes }
      newQuotes[normSymbol] = {
        ...currentQuote,
        last_price: safeNumber(price),
        change: safeNumber(change),
        change_percent: safeNumber(changePercent),
        timestamp: new Date().toISOString(),
      }
      set({ quotes: newQuotes })
    }
  },

  clearError: () => set({ error: null }),
}))

export default useWatchlistStore
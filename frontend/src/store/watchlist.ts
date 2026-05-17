import { create } from 'zustand'
import { watchlistApi, marketApi } from '../services/api'
import type { Watchlist, Quote } from '../types'

interface WatchlistState {
  watchlists: Watchlist[]
  activeWatchlist: Watchlist | null
  quotes: Map<string, Quote>
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
  activeWatchlist: null,
  quotes: new Map(),
  isLoading: false,
  error: null,

  fetchWatchlists: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await watchlistApi.list()
      set({ watchlists: response.data.data, isLoading: false })

      if (response.data.data.length > 0 && !get().activeWatchlist) {
        const defaultList = response.data.data.find((w: Watchlist) => w.is_default) || response.data.data[0]
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
        set({ quotes: new Map() })
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
      if (get().activeWatchlist?.watchlist_id === id) {
        set({ activeWatchlist: null })
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
      if (get().activeWatchlist?.watchlist_id === id) {
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
      const newQuotes = new Map(get().quotes)
      newQuotes.delete(symbol)
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
      const newQuotes = new Map<string, Quote>()
      response.data.data.forEach((quote: Quote) => {
        newQuotes.set(quote.symbol, quote)
      })
      set({ quotes: newQuotes })
    } catch (error) {
      console.error('Failed to fetch quotes:', error)
    }
  },

  updateQuote: (symbol, price, change, changePercent) => {
    const currentQuote = get().quotes.get(symbol)
    if (currentQuote) {
      const newQuotes = new Map(get().quotes)
      newQuotes.set(symbol, {
        ...currentQuote,
        last_price: price,
        change,
        change_percent: changePercent,
        timestamp: new Date().toISOString(),
      })
      set({ quotes: newQuotes })
    }
  },

  clearError: () => set({ error: null }),
}))

export default useWatchlistStore
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { marketApi, dashboardApi } from '../services/api'
import { socketService } from '../services/websocket'
import { 
  normalizeTick, 
  normalizeTicks, 
  normalizeSymbol, 
  safeNumber, 
  safeTimestamp,
  safeString 
} from '../utils/normalization'

export interface TickData {
  symbol: string
  exchange: string
  ltp: number
  change: number
  change_percent: number
  volume: number
  bid: number
  ask: number
  high: number
  low: number
  open: number
  close: number
  timestamp: string
}

export interface Candle {
  symbol: string
  timeframe: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  value: number
  trades: number
}

export interface OrderBookEntry {
  price: number
  quantity: number
  orders: number
}

export interface MarketDepth {
  symbol: string
  exchange: string
  bids: OrderBookEntry[]
  asks: OrderBookEntry[]
  spread: number
  spread_percent: number
  total_bid_quantity: number
  total_ask_quantity: number
  timestamp: string
}

export interface IndicatorData {
  symbol: string
  timestamp: string
  ema_9?: number
  ema_20?: number
  ema_50?: number
  ema_200?: number
  rsi_14?: number
  macd_line?: number
  macd_signal?: number
  macd_histogram?: number
  vwap?: number
  supertrend?: number
  supertrend_direction?: string
  bb_upper?: number
  bb_middle?: number
  bb_lower?: number
  sma_20?: number
  atr_14?: number
}

export interface MarketStatus {
  exchange: string
  status: 'OPEN' | 'CLOSED'
  session: 'PRE-MARKET' | 'REGULAR' | 'POST-MARKET' | 'CLOSED'
  next_session: string
  closes_in_seconds: number
  timestamp: string
}

export interface IndexData {
  symbol: string
  value: number
  change: number
  change_percent: number
}

export interface Quote {
  symbol: string
  exchange: string
  last_price: number
  change: number
  change_percent: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  value: number
  vwap: number
  high_52w: number
  low_52w: number
  avg_volume_20d: number
  timestamp: string
}

export const DEFAULT_MARKET_STATUS: MarketStatus = {
  exchange: 'NSE',
  status: 'CLOSED',
  session: 'CLOSED',
  next_session: '',
  closes_in_seconds: 0,
  timestamp: new Date(0).toISOString(),
};

export const normalizeMarketStatus = (raw: any): MarketStatus => {
  return {
    exchange: safeString(raw?.exchange, 'NSE'),
    status: (raw?.status || 'CLOSED').toUpperCase() as any,
    session: (raw?.session || 'CLOSED').toUpperCase() as any,
    next_session: safeString(raw?.next_session),
    closes_in_seconds: safeNumber(raw?.closes_in_seconds),
    timestamp: safeTimestamp(raw?.timestamp),
  };
};

export const normalizeIndexData = (raw: any): IndexData => {
  return {
    symbol: normalizeSymbol(raw?.symbol),
    value: safeNumber(raw?.value),
    change: safeNumber(raw?.change),
    change_percent: safeNumber(raw?.change_percent),
  };
};

interface MarketState {
  quotes: Record<string, TickData>
  prices: Record<string, { price: number; change_percent_24h: number }>
  candles: Record<string, Candle[]>
  currentCandles: Record<string, Candle>
  depth: Record<string, MarketDepth>
  indicators: Record<string, IndicatorData>
  marketStatus: MarketStatus
  indices: IndexData[]
  topGainers: TickData[]
  topLosers: TickData[]
  subscribedSymbols: string[]
  watchlist: string[]
  selectedSymbol: string | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  lastUpdated: string

  initializeMarketData: () => Promise<void>
  subscribeToSymbol: (symbol: string) => void
  unsubscribeFromSymbol: (symbol: string) => void
  fetchQuotes: (symbols: string[]) => Promise<void>
  fetchCandles: (symbol: string, timeframe: string, limit?: number) => Promise<Candle[] | null>
  fetchDepth: (symbol: string) => Promise<MarketDepth | null>
  fetchIndicators: (symbol: string) => Promise<IndicatorData | null>
  fetchMarketStatus: () => Promise<void>
  fetchMarketOverview: () => Promise<void>
  updateTick: (tick: TickData) => void
  updateBatchedTicks: (ticks: TickData[]) => void
  updateDepth: (depth: MarketDepth) => void
  updateIndicators: (indicators: IndicatorData) => void
  updateCandle: (candle: Candle) => void
  updatePrice: (symbol: string, price: number, change: number, changePercent: number) => void
  setSelectedSymbol: (symbol: string | null) => void
  addToWatchlist: (symbol: string) => void
  removeFromWatchlist: (symbol: string) => void
  clearError: () => void
  reset: () => void
  cleanup: () => void
}

const initialState = {
  quotes: {} as Record<string, TickData>,
  prices: {} as Record<string, { price: number; change_percent_24h: number }>,
  candles: {} as Record<string, Candle[]>,
  currentCandles: {} as Record<string, Candle>,
  depth: {} as Record<string, MarketDepth>,
  indicators: {} as Record<string, IndicatorData>,
  marketStatus: DEFAULT_MARKET_STATUS,
  indices: [] as IndexData[],
  topGainers: [] as TickData[],
  topLosers: [] as TickData[],
  subscribedSymbols: [] as string[],
  watchlist: ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'],
  selectedSymbol: null as string | null,
  isLoading: false,
  isInitialized: false,
  error: null as string | null,
  lastUpdated: new Date(0).toISOString(),
}

export const useMarketStore = create<MarketState>()(
  persist(
    (set, get) => ({
      ...initialState,

      initializeMarketData: async () => {
        if (get().isInitialized && get().lastUpdated !== new Date(0).toISOString()) return
        
        set({ isLoading: true, error: null })
        try {
          const status = await marketApi.getMarketStatus()
          set({ marketStatus: normalizeMarketStatus(status.data.data) })
          
          const overview = await marketApi.getMarketOverview()
          const data = overview.data.data
          set({ 
            indices: Array.isArray(data?.indices) ? data.indices.map(normalizeIndexData) : [],
            topGainers: Array.isArray(data?.top_gainers) ? data.top_gainers.map(normalizeTick) : [],
            topLosers: Array.isArray(data?.top_losers) ? data.top_losers.map(normalizeTick) : []
          })
          
          const watchlist = await marketApi.getWatchlist()
          const quotes: Record<string, TickData> = {}
          const prices: Record<string, { price: number; change_percent_24h: number }> = {}
          
          if (Array.isArray(watchlist?.data?.data)) {
            watchlist.data.data.forEach((tick: any) => {
              const normalized = normalizeTick(tick)
              if (normalized?.symbol) {
                quotes[normalized.symbol] = normalized as any
                prices[normalized.symbol] = { price: normalized.last_price || 0, change_percent_24h: normalized.change_percent || 0 }
              }
            })
          }
          
          set({ 
            quotes, 
            prices, 
            isLoading: false, 
            isInitialized: true,
            lastUpdated: new Date().toISOString() 
          })
        } catch (error) {
          console.error('Failed to initialize market data:', error)
          set({ 
            error: 'Failed to initialize market data', 
            isLoading: false,
            isInitialized: true 
          })
        }
      },

      subscribeToSymbol: (symbol: string) => {
        const { subscribedSymbols } = get()
        const normalizedSymbol = normalizeSymbol(symbol)
        if (subscribedSymbols.includes(normalizedSymbol)) return
        
        socketService.emit('subscribe_market', { symbols: [normalizedSymbol], channel: 'quotes' })
        set({ subscribedSymbols: [...subscribedSymbols, normalizedSymbol] })
      },

      unsubscribeFromSymbol: (symbol: string) => {
        const { subscribedSymbols } = get()
        const normalizedSymbol = normalizeSymbol(symbol)
        if (!subscribedSymbols.includes(normalizedSymbol)) return
        
        socketService.emit('unsubscribe_market', { symbols: [normalizedSymbol] })
        set({ subscribedSymbols: subscribedSymbols.filter(s => s !== normalizedSymbol) })
      },

      fetchQuotes: async (symbols: string[]) => {
        if (symbols.length === 0) return
        set({ isLoading: true })
        try {
          const response = await marketApi.quotes(symbols.join(','))
          const newQuotes: Record<string, TickData> = {}
          const newPrices: Record<string, { price: number; change_percent_24h: number }> = {}
          
          if (Array.isArray(response?.data?.data)) {
            response.data.data.forEach((quote: any) => {
              const normalized = normalizeTick(quote)
              if (normalized?.symbol) {
                newQuotes[normalized.symbol] = normalized as any
                newPrices[normalized.symbol] = { 
                  price: normalized.last_price || 0, 
                  change_percent_24h: normalized.change_percent || 0 
                }
              }
            })
          }
          
          set((state) => ({ 
            quotes: { ...state.quotes, ...newQuotes }, 
            prices: { ...state.prices, ...newPrices }, 
            isLoading: false, 
            lastUpdated: new Date().toISOString() 
          }))
        } catch (error) {
          console.error('Failed to fetch quotes:', error)
          set({ error: 'Failed to fetch market data', isLoading: false })
        }
      },

      fetchCandles: async (symbol, timeframe, limit = 100) => {
        try {
          const response = await marketApi.candles({ symbol, timeframe, limit })
          const candleData = response?.data?.data?.candles
          if (candleData) {
            set((state) => ({
              candles: { ...state.candles, [`${normalizeSymbol(symbol)}:${timeframe}`]: candleData },
            }))
          }
          return candleData ?? null
        } catch (error) {
          console.error('Failed to fetch candles:', error)
          return null
        }
      },

      fetchDepth: async (symbol) => {
        try {
          const response = await marketApi.depth(symbol)
          return response?.data?.data ?? null
        } catch (error) {
          console.error('Failed to fetch market depth:', error)
          return null
        }
      },

      fetchIndicators: async (symbol) => {
        try {
          const response = await marketApi.indicators(symbol)
          return response?.data?.data ?? null
        } catch (error) {
          console.error('Failed to fetch indicators:', error)
          return null
        }
      },

      fetchMarketStatus: async () => {
        try {
          const response = await marketApi.getMarketStatus()
          set({ marketStatus: normalizeMarketStatus(response?.data?.data) })
        } catch (error) {
          console.error('Failed to fetch market status:', error)
        }
      },

      fetchMarketOverview: async () => {
        set({ isLoading: true })
        try {
          const response = await marketApi.getMarketOverview()
          const data = response?.data?.data
          set({ 
            indices: Array.isArray(data?.indices) ? data.indices.map(normalizeIndexData) : [],
            topGainers: Array.isArray(data?.top_gainers) ? data.top_gainers.map(normalizeTick) : [],
            topLosers: Array.isArray(data?.top_losers) ? data.top_losers.map(normalizeTick) : [],
            marketStatus: normalizeMarketStatus(data?.market_status),
            isLoading: false 
          })
        } catch (error) {
          console.error('Failed to fetch market overview:', error)
          set({ error: 'Failed to fetch market overview', isLoading: false })
        }
      },

      updateTick: (tick: TickData) => {
        const normalized = normalizeTick(tick)
        if (!normalized?.symbol) return
        set((state) => {
          const newQuotes = { ...state.quotes }
          newQuotes[normalized.symbol] = normalized as any
          return { 
            quotes: newQuotes, 
            prices: {
              ...state.prices,
              [normalized.symbol]: { price: normalized.last_price || 0, change_percent_24h: normalized.change_percent || 0 }
            },
            lastUpdated: new Date().toISOString() 
          }
        })
      },

      updateBatchedTicks: (ticks: TickData[]) => {
        if (!Array.isArray(ticks) || ticks.length === 0) return
        set((state) => {
          const newQuotes = { ...state.quotes }
          const newPrices = { ...state.prices }
          
          ticks.forEach(tick => {
            const normalized = normalizeTick(tick)
            if (normalized?.symbol) {
              newQuotes[normalized.symbol] = normalized as any
              newPrices[normalized.symbol] = { 
                price: normalized.last_price || 0, 
                change_percent_24h: normalized.change_percent || 0 
              }
            }
          })
          
          return { 
            quotes: newQuotes, 
            prices: newPrices, 
            lastUpdated: new Date().toISOString() 
          }
        })
      },

      updateDepth: (depth: MarketDepth) => {
        if (!depth?.symbol) return
        set((state) => ({
          depth: { ...state.depth, [normalizeSymbol(depth.symbol)]: depth }
        }))
      },

      updateIndicators: (indicators: IndicatorData) => {
        if (!indicators?.symbol) return
        set((state) => ({
          indicators: { ...state.indicators, [normalizeSymbol(indicators.symbol)]: indicators }
        }))
      },

      updateCandle: (candle: Candle) => {
        if (!candle?.symbol) return
        set((state) => ({
          currentCandles: { ...state.currentCandles, [normalizeSymbol(candle.symbol)]: candle }
        }))
      },

      updatePrice: (symbol, price, change, changePercent) => {
        if (!symbol) return
        const normSymbol = normalizeSymbol(symbol)
        const currentQuote = get().quotes[normSymbol]
        if (currentQuote) {
          const newQuotes = { ...get().quotes }
          newQuotes[normSymbol] = {
            ...currentQuote,
            ltp: safeNumber(price),
            change: safeNumber(change),
            change_percent: safeNumber(changePercent),
            timestamp: new Date().toISOString(),
          }
          set({ quotes: newQuotes })
        }
        set((state) => ({
          prices: {
            ...state.prices,
            [normSymbol]: { price: safeNumber(price), change_percent_24h: safeNumber(changePercent) },
          },
          lastUpdated: new Date().toISOString()
        }))
      },

      setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol ? normalizeSymbol(symbol) : null }),

      addToWatchlist: (symbol: string) => {
        const { watchlist } = get()
        const normalized = normalizeSymbol(symbol)
        if (!watchlist.includes(normalized)) {
          set({ watchlist: [...watchlist, normalized] })
        }
      },

      removeFromWatchlist: (symbol: string) => {
        const { watchlist } = get()
        const normalized = normalizeSymbol(symbol)
        set({ watchlist: watchlist.filter(s => s !== normalized) })
      },

      clearError: () => set({ error: null }),

      reset: () => set(initialState),

      cleanup: () => {
        const { subscribedSymbols } = get()
        subscribedSymbols.forEach(symbol => {
          socketService.emit('unsubscribe_market', { symbols: [symbol] })
        })
        set({
          quotes: {},
          candles: {},
          currentCandles: {},
          depth: {},
          indicators: {},
          subscribedSymbols: [],
        })
      },
    }),
    {
      name: 'market-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        watchlist: state.watchlist,
        selectedSymbol: state.selectedSymbol,
        isInitialized: state.isInitialized,
      }),
    }
  )
)

export default useMarketStore
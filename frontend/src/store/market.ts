import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { marketApi, dashboardApi } from '../services/api'
import { socketService } from '../services/websocket'

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

interface MarketState {
  quotes: Record<string, TickData>
  prices: Record<string, { price: number; change_percent_24h: number }>
  candles: Record<string, Candle[]>
  currentCandles: Record<string, Candle>
  depth: Record<string, MarketDepth>
  indicators: Record<string, IndicatorData>
  marketStatus: MarketStatus | null
  indices: IndexData[]
  topGainers: TickData[]
  topLosers: TickData[]
  subscribedSymbols: string[]
  watchlist: string[]
  selectedSymbol: string | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  lastUpdated: string | null

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
  marketStatus: null as MarketStatus | null,
  indices: [] as IndexData[],
  topGainers: [] as TickData[],
  topLosers: [] as TickData[],
  subscribedSymbols: [] as string[],
  watchlist: ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'],
  selectedSymbol: null as string | null,
  isLoading: false,
  isInitialized: false,
  error: null as string | null,
  lastUpdated: null as string | null,
}

export const useMarketStore = create<MarketState>()(
  persist(
    (set, get) => ({
      ...initialState,

      initializeMarketData: async () => {
        if (get().isInitialized && get().lastUpdated) return
        
        set({ isLoading: true, error: null })
        try {
          const status = await marketApi.getMarketStatus()
          set({ marketStatus: status.data.data })
          
          const overview = await marketApi.getMarketOverview()
          const data = overview.data.data
          set({ 
            indices: data?.indices ?? [],
            topGainers: data?.top_gainers ?? [],
            topLosers: data?.top_losers ?? []
          })
          
          const watchlist = await marketApi.getWatchlist()
          const quotes: Record<string, TickData> = {}
          const prices: Record<string, { price: number; change_percent_24h: number }> = {}
          
          if (Array.isArray(watchlist?.data?.data)) {
            watchlist.data.data.forEach((tick: TickData) => {
              if (tick?.symbol) {
                quotes[tick.symbol] = tick
                prices[tick.symbol] = { price: tick.ltp ?? 0, change_percent_24h: tick.change_percent ?? 0 }
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
        if (subscribedSymbols.includes(symbol)) return
        
        socketService.emit('subscribe_market', { symbols: [symbol], channel: 'quotes' })
        set({ subscribedSymbols: [...subscribedSymbols, symbol] })
      },

      unsubscribeFromSymbol: (symbol: string) => {
        const { subscribedSymbols } = get()
        if (!subscribedSymbols.includes(symbol)) return
        
        socketService.emit('unsubscribe_market', { symbols: [symbol] })
        set({ subscribedSymbols: subscribedSymbols.filter(s => s !== symbol) })
      },

      fetchQuotes: async (symbols: string[]) => {
        if (symbols.length === 0) return
        set({ isLoading: true })
        try {
          const response = await marketApi.quotes(symbols.join(','))
          const newQuotes: Record<string, TickData> = {}
          const newPrices: Record<string, { price: number; change_percent_24h: number }> = {}
          
          if (Array.isArray(response?.data?.data)) {
            response.data.data.forEach((quote: TickData) => {
              if (quote?.symbol) {
                newQuotes[quote.symbol] = quote
                newPrices[quote.symbol] = { 
                  price: quote.ltp ?? 0, 
                  change_percent_24h: quote.change_percent ?? 0 
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
              candles: { ...state.candles, [`${symbol}:${timeframe}`]: candleData },
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
          set({ marketStatus: response?.data?.data })
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
            indices: data?.indices ?? [],
            topGainers: data?.top_gainers ?? [],
            topLosers: data?.top_losers ?? [],
            marketStatus: data?.market_status,
            isLoading: false 
          })
        } catch (error) {
          console.error('Failed to fetch market overview:', error)
          set({ error: 'Failed to fetch market overview', isLoading: false })
        }
      },

      updateTick: (tick: TickData) => {
        if (!tick?.symbol) return
        set((state) => {
          const newQuotes = { ...state.quotes }
          newQuotes[tick.symbol] = tick
          return { 
            quotes: newQuotes, 
            prices: {
              ...state.prices,
              [tick.symbol]: { price: tick.ltp ?? 0, change_percent_24h: tick.change_percent ?? 0 }
            },
            lastUpdated: new Date().toISOString() 
          }
        })
      },

      updateDepth: (depth: MarketDepth) => {
        if (!depth?.symbol) return
        set((state) => ({
          depth: { ...state.depth, [depth.symbol]: depth }
        }))
      },

      updateIndicators: (indicators: IndicatorData) => {
        if (!indicators?.symbol) return
        set((state) => ({
          indicators: { ...state.indicators, [indicators.symbol]: indicators }
        }))
      },

      updateCandle: (candle: Candle) => {
        if (!candle?.symbol) return
        set((state) => ({
          currentCandles: { ...state.currentCandles, [candle.symbol]: candle }
        }))
      },

      updatePrice: (symbol, price, change, changePercent) => {
        if (!symbol) return
        const currentQuote = get().quotes[symbol]
        if (currentQuote) {
          const newQuotes = { ...get().quotes }
          newQuotes[symbol] = {
            ...currentQuote,
            ltp: price,
            change,
            change_percent: changePercent,
            timestamp: new Date().toISOString(),
          }
          set({ quotes: newQuotes })
        }
        set((state) => ({
          prices: {
            ...state.prices,
            [symbol]: { price, change_percent_24h: changePercent },
          },
          lastUpdated: new Date().toISOString()
        }))
      },

      setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),

      addToWatchlist: (symbol: string) => {
        const { watchlist } = get()
        if (!watchlist.includes(symbol)) {
          set({ watchlist: [...watchlist, symbol] })
        }
      },

      removeFromWatchlist: (symbol: string) => {
        const { watchlist } = get()
        set({ watchlist: watchlist.filter(s => s !== symbol) })
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
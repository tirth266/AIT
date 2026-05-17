import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { tradingApi } from '../services/api'
import type { 
  Order, Position, Trade, MarginInfo, PnLData, 
  Portfolio, MarketQuote, CreateOrderRequest, DayPnL 
} from '../types'

interface TradingState {
  orders: Order[]
  positions: Position[]
  trades: Trade[]
  
  currentQuote: MarketQuote | null
  quotes: Record<string, MarketQuote>
  
  margin: MarginInfo | null
  pnl: PnLData | null
  dayPnL: DayPnL | null
  portfolio: Portfolio | null
  
  engineStatus: 'stopped' | 'running' | 'loading'
  
  isLoadingOrders: boolean
  isLoadingPositions: boolean
  isLoadingPnL: boolean
  isSubmittingOrder: boolean
  
  isInitialized: boolean
  error: string | null
  
  fetchOrders: (params?: { status?: string; symbol?: string; mode?: string }) => Promise<void>
  createOrder: (order: CreateOrderRequest) => Promise<Order | null>
  cancelOrder: (orderId: string) => Promise<boolean>
  modifyOrder: (orderId: string, data: { price?: number; quantity?: number; trigger_price?: number }) => Promise<boolean>
  
  fetchPositions: (params?: { status?: string; symbol?: string; mode?: string }) => Promise<void>
  fetchOpenPositions: (params?: { mode?: string }) => Promise<void>
  exitPosition: (positionId: string, exitPrice?: number, quantity?: number) => Promise<boolean>
  
  fetchPnL: (mode?: string) => Promise<void>
  fetchDayPnL: (mode?: string) => Promise<void>
  fetchMargin: () => Promise<void>
  fetchPortfolio: (mode?: string) => Promise<void>
  
  fetchQuote: (symbol: string) => Promise<MarketQuote | null>
  fetchQuotes: (symbols?: string) => Promise<void>
  
  updateOrderFromWS: (order: Order) => void
  updatePositionFromWS: (position: Position) => void
  updatePnLFromWS: (pnl: PnLData) => void
  updateQuoteFromWS: (quote: MarketQuote) => void
  
  clearError: () => void
  setInitialized: (initialized: boolean) => void
  reset: () => void
}

const initialState = {
  orders: [] as Order[],
  positions: [] as Position[],
  trades: [] as Trade[],
  currentQuote: null as MarketQuote | null,
  quotes: {} as Record<string, MarketQuote>,
  margin: null as MarginInfo | null,
  pnl: null as PnLData | null,
  dayPnL: null as DayPnL | null,
  portfolio: null as Portfolio | null,
  engineStatus: 'stopped' as const,
  isLoadingOrders: false,
  isLoadingPositions: false,
  isLoadingPnL: false,
  isSubmittingOrder: false,
  isInitialized: false,
  error: null as string | null,
}

export const useTradingEngineStore = create<TradingState>()(
  persist(
    (set, get) => ({
      ...initialState,

      fetchOrders: async (params = {}) => {
        set({ isLoadingOrders: true, error: null })
        try {
          const response = await tradingApi.listOrders(params)
          set({ 
            orders: Array.isArray(response?.data?.orders) ? response.data.orders : [],
            isLoadingOrders: false 
          })
        } catch (error) {
          console.error('Failed to fetch orders:', error)
          set({ error: 'Failed to fetch orders', isLoadingOrders: false })
        }
      },
      
      createOrder: async (orderData) => {
        set({ isSubmittingOrder: true, error: null })
        try {
          const response = await tradingApi.createOrder(orderData)
          const newOrder = response?.data?.order
          if (newOrder) {
            set((state) => ({
              orders: [newOrder, ...(Array.isArray(state.orders) ? state.orders : [])],
              isSubmittingOrder: false,
            }))
          }
          return newOrder ?? null
        } catch (error: unknown) {
          const err = error as { response?: { data?: { message?: string } } }
          const errorMessage = err?.response?.data?.message || 'Failed to place order'
          console.error('Failed to create order:', error)
          set({ error: errorMessage, isSubmittingOrder: false })
          return null
        }
      },
      
      cancelOrder: async (orderId) => {
        set({ isLoadingOrders: true })
        try {
          await tradingApi.cancelOrder(orderId)
          set((state) => ({
            orders: Array.isArray(state.orders)
              ? state.orders.map((o) =>
                  o?.order_id === orderId ? { ...o, status: 'CANCELLED' as const } : o
                )
              : [],
            isLoadingOrders: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to cancel order:', error)
          set({ error: 'Failed to cancel order', isLoadingOrders: false })
          return false
        }
      },
      
      modifyOrder: async (orderId, data) => {
        set({ isLoadingOrders: true })
        try {
          await tradingApi.modifyOrder(orderId, data)
          set((state) => ({
            orders: Array.isArray(state.orders)
              ? state.orders.map((o) =>
                  o?.order_id === orderId ? { ...o, ...data } : o
                )
              : [],
            isLoadingOrders: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to modify order:', error)
          set({ error: 'Failed to modify order', isLoadingOrders: false })
          return false
        }
      },
      
      fetchPositions: async (params = {}) => {
        set({ isLoadingPositions: true, error: null })
        try {
          const response = await tradingApi.listPositions(params)
          set({ 
            positions: Array.isArray(response?.data?.positions) ? response.data.positions : [],
            isLoadingPositions: false 
          })
        } catch (error) {
          console.error('Failed to fetch positions:', error)
          set({ error: 'Failed to fetch positions', isLoadingPositions: false })
        }
      },
      
      fetchOpenPositions: async (params = {}) => {
        set({ isLoadingPositions: true, error: null })
        try {
          const response = await tradingApi.getOpenPositions(params)
          set({ 
            positions: Array.isArray(response?.data?.positions) ? response.data.positions : [],
            isLoadingPositions: false 
          })
        } catch (error) {
          console.error('Failed to fetch open positions:', error)
          set({ error: 'Failed to fetch open positions', isLoadingPositions: false })
        }
      },
      
      exitPosition: async (positionId, exitPrice, quantity) => {
        set({ isLoadingPositions: true })
        try {
          await tradingApi.exitPosition(positionId, { exit_price: exitPrice, quantity })
          set((state) => ({
            positions: Array.isArray(state.positions)
              ? state.positions.filter((p) => p?.position_id !== positionId)
              : [],
            isLoadingPositions: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to exit position:', error)
          set({ error: 'Failed to exit position', isLoadingPositions: false })
          return false
        }
      },
      
      fetchPnL: async (mode = 'paper') => {
        set({ isLoadingPnL: true })
        try {
          const response = await tradingApi.getPnL({ mode })
          set({ pnl: response?.data, isLoadingPnL: false })
        } catch (error) {
          console.error('Failed to fetch P&L:', error)
          set({ isLoadingPnL: false })
        }
      },
      
      fetchDayPnL: async (mode = 'paper') => {
        try {
          const response = await tradingApi.getDayPnL({ mode })
          set({ dayPnL: response?.data })
        } catch (error) {
          console.error('Failed to fetch day P&L:', error)
        }
      },
      
      fetchMargin: async () => {
        try {
          const response = await tradingApi.getMargin()
          set({ margin: response?.data })
        } catch (error) {
          console.error('Failed to fetch margin:', error)
        }
      },
      
      fetchPortfolio: async (mode = 'paper') => {
        try {
          const response = await tradingApi.getPortfolio({ mode })
          set({ portfolio: response?.data })
        } catch (error) {
          console.error('Failed to fetch portfolio:', error)
        }
      },
      
      fetchQuote: async (symbol) => {
        try {
          const response = await tradingApi.getMarketQuotes(symbol)
          const quote = response?.data?.quotes?.[symbol]
          if (quote) {
            set((state) => ({
              currentQuote: quote,
              quotes: { ...state.quotes, [symbol]: quote }
            }))
            return quote
          }
          return null
        } catch (error) {
          console.error('Failed to fetch quote:', error)
          return null
        }
      },
      
      fetchQuotes: async (symbols) => {
        try {
          const response = await tradingApi.getMarketQuotes(symbols)
          set((state) => ({
            quotes: { ...state.quotes, ...(response?.data?.quotes ?? {}) }
          }))
        } catch (error) {
          console.error('Failed to fetch quotes:', error)
        }
      },
      
      updateOrderFromWS: (order) => {
        if (!order?.order_id) return
        set((state) => ({
          orders: Array.isArray(state.orders)
            ? state.orders.map((o) => o?.order_id === order.order_id ? order : o)
            : []
        }))
      },
      
      updatePositionFromWS: (position) => {
        if (!position?.position_id) return
        set((state) => ({
          positions: Array.isArray(state.positions)
            ? state.positions.some(p => p?.position_id === position.position_id)
              ? state.positions.map((p) => p?.position_id === position.position_id ? position : p)
              : [...state.positions, position]
            : [position]
        }))
      },
      
      updatePnLFromWS: (pnl) => {
        set({ pnl })
      },
      
      updateQuoteFromWS: (quote) => {
        if (!quote?.symbol) return
        set((state) => ({
          currentQuote: quote,
          quotes: { ...state.quotes, [quote.symbol]: quote }
        }))
      },
      
      clearError: () => set({ error: null }),
      
      setInitialized: (initialized) => set({ isInitialized: initialized }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'trading-engine-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        engineStatus: state.engineStatus,
        isInitialized: state.isInitialized,
      }),
    }
  )
)

export default useTradingEngineStore